"""
Bone Fracture Detection Model Training Script
Fixed for local execution with proper error handling
"""

import numpy as np
import pandas as pd
import os
import copy
import torchvision
import torch
from torch import nn
import gc
import cv2
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import random
from torchvision.transforms import v2
from torchvision.utils import draw_bounding_boxes
from PIL import Image
from pathlib import Path

# Configuration
BS = 12
LR = 0.0001
EPOCHS = 5
IS = 224
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# Model output directory (changed from Kaggle path)
MODEL_OUTPUT_DIR = Path('./trained_models')
MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

num_classes = 8
classes = {
    0: 'elbow positive',
    1: 'fingers positive',
    2: 'forearm fracture',
    3: 'humerus fracture',
    4: 'humerus',
    5: 'shoulder fracture',
    6: 'wrist positive',
    7: 'no fracture'
}

sub_paths = {
    'primaries': ['/train', '/valid', '/test'],
    'images': ['/train/images', '/valid/images', '/test/images'],
    'labels': ['/train/labels', '/valid/labels', '/test/labels'],
}


def import_boxes(list_data):
    """
    Convert text data in label files to functional dictionaries.
    Given a list from a read file, converts and returns a dictionary
    with correlated label and coordinate data.
    """
    # Convert strings to ints and floats
    converted = []
    for item in list_data:
        if len(item) == 1:
            converted.append(int(float(item)))
        else:
            converted.append(float(item))
    
    # Initialize variables
    boxes = {'labels': [], 'coords': []}
    i = -1
    neg_len = -(len(converted))
    temp_list = []
    
    # Convert list to a functional dictionary of labels and coords
    while i >= neg_len:
        if type(converted[i]) == int:
            boxes['labels'].insert(0, converted[i])
            boxes['coords'].insert(0, temp_list[::-1])
            temp_list = []
        else:
            temp_list.append(converted[i])
        i -= 1
    
    return boxes


class ImageDataset(torch.utils.data.Dataset):
    def __init__(self, root, transform=None, mode='train'):
        self.transform = transform
        self.mode = mode
        self.root = root
        
        # Build file paths
        images_path = f"{root}/{mode}/images"
        if not os.path.exists(images_path):
            raise ValueError(f"Images path does not exist: {images_path}")
        
        self.files = [
            f"{images_path}/{name}" 
            for name in os.listdir(images_path) 
            if name.endswith(".jpg")
        ]
        
        self.labels = {}
        self.boxes = {}
        
        assert len(self.files) > 0, f"No images found in {images_path}!"
        print(f"Loaded {len(self.files)} images for {mode} set")

    def get_image(self, index):
        try:
            img = Image.open(self.files[index]).convert('RGB')
            item = self.transform(img)
            
            # Ensure 3 channels
            if item.shape[0] != 3:
                item = item.repeat(3, 1, 1)
            
            return item
        except Exception as e:
            print(f"Error loading image {self.files[index]}: {e}")
            raise
    
    def get_annot(self, index):
        labels = []
        boxes = []
        
        text_file = self.files[index].replace(".jpg", ".txt").replace("images", "labels")
        
        if not os.path.exists(text_file):
            # No annotation file - assume no fracture
            labels.append(7)
            boxes.append([1, 1, 2, 2])
        else:
            with open(text_file, mode="r") as f:
                lines = f.readlines()
                
                if len(lines) == 0:
                    # Empty annotation - no fracture
                    labels.append(7)
                    boxes.append([1, 1, 2, 2])
                else:
                    for line in lines:
                        values = [value for value in line.split()]
                        bboxes = import_boxes(values)
                        
                        # Remove any odd boxes from poor labeling data
                        for j, box in enumerate(bboxes['coords']):
                            if len(box) % 4 != 0:
                                # Clean up duplicate values
                                cleaned = [val for i, val in enumerate(box) if val not in box[:i]]
                                if len(cleaned) % 2 != 0:
                                    cleaned.pop()
                                bboxes['coords'][j] = cleaned
                        
                        # Convert bbox dimensions to fit the transformed image
                        for i in range(len(bboxes['labels'])):
                            coords = bboxes['coords'][i]
                            
                            if len(coords) == 0 or (len(coords) == 1 and len(coords) % 2 == 1):
                                # Invalid coords
                                labels.append(7)
                                boxes.append([1, 1, 2, 2])
                            else:
                                if len(coords) % 2 == 1:
                                    coords.pop()
                                
                                # Get image dimensions
                                img_tensor = self.get_image(index)
                                
                                coords_tensor = torch.reshape(
                                    torch.FloatTensor(coords),
                                    (int(len(coords) / 2), 2)
                                )
                                
                                size = torch.tensor([
                                    img_tensor.shape[2],  # width
                                    img_tensor.shape[1]   # height
                                ])
                                
                                min_coords = torch.min(coords_tensor, dim=0).values * size
                                max_coords = torch.max(coords_tensor, dim=0).values * size
                                box = torch.cat((min_coords, max_coords), dim=0).tolist()
                                
                                labels.append(bboxes['labels'][i])
                                boxes.append(box)

        annot = {
            'labels': torch.Tensor(labels).long(),
            'boxes': torch.Tensor(boxes).float()  # Changed to float for proper bbox handling
        }
        
        return annot

    def __len__(self):
        return len(self.files)
    
    def __getitem__(self, index):
        image = self.get_image(index)
        annot = self.get_annot(index)
        return image, annot

    def collate_fn(self, batch):
        return tuple(zip(*batch))


