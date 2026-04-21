#!/usr/bin/env python3
"""
Automated Lambda Function Deployment Script
Automatically deploys all ML models as Lambda functions
"""

import os
import json
import boto3
import zipfile
import shutil
import subprocess
from pathlib import Path
import hashlib
import yaml
import sys

# AWS clients
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')
iam_client = boto3.client('iam')

# Configuration
MODELS_DIR = Path('models')
BUILD_DIR = Path('.build')
MODEL_BUCKET = 'mvanslyke-ml-models'
LAMBDA_ROLE_NAME = 'MLPortfolioLambdaRole'

def get_or_create_lambda_role():
    """Get or create IAM role for Lambda functions"""
    try:
        role = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
        return role['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        print(f"Creating IAM role: {LAMBDA_ROLE_NAME}")
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }
        
        role = iam_client.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Execution role for ML Portfolio Lambda functions'
        )
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Attach S3 read policy for model access
        iam_client.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'
        )
        
        print(f"✅ Created IAM role: {LAMBDA_ROLE_NAME}")
        return role['Role']['Arn']

def get_model_hash(model_path):
    """Calculate hash of model file for versioning"""
    hasher = hashlib.sha256()
    with open(model_path, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()[:8]

def package_lambda(model_dir):
    """Package Lambda function with dependencies"""
    model_name = model_dir.name
    config_file = model_dir / 'config.yml'
    
    if not config_file.exists():
        print(f"⚠️  Skipping {model_name}: no config.yml found")
        return None
    
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    # Container-based models are deployed separately via build_and_push.sh
    if config.get('deployment_type') == 'container':
        print(f"⏭️  Skipping {model_name}: container-based deployment (not a zip package)")
        print(f"   Deploy manually with: bash models/{model_name}/build_and_push.sh")
        return None
        
    print(f"📦 Packaging {model_name}...")
    
    # Create build directory
    build_path = BUILD_DIR / model_name
    if build_path.exists():
        shutil.rmtree(build_path)
    build_path.mkdir(parents=True, exist_ok=True)
    
    # Copy Lambda handler
    handler_file = model_dir / 'lambda_function.py'
    if handler_file.exists():
        shutil.copy(handler_file, build_path / 'lambda_function.py')
    else:
        print(f"❌ No lambda_function.py found for {model_name}")
        return None
    
    # Copy model file (if exists and small enough)
    model_file = model_dir / config.get('model_file', 'model.pkl')
    if model_file.exists():
        file_size_mb = model_file.stat().st_size / (1024 * 1024)
        if file_size_mb < 40:  # Keep under 40MB for direct packaging
            shutil.copy(model_file, build_path / model_file.name)
            model_hash = get_model_hash(model_file)
            print(f"   ✅ Included model file: {model_file.name} ({file_size_mb:.1f} MB)")
        else:
            print(f"   ⚠️  Model file too large ({file_size_mb:.1f} MB), will load from S3")
            model_hash = "s3"
    else:
        print(f"   ⚠️  Model file not found, will load from S3")
        model_hash = "s3"
    
    # Install dependencies if requirements.txt exists
    requirements_file = model_dir / 'requirements.txt'
    if requirements_file.exists():
        print(f"   Installing dependencies...")
        try:
            subprocess.run([
                'pip', 'install',
                '-r', str(requirements_file),
                '-t', str(build_path),
                '--quiet',
                '--upgrade'
            ], check=True)
            print(f"   ✅ Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Warning: Some dependencies may have failed to install")
    
    # Create deployment package
    zip_path = BUILD_DIR / f"{model_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(build_path):
            # Skip __pycache__ and .pyc files
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if not file.endswith('.pyc'):
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(build_path)
                    zipf.write(file_path, arcname)
    
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Package created: {zip_path.name} ({zip_size_mb:.2f} MB)")
    
    if zip_size_mb > 50:
        print(f"   ⚠️  Warning: Package size > 50 MB. Consider uploading to S3 first.")
    
    return {
        'name': model_name,
        'zip_path': zip_path,
        'config': config,
        'version': model_hash
    }

def deploy_lambda_function(package_info):
    """Deploy or update Lambda function"""
    function_name = f"ml-portfolio-{package_info['name']}"
    config = package_info['config']
    
    print(f"🚀 Deploying Lambda: {function_name}")
    
    # Read deployment package
    with open(package_info['zip_path'], 'rb') as f:
        zip_content = f.read()
    
    # Check if function exists
    try:
        lambda_client.get_function(FunctionName=function_name)
        function_exists = True
    except lambda_client.exceptions.ResourceNotFoundException:
        function_exists = False
    
    role_arn = get_or_create_lambda_role()
    
    environment_vars = {
        'MODEL_VERSION': package_info['version'],
        'MODEL_BUCKET': MODEL_BUCKET,
        **config.get('environment', {})
    }
    
    if function_exists:
        # Update existing function
        print(f"   Updating existing function...")
        try:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                MemorySize=config.get('memory', 512),
                Timeout=config.get('timeout', 30),
                Environment={'Variables': environment_vars}
            )
            print(f"   ✅ Function updated")
        except Exception as e:
            print(f"   ❌ Error updating function: {e}")
            return None
    else:
        # Create new function
        print(f"   Creating new function...")
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                MemorySize=config.get('memory', 512),
                Timeout=config.get('timeout', 30),
                Environment={'Variables': environment_vars},
                Description=config.get('description', 'ML Portfolio model endpoint')
            )
            print(f"   ✅ Function created")
        except Exception as e:
            print(f"   ❌ Error creating function: {e}")
            return None
    
    # Add resource-based policy to allow API Gateway
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='APIGatewayInvoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com'
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass  # Permission already exists
    except Exception as e:
        print(f"   ⚠️  Warning: Could not add API Gateway permission: {e}")
    
    # Get function ARN
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response['Configuration']['FunctionArn']
        
        print(f"   ✅ Deployed: {function_name}")
        print(f"   Version: {package_info['version']}")
        print(f"   ARN: {function_arn}")
        
        return {
            'function_name': function_name,
            'function_arn': function_arn,
            'api_route': config.get('api_route', f"/{package_info['name']}"),
            'config': config
        }
    except Exception as e:
        print(f"   ❌ Error getting function info: {e}")
        return None

