"""
Bone Fracture Detection Training Pipeline
==========================================
Faster R-CNN (ResNet50 FPN V2) with:
  - Custom anchor generator + RPN head
  - Mixed precision training (autocast / GradScaler)
  - EMA weight averaging
  - Cosine LR schedule with warmup
  - WeightedRandomSampler for class imbalance
  - 5-fold cross-validation
  - Final training on full dataset
  - SageMaker packaging + deployment
"""

import os
import json
import copy
import hashlib
import shutil
import tarfile
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm

import torch
from torch.amp import autocast, GradScaler
from torch.utils.data import (
    Dataset, DataLoader, Subset, ConcatDataset, WeightedRandomSampler
)

from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.anchor_utils import AnchorGenerator
from torchvision.models.detection.rpn import RPNHead
from torchvision.transforms import v2
from torchvision.tv_tensors import BoundingBoxes

from sklearn.model_selection import KFold
from sklearn.metrics import roc_curve, auc

from torchmetrics.detection.mean_ap import MeanAveragePrecision

import yaml
import boto3


# ============================================================
# CONFIG
# ============================================================

PROJECT_NAME = "fracture-detector"
MODEL_NAME = "fasterrcnn_resnet50_fpn_v2_fracture"
OUTPUT_DIR = f"./models/{MODEL_NAME}"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

NUM_CLASSES = 7           # 7 fracture classes (background is handled internally)
LR = 5e-5
WEIGHT_DECAY = 1e-4
EPOCHS = 25
WARMUP_EPOCHS = 3
BATCH_SIZE = 4
ACCUM_STEPS = 2
NUM_WORKERS = 4
DATA_ROOT = "data/bone_fracture_detection_v4-v4_yolov8"

S3_BUCKET = "mvanslyke-ml-models"
SAGEMAKER_MODEL_NAME = "fasterrcnn_fracture_v1"

print(f"Device: {DEVICE}")
if DEVICE == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")


# ============================================================
# DATASET
# ============================================================

class FractureDataset(Dataset):
    def __init__(self, root, split="train", transforms=None):
        self.root = root
        self.split = split
        self.transforms = transforms

        self.img_dir = os.path.join(root, split, "images")
        self.label_dir = os.path.join(root, split, "labels")

        self.images = sorted([
            f for f in os.listdir(self.img_dir)
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ])

        self.class_counts = None  # populated later if needed

    def __len__(self):
        return len(self.images)

    def _clamp_box(self, xmin, ymin, xmax, ymax, W, H):
        xmin = max(0, min(xmin, W - 1))
        ymin = max(0, min(ymin, H - 1))
        xmax = max(0, min(xmax, W - 1))
        ymax = max(0, min(ymax, H - 1))
        return xmin, ymin, xmax, ymax

    def __getitem__(self, idx):
        img_name = self.images[idx]
        img_path = os.path.join(self.img_dir, img_name)
        label_path = os.path.join(
            self.label_dir,
            os.path.splitext(img_name)[0] + ".txt"
        )

        image = Image.open(img_path).convert("RGB")
        W, H = image.size  # PIL gives (W, H)

        boxes = []
        labels = []

        if os.path.exists(label_path):
            with open(label_path) as f:
                lines = f.readlines()

            for line in lines:
                try:
                    values = list(map(float, line.strip().split()))
                    cls = int(values[0])
                    coords = values[1:]

                    xs = [coords[i] * W for i in range(0, len(coords), 2)]
                    ys = [coords[i] * H for i in range(1, len(coords), 2)]

                    xmin = min(xs)
                    ymin = min(ys)
                    xmax = max(xs)
                    ymax = max(ys)

                    xmin, ymin, xmax, ymax = self._clamp_box(
                        xmin, ymin, xmax, ymax, W, H
                    )

                    if xmax <= xmin or ymax <= ymin:
                        continue

                    boxes.append([xmin, ymin, xmax, ymax])
                    labels.append(cls + 1)  # reserve 0 for background

                except Exception:
                    continue

        if len(boxes) == 0:
            boxes = BoundingBoxes(
                torch.zeros((0, 4), dtype=torch.float32),
                format="XYXY",
                canvas_size=(H, W)
            )
            labels = torch.zeros((0,), dtype=torch.int64)
            area = torch.zeros((0,), dtype=torch.float32)
        else:
            boxes = BoundingBoxes(
                torch.tensor(boxes, dtype=torch.float32),
                format="XYXY",
                canvas_size=(H, W)
            )
            labels = torch.tensor(labels, dtype=torch.int64)
            area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])

        target = {
            "boxes": boxes,
            "labels": labels,
            "area": area,
            "iscrowd": torch.zeros((len(boxes),), dtype=torch.int64),
        }

        if self.transforms:
            image, target = self.transforms(image, target)

        target["boxes"] = torch.as_tensor(target["boxes"], dtype=torch.float32)

        return image, target


