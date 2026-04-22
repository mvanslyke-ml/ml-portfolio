#!/usr/bin/env python3
"""
Automated Lambda Function Deployment Script
Automatically deploys all ML models as Lambda functions
"""

import os
import json
import time
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

SAGEMAKER_INVOKE_POLICY_NAME = 'SageMakerInvokeEndpoint'
SAGEMAKER_INVOKE_POLICY_DOC = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": ["sagemaker:InvokeEndpoint"],
        "Resource": "*"
    }]
}

# Managed policy ARNs that every Lambda execution role must have
_REQUIRED_MANAGED_POLICIES = [
    'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
    'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess',
]


def _ensure_managed_policies(role_name):
    """Make sure all required managed policies are attached to the role.

    When get_or_create_lambda_role() finds an existing role it previously
    skipped re-attaching managed policies, which left roles without
    AWSLambdaBasicExecutionRole — causing Lambda to run silently without
    CloudWatch Logs.
    """
    try:
        attached = iam_client.list_attached_role_policies(RoleName=role_name)
        current_arns = {p['PolicyArn'] for p in attached.get('AttachedPolicies', [])}
    except Exception as e:
        print(f"   ⚠️  Could not list role policies: {e}")
        return

    for arn in _REQUIRED_MANAGED_POLICIES:
        if arn not in current_arns:
            try:
                iam_client.attach_role_policy(RoleName=role_name, PolicyArn=arn)
                short = arn.split('/')[-1]
                print(f"   ✅ Attached managed policy: {short}")
            except Exception as e:
                print(f"   ⚠️  Could not attach {arn}: {e}")


def _ensure_sagemaker_invoke_policy(role_name):
    """Attach an inline policy that lets the role invoke any SageMaker endpoint."""
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=SAGEMAKER_INVOKE_POLICY_NAME,
            PolicyDocument=json.dumps(SAGEMAKER_INVOKE_POLICY_DOC)
        )
    except Exception as e:
        print(f"   ⚠️  Could not attach SageMaker invoke policy: {e}")


def get_or_create_lambda_role():
    """Get or create IAM role for Lambda functions"""
    try:
        role = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
        _ensure_managed_policies(LAMBDA_ROLE_NAME)       # CloudWatch Logs + S3
        _ensure_sagemaker_invoke_policy(LAMBDA_ROLE_NAME)  # SageMaker invoke
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

        iam_client.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )

        iam_client.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'
        )

        _ensure_sagemaker_invoke_policy(LAMBDA_ROLE_NAME)

        print(f"✅ Created IAM role: {LAMBDA_ROLE_NAME}")
        print("   Waiting 15s for IAM role to propagate...")
        time.sleep(15)

        return role['Role']['Arn']


