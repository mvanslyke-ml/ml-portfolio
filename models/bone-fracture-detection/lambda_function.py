"""
AWS Lambda Handler - Bone Fracture Detection
Faster R-CNN with ResNet50 FPN V2 backbone
Loads model weights from S3 on cold start.
"""

import json
import base64
import os
import io
import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import v2
from PIL import Image
import boto3

# Configuration from environment variables
MODEL_BUCKET = os.environ.get('MODEL_BUCKET', 'mvanslyke-ml-models')
MODEL_KEY = os.environ.get('MODEL_KEY', 'bone-fracture-detection/model.pt')
IMAGE_SIZE = int(os.environ.get('IMAGE_SIZE', '224'))
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.5'))

NUM_CLASSES = 8
CLASSES = {
    0: 'elbow positive',
    1: 'fingers positive',
    2: 'forearm fracture',
    3: 'humerus fracture',
    4: 'humerus',
    5: 'shoulder fracture',
    6: 'wrist positive',
    7: 'no fracture'
}

# Image preprocessing (same as training, minus augmentations)
transform = v2.Compose([
    v2.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    v2.ToImage(),
    v2.ToDtype(torch.float32, scale=True),
])


def load_model():
    """Load model architecture and weights from S3."""
    print(f"Loading model from s3://{MODEL_BUCKET}/{MODEL_KEY}")

    s3 = boto3.client('s3')
    model_buffer = io.BytesIO()
    s3.download_fileobj(MODEL_BUCKET, MODEL_KEY, model_buffer)
    model_buffer.seek(0)

    # Recreate exact architecture used during training
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, NUM_CLASSES)

    # Load the saved state dict
    state_dict = torch.load(model_buffer, map_location=torch.device('cpu'))
    model.load_state_dict(state_dict)
    model.eval()

    print("Model loaded successfully")
    return model


# Load model at cold start — cached for warm invocations
model = load_model()


def preprocess_image(image_data: str) -> torch.Tensor:
    """Decode base64 image and prepare it for inference."""
    if ',' in image_data:
        image_data = image_data.split(',')[1]

    image_bytes = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    tensor = transform(image)
    return tensor


def lambda_handler(event, context):
    """
    Lambda entry point.

    Expects JSON body:
    {
        "image": "<base64 encoded image>",
        "threshold": 0.5   (optional, 0.0 - 1.0)
    }
    """
    try:
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event

        image_data = body.get('image')
        if not image_data:
            return _error(400, 'Missing required field: image (base64 encoded)')

        threshold = float(body.get('threshold', CONFIDENCE_THRESHOLD))

        # Preprocess
        image_tensor = preprocess_image(image_data)

        # Inference
        with torch.no_grad():
            predictions = model([image_tensor])

        pred = predictions[0]

        # Apply NMS and confidence threshold
        keep = torchvision.ops.nms(pred['boxes'], pred['scores'], iou_threshold=0.3)

        results = []
        for idx in keep:
            score = pred['scores'][idx].item()
            if score < threshold:
                continue
            box = pred['boxes'][idx].long().tolist()
            label_idx = pred['labels'][idx].item()
            results.append({
                'box': box,            # [x_min, y_min, x_max, y_max]
                'label': CLASSES.get(label_idx, f'class_{label_idx}'),
                'confidence': round(score, 4)
            })

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'predictions': results,
                'num_detections': len(results)
            })
        }

    except Exception as e:
        print(f"Error: {e}")
        return _error(500, str(e))


def _error(status_code: int, message: str) -> dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }
