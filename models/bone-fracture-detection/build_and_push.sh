#!/bin/bash
# Build and push the bone fracture Lambda container to ECR
# Run this script on your local machine from the repo root:
#   bash models/bone-fracture-detection/build_and_push.sh

set -e

REGION="us-east-1"
REPO_NAME="ml-portfolio-bone-fracture"
FUNCTION_NAME="ml-portfolio-bone-fracture-detection"
ROLE_NAME="MLPortfolioLambdaRole"
MODEL_BUCKET="mvanslyke-ml-models"
MODEL_KEY="bone-fracture-detection/model.pt"

# ── Step 1: Get AWS account ID ────────────────────────────────────────────────
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"

echo "Account:  ${ACCOUNT_ID}"
echo "ECR URI:  ${ECR_URI}"
echo ""

# ── Step 2: Upload model weights to S3 ───────────────────────────────────────
echo ">>> Uploading model to S3..."
echo "    Make sure your model file is at: trained_models/model1_best.pt"
echo ""

if [ ! -f "trained_models/model1_best.pt" ]; then
    echo "ERROR: trained_models/model1_best.pt not found."
    echo "       Train the model first with: python train_bone_fracture_model.py"
    exit 1
fi

aws s3 cp trained_models/model1_best.pt \
    s3://${MODEL_BUCKET}/${MODEL_KEY} \
    --region ${REGION}

echo "✓ Model uploaded to s3://${MODEL_BUCKET}/${MODEL_KEY}"
echo ""

# ── Step 3: Create ECR repository (safe to run if already exists) ─────────────
echo ">>> Creating ECR repository..."
aws ecr create-repository \
    --repository-name ${REPO_NAME} \
    --region ${REGION} 2>/dev/null || echo "  (repository already exists)"
echo ""

# ── Step 4: Authenticate Docker with ECR ─────────────────────────────────────
echo ">>> Authenticating Docker with ECR..."
aws ecr get-login-password --region ${REGION} \
    | docker login --username AWS --password-stdin \
      "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
echo ""

# ── Step 5: Build Docker image ────────────────────────────────────────────────
echo ">>> Building Docker image (this takes a few minutes)..."
docker build \
    --platform linux/amd64 \
    -t ${REPO_NAME}:latest \
    models/bone-fracture-detection/
echo "✓ Image built"
echo ""

# ── Step 6: Tag and push ──────────────────────────────────────────────────────
echo ">>> Pushing image to ECR..."
docker tag ${REPO_NAME}:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest
echo "✓ Image pushed to ${ECR_URI}:latest"
echo ""

# ── Step 7: Get the Lambda IAM role ARN ──────────────────────────────────────
ROLE_ARN=$(aws iam get-role \
    --role-name ${ROLE_NAME} \
    --query Role.Arn \
    --output text)

# ── Step 8: Create or update the Lambda function ──────────────────────────────
echo ">>> Deploying Lambda function..."

EXISTING=$(aws lambda get-function \
    --function-name ${FUNCTION_NAME} \
    --region ${REGION} 2>/dev/null || echo "not_found")

if echo "$EXISTING" | grep -q "not_found"; then
    # Create new function
    aws lambda create-function \
        --function-name ${FUNCTION_NAME} \
        --package-type Image \
        --code ImageUri=${ECR_URI}:latest \
        --role ${ROLE_ARN} \
        --memory-size 3008 \
        --timeout 120 \
        --region ${REGION} \
        --environment Variables="{
            MODEL_BUCKET=${MODEL_BUCKET},
            MODEL_KEY=${MODEL_KEY},
            IMAGE_SIZE=224,
            CONFIDENCE_THRESHOLD=0.5
        }"
    echo "✓ Lambda function created"
else
    # Update existing function
    aws lambda update-function-code \
        --function-name ${FUNCTION_NAME} \
        --image-uri ${ECR_URI}:latest \
        --region ${REGION}
    echo "✓ Lambda function updated"
fi

echo ""
echo ">>> Adding API Gateway permission..."
aws lambda add-permission \
    --function-name ${FUNCTION_NAME} \
    --statement-id APIGatewayInvoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --region ${REGION} 2>/dev/null || echo "  (permission already exists)"

echo ""
echo "========================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "Function: ${FUNCTION_NAME}"
echo "Image:    ${ECR_URI}:latest"
echo "Model:    s3://${MODEL_BUCKET}/${MODEL_KEY}"
echo ""
echo "Next: run  python scripts/update_api_gateway.py"
echo "      to wire this function to API Gateway and get your live URL."
echo ""
