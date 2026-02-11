"""
Example: Deploying Bone Fracture Detection Model
=================================================

This script demonstrates how to use the deployment_utils module
to package the trained bone fracture detection model for AWS Lambda.

Usage:
    python deploy_bone_fracture_model.py
"""

from deployment_utils import ModelDeployer
import torch
from pathlib import Path

# Import your trained model
# Assuming you've trained the model using train_bone_fracture_model.py
MODEL_PATH = Path('./trained_models/model1_best.pt')

# Load the trained model
print("Loading trained model...")
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torchvision

# Recreate model architecture
num_classes = 8
model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=None)
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

# Load trained weights
model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
model.eval()

print("✓ Model loaded successfully\n")

# Define class mappings
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

# Example input/output for API documentation
input_example = {
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "threshold": 0.5
}

output_example = {
    "predictions": [
        {
            "box": [10, 20, 100, 150],
            "label": "forearm fracture",
            "confidence": 0.92
        }
    ],
    "num_detections": 1
}

# Initialize deployer
deployer = ModelDeployer(
    model=model,
    project_name="bone-fracture-detection",
    model_type="pytorch",
    input_example=input_example,
    output_example=output_example,
    classes=classes
)

# Package everything for deployment
deployer.package_for_deployment(
    description="AI-powered bone fracture detection using Faster R-CNN with ResNet50 FPN V2 backbone. Detects and localizes fractures in upper extremity X-ray images.",
    memory=2048,  # 2GB for computer vision model
    timeout=60,    # 60 seconds for image processing
    handler_template="computer_vision",
    additional_packages=[
        'opencv-python-headless==4.8.0.74',  # For image processing (headless for Lambda)
    ],
    environment_vars={
        'MODEL_ARCHITECTURE': 'fasterrcnn_resnet50_fpn_v2',
        'IMAGE_SIZE': '224',
        'CONFIDENCE_THRESHOLD': '0.5'
    },
    api_route='/bone-fracture-detect',
    additional_notes="""
## Model Details

### Architecture
- **Base Model**: Faster R-CNN with ResNet50 FPN V2 backbone
- **Task**: Object detection and classification
- **Input**: X-ray images (224x224)
- **Output**: Bounding boxes with fracture classifications

### Performance Metrics
- **Accuracy**: 88.6%
- **Loss**: 11.4%
- **Training Time**: 5 epochs
- **Dataset**: 3,000+ annotated X-ray images

### Deployment Considerations
- Model size: ~150MB (will be uploaded to S3)
- Cold start: ~5-8 seconds
- Warm inference: ~2-3 seconds per image
- Memory: 2GB recommended

### Usage Notes
1. Images should be base64 encoded
2. Adjust `threshold` parameter (0.0-1.0) to control detection sensitivity
3. Higher threshold = fewer but more confident detections
4. Lower threshold = more detections but may include false positives

### Example cURL Request
```bash
curl -X POST https://api.mvanslyke-ml.com/bone-fracture-detect \\
  -H "Content-Type: application/json" \\
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "threshold": 0.5
  }'
```

### Response Format
```json
{
  "predictions": [
    {
      "box": [x_min, y_min, x_max, y_max],
      "label": "fracture_type",
      "confidence": 0.92
    }
  ],
  "num_detections": 1
}
```

### Model Training
Trained using:
- PyTorch 2.0.1
- TorchVision 0.15.2
- Data augmentation (contrast, sharpness, flips, etc.)
- Adam optimizer (lr=0.0001)
- Batch size: 12
- Device: CUDA (GPU)

For more details, see the project blog post and GitHub repository.
"""
)

print("\n" + "="*70)
print("🎉 DEPLOYMENT PACKAGE READY!")
print("="*70)
print("""
Next steps:

1. Test locally:
   cd models/bone-fracture-detection
   python lambda_function.py

2. Upload model to S3 (model is >50MB):
   aws s3 cp model.pt s3://mvanslyke-ml-models/bone-fracture-detection/

3. Update lambda_function.py to load from S3 if needed

4. Commit and push to GitHub:
   git add models/bone-fracture-detection/
   git commit -m "Add: Bone Fracture Detection Model - 88.6% accuracy"
   git push

5. GitHub Actions will automatically deploy to AWS Lambda

6. Your model will be live at:
   https://api.mvanslyke-ml.com/bone-fracture-detect

7. Update your blog post with the live demo URL!
""")
