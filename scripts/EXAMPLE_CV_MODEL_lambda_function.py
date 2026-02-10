"""
Example Lambda Function for Computer Vision Models
Handles image uploads and processes them for inference
"""

import json
import base64
import io
from PIL import Image
import numpy as np

# Import your model libraries
# import torch
# import torchvision.transforms as transforms

# Load model at cold start (cached for warm starts)
# model = torch.load('model.pt')
# model.eval()

def lambda_handler(event, context):
    """
    Lambda handler for CV model with image input
    
    Expects JSON body:
    {
        "image": "base64_encoded_image_string",
        "filename": "image.jpg"  (optional)
    }
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        # Get base64 image data
        image_base64 = body.get('image')
        filename = body.get('filename', 'uploaded_image.jpg')
        
        if not image_base64:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'error': 'No image data provided',
                    'usage': 'Send base64 encoded image in "image" field'
                })
            }
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'Invalid image data',
                    'details': str(e)
                })
            }
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Preprocess image
        # Example preprocessing (customize for your model):
        # transform = transforms.Compose([
        #     transforms.Resize((224, 224)),
        #     transforms.ToTensor(),
        #     transforms.Normalize(mean=[0.485, 0.456, 0.406], 
        #                         std=[0.229, 0.224, 0.225])
        # ])
        # input_tensor = transform(image).unsqueeze(0)
        
        # Run inference
        # with torch.no_grad():
        #     output = model(input_tensor)
        #     probabilities = torch.nn.functional.softmax(output[0], dim=0)
        #     predicted_class = probabilities.argmax().item()
        #     confidence = probabilities[predicted_class].item()
        
        # For demo purposes, return image info
        # Replace this with your actual model inference
        demo_result = {
            'status': 'success',
            'filename': filename,
            'image_size': {
                'width': image.width,
                'height': image.height
            },
            'format': image.format or 'unknown',
            'mode': image.mode,
            'message': 'Image received and processed successfully'
            
            # Add your model results here:
            # 'prediction': predicted_class,
            # 'confidence': confidence,
            # 'probabilities': probabilities.tolist(),
            # 'bounding_boxes': [...],  # For object detection
            # 'segmentation_mask': [...],  # For segmentation
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(demo_result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }


# For local testing
if __name__ == '__main__':
    # Read a test image
    with open('test_image.jpg', 'rb') as f:
        image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Create test event
    test_event = {
        'body': json.dumps({
            'image': image_base64,
            'filename': 'test_image.jpg'
        })
    }
    
    # Test the handler
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
