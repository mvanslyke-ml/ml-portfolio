#!/usr/bin/env python3
"""
Fix the SageMaker inference.py to match the trained model's architecture.

Root cause: model_fn in inference.py initialises FasterRCNN with PyTorch defaults
(num_classes=7, 3 anchor aspect-ratios) but the checkpoint was trained with
num_classes=8 and 5 anchor aspect-ratios, so load_state_dict always fails.

This script:
  1. Downloads fasterrcnn_fracture_v1.tar.gz from S3
  2. Extracts it and patches code/inference.py with the correct architecture
  3. Re-packs and uploads the fixed tar.gz back to S3
  4. Redeploys the SageMaker Serverless endpoint

Usage:
  python scripts/fix_inference.py [--dry-run]
"""

import argparse
import io
import os
import sys
import tarfile
import tempfile
from pathlib import Path

import boto3

S3_BUCKET  = "mvanslyke-ml-models"
MODEL_NAME = "fasterrcnn_fracture_v1"
S3_KEY     = f"{MODEL_NAME}/{MODEL_NAME}.tar.gz"
ENDPOINT   = "fracture-detector"
REGION     = os.environ.get("AWS_REGION", "us-east-1")

# ---------------------------------------------------------------------------
# The corrected inference.py
# ---------------------------------------------------------------------------
# Architecture derived from the checkpoint weight shapes:
#   rpn.head.cls_logits.weight  → [5, 256, 1, 1]  → 5 anchors/location
#   roi_heads.cls_score.weight  → [8, 1024]        → 8 classes (bg + 7 fractures)
#
# 5 anchors/location = 1 size/level × 5 aspect-ratios  ← most common medical-imaging config
FIXED_INFERENCE_PY = '''\
"""
SageMaker inference handler for the bone fracture Faster R-CNN model.

Architecture (must match training exactly):
  - backbone  : ResNet-50 FPN v2
  - num_classes: 8  (background + 7 fracture classes)
  - anchors   : sizes=((32,),(64,),(128,),(256,),(512,)) per FPN level,
                aspect_ratios=((0.25,0.5,1.0,2.0,4.0),)*5  → 5 anchors/cell
"""
import io
import json
import os
import torch
from PIL import Image
from torchvision import transforms
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.backbone_utils import resnet_fpn_backbone
from torchvision.models.detection.rpn import AnchorGenerator

NUM_CLASSES = 8          # background + 7 fracture types
SCORE_THRESH = 0.25      # detections below this are dropped before returning

CLASS_NAMES = [
    "__background__",
    "fracture_type_1",
    "fracture_type_2",
    "fracture_type_3",
    "fracture_type_4",
    "fracture_type_5",
    "fracture_type_6",
    "fracture_type_7",
]


def _build_model():
    # Build FasterRCNN directly so we can supply a custom anchor generator.
    # fasterrcnn_resnet50_fpn_v2() hardcodes rpn_anchor_generator internally
    # and passing it again via kwargs raises "multiple values" TypeError.
    backbone = resnet_fpn_backbone(
        backbone_name="resnet50",
        weights=None,
        trainable_layers=3,
    )
    anchor_generator = AnchorGenerator(
        sizes=((32,), (64,), (128,), (256,), (512,)),
        aspect_ratios=((0.25, 0.5, 1.0, 2.0, 4.0),) * 5,
    )
    model = FasterRCNN(
        backbone,
        num_classes=NUM_CLASSES,
        rpn_anchor_generator=anchor_generator,
    )
    return model


def model_fn(model_dir):
    model = _build_model()

    # Try common weight file names
    for name in ("model.pth", "model.pt", "pytorch_model.bin"):
        weight_path = os.path.join(model_dir, name)
        if os.path.exists(weight_path):
            state_dict = torch.load(weight_path, map_location="cpu")
            # Unwrap common wrapper keys
            if isinstance(state_dict, dict) and "model_state_dict" in state_dict:
                state_dict = state_dict["model_state_dict"]
            model.load_state_dict(state_dict)
            break
    else:
        raise FileNotFoundError(
            f"No weight file found in {model_dir}. "
            "Expected model.pth, model.pt, or pytorch_model.bin."
        )

    model.eval()
    return model


def input_fn(request_body, content_type):
    """Accept raw image bytes (any PIL-readable format)."""
    image = Image.open(io.BytesIO(request_body)).convert("RGB")
    to_tensor = transforms.ToTensor()
    return [to_tensor(image)]


def predict_fn(input_data, model):
    with torch.no_grad():
        outputs = model(input_data)
    return outputs[0]


def output_fn(prediction, accept):
    """Return JSON with bounding boxes, labels, and scores."""
    boxes  = prediction["boxes"].tolist()
    labels = prediction["labels"].tolist()
    scores = prediction["scores"].tolist()

    results = []
    for box, label, score in zip(boxes, labels, scores):
        if score >= SCORE_THRESH:
            results.append({
                "box":   [round(v, 2) for v in box],
                "label": CLASS_NAMES[label] if label < len(CLASS_NAMES) else str(label),
                "score": round(score, 4),
            })

    return json.dumps({"predictions": results})
'''


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def download_tarball(s3, bucket, key):
    print(f"⬇️  Downloading s3://{bucket}/{key} ...")
    buf = io.BytesIO()
    s3.download_fileobj(bucket, key, buf)
    buf.seek(0)
    print("   Done.")
    return buf


