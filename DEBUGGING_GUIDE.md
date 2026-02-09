# Debugging & Testing Guide
## ML Portfolio Auto-Deployment System

This guide helps you debug issues and ensure all components are working correctly.

---

## 🧪 Pre-Deployment Testing

### Test 1: Local Website Preview

```bash
cd website

# Start local server
python3 -m http.server 8000

# Visit: http://localhost:8000
```

**Expected Result:**
- ✅ Website loads with all styles
- ✅ Navigation works
- ✅ Particle animations visible
- ✅ Projects section shows placeholder text

**Troubleshooting:**
- Missing styles? Check `styles.css` is in same directory
- JavaScript errors? Check console (F12) for errors
- Projects not loading? Ensure `projects.json` exists

---

### Test 2: Validate Projects JSON

```bash
# Validate JSON syntax
python3 -m json.tool website/projects.json

# Or use online validator
# https://jsonlint.com
```

**Expected Result:**
```
✅ Valid JSON
```

**Troubleshooting:**
- Syntax error? Check for missing commas, quotes, brackets
- Use VSCode or another editor with JSON validation

---

### Test 3: Test Project Generation Script

```bash
# Run script locally
python3 scripts/generate_projects.py

# Check output
cat website/projects.json
```

**Expected Result:**
```
✅ Generated projects.json with [N] project(s)
```

**Troubleshooting:**
```bash
# Missing dependencies?
pip install pyyaml

# YAML errors?
python3 -c "import yaml; yaml.safe_load(open('projects/your-project.md').read())"
```

---

## 🔍 Component Testing

### Test 4: AWS Credentials

```bash
# Test AWS CLI access
aws sts get-caller-identity
```

**Expected Result:**
```json
{
    "UserId": "...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**Troubleshooting:**
```bash
# Reconfigure AWS CLI
aws configure

# Check credentials file
cat ~/.aws/credentials
```

---

### Test 5: S3 Bucket Access

```bash
# Test bucket exists
aws s3 ls s3://mvanslyke-ml.com

# Test public access
curl -I http://mvanslyke-ml.com.s3-website-us-east-1.amazonaws.com
```

**Expected Result:**
```
HTTP/1.1 200 OK
```

**Troubleshooting:**
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket mvanslyke-ml.com

# Verify public access block is removed
aws s3api get-public-access-block --bucket mvanslyke-ml.com
# Should return: "NoSuchPublicAccessBlockConfiguration"
```

---

### Test 6: CloudFront Distribution

```bash
# Get distribution status
aws cloudfront get-distribution \
  --id YOUR_DIST_ID \
  --query "Distribution.Status"
```

**Expected Result:**
```
"Deployed"
```

**Troubleshooting:**
```bash
# If status is "InProgress", wait 10-15 minutes

# Test CloudFront URL
curl -I https://YOUR_CLOUDFRONT_DOMAIN.cloudfront.net
```

---

### Test 7: Lambda Function Deployment

```bash
# Run deployment script
python3 scripts/deploy_lambda.py

# Check function exists
aws lambda get-function --function-name ml-portfolio-sentiment-analysis
```

**Expected Result:**
```
✅ Deployed: ml-portfolio-sentiment-analysis
```

**Troubleshooting:**
```bash
# Check IAM role exists
aws iam get-role --role-name MLPortfolioLambdaRole

# Check function logs
aws logs tail /aws/lambda/ml-portfolio-sentiment-analysis --follow

# Test function directly
aws lambda invoke \
  --function-name ml-portfolio-sentiment-analysis \
  --payload '{"body": "{\"input\": \"test\"}"}' \
  response.json

cat response.json
```

---

### Test 8: API Gateway

```bash
# Run API Gateway script
python3 scripts/update_api_gateway.py

# Test endpoint
curl -X POST https://YOUR_API_ENDPOINT/sentiment \
  -H "Content-Type: application/json" \
  -d '{"input": "This is a test"}'
```

**Expected Result:**
```json
{
  "prediction": "...",
  "input": "This is a test"
}
```

**Troubleshooting:**
```bash
# Check API exists
aws apigatewayv2 get-apis

# Check routes
cat .build/api_docs.json

# Check CORS
curl -I -X OPTIONS https://YOUR_API_ENDPOINT/sentiment
```

---

## 🚀 GitHub Actions Testing

### Test 9: GitHub Secrets

**Check secrets are set:**
1. Go to GitHub → Settings → Secrets and variables → Actions
2. Verify these exist:
   - ✅ AWS_ACCESS_KEY_ID
   - ✅ AWS_SECRET_ACCESS_KEY
   - ✅ CLOUDFRONT_DISTRIBUTION_ID

**Troubleshooting:**
- Secrets not showing? Click "Update" to verify they're saved
- Wrong values? Delete and re-create

---

### Test 10: Workflow Syntax

```bash
# Validate workflow file
cat .github/workflows/deploy.yml

# Or use online validator
# https://rhysd.github.io/actionlint/
```

**Expected Result:**
```
✅ Valid YAML syntax
```

**Troubleshooting:**
```bash
# Install actionlint
brew install actionlint

# Run validation
actionlint .github/workflows/deploy.yml
```

---

### Test 11: Manual Workflow Trigger

1. Go to GitHub → Actions
2. Select "Deploy ML Portfolio" workflow
3. Click "Run workflow" → "Run workflow"
4. Watch the jobs execute

**Expected Result:**
- ✅ Deploy Website to S3 (green checkmark)
- ✅ Deploy Lambda Functions (green checkmark)
- ✅ Update Projects with Lambda Demos (green checkmark)

**Troubleshooting:**
- Job failed? Click on it to see logs
- Permission denied? Check AWS credentials
- S3 upload failed? Check bucket permissions

---

## 🔧 Common Issues & Solutions

### Issue 1: Projects Not Appearing on Website

**Symptoms:**
- Website loads but projects section is empty
- Console shows "No projects.json file found"

**Debug Steps:**
```bash
# 1. Check projects.json exists
ls website/projects.json

# 2. Check it's valid JSON
python3 -m json.tool website/projects.json

# 3. Check it's in S3
aws s3 ls s3://mvanslyke-ml.com/projects.json

# 4. Check file content
curl https://mvanslyke-ml.com/projects.json

# 5. Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/projects.json"
```

**Solution:**
```bash
# Regenerate and upload
python3 scripts/generate_projects.py
aws s3 cp website/projects.json s3://mvanslyke-ml.com/projects.json
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

---

### Issue 2: Lambda Function Not Deploying

**Symptoms:**
- GitHub Action fails on "Deploy Lambda Functions"
- Error: "Package size exceeds 50 MB"

**Debug Steps:**
```bash
# 1. Check package size
du -sh .build/your-model.zip

# 2. Check model file size
du -sh models/your-model/model.pkl
```

**Solution for Large Models:**
```bash
# Upload model to S3 separately
aws s3 cp models/your-model/model.pkl \
  s3://mvanslyke-ml-models/your-model/model.pkl

# Remove from deployment package
rm models/your-model/model.pkl

# Update lambda_function.py to load from S3
```

---

### Issue 3: API Not Working (CORS Errors)

**Symptoms:**
- Browser console: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Debug Steps:**
```bash
# 1. Test API directly
curl -X POST https://YOUR_API/sentiment \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# 2. Check CORS headers
curl -I -X OPTIONS https://YOUR_API/sentiment
```

**Solution:**
```python
# Ensure lambda_function.py has CORS headers
return {
    'statusCode': 200,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://mvanslyke-ml.com',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    },
    'body': json.dumps(result)
}
```

---

### Issue 4: CloudFront Shows Old Content

**Symptoms:**
- Changes pushed to GitHub but website still shows old content
- Updates not visible after 30+ minutes

**Debug Steps:**
```bash
# 1. Check S3 has new content
aws s3 ls s3://mvanslyke-ml.com/ --recursive

# 2. Check file modification time
aws s3api head-object --bucket mvanslyke-ml.com --key index.html

# 3. Check CloudFront cache
curl -I https://mvanslyke-ml.com/index.html
# Look for "X-Cache: Hit from cloudfront"
```

**Solution:**
```bash
# Force invalidation
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"

# Wait 2-3 minutes
sleep 180