def collate_fn(batch):
    return tuple(zip(*batch))


# ============================================================
# CLASS WEIGHT BALANCER
# ============================================================

def compute_class_weights(dataset):
    """Compute per-sample weights for WeightedRandomSampler."""
    # Recurse through ConcatDataset
    if isinstance(dataset, ConcatDataset):
        all_weights = []
        for sub in dataset.datasets:
            all_weights.extend(compute_class_weights(sub))
        return all_weights

    base = dataset.dataset if hasattr(dataset, "dataset") else dataset
    indices = dataset.indices if hasattr(dataset, "indices") else range(len(dataset))

    class_freq = {}
    sample_labels = []

    for i in indices:
        img_name = base.images[i]
        label_path = os.path.join(
            base.label_dir,
            os.path.splitext(img_name)[0] + ".txt"
        )

        labels = []
        if os.path.exists(label_path):
            with open(label_path) as f:
                for line in f:
                    try:
                        cls = int(float(line.strip().split()[0])) + 1
                        labels.append(cls)
                        class_freq[cls] = class_freq.get(cls, 0) + 1
                    except Exception:
                        continue

        sample_labels.append(labels)

    total = sum(class_freq.values()) if class_freq else 1
    class_weights = {cls: total / count for cls, count in class_freq.items()}

    final_weights = []
    for labels in sample_labels:
        if len(labels) == 0:
            final_weights.append(1.0)
        else:
            final_weights.append(
                float(np.mean([class_weights[l] for l in labels]))
            )

    return final_weights


# ============================================================
# EMA
# ============================================================

class EMA:
    def __init__(self, model, decay=0.999):
        self.shadow = {}
        self.decay = decay
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self, model):
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = (
                    self.decay * self.shadow[name]
                    + (1 - self.decay) * param.data
                )

    def apply(self, model):
        for name, param in model.named_parameters():
            if param.requires_grad:
                param.data = self.shadow[name]


# ============================================================
# MODEL
# ============================================================

def build_model(num_classes):
    """Faster R-CNN with custom anchors + deeper RPN head."""
    model = fasterrcnn_resnet50_fpn_v2(weights="DEFAULT")

    anchor_generator = AnchorGenerator(
        sizes=((16,), (32,), (64,), (128,), (256,)),
        aspect_ratios=((0.25, 0.5, 1.0, 2.0, 4.0),) * 5,
    )
    model.rpn.anchor_generator = anchor_generator
    model.rpn.head = RPNHead(
        in_channels=model.backbone.out_channels,
        num_anchors=anchor_generator.num_anchors_per_location()[0],
        conv_depth=2,
    )

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    return model


# ============================================================
# TRAINER
# ============================================================