def patch_tarball(original_buf):
    """Return a new in-memory tar.gz with inference.py replaced."""
    original_buf.seek(0)
    out_buf = io.BytesIO()

    with tarfile.open(fileobj=original_buf, mode="r:gz") as src, \
         tarfile.open(fileobj=out_buf, mode="w:gz") as dst:

        patched = False
        for member in src.getmembers():
            # inference.py may be at code/inference.py or ./code/inference.py
            if member.name.rstrip("/").endswith("inference.py"):
                print(f"   Patching member: {member.name}")
                data = FIXED_INFERENCE_PY.encode("utf-8")
                info = tarfile.TarInfo(name=member.name)
                info.size = len(data)
                dst.addfile(info, io.BytesIO(data))
                patched = True
            else:
                f = src.extractfile(member)
                if f is not None:
                    dst.addfile(member, f)
                else:
                    dst.addfile(member)

        if not patched:
            # inference.py wasn't in the archive — add it at code/inference.py
            print("   inference.py not found in archive — adding at code/inference.py")
            data = FIXED_INFERENCE_PY.encode("utf-8")
            info = tarfile.TarInfo(name="code/inference.py")
            info.size = len(data)
            dst.addfile(info, io.BytesIO(data))

    out_buf.seek(0)
    return out_buf


def upload_tarball(s3, bucket, key, buf):
    print(f"⬆️  Uploading patched archive to s3://{bucket}/{key} ...")
    s3.upload_fileobj(buf, bucket, key)
    print("   Done.")


def redeploy(dry_run):
    if dry_run:
        print("\n[dry-run] Skipping SageMaker redeployment.")
        return

    role_arn = os.environ.get("SAGEMAKER_ROLE_ARN")
    if not role_arn:
        print(
            "\n⚠️  SAGEMAKER_ROLE_ARN not set — skipping auto-redeploy.\n"
            "   Set it and re-run:\n"
            "     export SAGEMAKER_ROLE_ARN=arn:aws:iam::<account>:role/<role>\n"
            "     python scripts/fix_inference.py"
        )
        return

    import time
    sm = boto3.client("sagemaker", region_name=REGION)

    print("\n🚀 Redeploying SageMaker endpoint (pure boto3) ...")

    # ── 1. Find the container image the current endpoint already uses ────────
    # This avoids hard-coding a framework version URI.
    container_image = None
    try:
        ep      = sm.describe_endpoint(EndpointName=ENDPOINT)
        cfg     = sm.describe_endpoint_config(EndpointConfigName=ep["EndpointConfigName"])
        variant = cfg["ProductionVariants"][0]
        model   = sm.describe_model(ModelName=variant["ModelName"])
        container_image = model["PrimaryContainer"]["Image"]
        print(f"   Reusing container image: {container_image}")
    except Exception as e:
        print(f"   Could not read existing container ({e}); using default PyTorch 2.1 image.")

    if not container_image:
        # Fallback — PyTorch 2.1 CPU inference container for us-east-1
        container_image = (
            "763104351884.dkr.ecr.us-east-1.amazonaws.com/"
            "pytorch-inference:2.1.0-cpu-py310-ubuntu20.04-sagemaker"
        )

    model_s3_uri  = f"s3://{S3_BUCKET}/{S3_KEY}"
    ts            = int(time.time())
    new_model     = f"{MODEL_NAME.replace('_', '-')}-fixed-{ts}"
    new_cfg       = f"{ENDPOINT}-cfg-{ts}"

    # ── 2. Create a new SageMaker model ─────────────────────────────────────
    print(f"   Creating model: {new_model}")
    sm.create_model(
        ModelName=new_model,
        PrimaryContainer={
            "Image":        container_image,
            "ModelDataUrl": model_s3_uri,
            "Environment": {
                # inference.py is already inside the tar.gz at code/inference.py
                # — do NOT set SAGEMAKER_SUBMIT_DIRECTORY (causes a second S3 check)
                "SAGEMAKER_PROGRAM": "inference.py",
            },
        },
        ExecutionRoleArn=role_arn,
    )

    # ── 3. Create a new serverless endpoint config ───────────────────────────
    print(f"   Creating endpoint config: {new_cfg}")
    sm.create_endpoint_config(
        EndpointConfigName=new_cfg,
        ProductionVariants=[{
            "VariantName":    "AllTraffic",
            "ModelName":      new_model,
            "ServerlessConfig": {
                "MemorySizeInMB": 3072,
                "MaxConcurrency": 5,
            },
        }],
    )

    # ── 4. Update or create the endpoint ────────────────────────────────────
    try:
        sm.describe_endpoint(EndpointName=ENDPOINT)
        print(f"   Updating endpoint: {ENDPOINT}")
        sm.update_endpoint(EndpointName=ENDPOINT, EndpointConfigName=new_cfg)
    except sm.exceptions.ClientError:
        print(f"   Creating endpoint: {ENDPOINT}")
        sm.create_endpoint(EndpointName=ENDPOINT, EndpointConfigName=new_cfg)

    print(f"\n✅ Endpoint update submitted.")
    print(f"   Monitor: aws sagemaker describe-endpoint --endpoint-name {ENDPOINT} --query EndpointStatus")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Patch and show diff but do not upload or redeploy")
    args = parser.parse_args()

    s3 = boto3.client("s3", region_name=REGION)

    original = download_tarball(s3, S3_BUCKET, S3_KEY)
    patched  = patch_tarball(original)

    if args.dry_run:
        print("\n[dry-run] Patched tarball ready (not uploaded).")
    else:
        upload_tarball(s3, S3_BUCKET, S3_KEY, patched)
        redeploy(dry_run=False)
        print("\n✅ Done — endpoint will be InService in ~2–5 minutes.")
        print("   Monitor: aws sagemaker describe-endpoint --endpoint-name", ENDPOINT)


if __name__ == "__main__":
    main()
