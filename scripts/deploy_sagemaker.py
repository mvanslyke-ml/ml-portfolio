"""
Deploy the fracture detection model from S3 to a SageMaker Serverless endpoint.

Serverless Inference scales to zero when idle — you only pay per request,
which is ideal for a portfolio demo with occasional traffic.

Prerequisites:
  1. Model artifact already uploaded to:
     s3://mvanslyke-ml-models/fasterrcnn_fracture_v1/fasterrcnn_fracture_v1.tar.gz
  2. A SageMaker execution IAM role exists in your AWS account.
     The role needs:
       - AmazonSageMakerFullAccess
       - AmazonS3ReadOnlyAccess (or scoped read on mvanslyke-ml-models)
     Trust relationship must allow service: sagemaker.amazonaws.com
  3. Environment variable SAGEMAKER_ROLE_ARN is set, e.g.:
       export SAGEMAKER_ROLE_ARN="arn:aws:iam::123456789012:role/SageMakerExecutionRole"

Usage:
  python scripts/deploy_sagemaker.py
  python scripts/deploy_sagemaker.py --memory 4096
  python scripts/deploy_sagemaker.py --delete    # tear down the endpoint
"""

import argparse
import os
import sys
import time

import boto3
from sagemaker.pytorch import PyTorchModel
from sagemaker.serverless import ServerlessInferenceConfig


# ───────────────────────────── Defaults ─────────────────────────────
S3_BUCKET = "mvanslyke-ml-models"
MODEL_NAME = "fasterrcnn_fracture_v1"
MODEL_S3_KEY = f"{MODEL_NAME}/{MODEL_NAME}.tar.gz"
ENDPOINT_NAME = "fracture-detector"

# Serverless config: 1024–6144 MB in 1024 increments.
# Faster R-CNN + PyTorch needs the high end to load and run inference.
DEFAULT_MEMORY_MB = 3072
DEFAULT_MAX_CONCURRENCY = 5

REGION = os.environ.get("AWS_REGION", "us-east-1")


def _require_role():
    role_arn = os.environ.get("SAGEMAKER_ROLE_ARN")
    if not role_arn:
        sys.exit(
            "ERROR: SAGEMAKER_ROLE_ARN environment variable is not set.\n"
            "  Create a SageMaker execution role in IAM, then:\n"
            "    export SAGEMAKER_ROLE_ARN=\"arn:aws:iam::<acct>:role/<role>\""
        )
    return role_arn


def _endpoint_exists(client, endpoint_name):
    try:
        client.describe_endpoint(EndpointName=endpoint_name)
        return True
    except client.exceptions.ClientError:
        return False


def deploy(memory_mb: int, max_concurrency: int):
    """Create or replace the SageMaker Serverless endpoint."""
    role_arn = _require_role()
    sm = boto3.client("sagemaker", region_name=REGION)

    model_s3_uri = f"s3://{S3_BUCKET}/{MODEL_S3_KEY}"
    print(f"Model artifact:  {model_s3_uri}")
    print(f"IAM role:        {role_arn}")
    print(f"Endpoint:        {ENDPOINT_NAME}")
    print(f"Memory:          {memory_mb} MB (serverless)")
    print(f"Max concurrency: {max_concurrency}")
    print()

    pytorch_model = PyTorchModel(
        model_data=model_s3_uri,
        role=role_arn,
        entry_point="inference.py",
        framework_version="2.1",
        py_version="py310",
        name=f"{MODEL_NAME.replace('_', '-')}-{int(time.time())}",
    )

    serverless_config = ServerlessInferenceConfig(
        memory_size_in_mb=memory_mb,
        max_concurrency=max_concurrency,
    )

    if _endpoint_exists(sm, ENDPOINT_NAME):
        print(f"Endpoint {ENDPOINT_NAME} exists — updating with new model...")
        pytorch_model.deploy(
            endpoint_name=ENDPOINT_NAME,
            serverless_inference_config=serverless_config,
            update_endpoint=True,
        )
    else:
        # Clean up any stale endpoint config left from a previous failed attempt.
        try:
            sm.describe_endpoint_config(EndpointConfigName=ENDPOINT_NAME)
            print(f"Removing stale endpoint config {ENDPOINT_NAME}...")
            sm.delete_endpoint_config(EndpointConfigName=ENDPOINT_NAME)
        except sm.exceptions.ClientError:
            pass

        print(f"Endpoint {ENDPOINT_NAME} not found — creating new endpoint...")
        pytorch_model.deploy(
            endpoint_name=ENDPOINT_NAME,
            serverless_inference_config=serverless_config,
        )

    print()
    print("=" * 60)
    print(f"✅ Serverless endpoint live: {ENDPOINT_NAME}")
    print("=" * 60)
    print()
    print("Test it with:")
    print(f"  aws sagemaker-runtime invoke-endpoint \\")
    print(f"    --endpoint-name {ENDPOINT_NAME} \\")
    print(f"    --content-type application/octet-stream \\")
    print(f"    --body fileb://path/to/xray.jpg \\")
    print(f"    response.json")
    print()
    print("Cost: pay-per-request, scales to zero when idle.")
    print("First request after idle has a ~10–30s cold start.")


def delete():
    """Tear down the endpoint and its config."""
    sm = boto3.client("sagemaker", region_name=REGION)

    if not _endpoint_exists(sm, ENDPOINT_NAME):
        print(f"Endpoint {ENDPOINT_NAME} does not exist. Nothing to delete.")
        return

    print(f"Deleting endpoint {ENDPOINT_NAME}...")
    sm.delete_endpoint(EndpointName=ENDPOINT_NAME)

    try:
        sm.delete_endpoint_config(EndpointConfigName=ENDPOINT_NAME)
    except sm.exceptions.ClientError:
        pass

    print(f"✅ Endpoint {ENDPOINT_NAME} deleted.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--memory",
        type=int,
        default=DEFAULT_MEMORY_MB,
        choices=[1024, 2048, 3072, 4096, 5120, 6144],
        help=f"Serverless memory in MB (default: {DEFAULT_MEMORY_MB})",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=DEFAULT_MAX_CONCURRENCY,
        help=f"Max concurrent requests (default: {DEFAULT_MAX_CONCURRENCY})",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the endpoint instead of creating/updating it",
    )
    args = parser.parse_args()

    if args.delete:
        delete()
    else:
        deploy(args.memory, args.max_concurrency)


if __name__ == "__main__":
    main()