class Trainer:
    def __init__(self, model):
        self.model = model.to(DEVICE)
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=LR,
            weight_decay=WEIGHT_DECAY,
        )
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=EPOCHS - WARMUP_EPOCHS,
            eta_min=1e-6,
        )
        self.scaler = GradScaler("cuda")
        self.ema = EMA(model)
        self.map_metric = MeanAveragePrecision(
            box_format="xyxy",
            iou_type="bbox",
            class_metrics=True,
        )
        self.best_map = 0

    def train_one_epoch(self, loader):
        self.model.train()
        total_loss = 0
        component_totals = {
            "loss_classifier": 0,
            "loss_box_reg": 0,
            "loss_objectness": 0,
            "loss_rpn_box_reg": 0,
        }

        self.optimizer.zero_grad()

        for i, (images, targets) in enumerate(tqdm(loader)):
            if len(images) == 0:
                continue
            images = [img.to(DEVICE) for img in images]
            targets = [{k: v.to(DEVICE) for k, v in t.items()} for t in targets]

            with autocast("cuda"):
                loss_dict = self.model(images, targets)
                loss = sum(loss_dict.values()) / ACCUM_STEPS

            self.scaler.scale(loss).backward()

            if (i + 1) % ACCUM_STEPS == 0 or (i + 1) == len(loader):
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), max_norm=1.0
                )
                self.scaler.step(self.optimizer)
                self.scaler.update()
                self.optimizer.zero_grad()
                self.ema.update(self.model)

            total_loss += loss.item() * ACCUM_STEPS
            for k, v in loss_dict.items():
                component_totals[k] += v.item()

            del images, targets, loss_dict, loss
            if i % 50 == 0:
                torch.cuda.empty_cache()

        n = len(loader)
        print(f"  classifier:   {component_totals['loss_classifier']/n:.4f}")
        print(f"  box_reg:      {component_totals['loss_box_reg']/n:.4f}")
        print(f"  objectness:   {component_totals['loss_objectness']/n:.4f}")
        print(f"  rpn_box_reg:  {component_totals['loss_rpn_box_reg']/n:.4f}")

        return total_loss / n

    def validate(self, loader):
        self.model.eval()
        self.map_metric.reset()

        y_true = []
        y_scores = []

        with torch.no_grad():
            for images, targets in loader:
                images = [img.to(DEVICE) for img in images]
                outputs = self.model(images)

                cpu_outputs = [
                    {k: v.cpu() for k, v in o.items()} for o in outputs
                ]
                cpu_targets = [
                    {k: v.cpu() for k, v in t.items()} for t in targets
                ]

                self.map_metric.update(cpu_outputs, cpu_targets)

                for out, tgt in zip(cpu_outputs, cpu_targets):
                    score = out["scores"].numpy()
                    label = 1 if len(tgt["boxes"]) > 0 else 0
                    y_true.append(label)
                    y_scores.append(score[0] if len(score) else 0)

        metrics = self.map_metric.compute()
        self.map_metric.reset()

        return metrics, np.array(y_true), np.array(y_scores)

    def fit(self, train_loader, val_loader):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        for epoch in range(EPOCHS):
            loss = self.train_one_epoch(train_loader)

            if epoch >= WARMUP_EPOCHS:
                self.scheduler.step()

            metrics, y_true, y_scores = self.validate(val_loader)
            map5095 = metrics["map"].item()

            print(
                f"Epoch {epoch+1} | Loss: {loss:.4f} "
                f"| mAP@0.5:0.95: {map5095:.4f}"
            )

            if map5095 > self.best_map:
                self.best_map = map5095

                # Save EMA weights to a copy, never touch the live model
                ema_model = copy.deepcopy(self.model)
                self.ema.apply(ema_model)
                torch.save(
                    ema_model.state_dict(),
                    os.path.join(OUTPUT_DIR, "model.pth"),
                )
                del ema_model

                self.save_metrics(metrics)
                self.generate_analysis(y_true, y_scores)

        torch.cuda.empty_cache()

    def save_metrics(self, metrics):
        metric_dict = {
            "mAP@0.5:0.95": metrics["map"].item(),
            "mAP@0.5": metrics["map_50"].item(),
            "per_class_AP": metrics["map_per_class"].tolist(),
        }
        with open(os.path.join(OUTPUT_DIR, "coco_metrics.json"), "w") as f:
            json.dump(metric_dict, f, indent=4)

    def generate_analysis(self, y_true, y_scores):
        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)

        plt.figure()
        plt.plot(fpr, tpr)
        plt.title(f"ROC Curve (AUC={roc_auc:.2f})")
        plt.savefig(os.path.join(OUTPUT_DIR, "roc_curve.png"))
        plt.close()


# ============================================================
# FINAL TRAINING ON FULL DATASET
# ============================================================

