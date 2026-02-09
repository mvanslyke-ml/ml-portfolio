# Quick Reference Guide
## Common Commands & Operations

---

## 📝 Daily Operations

### Add New Project

```bash
# 1. Create markdown file
vim projects/my-project.md

# 2. Add frontmatter and content
# 3. Commit and push
git add projects/my-project.md
git commit -m "Add: My Project Title"
git push origin main

# ✅ Auto-deployed in 2 minutes!
```

### Deploy New ML Model

```bash
# 1. Create model directory
mkdir -p models/my-model

# 2. Add files
# - config.yml
# - lambda_function.py  
# - model.pkl
# - requirements.txt

# 3. Commit and push
git add models/my-model/
git commit -m "Deploy: My Model Name"
git push origin main

# ✅ Auto-deployed in 3 minutes!
```

### Update Website Content

```bash
# 1. Edit file
vim website/index.html

# 2. Commit and push
git add .
git commit -m "Update: Homepage content"
git push origin main

# ✅ Auto-deployed in 2 minutes!
```

---

## 🔧 Maintenance Commands

### Invalidate CloudFront Cache

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

### Regenerate projects.json

```bash
python3 scripts/generate_projects.py
```

### Manual Lambda Deployment

```bash
python3 scripts/deploy_lambda.py
```

### Update API Gateway

```bash
python3 scripts/update_api_gateway.py
```

---

## 🧪 Testing Commands

### Test Website Locally

```bash
cd website
python3 -m http.server 8000
# Visit: http://localhost:8000
```

### Validate JSON

```bash
python3 -m json.tool website/projects.json
```

### Test Lambda Function

```bash
aws lambda invoke \
  --function-name ml-portfolio-MODEL-NAME \
  --payload '{"body": "{\"input\": \"test\"}"}' \
  response.json

cat response.json
```

### Test API Endpoint

```bash
curl -X POST https://YOUR_API_URL/endpoint \
  -H "Content-Type: application/json" \
  -d '{"input": "test data"}'
```

---

## 📊 Monitoring Commands

### Check GitHub Actions

```bash
# Visit in browser:
# https://github.com/mvanslyke/ml-portfolio/actions
```

### View Lambda Logs

```bash
aws logs tail /aws/lambda/ml-portfolio-MODEL-NAME --follow
```

### Check S3 Contents

```bash
aws s3 ls s3://mvanslyke-ml.com/ --recursive
```

### Check CloudFront Status

```bash
aws cloudfront get-distribution --id YOUR_DIST_ID
```

### Monitor AWS Costs

```bash
# Current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -v1d +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost

# Last 30 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -v-30d +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost
```

---

## 🔍 Debugging Commands

### Check AWS Credentials

```bash
aws sts get-caller-identity
```

### Test S3 Access

```bash
aws s3 ls s3://mvanslyke-ml.com/
```

### Check Lambda Functions

```bash
aws lambda list-functions | grep ml-portfolio
```

### Check API Gateway

```bash
aws apigatewayv2 get-apis
```

### View Build Artifacts

```bash
cat .build/deployment_manifest.json
cat .build/api_docs.json
```

---

## 🗑️ Cleanup Commands

### Delete Lambda Function

```bash
aws lambda delete-function --function-name ml-portfolio-MODEL-NAME
```

### Delete API Gateway

```bash
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='ML-Portfolio-API'].ApiId" --output text)
aws apigatewayv2 delete-api --api-id $API_ID
```

### Clear S3 Bucket (Careful!)

```bash
aws s3 rm s3://mvanslyke-ml.com --recursive
```

---

## 📦 Git Commands

### Common Git Operations

```bash
# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "Description"

# Push to GitHub
git push origin main

# View commit history
git log --oneline -10

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard local changes
git checkout -- filename
```

---

## 🔐 Security Commands

### Rotate AWS Credentials

```bash
# 1. Create new access key in AWS Console
# 2. Update locally
aws configure

# 3. Update GitHub Secrets
# Go to: Settings → Secrets → Update secrets

# 4. Delete old access key in AWS Console
```

### Check for Exposed Secrets

```bash
# Check git history for secrets (don't push if found!)
git log --all -p | grep -i "aws_access_key"
git log --all -p | grep -i "secret"
```

---

## 📝 Project Frontmatter Template

```yaml
---
title: Project Title
date: Feb 2026
category: ml, cv, nlp, deploy
tags: Python, TensorFlow, AWS, Docker
github: https://github.com/mvanslyke/project
demo_url: https://api.mvanslyke-ml.com/endpoint
demo_description: What the demo does
article: https://medium.com/@yourname/article
metrics:
  Accuracy: 95.2%
  Latency: 50ms
  Dataset: 10K samples
---
```

---

## 🤖 Lambda Config Template

```yaml
name: model-name
description: What the model does
memory: 512
timeout: 30
model_file: model.pkl
api_route: /model-endpoint

environment:
  MODEL_VERSION: v1.0
  PARAM_NAME: value

example_request:
  input: "example input"

example_response:
  prediction: "result"
  confidence: 0.95
```

---

## 📊 Useful AWS Console URLs

```
S3 Buckets:
https://s3.console.aws.amazon.com/s3/

CloudFront:
https://console.aws.amazon.com/cloudfront/

Lambda:
https://console.aws.amazon.com/lambda/

API Gateway:
https://console.aws.amazon.com/apigateway/

IAM:
https://console.aws.amazon.com/iam/

CloudWatch Logs:
https://console.aws.amazon.com/cloudwatch/

Cost Explorer:
https://console.aws.amazon.com/cost-management/

ACM (Certificates):
https://console.aws.amazon.com/acm/
```

---

## 🎯 Quick Checklist

Before each push:
- [ ] Test locally
- [ ] Validate JSON
- [ ] Check for secrets in code
- [ ] Write descriptive commit message

After each push:
- [ ] Check GitHub Actions (green checkmarks)
- [ ] Verify website updates
- [ ] Test any new features
- [ ] Monitor for errors

Weekly:
- [ ] Check AWS costs
- [ ] Review CloudWatch logs
- [ ] Update projects if needed

Monthly:
- [ ] Rotate AWS keys (every 90 days)
- [ ] Update dependencies
- [ ] Review and optimize Lambda functions

---

## 🆘 Emergency Contacts

**AWS Support**: https://aws.amazon.com/support/  
**GitHub Support**: https://support.github.com/

**Documentation**:
- COMPLETE_INSTRUCTIONS.md
- SETUP_GUIDE.md
- DEBUGGING_GUIDE.md
- DEPLOYMENT_CHECKLIST.md

---

## 💡 Pro Tips

1. **Use descriptive commit messages** - Makes debugging easier
2. **Test locally first** - Saves GitHub Actions minutes
3. **Monitor costs weekly** - Avoid surprises
4. **Keep models < 40 MB** - Faster deployments
5. **Use CloudFront invalidations sparingly** - They count towards free tier
6. **Tag Lambda functions** - Easy cost tracking
7. **Enable CloudWatch alarms** - Get notified of errors
8. **Back up models to S3** - Never lose trained models
9. **Document API endpoints** - Easy integration later
10. **Celebrate small wins** - Each project is an achievement!

---

**Save this file for quick reference!** 📌

**Print it out or bookmark it!** 🔖