# Test again
curl -I https://mvanslyke-ml.com/index.html
# Should see "X-Cache: Miss from cloudfront"
```

---

### Issue 5: GitHub Action Hangs on Lambda Deployment

**Symptoms:**
- Workflow stuck at "Deploy all Lambda functions"
- Takes > 10 minutes

**Debug Steps:**
```bash
# 1. Check GitHub Actions logs
# Look for specific error messages

# 2. Test deployment locally
python3 scripts/deploy_lambda.py
```

**Solution:**
```bash
# Often caused by large dependencies
# Optimize requirements.txt

# Remove unnecessary packages
# Use lightweight alternatives
# Example: use 'scikit-learn-intelex' instead of full 'scikit-learn'
```

---

## ✅ System Health Check

Run this complete health check:

```bash
#!/bin/bash

echo "🔍 ML Portfolio System Health Check"
echo "===================================="

# 1. AWS Credentials
echo -n "1. AWS Credentials... "
aws sts get-caller-identity > /dev/null 2>&1 && echo "✅" || echo "❌"

# 2. S3 Bucket
echo -n "2. S3 Bucket... "
aws s3 ls s3://mvanslyke-ml.com > /dev/null 2>&1 && echo "✅" || echo "❌"

# 3. CloudFront
echo -n "3. CloudFront... "
curl -I https://mvanslyke-ml.com 2>/dev/null | grep "200 OK" > /dev/null && echo "✅" || echo "❌"

# 4. Projects JSON
echo -n "4. Projects JSON... "
curl -s https://mvanslyke-ml.com/projects.json | python3 -m json.tool > /dev/null 2>&1 && echo "✅" || echo "❌"

# 5. Lambda Functions
echo -n "5. Lambda Functions... "
aws lambda list-functions --query "Functions[?contains(FunctionName, 'ml-portfolio')]" --output text > /dev/null 2>&1 && echo "✅" || echo "❌"

# 6. API Gateway
echo -n "6. API Gateway... "
aws apigatewayv2 get-apis --query "Items[?Name=='ML-Portfolio-API']" --output text > /dev/null 2>&1 && echo "✅" || echo "❌"

echo "===================================="
echo "Health check complete!"
```

Save this as `health_check.sh` and run: `bash health_check.sh`

---

## 📊 Monitoring

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/ml-portfolio-[MODEL-NAME] --follow

# View API Gateway logs (if enabled)
aws logs tail /aws/apigateway/ML-Portfolio-API --follow
```

### S3 Access Logs

```bash
# Enable S3 access logging
aws s3api put-bucket-logging \
  --bucket mvanslyke-ml.com \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "mvanslyke-ml-logs",
      "TargetPrefix": "s3-access/"
    }
  }'
```

### Cost Monitoring

```bash
# Check AWS costs (current month)
aws ce get-cost-and-usage \
  --time-period Start=$(date -v1d +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --query "ResultsByTime[*].Total.BlendedCost.Amount" \
  --output text

# Get cost breakdown by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -v1d +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

---

## 🆘 Emergency Procedures

### Complete Reset

```bash
# WARNING: This deletes everything!

# 1. Delete Lambda functions
for func in $(aws lambda list-functions --query "Functions[?contains(FunctionName, 'ml-portfolio')].FunctionName" --output text); do
  aws lambda delete-function --function-name $func
done

# 2. Delete API Gateway
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='ML-Portfolio-API'].ApiId" --output text)
aws apigatewayv2 delete-api --api-id $API_ID

# 3. Clear S3 bucket
aws s3 rm s3://mvanslyke-ml.com --recursive

# 4. Start fresh
# Follow SETUP_GUIDE.md from the beginning
```

---

## 📞 Getting Help

1. **Check this guide first**
2. **Check GitHub Actions logs**
3. **Check CloudWatch logs**
4. **Review SETUP_GUIDE.md**
5. **Create GitHub issue with:**
   - Error message
   - Steps to reproduce
   - Logs/screenshots
   - What you've already tried

---

**Remember**: Most issues are caused by:
1. Incorrect AWS credentials
2. Missing GitHub secrets
3. CloudFront caching
4. CORS configuration
5. Package size limits

Always check these first! 🔍