def train_final_model(transforms):
    print("\n===== Training Final Model on Full Dataset =====")

    train_dataset = FractureDataset(DATA_ROOT, split="train", transforms=transforms)
    valid_dataset = FractureDataset(DATA_ROOT, split="valid", transforms=transforms)
    test_dataset = FractureDataset(DATA_ROOT, split="test", transforms=transforms)

    full_dataset = ConcatDataset([train_dataset, valid_dataset, test_dataset])

    print(f"Train samples:  {len(train_dataset)}")
    print(f"Valid samples:  {len(valid_dataset)}")
    print(f"Test samples:   {len(test_dataset)}")
    print(f"Total samples:  {len(full_dataset)}")

    sample_weights = compute_class_weights(full_dataset)
    sampler = WeightedRandomSampler(
        sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )

    train_loader = DataLoader(
        full_dataset,
        batch_size=BATCH_SIZE,
        sampler=sampler,
        num_workers=NUM_WORKERS,
        collate_fn=collate_fn,
        pin_memory=True,
        persistent_workers=True,
    )

    model = build_model(NUM_CLASSES)
    trainer = Trainer(model)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for epoch in range(EPOCHS):
        loss = trainer.train_one_epoch(train_loader)

        if epoch >= WARMUP_EPOCHS:
            trainer.scheduler.step()

        print(f"Epoch {epoch+1} | Loss: {loss:.4f}")

        ema_model = copy.deepcopy(trainer.model)
        trainer.ema.apply(ema_model)
        torch.save(
            ema_model.state_dict(),
            os.path.join(OUTPUT_DIR, f"final_model_epoch{epoch+1}.pth"),
        )
        del ema_model
        torch.cuda.empty_cache()

    final_model = build_model(NUM_CLASSES)
    final_model.load_state_dict(
        torch.load(os.path.join(OUTPUT_DIR, f"final_model_epoch{EPOCHS}.pth"))
    )
    final_model.eval()

    print(
        f"\nFinal model trained for {EPOCHS} epochs on "
        f"{len(full_dataset)} total samples."
    )
    return final_model


# ============================================================
# DEPLOYMENT PACKAGING (SageMaker)
# ============================================================

def compute_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


INFERENCE_SCRIPT = f'''"""SageMaker inference handler for the fracture detector."""

import io
import json
import logging

import torch
import torchvision
from PIL import Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.anchor_utils import AnchorGenerator
from torchvision.models.detection.rpn import RPNHead

NUM_CLASSES = {NUM_CLASSES}

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _build_model(num_classes):
    model = fasterrcnn_resnet50_fpn_v2(weights=None)

    anchor_generator = AnchorGenerator(
        sizes=((16,), (32,), (64,), (128,), (256,)),
        aspect_ratios=((0.25, 0.5, 1.0, 2.0, 4.0),) * 5,
    )
    model.rpn.anchor_generator = anchor_generator
    model.rpn.head = RPNHead(
        in_channels=model.backbone.out_channels,
        num_anchors=anchor_generator.num_anchors_per_location()[0],
        conv_depth=2,
    )

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model


def model_fn(model_dir):
    model = _build_model(NUM_CLASSES)
    state_dict = torch.load(f"{{model_dir}}/model.pth", map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    logger.info("Model loaded successfully.")
    return model


def input_fn(request_body, request_content_type):
    image = Image.open(io.BytesIO(request_body)).convert("RGB")
    image = torchvision.transforms.functional.to_tensor(image)
    return image


def predict_fn(input_data, model):
    with torch.no_grad():
        outputs = model([input_data])
    return outputs[0]


def output_fn(prediction, content_type):
    return json.dumps({{
        "boxes": prediction["boxes"].tolist(),
        "scores": prediction["scores"].tolist(),
        "labels": prediction["labels"].tolist(),
    }})
'''