def wait_for_function_ready(function_name, max_wait=60):
    """Wait until Lambda function is not in a pending update state."""
    print(f"   Waiting for function to be ready...", end='', flush=True)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = lambda_client.get_function_configuration(FunctionName=function_name)
        state = resp.get('LastUpdateStatus', 'Successful')
        if state in ('Successful', 'Failed'):
            print(" ready.")
            return state == 'Successful'
        print('.', end='', flush=True)
        time.sleep(3)
    print(" timed out.")
    return False


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

    if config.get('deployment_type') == 'container':
        print(f"⏭️  Skipping {model_name}: container-based deployment")
        print(f"   Deploy manually with: bash models/{model_name}/build_and_push.sh")
        return None

    print(f"📦 Packaging {model_name}...")

    build_path = BUILD_DIR / model_name
    if build_path.exists():
        shutil.rmtree(build_path)
    build_path.mkdir(parents=True, exist_ok=True)

    handler_file = model_dir / 'lambda_function.py'
    if handler_file.exists():
        shutil.copy(handler_file, build_path / 'lambda_function.py')
    else:
        print(f"❌ No lambda_function.py found for {model_name}")
        return None

    model_file = model_dir / config.get('model_file', 'model.pkl')
    if model_file.exists():
        file_size_mb = model_file.stat().st_size / (1024 * 1024)
        if file_size_mb < 40:
            shutil.copy(model_file, build_path / model_file.name)
            model_hash = get_model_hash(model_file)
            print(f"   ✅ Included model file: {model_file.name} ({file_size_mb:.1f} MB)")
        else:
            print(f"   ⚠️  Model file too large ({file_size_mb:.1f} MB), will load from S3")
            model_hash = "s3"
    else:
        print(f"   ⚠️  Model file not found, will load from S3")
        model_hash = "s3"

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
        except subprocess.CalledProcessError:
            print(f"   ⚠️  Warning: Some dependencies may have failed to install")

    zip_path = BUILD_DIR / f"{model_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(build_path):
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

    with open(package_info['zip_path'], 'rb') as f:
        zip_content = f.read()

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
        print(f"   Updating existing function...")
        try:
            # Step 1: update code
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )

            # Step 2: wait for AWS to finish propagating the code update
            # before touching configuration — avoids ResourceConflictException
            if not wait_for_function_ready(function_name):
                print(f"   ❌ Function did not reach ready state after code update")
                return None

            # Step 3: now safe to update configuration
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                MemorySize=config.get('memory', 512),
                Timeout=config.get('timeout', 30),
                Environment={'Variables': environment_vars}
            )

            # Wait again — config update also takes a moment
            wait_for_function_ready(function_name)
            print(f"   ✅ Function updated")

        except Exception as e:
            print(f"   ❌ Error updating function: {e}")
            return None
    else:
        print(f"   Creating new function...")
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.12',
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


def save_deployment_manifest(deployed_functions, failed_count=0):
    """Save manifest of deployed functions for API Gateway configuration"""
    import datetime
    manifest = {
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'functions': deployed_functions,
        'failed': failed_count
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

    BUILD_DIR.mkdir(exist_ok=True)

    try:
        s3_client.head_bucket(Bucket=MODEL_BUCKET)
    except Exception:
        try:
            print(f"Creating S3 bucket: {MODEL_BUCKET}")
            s3_client.create_bucket(Bucket=MODEL_BUCKET)
            print(f"✅ Created S3 bucket: {MODEL_BUCKET}")
        except Exception as e:
            print(f"⚠️  Warning: Could not create S3 bucket: {e}")

    if not MODELS_DIR.exists():
        print(f"⚠️  Models directory not found: {MODELS_DIR}")
        return

    model_dirs = [
        d for d in MODELS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('EXAMPLE')
    ]

    if not model_dirs:
        print(f"\n⚠️  No models found in '{MODELS_DIR}/' directory")
        save_deployment_manifest([])
        print("\n✅ Skipping Lambda deployment (no models to deploy)")
        return

    print(f"\n📂 Found {len(model_dirs)} model(s) to deploy:\n")

    deployed_functions = []
    failed_names = []

    for model_dir in model_dirs:
        print(f"\n{'─' * 60}")
        print(f"Processing: {model_dir.name}")
        print(f"{'─' * 60}")

        package_info = package_lambda(model_dir)
        if package_info is None:
            continue

        deployment_info = deploy_lambda_function(package_info)
        if deployment_info:
            deployed_functions.append(deployment_info)
        else:
            failed_names.append(model_dir.name)

    save_deployment_manifest(deployed_functions, failed_count=len(failed_names))

    print("\n" + "=" * 60)
    if deployed_functions:
        print("✅ Deployment Complete!")
        print("=" * 60)
        print(f"\nDeployed {len(deployed_functions)} function(s):")
        for func in deployed_functions:
            print(f"  • {func['function_name']} → {func['api_route']}")
    else:
        print("❌ Deployment finished with no successful deployments.")
        print("=" * 60)

    if failed_names:
        print(f"\n⚠️  Failed ({len(failed_names)}): {', '.join(failed_names)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
