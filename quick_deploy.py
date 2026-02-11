#!/usr/bin/env python3
"""
Quick Deploy CLI
================

Simple command-line tool for deploying trained models to AWS Lambda.

Usage:
    python quick_deploy.py --model model.pt --name my-model --type pytorch
    
Examples:
    # PyTorch model
    python quick_deploy.py --model trained_models/model.pt --name fracture-detector --type pytorch
    
    # Scikit-learn model
    python quick_deploy.py --model trained_models/model.pkl --name iris-classifier --type sklearn
    
    # With custom settings
    python quick_deploy.py --model model.pt --name my-model --memory 2048 --timeout 60
"""

import argparse
import sys
from pathlib import Path
import torch
import pickle
import json

try:
    from deployment_utils import ModelDeployer
except ImportError:
    print("Error: deployment_utils.py not found in current directory")
    print("Make sure deployment_utils.py is in the same directory as this script")
    sys.exit(1)


def load_model(model_path: Path, model_type: str):
    """Load model from file based on type"""
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    print(f"Loading model from {model_path}...")
    
    if model_type == 'pytorch':
        model = torch.load(model_path, map_location='cpu')
        if hasattr(model, 'eval'):
            model.eval()
    elif model_type in ['sklearn', 'xgboost', 'lightgbm']:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    elif model_type == 'tensorflow':
        import tensorflow as tf
        model = tf.keras.models.load_model(model_path)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    
    print("✓ Model loaded successfully")
    return model


def interactive_setup():
    """Interactive setup for users who don't want to use CLI args"""
    print("\n" + "="*70)
    print("🚀 Quick Deploy - Interactive Setup")
    print("="*70 + "\n")
    
    # Get model path
    model_path = input("Enter path to trained model file: ").strip()
    model_path = Path(model_path)
    
    if not model_path.exists():
        print(f"Error: File not found: {model_path}")
        sys.exit(1)
    
    # Get model type
    print("\nModel types:")
    print("  1. PyTorch")
    print("  2. Scikit-learn")
    print("  3. XGBoost")
    print("  4. LightGBM")
    print("  5. TensorFlow")
    
    type_map = {
        '1': 'pytorch',
        '2': 'sklearn',
        '3': 'xgboost',
        '4': 'lightgbm',
        '5': 'tensorflow'
    }
    
    choice = input("\nSelect model type (1-5): ").strip()
    model_type = type_map.get(choice)
    
    if not model_type:
        print("Error: Invalid choice")
        sys.exit(1)
    
    # Get project name
    project_name = input("\nEnter project name (e.g., 'fraud-detector'): ").strip()
    if not project_name:
        print("Error: Project name required")
        sys.exit(1)
    
    # Get description
    description = input("Enter brief description: ").strip()
    if not description:
        description = f"{project_name} ML model"
    
    # Get memory
    memory_input = input("\nLambda memory in MB (default: 512): ").strip()
    memory = int(memory_input) if memory_input else 512
    
    # Get timeout
    timeout_input = input("Lambda timeout in seconds (default: 30): ").strip()
    timeout = int(timeout_input) if timeout_input else 30
    
    # Ask about classes
    has_classes = input("\nDoes your model have class labels? (y/n): ").strip().lower()
    classes = {}
    
    if has_classes == 'y':
        print("\nEnter class mappings (format: 0=class_name, or leave empty to finish):")
        while True:
            entry = input("  Class: ").strip()
            if not entry:
                break
            try:
                idx, name = entry.split('=')
                classes[int(idx)] = name.strip()
            except ValueError:
                print("  Invalid format. Use: 0=class_name")
    
    return {
        'model_path': model_path,
        'model_type': model_type,
        'project_name': project_name,
        'description': description,
        'memory': memory,
        'timeout': timeout,
        'classes': classes
    }


def main():
    parser = argparse.ArgumentParser(
        description='Quick Deploy - Package ML models for AWS Lambda',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model model.pt --name fracture-detector --type pytorch
  %(prog)s --model model.pkl --name iris-classifier --type sklearn --memory 1024
  %(prog)s --interactive
        """
    )
    
    parser.add_argument(
        '--model',
        type=str,
        help='Path to trained model file'
    )
    
    parser.add_argument(
        '--name',
        type=str,
        help='Project name (e.g., "fraud-detector")'
    )
    
    parser.add_argument(
        '--type',
        type=str,
        choices=['pytorch', 'sklearn', 'xgboost', 'lightgbm', 'tensorflow'],
        help='Model type'
    )
    
    parser.add_argument(
        '--description',
        type=str,
        help='Brief model description'
    )
    
    parser.add_argument(
        '--memory',
        type=int,
        default=512,
        help='Lambda memory in MB (default: 512)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Lambda timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--classes',
        type=str,
        help='Class mappings as JSON (e.g., \'{"0": "cat", "1": "dog"}\')'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run interactive setup wizard'
    )
    
    parser.add_argument(
        '--template',
        type=str,
        choices=['generic', 'computer_vision', 'nlp', 'classification', 'regression'],
        default='generic',
        help='Lambda handler template (default: generic)'
    )
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive or (not args.model and not args.name):
        config = interactive_setup()
    else:
        # Validate required args
        if not args.model or not args.name or not args.type:
            parser.error("--model, --name, and --type are required (or use --interactive)")
        
        config = {
            'model_path': Path(args.model),
            'model_type': args.type,
            'project_name': args.name,
            'description': args.description or f"{args.name} ML model",
            'memory': args.memory,
            'timeout': args.timeout,
            'classes': json.loads(args.classes) if args.classes else {}
        }
    
    # Load model
    try:
        model = load_model(config['model_path'], config['model_type'])
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    # Create deployer
    deployer = ModelDeployer(
        model=model,
        project_name=config['project_name'],
        model_type=config['model_type'],
        classes=config['classes']
    )
    
    # Package for deployment
    print("\n" + "="*70)
    print("Packaging model for deployment...")
    print("="*70 + "\n")
    
    generated_files = deployer.package_for_deployment(
        description=config['description'],
        memory=config['memory'],
        timeout=config['timeout'],
        handler_template=args.template if not args.interactive else 'generic'
    )
    
    print("\n" + "="*70)
    print("✅ DEPLOYMENT PACKAGE READY!")
    print("="*70)
    print(f"""
📁 Files generated in: models/{config['project_name']}/

🚀 Next steps:

1. Test locally:
   cd models/{config['project_name']}
   python lambda_function.py

2. Commit and push:
   git add models/{config['project_name']}/
   git commit -m "Add: {config['project_name']}"
   git push

3. Model will be deployed automatically by GitHub Actions

4. Access your API at:
   https://api.mvanslyke-ml.com/{config['project_name']}

Need help? Check DEPLOYMENT_README.md for detailed documentation.
""")


if __name__ == "__main__":
    main()