def package_for_sagemaker(
    model,
    model_name=SAGEMAKER_MODEL_NAME,
    bucket=S3_BUCKET,
):
    """Package model + inference code into a SageMaker tarball and upload to S3."""
    export_dir = Path("deployment_package")
    code_dir = export_dir / "code"

    if export_dir.exists():
        shutil.rmtree(export_dir)
    code_dir.mkdir(parents=True)

    # Save weights
    torch.save(model.state_dict(), export_dir / "model.pth")
    print("Model weights saved.")

    # Inference handler
    with open(code_dir / "inference.py", "w") as f:
        f.write(INFERENCE_SCRIPT)
    print("inference.py written.")

    # Requirements
    with open(code_dir / "requirements.txt", "w") as f:
        f.write("torch\ntorchvision\npillow\nnumpy\n")
    print("requirements.txt written.")

    # Config metadata
    config = {
        "model_name": model_name,
        "framework": "pytorch",
        "num_classes": NUM_CLASSES,
        "input_size": [3, 512, 512],
    }
    with open(export_dir / "config.yml", "w") as f:
        yaml.dump(config, f)
    print("config.yml written.")

    print("\nPackage contents:")
    for root, _, files in os.walk(export_dir):
        for fname in files:
            print(f"  {os.path.join(root, fname)}")

    # Tar
    tar_path = Path(f"{model_name}.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(export_dir, arcname="")
    print(f"\nModel packaged: {tar_path}")

    # Hash
    hash_value = compute_sha256(tar_path)
    with open("artifact_hash.txt", "w") as f:
        f.write(hash_value)
    print(f"SHA256: {hash_value}")

    # Upload
    s3 = boto3.client("s3")
    s3.upload_file(str(tar_path), bucket, f"{model_name}/{tar_path.name}")
    print(f"Uploaded to s3://{bucket}/{model_name}/{tar_path.name}")


def deploy_to_sagemaker(
    model_name=SAGEMAKER_MODEL_NAME,
    bucket=S3_BUCKET,
    instance_type="ml.m5.large",
):
    """Create a SageMaker PyTorch endpoint from the uploaded model artifact."""
    import sagemaker
    from sagemaker.pytorch import PyTorchModel
    from sagemaker import get_execution_role

    sagemaker.Session()
    role = get_execution_role()

    model_s3_path = f"s3://{bucket}/{model_name}/{model_name}.tar.gz"

    pytorch_model = PyTorchModel(
        model_data=model_s3_path,
        role=role,
        entry_point="inference.py",
        source_dir="deployment_package/code",
        framework_version="2.1",
        py_version="py310",
    )

    predictor = pytorch_model.deploy(
        initial_instance_count=1,
        instance_type=instance_type,
        endpoint_name=model_name,
    )
    print("Endpoint deployed:", model_name)
    return predictor


# ============================================================
# MAIN
# ============================================================

def main():
    transforms = v2.Compose([
        v2.ToImage(),
        v2.Grayscale(num_output_channels=3),
        v2.ToDtype(torch.float32, scale=True),
        v2.RandomHorizontalFlip(p=0.5),
        v2.RandomVerticalFlip(p=0.2),
        v2.RandomRotation(degrees=15),
        v2.ColorJitter(brightness=0.3, contrast=0.3),
        v2.RandomAdjustSharpness(sharpness_factor=2, p=0.3),
        v2.RandomAutocontrast(p=0.3),
        v2.Resize((512, 512)),
        v2.SanitizeBoundingBoxes(),
    ])

    full_dataset = FractureDataset(
        DATA_ROOT, split="train", transforms=transforms
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    fold_scores = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(full_dataset)):
        print(f"\n===== Fold {fold+1} =====")

        train_subset = Subset(full_dataset, train_idx)
        val_subset = Subset(full_dataset, val_idx)

        sample_weights = compute_class_weights(train_subset)
        sampler = WeightedRandomSampler(
            sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
        )

        train_loader = DataLoader(
            train_subset,
            batch_size=BATCH_SIZE,
            sampler=sampler,
            num_workers=NUM_WORKERS,
            collate_fn=collate_fn,
            pin_memory=True,
            persistent_workers=True,
        )

        val_loader = DataLoader(
            val_subset,
            batch_size=BATCH_SIZE,
            shuffle=False,
            num_workers=NUM_WORKERS,
            collate_fn=collate_fn,
            pin_memory=True,
            persistent_workers=True,
        )

        model = build_model(NUM_CLASSES)
        trainer = Trainer(model)
        trainer.fit(train_loader, val_loader)

        fold_scores.append(trainer.best_map)

        del model
        torch.cuda.empty_cache()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "cv_results.json"), "w") as f:
        json.dump(fold_scores, f, indent=4)

    print("\nCross-Validation Results:", fold_scores)
    print("Mean mAP:", np.mean(fold_scores))

    # Train final model on full dataset
    final_model = train_final_model(transforms)

    # Load the last final-model checkpoint for deployment
    best_model = build_model(NUM_CLASSES)
    best_model.load_state_dict(
        torch.load(os.path.join(OUTPUT_DIR, f"final_model_epoch{EPOCHS}.pth"))
    )
    best_model.eval()

    package_for_sagemaker(
        best_model,
        model_name=SAGEMAKER_MODEL_NAME,
        bucket=S3_BUCKET,
    )


if __name__ == "__main__":
    main()