def save_deployment_manifest(deployed_functions):
    """Save manifest of deployed functions for API Gateway configuration"""
    manifest = {
        'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        'functions': deployed_functions
    }
    
    BUILD_DIR.mkdir(exist_ok=True)
    manifest_path = BUILD_DIR / 'deployment_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n📄 Deployment manifest saved: {manifest_path}")
    return manifest_path

def main():
    """Main deployment pipeline"""
    print("=" * 60)
    print("🤖 ML Portfolio - Automated Lambda Deployment")
    print("=" * 60)
    
    # Create build directory
    BUILD_DIR.mkdir(exist_ok=True)
    
    # Ensure S3 bucket exists for large models
    try:
        s3_client.head_bucket(Bucket=MODEL_BUCKET)
    except:
        try:
            print(f"Creating S3 bucket: {MODEL_BUCKET}")
            s3_client.create_bucket(Bucket=MODEL_BUCKET)
            print(f"✅ Created S3 bucket: {MODEL_BUCKET}")
        except Exception as e:
            print(f"⚠️  Warning: Could not create S3 bucket: {e}")
    
    # Find all model directories
    if not MODELS_DIR.exists():
        print(f"⚠️  Models directory not found: {MODELS_DIR}")
        print("   Create a models/ directory with your model folders")
        return
    
    model_dirs = [d for d in MODELS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('EXAMPLE')]
    
    if not model_dirs:
        print(f"\n⚠️  No models found in '{MODELS_DIR}/' directory")
        print("   This is fine - add models when ready!")
        print("   Creating empty deployment manifest...")
        save_deployment_manifest([])
        print("\n✅ Skipping Lambda deployment (no models to deploy)")
        return
    
    print(f"\n📂 Found {len(model_dirs)} model(s) to deploy:\n")
    
    deployed_functions = []
    
    for model_dir in model_dirs:
        print(f"\n{'─' * 60}")
        print(f"Processing: {model_dir.name}")
        print(f"{'─' * 60}")
        
        # Package Lambda function
        package_info = package_lambda(model_dir)
        
        if package_info is None:
            continue
        
        # Deploy to Lambda
        deployment_info = deploy_lambda_function(package_info)
        if deployment_info:
            deployed_functions.append(deployment_info)
    
    # Save deployment manifest (even if empty)
    save_deployment_manifest(deployed_functions)
    
    if deployed_functions:
        print("\n" + "=" * 60)
        print("✅ Deployment Complete!")
        print("=" * 60)
        print(f"\nDeployed {len(deployed_functions)} function(s):")
        for func in deployed_functions:
            print(f"  • {func['function_name']} → {func['api_route']}")
    else:
        print("\n" + "=" * 60)
        print("✅ No models to deploy - this is normal!")
        print("=" * 60)
        print("\nAdd models when ready by creating directories in models/")
        print("Example: models/my-model/ with config.yml and lambda_function.py")

if __name__ == '__main__':
    main()
