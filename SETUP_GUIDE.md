# Complete Setup & Deployment Guide
## ML Portfolio with Auto-Deployment - mvanslyke-ml.com

**Time to Deploy**: 30-45 minutes  
**Monthly Cost**: $1-3 (after free tier)  
**Skill Level**: Intermediate

---

## 📋 Prerequisites

Before you begin, ensure you have:

- [x] AWS Account ([sign up](https://aws.amazon.com))
- [x] GitHub Account
- [x] Git installed locally
- [x] Python 3.9+ installed
- [x] AWS CLI installed
- [x] Domain name (mvanslyke-ml.com) registered
- [x] Basic knowledge of: Git, Python, AWS

---

## 🚀 Part 1: Initial AWS Setup (15 minutes)

### Step 1: Install AWS CLI

```bash
# macOS
brew install awscli

# Linux
sudo apt install awscli

# Windows
# Download from: https://aws.amazon.com/cli/

# Verify installation
aws --version
```

### Step 2: Configure AWS Credentials

```bash
# Run AWS configure
aws configure

# Enter when prompted:
AWS Access Key ID: [Your Access Key]
AWS Secret Access Key: [Your Secret Key]
Default region name: us-east-1
Default output format: json
```

**Get AWS Credentials:**
1. Go to AWS Console → IAM → Users
2. Click your username → Security credentials
3. Create access key → Command Line Interface (CLI)
4. Copy Access Key ID and Secret Access Key

### Step 3: Create S3 Bucket for Website

```bash
# Create website bucket
aws s3 mb s3://mvanslyke-ml.com --region us-east-1

# Create models bucket
aws s3 mb s3://mvanslyke-ml-models --region us-east-1

# Enable static website hosting
aws s3 website s3://mvanslyke-ml.com \
    --index-document index.html \
    --error-document index.html

# Set bucket policy for public read
cat > bucket-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::mvanslyke-ml.com/*"
    }]
}
EOF

aws s3api put-bucket-policy \
    --bucket mvanslyke-ml.com \
    --policy file://bucket-policy.json

# Remove public access block
aws s3api delete-public-access-block \
    --bucket mvanslyke-ml.com
```

### Step 4: Create CloudFront Distribution

```bash
# Create distribution config
cat > cloudfront-config.json << 'EOF'
{
    "CallerReference": "ml-portfolio-$(date +%s)",
    "Comment": "ML Portfolio - mvanslyke-ml.com",
    "Enabled": true,
    "DefaultRootObject": "index.html",
    "Origins": {
        "Quantity": 1,
        "Items": [{
            "Id": "S3-mvanslyke-ml.com",
            "DomainName": "mvanslyke-ml.com.s3-website-us-east-1.amazonaws.com",
            "CustomOriginConfig": {
                "HTTPPort": 80,
                "HTTPSPort": 443,
                "OriginProtocolPolicy": "http-only"
            }
        }]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-mvanslyke-ml.com",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 2,
            "Items": ["GET", "HEAD"],
            "CachedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"]
            }
        },
        "ForwardedValues": {
            "QueryString": false,
            "Cookies": {"Forward": "none"}
        },
        "MinTTL": 0,
        "DefaultTTL": 86400,
        "MaxTTL": 31536000,
        "Compress": true
    }
}
EOF

# Create distribution
aws cloudfront create-distribution \
    --distribution-config file://cloudfront-config.json \
    > cloudfront-output.json

# Extract distribution ID
DIST_ID=$(cat cloudfront-output.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Distribution']['Id'])")
echo "CloudFront Distribution ID: $DIST_ID"
echo "Save this for GitHub Secrets!"

# Get CloudFront domain
CF_DOMAIN=$(cat cloudfront-output.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Distribution']['DomainName'])")
echo "CloudFront Domain: $CF_DOMAIN"
```

**⏳ Wait 10-15 minutes for CloudFront to deploy**

---

## 🔧 Part 2: GitHub Repository Setup (10 minutes)

### Step 5: Clone and Configure Repository

```bash
# Create new repository on GitHub named: ml-portfolio

# Clone your repository
git clone https://github.com/mvanslyke/ml-portfolio.git
cd ml-portfolio

# Copy all project files into this directory
# (index.html, styles.css, app.js, scripts/, .github/, etc.)

# Create necessary directories
mkdir -p website
mkdir -p projects
mkdir -p models
mkdir -p scripts
mkdir -p .github/workflows
mkdir -p .build

# Move files to correct locations
mv index.html styles.css app.js website/

# Initial commit
git add .
git commit -m "Initial commit: ML portfolio with auto-deployment"
git push origin main
```

### Step 6: Configure GitHub Secrets

Go to GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Name | Value | Where to Find |
|------|-------|---------------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | IAM → Users → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | IAM → Users → Security credentials |
| `CLOUDFRONT_DISTRIBUTION_ID` | Your CloudFront ID | Output from Step 4 above |

**Screenshot guide:**
1. Click "New repository secret"
2. Name: `AWS_ACCESS_KEY_ID`
3. Secret: Paste your AWS access key
4. Click "Add secret"
5. Repeat for other two secrets

---

## 🌐 Part 3: Domain Configuration (10 minutes)

### Step 7: Request SSL Certificate

```bash
# Request certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
    --domain-name mvanslyke-ml.com \
    --subject-alternative-names "*.mvanslyke-ml.com" \
    --validation-method DNS \
    --region us-east-1 \
    > certificate-output.json

# Get certificate ARN
CERT_ARN=$(cat certificate-output.json | python3 -c "import sys, json; print(json.load(sys.stdin)['CertificateArn'])")
echo "Certificate ARN: $CERT_ARN"

# Get validation records
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region us-east-1 \
    > cert-validation.json

# Extract DNS validation records
python3 -c "
import sys, json
cert = json.load(open('cert-validation.json'))
for record in cert['Certificate']['DomainValidationOptions']:
    r = record['ResourceRecord']
    print(f\"Add DNS record:\")
    print(f\"  Type: {r['Type']}\")
    print(f\"  Name: {r['Name']}\")
    print(f\"  Value: {r['Value']}\")
    print()
"
```

### Step 8: Add DNS Records

**If using Route 53:**
```bash
# Get hosted zone ID
ZONE_ID=$(aws route53 list-hosted-zones \
    --query "HostedZones[?Name=='mvanslyke-ml.com.'].Id" \
    --output text)

# Create validation record
aws route53 change-resource-record-sets \
    --hosted-zone-id $ZONE_ID \
    --change-batch file://dns-validation.json
```

**If using external DNS provider (GoDaddy, Namecheap, etc):**
1. Log into your DNS provider
2. Add the CNAME records from Step 7 output
3. Wait 5-10 minutes for DNS propagation
4. Verify certificate:
```bash
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region us-east-1 \
    --query Certificate.Status
# Should return: ISSUED
```

### Step 9: Update CloudFront with Custom Domain

```bash
# Update CloudFront distribution
aws cloudfront update-distribution \
    --id $DIST_ID \
    --if-match $(aws cloudfront get-distribution --id $DIST_ID --query ETag --output text) \
    --distribution-config '{
        "Comment": "ML Portfolio - mvanslyke-ml.com",
        "Enabled": true,
        "Aliases": {
            "Quantity": 1,
            "Items": ["mvanslyke-ml.com"]
        },
        "ViewerCertificate": {
            "ACMCertificateArn": "'$CERT_ARN'",
            "SSLSupportMethod": "sni-only",
            "MinimumProtocolVersion": "TLSv1.2_2021"
        }
    }'
```

### Step 10: Point Domain to CloudFront

**Route 53:**
```bash
# Create A record pointing to CloudFront
cat > route53-record.json << EOF
{
    "Changes": [{
        "Action": "CREATE",
        "ResourceRecordSet": {
            "Name": "mvanslyke-ml.com",
            "Type": "A",
            "AliasTarget": {
                "HostedZoneId": "Z2FDTNDATAQYW2",
                "DNSName": "$CF_DOMAIN",
                "EvaluateTargetHealth": false
            }
        }
    }]
}
EOF

aws route53 change-resource-record-sets \
    --hosted-zone-id $ZONE_ID \
    --change-batch file://route53-record.json
```

**External DNS:**
1. Add A or CNAME record:
   - Type: CNAME
   - Name: @ (or blank)
   - Value: Your CloudFront domain (e.g., d1234.cloudfront.net)
   - TTL: 300

---

## 📝 Part 4: Add Your First Project (5 minutes)

### Step 11: Create Project Markdown File

```bash
# Create projects directory
cd ml-portfolio
mkdir -p projects

# Create your first project
cat > projects/bone-fracture-detection.md << 'EOF'
---
title: AI-Powered Bone Fracture Detection
date: Feb 2026
category: ml, cv, deploy
tags: Deep Learning, Computer Vision, PyTorch, Medical AI
github: https://github.com/mvanslyke/bone-fracture-detection
description: Deep learning system to detect fractures in X-ray images
metrics:
  Accuracy: 88.6%
  Model: ResNet50 FPN
  Dataset: 3,000+ images
---

## Overview

Built an AI system to detect bone fractures in X-ray images with 88.6% accuracy...

[Add your project details here]
EOF

# Commit and push
git add projects/bone-fracture-detection.md
git commit -m "Add: Bone Fracture Detection project"
git push origin main
```

**GitHub Actions will automatically:**
1. Generate projects.json
2. Upload to S3
3. Invalidate CloudFront
4. Deploy in ~2 minutes

**Verify:** Visit `https://mvanslyke-ml.com` and see your project!

---

## 🤖 Part 5: Deploy Your First ML Model (Optional)

### Step 12: Create Model Structure

```bash
# Create model directory
mkdir -p models/sentiment-analysis

# Create config file
cat > models/sentiment-analysis/config.yml << 'EOF'
name: sentiment-analysis
description: Real-time sentiment classification
memory: 512
timeout: 30
model_file: model.pkl
api_route: /sentiment

environment:
  MODEL_NAME: sentiment-v1
  MAX_LENGTH: 512

example_request:
  input: "This product is amazing!"

example_response:
  sentiment: "Positive"
  confidence: 0.987
EOF

# Create Lambda handler
cat > models/sentiment-analysis/lambda_function.py << 'EOF'
import json
import pickle

# Load model (cached between invocations)
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

def lambda_handler(event, context):
    # Parse input
    body = json.loads(event.get('body', '{}'))
    text = body.get('input', '')
    
    # Make prediction (replace with your model logic)
    prediction = model.predict([text])[0]
    
    # Return response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': 'https://mvanslyke-ml.com'
        },
        'body': json.dumps({
            'prediction': prediction,
            'input': text
        })
    }
EOF

# Add your trained model
cp /path/to/your/model.pkl models/sentiment-analysis/model.pkl

# Create requirements.txt
cat > models/sentiment-analysis/requirements.txt << 'EOF'
scikit-learn==1.3.0
numpy==1.24.3
EOF

# Commit and push
git add models/sentiment-analysis/
git commit -m "Deploy: Sentiment Analysis Model"
git push origin main
```

**GitHub Actions will automatically:**
1. Package Lambda function
2. Deploy to AWS Lambda
3. Create API Gateway endpoint
4. Update projects.json with demo URL

**Your API will be live at:** `https://[api-id].execute-api.us-east-1.amazonaws.com/sentiment`

---

## ✅ Part 6: Verification & Testing

### Step 13: Test Everything

```bash
# Test website
curl -I https://mvanslyke-ml.com
# Should return: 200 OK

# Test projects.json
curl https://mvanslyke-ml.com/projects.json
# Should return: JSON with your projects

# Test Lambda API (if deployed)
curl -X POST https://[your-api-url]/sentiment \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'
# Should return: prediction response
```

### Step 14: Monitor GitHub Actions

1. Go to GitHub repository → Actions tab
2. Check latest workflow run
3. Verify all jobs completed successfully:
   - ✅ Deploy Website to S3
   - ✅ Deploy Lambda Functions
   - ✅ Update Projects with Lambda Demos

---

## 💰 Cost Breakdown

### Free Tier (First 12 Months)
- S3: 5 GB storage, 20,000 GET requests
- CloudFront: 50 GB data transfer, 2M requests
- Lambda: 1M requests, 400,000 GB-seconds compute
- API Gateway: 1M requests

### After Free Tier

| Component | Usage | Monthly Cost |
|-----------|-------|-------------|
| S3 Storage (10 MB) | - | $0.23 |
| CloudFront (10K visitors) | 20 GB transfer | $0.50 |
| Lambda (100 demos) | 100 requests | $0.02 |
| Route 53 Hosted Zone | - | $0.50 |
| **Total** | | **~$1.25/month** |

**Cost Optimization Tips:**
- Enable CloudFront compression
- Set appropriate cache TTLs
- Use Lambda provisioned concurrency only if needed
- Monitor usage with AWS Cost Explorer

---

## 🔄 Daily Workflow

### Adding New Projects

```bash
# 1. Create markdown file
vim projects/my-new-project.md

# 2. Commit and push
git add projects/my-new-project.md
git commit -m "Add: My New Project"
git push origin main

# 3. Wait 2 minutes - auto-deployed! ✅
```

### Deploying New Models

```bash
# 1. Create model directory
mkdir models/my-model

# 2. Add files
cp config.yml models/my-model/
cp lambda_function.py models/my-model/
cp model.pkl models/my-model/
cp requirements.txt models/my-model/

# 3. Commit and push
git add models/my-model/
git commit -m "Deploy: My Model"
git push origin main

# 4. Wait 3 minutes - auto-deployed! ✅
```

### Updating Website Content

```bash
# Edit any file
vim website/index.html

# Commit and push
git add .
git commit -m "Update: Homepage content"
git push origin main

# Auto-deployed in 2 minutes! ✅
```

---

## 🛠️ Troubleshooting

### Website not loading
```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket mvanslyke-ml.com

# Check CloudFront distribution
aws cloudfront get-distribution --id $DIST_ID

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"
```

### Projects not appearing
```bash
# Check projects.json was generated
cat website/projects.json

# Check GitHub Actions logs
# Go to: GitHub → Actions → Latest run → View logs
```

### Lambda deployment failed
```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/ml-portfolio-[model-name] --follow

# Check IAM role exists
aws iam get-role --role-name MLPortfolioLambdaRole

# Manually deploy
cd ml-portfolio
python scripts/deploy_lambda.py
```

### API not working
```bash
# Check API Gateway
python scripts/update_api_gateway.py

# Test Lambda directly
aws lambda invoke \
  --function-name ml-portfolio-sentiment-analysis \
  --payload '{"body": "{\"input\": \"test\"}"}' \
  response.json

cat response.json
```

---

## 📚 Next Steps

1. ✅ Customize `website/index.html` with your information
2. ✅ Add more projects to `projects/` directory
3. ✅ Deploy ML models to `models/` directory
4. ✅ Configure custom domain (api.mvanslyke-ml.com) for API Gateway
5. ✅ Add Google Analytics
6. ✅ Create blog section
7. ✅ Integrate with LinkedIn, GitHub APIs

---

## 🎓 Learning Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [YAML Syntax Guide](https://yaml.org/spec/1.2.2/)

---

## 💬 Support

**Issues?** Create an issue in your GitHub repository  
**Questions?** Check the troubleshooting section above

---

**Congratulations! Your ML portfolio is live and auto-deploying!** 🎉

Every git push will automatically:
- ✅ Update your website
- ✅ Deploy new models
- ✅ Generate projects from markdown
- ✅ Invalidate caches
- ✅ Update API Gateway

**Time to build cool ML projects and watch them deploy automatically!**