def train_cycle(model, dataloader, optimizer):
    """Training cycle for one epoch"""
    model.train()
    train_loss = 0.0
    
    progress_bar = tqdm(dataloader, desc="Training")
    
    for images, targets in progress_bar:
        # Move to device
        images = [img.to(DEVICE) for img in images]
        targets = [
            {
                key: (
                    torch.Tensor(value).long().to(DEVICE) 
                    if isinstance(value, list) 
                    else value.to(DEVICE)
                ) 
                for key, value in elements.items()
            } 
            for elements in targets
        ]
        
        optimizer.zero_grad()
        
        # Forward pass
        losses = model(images, targets)
        
        # Calculate total loss
        loss = sum(loss_value for loss_value in losses.values())
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
        
        # Update progress bar
        progress_bar.set_postfix({'loss': loss.item()})
    
    # Cleanup
    del images, targets
    gc.collect()
    torch.cuda.empty_cache()
    
    return train_loss / len(dataloader)


def eval_cycle(model, dataloader):
    """Evaluation cycle"""
    model.train()  # Keep in train mode for loss calculation
    val_loss = 0.0
    
    progress_bar = tqdm(dataloader, desc="Validation")
    
    with torch.no_grad():
        for images, targets in progress_bar:
            # Move to device
            images = [img.to(DEVICE) for img in images]
            targets = [
                {
                    key: (
                        torch.Tensor(value).long().to(DEVICE) 
                        if isinstance(value, list) 
                        else value.to(DEVICE)
                    ) 
                    for key, value in elements.items()
                } 
                for elements in targets
            ]
            
            # Forward pass
            losses = model(images, targets)
            loss = sum(loss_value for loss_value in losses.values())
            
            val_loss += loss.item()
            
            # Update progress bar
            progress_bar.set_postfix({'loss': loss.item()})
    
    # Cleanup
    del images, targets
    gc.collect()
    torch.cuda.empty_cache()
    
    return val_loss / len(dataloader)


