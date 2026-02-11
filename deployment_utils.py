"""
ML Model Deployment Utility
============================

Universal module for packaging trained ML models for AWS Lambda deployment.
This module handles:
- Model serialization (pickle/torch)
- Config.yml generation
- Lambda function template creation
- Requirements.txt generation
- Proper directory structure

Usage:
    from deployment_utils import ModelDeployer
    
    deployer = ModelDeployer(
        model=trained_model,
        project_name="bone-fracture-detection",
        model_type="pytorch",
        input_example={"image": "base64_string"},
        classes={0: "fracture", 1: "no_fracture"}
    )
    
    deployer.package_for_deployment(
        description="AI-powered bone fracture detection",
        memory=1024,
        timeout=60,
        handler_template="computer_vision"
    )
"""

import os
import pickle
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import torch


class ModelDeployer:
    """
    Universal model deployment packager for AWS Lambda.
    Supports PyTorch, scikit-learn, TensorFlow, and other model types.
    """
    
    # Lambda handler templates for different model types
    HANDLER_TEMPLATES = {
        'computer_vision': 'cv_lambda_template.py',
        'nlp': 'nlp_lambda_template.py',
        'classification': 'classification_lambda_template.py',
        'regression': 'regression_lambda_template.py',
        'generic': 'generic_lambda_template.py'
    }
    
    def __init__(
        self,
        model: Any,
        project_name: str,
        model_type: str = 'pytorch',
        input_example: Optional[Dict] = None,
        output_example: Optional[Dict] = None,
        classes: Optional[Dict] = None,
        preprocessing_func: Optional[callable] = None,
        postprocessing_func: Optional[callable] = None
    ):
        """
        Initialize the model deployer.
        
        Args:
            model: Trained ML model (PyTorch, sklearn, TensorFlow, etc.)
            project_name: Name of the project (will be used for directory structure)
            model_type: Type of model ('pytorch', 'sklearn', 'tensorflow', etc.)
            input_example: Example input for API documentation
            output_example: Example output for API documentation
            classes: Dictionary mapping class indices to names
            preprocessing_func: Custom preprocessing function
            postprocessing_func: Custom postprocessing function
        """
        self.model = model
        self.project_name = project_name.lower().replace(' ', '-')
        self.model_type = model_type
        self.input_example = input_example or {}
        self.output_example = output_example or {}
        self.classes = classes or {}
        self.preprocessing_func = preprocessing_func
        self.postprocessing_func = postprocessing_func
        
        # Set up paths
        self.repo_root = Path.cwd()
        self.models_dir = self.repo_root / 'models' / self.project_name
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"✓ Initialized deployer for project: {self.project_name}")
        print(f"✓ Target directory: {self.models_dir}")
    
    def save_model(self, model_filename: Optional[str] = None) -> Path:
        """
        Save the model to the appropriate format.
        
        Args:
            model_filename: Custom filename for the model
            
        Returns:
            Path to saved model file
        """
        if model_filename is None:
            if self.model_type == 'pytorch':
                model_filename = 'model.pt'
            elif self.model_type in ['sklearn', 'xgboost', 'lightgbm']:
                model_filename = 'model.pkl'
            elif self.model_type == 'tensorflow':
                model_filename = 'model.h5'
            else:
                model_filename = 'model.pkl'
        
        model_path = self.models_dir / model_filename
        
        print(f"\n📦 Saving model...")
        
        if self.model_type == 'pytorch':
            # Save PyTorch model state dict
            if hasattr(self.model, 'state_dict'):
                torch.save(self.model.state_dict(), model_path)
            else:
                torch.save(self.model, model_path)
            print(f"  ✓ PyTorch model saved to {model_path}")
        
        elif self.model_type in ['sklearn', 'xgboost', 'lightgbm']:
            # Pickle scikit-learn compatible models
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            print(f"  ✓ Pickled model saved to {model_path}")
        
        elif self.model_type == 'tensorflow':
            # Save TensorFlow/Keras model
            self.model.save(model_path)
            print(f"  ✓ TensorFlow model saved to {model_path}")
        
        else:
            # Default to pickle
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            print(f"  ✓ Model pickled to {model_path}")
        
        # Get file size
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ Model size: {size_mb:.2f} MB")
        
        if size_mb > 50:
            print(f"  ⚠️  Warning: Model is >{size_mb:.0f}MB. Consider uploading to S3.")
        
        return model_path
    
    def generate_config(
        self,
        description: str,
        memory: int = 512,
        timeout: int = 30,
        api_route: Optional[str] = None,
        environment_vars: Optional[Dict] = None
    ) -> Path:
        """
        Generate config.yml for Lambda deployment.
        
        Args:
            description: Model description
            memory: Lambda memory in MB (128-10240)
            timeout: Lambda timeout in seconds (1-900)
            api_route: Custom API route (default: /project-name)
            environment_vars: Additional environment variables
            
        Returns:
            Path to generated config.yml
        """
        if api_route is None:
            api_route = f'/{self.project_name}'
        
        env_vars = environment_vars or {}
        
        # Add model metadata to environment
        env_vars.update({
            'MODEL_TYPE': self.model_type,
            'NUM_CLASSES': str(len(self.classes)) if self.classes else '0',
        })
        
        config = {
            'name': self.project_name,
            'description': description,
            'version': '1.0.0',
            'memory': memory,
            'timeout': timeout,
            'model_file': self._get_model_filename(),
            'api_route': api_route,
            'environment': env_vars,
            'example_request': self.input_example,
            'example_response': self.output_example
        }
        
        config_path = self.models_dir / 'config.yml'
        
        print(f"\n📝 Generating config.yml...")
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"  ✓ Config saved to {config_path}")
        print(f"  ✓ Memory: {memory}MB, Timeout: {timeout}s")
        print(f"  ✓ API Route: {api_route}")
        
        return config_path
    
    def generate_lambda_function(
        self,
        template_type: str = 'generic',
        custom_preprocessing: Optional[str] = None,
        custom_postprocessing: Optional[str] = None
    ) -> Path:
        """
        Generate lambda_function.py from template.
        
        Args:
            template_type: Type of Lambda handler template
            custom_preprocessing: Custom preprocessing code as string
            custom_postprocessing: Custom postprocessing code as string
            
        Returns:
            Path to generated lambda_function.py
        """
        print(f"\n🔧 Generating lambda_function.py...")
        print(f"  ✓ Template type: {template_type}")
        
        # Select appropriate template
        if self.model_type == 'pytorch' and 'vision' in self.project_name.lower():
            template = self._get_cv_pytorch_template()
        elif self.model_type == 'pytorch':
            template = self._get_pytorch_template()
        elif self.model_type in ['sklearn', 'xgboost', 'lightgbm']:
            template = self._get_sklearn_template()
        elif self.model_type == 'tensorflow':
            template = self._get_tensorflow_template()
        else:
            template = self._get_generic_template()
        
        # Add custom preprocessing/postprocessing if provided
        if custom_preprocessing:
            template = template.replace(
                '# CUSTOM_PREPROCESSING_PLACEHOLDER',
                custom_preprocessing
            )
        
        if custom_postprocessing:
            template = template.replace(
                '# CUSTOM_POSTPROCESSING_PLACEHOLDER',
                custom_postprocessing
            )
        
        # Add classes mapping if available
        if self.classes:
            classes_str = json.dumps(self.classes, indent=4)
            template = template.replace(
                'CLASSES = {}',
                f'CLASSES = {classes_str}'
            )
        
        lambda_path = self.models_dir / 'lambda_function.py'
        
        with open(lambda_path, 'w') as f:
            f.write(template)
        
        print(f"  ✓ Lambda function saved to {lambda_path}")
        
        return lambda_path
    
    def generate_requirements(
        self,
        additional_packages: Optional[List[str]] = None
    ) -> Path:
        """
        Generate requirements.txt with necessary dependencies.
        
        Args:
            additional_packages: Additional packages to include
            
        Returns:
            Path to generated requirements.txt
        """
        print(f"\n📋 Generating requirements.txt...")
        
        requirements = []
        
        # Base dependencies by model type
        if self.model_type == 'pytorch':
            requirements.extend([
                'torch==2.0.1',
                'torchvision==0.15.2',
                'numpy==1.24.3',
                'pillow==10.0.0'
            ])
        
        elif self.model_type == 'sklearn':
            requirements.extend([
                'scikit-learn==1.3.0',
                'numpy==1.24.3',
                'scipy==1.11.1'
            ])
        
        elif self.model_type == 'xgboost':
            requirements.extend([
                'xgboost==2.0.0',
                'numpy==1.24.3',
                'scikit-learn==1.3.0'
            ])
        
        elif self.model_type == 'lightgbm':
            requirements.extend([
                'lightgbm==4.0.0',
                'numpy==1.24.3',
                'scikit-learn==1.3.0'
            ])
        
        elif self.model_type == 'tensorflow':
            requirements.extend([
                'tensorflow==2.13.0',
                'numpy==1.24.3'
            ])
        
        # Add additional packages
        if additional_packages:
            requirements.extend(additional_packages)
        
        # Remove duplicates and sort
        requirements = sorted(list(set(requirements)))
        
        req_path = self.models_dir / 'requirements.txt'
        
        with open(req_path, 'w') as f:
            f.write('\n'.join(requirements))
        
        print(f"  ✓ Requirements saved to {req_path}")
        print(f"  ✓ Packages included:")
        for pkg in requirements:
            print(f"    - {pkg}")
        
        return req_path
    
    def generate_readme(self, additional_notes: Optional[str] = None) -> Path:
        """Generate README.md for the model directory."""
        readme_content = f"""# {self.project_name.title()} Model

## Description
AWS Lambda-deployable ML model for {self.project_name}.

## Model Information
- **Type**: {self.model_type}
- **Classes**: {len(self.classes) if self.classes else 'N/A'}
- **Model File**: {self._get_model_filename()}

## Deployment
This model is ready for AWS Lambda deployment using the automated CI/CD pipeline.

### Files
- `config.yml` - Lambda configuration
- `lambda_function.py` - Lambda handler code
- `{self._get_model_filename()}` - Trained model weights
- `requirements.txt` - Python dependencies

### API Endpoint
Once deployed, this model will be available at:
```
POST https://api.mvanslyke-ml.com/{self.project_name}
```

### Example Request
```json
{json.dumps(self.input_example, indent=2)}
```

### Example Response
```json
{json.dumps(self.output_example, indent=2)}
```

## Local Testing
```python
from lambda_function import lambda_handler

event = {{'body': json.dumps({json.dumps(self.input_example)})}}
result = lambda_handler(event, None)
print(result)
```

{additional_notes or ''}

## Generated
Auto-generated by deployment_utils.py
"""
        
        readme_path = self.models_dir / 'README.md'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print(f"  ✓ README saved to {readme_path}")
        return readme_path
    
    def package_for_deployment(
        self,
        description: str,
        memory: int = 512,
        timeout: int = 30,
        handler_template: str = 'generic',
        additional_packages: Optional[List[str]] = None,
        environment_vars: Optional[Dict] = None,
        api_route: Optional[str] = None,
        custom_preprocessing: Optional[str] = None,
        custom_postprocessing: Optional[str] = None,
        additional_notes: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Complete packaging process - generates all necessary files.
        
        Args:
            description: Model description
            memory: Lambda memory in MB
            timeout: Lambda timeout in seconds
            handler_template: Lambda handler template type
            additional_packages: Additional Python packages
            environment_vars: Additional environment variables
            api_route: Custom API route
            custom_preprocessing: Custom preprocessing code
            custom_postprocessing: Custom postprocessing code
            additional_notes: Additional notes for README
            
        Returns:
            Dictionary of generated file paths
        """
        print("\n" + "="*70)
        print(f"📦 PACKAGING MODEL FOR DEPLOYMENT: {self.project_name}")
        print("="*70)
        
        generated_files = {}
        
        # 1. Save model
        generated_files['model'] = self.save_model()
        
        # 2. Generate config.yml
        generated_files['config'] = self.generate_config(
            description=description,
            memory=memory,
            timeout=timeout,
            api_route=api_route,
            environment_vars=environment_vars
        )
        
        # 3. Generate lambda_function.py
        generated_files['lambda'] = self.generate_lambda_function(
            template_type=handler_template,
            custom_preprocessing=custom_preprocessing,
            custom_postprocessing=custom_postprocessing
        )
        
        # 4. Generate requirements.txt
        generated_files['requirements'] = self.generate_requirements(
            additional_packages=additional_packages
        )
        
        # 5. Generate README.md
        generated_files['readme'] = self.generate_readme(
            additional_notes=additional_notes
        )
        
        print("\n" + "="*70)
        print("✅ PACKAGING COMPLETE!")
        print("="*70)
        print(f"\n📁 All files saved to: {self.models_dir}")
        print("\n📝 Generated files:")
        for file_type, path in generated_files.items():
            print(f"  ✓ {file_type:12s} → {path.name}")
        
        print("\n🚀 Next steps:")
        print("  1. Test Lambda function locally")
        print("  2. Commit and push to GitHub")
        print("  3. GitHub Actions will auto-deploy to AWS Lambda")
        print(f"  4. Model will be live at: https://api.mvanslyke-ml.com/{api_route or self.project_name}")
        
        return generated_files
    
    def _get_model_filename(self) -> str:
        """Get the model filename based on model type."""
        if self.model_type == 'pytorch':
            return 'model.pt'
        elif self.model_type in ['sklearn', 'xgboost', 'lightgbm']:
            return 'model.pkl'
        elif self.model_type == 'tensorflow':
            return 'model.h5'
        else:
            return 'model.pkl'
    
    def _get_pytorch_template(self) -> str:
        """Get PyTorch Lambda function template."""
        return '''"""
AWS Lambda Handler for PyTorch Model
Auto-generated by deployment_utils.py
"""

import json
import torch
import numpy as np
from typing import Dict, Any

# Model configuration
MODEL_FILE = 'model.pt'
CLASSES = {}

# Load model at cold start (cached for warm starts)
print("Loading model...")
model = torch.load(MODEL_FILE, map_location=torch.device('cpu'))
model.eval()
print("Model loaded successfully")


def preprocess_input(input_data: Any) -> torch.Tensor:
    """
    Preprocess input data for model inference.
    
    Args:
        input_data: Raw input from API request
        
    Returns:
        Preprocessed tensor ready for model
    """
    # CUSTOM_PREPROCESSING_PLACEHOLDER
    
    # Default preprocessing
    if isinstance(input_data, list):
        input_tensor = torch.tensor(input_data, dtype=torch.float32)
    else:
        input_tensor = torch.tensor([input_data], dtype=torch.float32)
    
    return input_tensor


def postprocess_output(output: torch.Tensor) -> Dict[str, Any]:
    """
    Postprocess model output for API response.
    
    Args:
        output: Raw model output tensor
        
    Returns:
        Formatted response dictionary
    """
    # CUSTOM_POSTPROCESSING_PLACEHOLDER
    
    # Default postprocessing
    if CLASSES:
        # Classification task
        probabilities = torch.softmax(output, dim=-1)
        predicted_class = torch.argmax(probabilities, dim=-1).item()
        confidence = probabilities[0][predicted_class].item()
        
        return {
            'prediction': CLASSES.get(predicted_class, predicted_class),
            'confidence': float(confidence),
            'probabilities': {
                CLASSES.get(i, i): float(prob)
                for i, prob in enumerate(probabilities[0].tolist())
            }
        }
    else:
        # Regression or generic task
        return {
            'prediction': output.tolist()
        }


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda handler function.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        input_data = body.get('input')
        
        if input_data is None:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: input'
                })
            }
        
        # Preprocess
        input_tensor = preprocess_input(input_data)
        
        # Inference
        with torch.no_grad():
            output = model(input_tensor)
        
        # Postprocess
        result = postprocess_output(output)
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


# Local testing
if __name__ == '__main__':
    test_event = {
        'body': json.dumps({
            'input': [1.0, 2.0, 3.0, 4.0]  # Replace with actual test input
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
'''
    
    def _get_cv_pytorch_template(self) -> str:
        """Get computer vision PyTorch Lambda template."""
        return '''"""
AWS Lambda Handler for PyTorch Computer Vision Model
Auto-generated by deployment_utils.py
"""

import json
import base64
import torch
import torchvision.transforms as transforms
from PIL import Image
import io
from typing import Dict, Any

# Model configuration
MODEL_FILE = 'model.pt'
CLASSES = {}

# Image preprocessing
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# Load model at cold start
print("Loading model...")
model = torch.load(MODEL_FILE, map_location=torch.device('cpu'))
model.eval()
print("Model loaded successfully")


def preprocess_image(image_data: str) -> torch.Tensor:
    """
    Preprocess base64 encoded image.
    
    Args:
        image_data: Base64 encoded image string
        
    Returns:
        Preprocessed image tensor
    """
    # Decode base64 image
    if ',' in image_data:
        image_data = image_data.split(',')[1]
    
    image_bytes = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    
    # Apply transforms
    image_tensor = transform(image).unsqueeze(0)
    
    return image_tensor


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda handler for computer vision inference.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        image_data = body.get('image') or body.get('input')
        
        if not image_data:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: image (base64 encoded)'
                })
            }
        
        # Preprocess image
        image_tensor = preprocess_image(image_data)
        
        # Inference
        with torch.no_grad():
            output = model(image_tensor)
        
        # Process output for object detection
        if isinstance(output, list) and len(output) > 0:
            # Object detection model (Faster R-CNN, etc.)
            predictions = output[0]
            
            boxes = predictions['boxes'].cpu().numpy().tolist()
            labels = predictions['labels'].cpu().numpy().tolist()
            scores = predictions['scores'].cpu().numpy().tolist()
            
            # Filter by confidence threshold
            threshold = body.get('threshold', 0.5)
            filtered_predictions = []
            
            for box, label, score in zip(boxes, labels, scores):
                if score >= threshold:
                    filtered_predictions.append({
                        'box': box,
                        'label': CLASSES.get(label, label),
                        'confidence': float(score)
                    })
            
            result = {
                'predictions': filtered_predictions,
                'num_detections': len(filtered_predictions)
            }
        
        else:
            # Classification model
            probabilities = torch.softmax(output, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()
            
            result = {
                'prediction': CLASSES.get(predicted_class, predicted_class),
                'confidence': float(confidence),
                'probabilities': {
                    CLASSES.get(i, i): float(prob)
                    for i, prob in enumerate(probabilities[0].tolist())
                }
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


if __name__ == '__main__':
    # Local testing
    test_event = {
        'body': json.dumps({
            'image': 'data:image/jpeg;base64,/9j/4AAQ...',  # Add test image
            'threshold': 0.5
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
'''
    
    def _get_sklearn_template(self) -> str:
        """Get scikit-learn Lambda template."""
        return '''"""
AWS Lambda Handler for Scikit-learn Model
Auto-generated by deployment_utils.py
"""

import json
import pickle
import numpy as np
from typing import Dict, Any, List

# Model configuration
MODEL_FILE = 'model.pkl'
CLASSES = {}

# Load model at cold start
print("Loading model...")
with open(MODEL_FILE, 'rb') as f:
    model = pickle.load(f)
print("Model loaded successfully")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda handler for scikit-learn model.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        input_data = body.get('input') or body.get('features')
        
        if input_data is None:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: input'
                })
            }
        
        # Convert to numpy array
        if isinstance(input_data, list):
            if isinstance(input_data[0], list):
                X = np.array(input_data)
            else:
                X = np.array([input_data])
        else:
            X = np.array([[input_data]])
        
        # Make prediction
        prediction = model.predict(X)
        
        # Get probabilities if available
        result = {}
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X)
            
            if CLASSES:
                result = {
                    'prediction': CLASSES.get(int(prediction[0]), int(prediction[0])),
                    'confidence': float(np.max(probabilities[0])),
                    'probabilities': {
                        CLASSES.get(i, i): float(prob)
                        for i, prob in enumerate(probabilities[0])
                    }
                }
            else:
                result = {
                    'prediction': int(prediction[0]),
                    'confidence': float(np.max(probabilities[0])),
                    'probabilities': probabilities[0].tolist()
                }
        else:
            # Regression or model without probabilities
            result = {
                'prediction': prediction[0].tolist() if hasattr(prediction[0], 'tolist') else float(prediction[0])
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


if __name__ == '__main__':
    test_event = {
        'body': json.dumps({
            'input': [5.1, 3.5, 1.4, 0.2]  # Replace with actual test input
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
'''
    
    def _get_tensorflow_template(self) -> str:
        """Get TensorFlow Lambda template."""
        return '''"""
AWS Lambda Handler for TensorFlow Model
Auto-generated by deployment_utils.py
"""

import json
import numpy as np
import tensorflow as tf
from typing import Dict, Any

# Model configuration
MODEL_FILE = 'model.h5'
CLASSES = {}

# Load model at cold start
print("Loading model...")
model = tf.keras.models.load_model(MODEL_FILE)
print("Model loaded successfully")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda handler for TensorFlow model.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        input_data = body.get('input')
        
        if input_data is None:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: input'
                })
            }
        
        # Convert to numpy array
        X = np.array(input_data)
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        
        # Make prediction
        prediction = model.predict(X)
        
        # Format output
        if CLASSES:
            predicted_class = np.argmax(prediction, axis=-1)[0]
            confidence = float(np.max(prediction[0]))
            
            result = {
                'prediction': CLASSES.get(int(predicted_class), int(predicted_class)),
                'confidence': confidence,
                'probabilities': {
                    CLASSES.get(i, i): float(prob)
                    for i, prob in enumerate(prediction[0])
                }
            }
        else:
            result = {
                'prediction': prediction.tolist()
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


if __name__ == '__main__':
    test_event = {
        'body': json.dumps({
            'input': [[1.0, 2.0, 3.0, 4.0]]
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
'''
    
    def _get_generic_template(self) -> str:
        """Get generic Lambda template."""
        return '''"""
AWS Lambda Handler - Generic Template
Auto-generated by deployment_utils.py
"""

import json
import pickle
from typing import Dict, Any

# Model configuration
MODEL_FILE = 'model.pkl'

# Load model at cold start
print("Loading model...")
with open(MODEL_FILE, 'rb') as f:
    model = pickle.load(f)
print("Model loaded successfully")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    AWS Lambda handler function.
    
    Args:
        event: Lambda event containing request data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        input_data = body.get('input')
        
        if input_data is None:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: input'
                })
            }
        
        # Make prediction (adjust based on your model's interface)
        prediction = model.predict([input_data])
        
        # Format response
        result = {
            'prediction': prediction[0] if hasattr(prediction, '__getitem__') else prediction
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


if __name__ == '__main__':
    test_event = {
        'body': json.dumps({
            'input': 'test_input'  # Replace with actual test input
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
'''