def model_testing(model, testset, num_samples=5):
    """Test the model on random samples from test set"""
    model.eval()
    
    print(f"\nTesting model on {num_samples} random samples...")
    
    for _ in range(num_samples):
        idx = random.randint(0, len(testset) - 1)
        test_img, test_tar = testset[idx]
        
        with torch.no_grad():
            pred = model(test_img.unsqueeze(0).to(DEVICE))
        
        # Apply NMS
        keep_indices = torchvision.ops.nms(
            pred[0]['boxes'].detach(),
            pred[0]['scores'].detach(),
            0.3  # Increased threshold for better filtering
        )
        
        if len(keep_indices) == 0:
            print(f"Sample {idx}: No detections")
            continue
        
        # Get prediction
        xmin, ymin, xmax, ymax = pred[0]['boxes'][keep_indices[0]].detach().cpu().long().tolist()
        label = pred[0]['labels'][keep_indices[0]].item()
        score = pred[0]['scores'][keep_indices[0]].item()
        
        # Get ground truth
        Txmin, Tymin, Txmax, Tymax = test_tar['boxes'][0].long().tolist()
        true_label = test_tar['labels'][0].item()
        
        # Visualize
        image = test_img.permute(1, 2, 0).cpu().numpy().copy()
        
        # Draw prediction (blue)
        image = cv2.rectangle(image, (xmin, ymin), (xmax, ymax), (255, 0, 0), 2)
        cv2.putText(image, f"{classes[label]} ({score:.2f})", 
                   (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Draw ground truth (green)
        image = cv2.rectangle(image, (Txmin, Tymin), (Txmax, Tymax), (0, 255, 0), 2)
        cv2.putText(image, f"True: {classes[true_label]}", 
                   (Txmin, Tymax + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        plt.figure(figsize=(10, 10))
        plt.imshow(image)
        plt.title(f"Sample {idx}: Prediction vs Ground Truth")
        plt.axis('off')
        plt.show()


def model_training(model, train_loader, val_loader, optimizer, model_idx):
    """Complete training loop"""
    t_traj = []
    v_traj = []
    epoch_list = []
    best_val_loss = np.Inf
    best_state_dict = None  # keep best weights in memory
    
    print(f"\n{'='*60}")
    print(f"Training Model {model_idx + 1}")
    print(f"{'='*60}\n")
    
    for epoch in range(EPOCHS):
        print(f"\nEpoch {epoch + 1}/{EPOCHS}")
        print("-" * 60)
        
        # Training
        train_loss = train_cycle(model, train_loader, optimizer)
        
        # Validation
        val_loss = eval_cycle(model, val_loader)
        
        # Track metrics
        t_traj.append(train_loss)
        v_traj.append(val_loss)
        epoch_list.append(epoch + 1)
        
        print(f"\nEpoch {epoch + 1} Summary:")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss:   {val_loss:.4f}")
        
        # Keep track of best weights
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state_dict = copy.deepcopy(model.state_dict())
            print(f"  ✓ New best validation loss: {best_val_loss:.4f}")
    
    # Guarantee model1_best.pt is always written at the end of training.
    # Use the best weights captured during training; fall back to the
    # final epoch weights if something went wrong.
    if best_state_dict is None:
        best_state_dict = model.state_dict()
    
    best_model_path = MODEL_OUTPUT_DIR / f'model{model_idx + 1}_best.pt'
    torch.save(best_state_dict, best_model_path)
    print(f"\n✓ Best model saved to {best_model_path}")
    
    # Save final model (last epoch weights)
    final_model_path = MODEL_OUTPUT_DIR / f'model{model_idx + 1}_final.pt'
    torch.save(model.state_dict(), final_model_path)
    print(f"✓ Final model saved to {final_model_path}")
    print(f"✓ Best Validation Loss: {best_val_loss:.4f}")
    
    # Plot training curves
    plt.figure(figsize=(10, 6))
    plt.plot(epoch_list, t_traj, label='Train Loss', marker='o')
    plt.plot(epoch_list, v_traj, label='Validation Loss', marker='s')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title(f'Model {model_idx + 1}: Training/Validation Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot
    plot_path = MODEL_OUTPUT_DIR / f'model{model_idx + 1}_training_curve.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"✓ Training curve saved to {plot_path}")
    plt.show()
    
    # Cleanup
    torch.cuda.empty_cache()
    
    return best_val_loss


def main():
    """Main training function"""
    # Set seeds for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    print(f"Using device: {DEVICE}")
    
    # Data directory
    dir_path = './Data'
    
    if not os.path.exists(dir_path):
        raise ValueError(f"Data directory not found: {dir_path}")
    
    # Set up transforms
    transform = v2.Compose([
        v2.Resize((IS, IS)),
        v2.ToImage(),
        v2.ToDtype(torch.float32, scale=True),
        v2.RandomAutocontrast(0.1),
        v2.RandomAdjustSharpness(0.1, sharpness_factor=2),
        v2.RandomErasing(0.1),
        v2.RandomHorizontalFlip(0.1),
        v2.RandomInvert(0.1)
    ])
    
    # Create datasets
    print("\nLoading datasets...")
    train_set = ImageDataset(dir_path, transform, mode='train')
    val_set = ImageDataset(dir_path, transform, mode='valid')
    test_set = ImageDataset(dir_path, transform, mode='test')
    
    # Create dataloaders
    train_loader = torch.utils.data.DataLoader(
        train_set,
        batch_size=BS,
        collate_fn=train_set.collate_fn,
        shuffle=True,
        num_workers=4,
        pin_memory=True if DEVICE == 'cuda' else False
    )
    
    val_loader = torch.utils.data.DataLoader(
        val_set,
        batch_size=BS,
        collate_fn=val_set.collate_fn,
        shuffle=False,
        num_workers=4,
        pin_memory=True if DEVICE == 'cuda' else False
    )
    
    test_loader = torch.utils.data.DataLoader(
        test_set,
        batch_size=BS,
        collate_fn=test_set.collate_fn,
        shuffle=False
    )
    
    print(f'\nDataset Summary:')
    print(f'  Training:   {len(train_set)} images in {len(train_loader)} batches')
    print(f'  Validation: {len(val_set)} images in {len(val_loader)} batches')
    print(f'  Testing:    {len(test_set)} images in {len(test_loader)} batches')
    
    # Test data loading
    print("\nTesting data loading...")
    image, target = next(iter(val_loader))
    print(f"  ✓ Batch loaded: {len(image)} images")
    
    # Create model
    print("\nInitializing model...")
    from torchvision.models.detection.faster_rcnn import (
        FastRCNNPredictor, 
        FasterRCNN_ResNet50_FPN_V2_Weights
    )
    
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(
        weights=FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
    )
    
    # Replace the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    # Move to device
    model.to(DEVICE)
    
    # Create optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    
    print(f"  ✓ Model initialized")
    print(f"  ✓ Number of classes: {num_classes}")
    print(f"  ✓ Learning rate: {LR}")
    
    # Train model
    best_loss = model_training(model, train_loader, val_loader, optimizer, model_idx=0)
    
    # Test model
    print("\n" + "="*60)
    print("Testing trained model")
    print("="*60)
    model_testing(model, test_set, num_samples=5)
    
    print("\n" + "="*60)
    print("Training Complete!")
    print(f"Best validation loss: {best_loss:.4f}")
    print(f"Models saved to: {MODEL_OUTPUT_DIR}")
    print("="*60)
    
    return model, best_loss


if __name__ == "__main__":
    model, final_loss = main()
