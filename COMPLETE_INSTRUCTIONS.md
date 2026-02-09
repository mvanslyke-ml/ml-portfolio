# COMPLETE DEPLOYMENT INSTRUCTIONS
## Everything You Need to Do - Step by Step

**Estimated Time**: 45-60 minutes  
**Cost**: ~$1-3/month after free tier  
**Prerequisites**: AWS account, GitHub account, domain name

---

## 📋 WHAT YOU NEED BEFORE STARTING

1. **AWS Account** - [Sign up here](https://aws.amazon.com)
2. **GitHub Account** - [Sign up here](https://github.com)
3. **Domain Name** - mvanslyke-ml.com (already registered)
4. **Local Machine** with:
   - Python 3.9+
   - Git
   - Code editor (VSCode, Sublime, etc.)

---

## 🎯 PHASE 1: LOCAL SETUP (10 minutes)

### Step 1.1: Install AWS CLI

**macOS:**
```bash
brew install awscli
```

**Linux:**
```bash
sudo apt install awscli
```

**Windows:**
Download from: https://aws.amazon.com/cli/

**Verify:**
```bash
aws --version
# Should show: aws-cli/2.x.x
```

### Step 1.2: Configure AWS Credentials

```bash
aws configure
```

**You'll need:**
- AWS Access Key ID (get from AWS Console → IAM → Users → Security credentials)
- AWS Secret Access Key (shown once when creating access key)
- Default region: `us-east-1`
- Default output format: `json`

**Test it works:**
```bash
aws sts get-caller-identity
# Should show your account details
```

### Step 1.3: Install Python Dependencies

```bash
pip install boto3 pyyaml
```

### Step 1.4: Clone/Setup Repository

**Option A: Use these files (Recommended)**
```bash
# Download all the files I created to a directory
cd path/to/downloaded/files

# Initialize git
git init
git add .
git commit -m "Initial commit"
```

**Option B: Start from scratch**
```bash
mkdir ml-portfolio
cd ml-portfolio
# Copy all files I created into this directory
```

---

## 🌐 PHASE 2: AWS INFRASTRUCTURE (20 minutes)

### Step 2.1: Create S3 Buckets

```bash
# Website bucket
aws s3 mb s3://mvanslyke-ml.com --region us-east-1

# Models bucket
aws s3 mb s3://mvanslyke-ml-models --region us-east-1

# Enable static website hosting
aws s3 website s3://mvanslyke-ml.com \
    --index-document index.html \
    --error-document index.html
```

### Step 2.2: Set Bucket Permissions

```bash
# Create bucket policy file
cat > /tmp/bucket-policy.json << 'EOF'
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

# Apply policy
aws s3api put-bucket-policy \
    --bucket mvanslyke-ml.com \
    --policy file:///tmp/bucket-policy.json

# Remove public access block
aws s3api delete-public-access-block \
    --bucket mvanslyke-ml.com
```

### Step 2.3: Create CloudFront Distribution

```bash
# This is a simplified version - see SETUP_GUIDE.md for full config
# Or use AWS Console (easier):

1. Go to CloudFront → Create Distribution
2. Origin domain: mvanslyke-ml.com.s3-website-us-east-1.amazonaws.com
   (Important: Use website endpoint, NOT the bucket from dropdown!)
3. Viewer protocol policy: Redirect HTTP to HTTPS
4. Default root object: index.html
5. Click "Create distribution"
6. SAVE THE DISTRIBUTION ID - you'll need it for GitHub Secrets!
```

**Wait 10-15 minutes for deployment** ⏳

### Step 2.4: Request SSL Certificate

```bash
# Request certificate
aws acm request-certificate \
    --domain-name mvanslyke-ml.com \
    --subject-alternative-names "*.mvanslyke-ml.com" \
    --validation-method DNS \
    --region us-east-1

# Get validation records
# (Will need to add these to your DNS)
```

**Add DNS validation records to your domain provider**

**Wait for certificate status to become "Issued"** ⏳

### Step 2.5: Configure Domain

**Option A: Using Route 53**
```bash
# Create A record pointing to CloudFront
# (See SETUP_GUIDE.md for complete commands)
```

**Option B: External DNS (GoDaddy, Namecheap, etc.)**
1. Log into your DNS provider
2. Add A or CNAME record:
   - Type: CNAME
   - Name: @ (or blank for root)
   - Value: d1234abcd.cloudfront.net (your CloudFront domain)
   - TTL: 300

---

## 🔧 PHASE 3: GITHUB SETUP (10 minutes)

### Step 3.1: Create GitHub Repository

1. Go to GitHub → New Repository
2. Name: `ml-portfolio`
3. Public or Private (your choice)
4. Don't initialize with README (you already have files)
5. Create repository

### Step 3.2: Connect Local to GitHub

```bash
# If you haven't already initialized git
git init

# Add remote
git remote add origin https://github.com/mvanslyke/ml-portfolio.git

# Push to GitHub
git branch -M main
git add .
git commit -m "Initial commit: ML portfolio with auto-deployment"
git push -u origin main
```

### Step 3.3: Add GitHub Secrets

1. Go to repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add these three secrets:

**Secret 1:**
- Name: `AWS_ACCESS_KEY_ID`
- Value: Your AWS access key ID

**Secret 2:**
- Name: `AWS_SECRET_ACCESS_KEY`
- Value: Your AWS secret access key

**Secret 3:**
- Name: `CLOUDFRONT_DISTRIBUTION_ID`
- Value: Your CloudFront distribution ID (from Step 2.3)

---

## 📝 PHASE 4: CUSTOMIZE CONTENT (5 minutes)

### Step 4.1: Update Personal Information

Edit `website/index.html`:

```html
<!-- Line ~46: Update name -->
<h1>Michael Van Slyke</h1>

<!-- Line ~47: Update tagline -->
<h2><span class="typing">Building intelligent systems</span></h2>

<!-- Line ~48-52: Update bio -->
<p>
    Transforming complex data into actionable insights...
    [Your bio here]
</p>

<!-- Line ~180-185: Update contact info -->
<a href="mailto:michael@mvanslyke-ml.com">michael@mvanslyke-ml.com</a>
<a href="https://linkedin.com/in/michaelvanslyke">Connect with me</a>
<a href="https://github.com/mvanslyke">@mvanslyke</a>

<!-- Line ~65-85: Update stats -->
<div class="stat-number">15+</div>
<div class="stat-label">ML Models Deployed</div>
<!-- Update with your numbers -->
```

### Step 4.2: Add Your First Project

Edit `projects/bone-fracture-detection.md` or create a new one:

```bash
# Create new project file
vim projects/my-first-project.md

# Add this content:
---
title: My Amazing ML Project
date: Feb 2026
category: ml
tags: Python, TensorFlow
github: https://github.com/mvanslyke/my-project
metrics:
  Accuracy: 95%
  Dataset: 10K samples
---

## Overview

[Describe your project here]
```

---

## 🚀 PHASE 5: FIRST DEPLOYMENT (5 minutes)

### Step 5.1: Commit and Push

```bash
# Add all changes
git add .

# Commit
git commit -m "Customize: Add personal information and first project"

# Push to GitHub
git push origin main
```

### Step 5.2: Watch GitHub Actions

1. Go to GitHub → Actions tab
2. You should see a workflow running: "Deploy ML Portfolio"
3. Click on it to watch progress
4. Wait for all jobs to complete (2-3 minutes)

### Step 5.3: Verify Deployment

**Check these in order:**

1. **GitHub Actions** - All jobs should show ✅ green checkmarks
2. **Website** - Visit https://mvanslyke-ml.com
   - Should load with your information
   - Projects should appear
   - Styles should work
   - No console errors (press F12)
3. **S3** - Check files uploaded:
   ```bash
   aws s3 ls s3://mvanslyke-ml.com/
   ```
4. **CloudFront** - May need to wait a few more minutes for cache

---

## 🤖 PHASE 6: DEPLOY FIRST ML MODEL (Optional, 10 minutes)

### Step 6.1: Create Model Directory

```bash
mkdir -p models/sentiment-analysis
```

### Step 6.2: Create Configuration

```bash
cat > models/sentiment-analysis/config.yml << 'EOF'
name: sentiment-analysis
description: Real-time sentiment classification
memory: 512
timeout: 30
model_file: model.pkl
api_route: /sentiment

environment:
  MODEL_VERSION: v1.0

example_request:
  input: "This is great!"

example_response:
  sentiment: "Positive"
  confidence: 0.95
EOF
```

### Step 6.3: Create Lambda Handler

```bash
cat > models/sentiment-analysis/lambda_function.py << 'EOF'
import json
import pickle

# Load model (cached between invocations)
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

def lambda_handler(event, context):
    # Parse request
    body = json.loads(event.get('body', '{}'))
    text = body.get('input', '')
    
    if not text:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'No input provided'})
        }
    
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
            'prediction': str(prediction),
            'input': text
        })
    }
EOF
```

### Step 6.4: Add Your Model

```bash
# Copy your trained model
cp /path/to/your/trained/model.pkl models/sentiment-analysis/model.pkl

# Or create a dummy one for testing:
python3 << 'EOF'
import pickle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# Dummy model
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(['good', 'bad'])
y = ['Positive', 'Negative']
model = MultinomialNB().fit(X, y)

# Save
with open('models/sentiment-analysis/model.pkl', 'wb') as f:
    pickle.dump((vectorizer, model), f)
EOF
```

### Step 6.5: Add Requirements

```bash
cat > models/sentiment-analysis/requirements.txt << 'EOF'
scikit-learn==1.3.0
numpy==1.24.3
EOF
```

### Step 6.6: Deploy

```bash
git add models/sentiment-analysis/
git commit -m "Deploy: Sentiment Analysis Model"
git push origin main
```

**Watch GitHub Actions** - Wait for completion (3-4 minutes)

**Your API is now live!**

---

## ✅ PHASE 7: VERIFICATION (5 minutes)

### Final Checks

```bash
# 1. Website loads
curl -I https://mvanslyke-ml.com
# Should return: HTTP/2 200

# 2. Projects appear
curl -s https://mvanslyke-ml.com/projects.json | python3 -m json.tool

# 3. GitHub Actions successful
# Visit: https://github.com/mvanslyke/ml-portfolio/actions
# Should show: ✅ All green

# 4. Lambda deployed (if you did Phase 6)
aws lambda list-functions | grep ml-portfolio

# 5. API working (if you did Phase 6)
# Get API URL from .build/api_docs.json or GitHub Actions logs
curl -X POST https://YOUR_API_URL/sentiment \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'
```

### Run Health Check

```bash
# Create health check script
cat > health_check.sh << 'EOF'
#!/bin/bash
echo "🔍 System Health Check"
echo "======================"

echo -n "1. AWS Credentials... "
aws sts get-caller-identity > /dev/null 2>&1 && echo "✅" || echo "❌"

echo -n "2. S3 Bucket... "
aws s3 ls s3://mvanslyke-ml.com > /dev/null 2>&1 && echo "✅" || echo "❌"

echo -n "3. Website... "
curl -I https://mvanslyke-ml.com 2>/dev/null | grep "200" > /dev/null && echo "✅" || echo "❌"

echo -n "4. Projects JSON... "
curl -s https://mvanslyke-ml.com/projects.json | python3 -m json.tool > /dev/null 2>&1 && echo "✅" || echo "❌"

echo "======================"
echo "Health check complete!"
EOF

chmod +x health_check.sh
./health_check.sh
```

**Expected output:** All ✅

---

## 🎓 WHAT YOU'VE JUST BUILT

✅ **Professional ML Portfolio** at https://mvanslyke-ml.com  
✅ **Auto-deployment system** - git push = auto-deploy  
✅ **Serverless ML API** (if you deployed a model)  
✅ **Production infrastructure** with global CDN  
✅ **Cost-optimized** at ~$1-3/month  
✅ **Fully documented** system  
✅ **Maintainable** with decoupled components  

---

## 📚 NEXT STEPS

### Immediate (Today)
1. ✅ Test everything works
2. ✅ Share portfolio on LinkedIn
3. ✅ Add to resume

### This Week
1. 📝 Add 2-3 more projects
2. 🤖 Deploy another ML model
3. 🎨 Customize colors/styles

### This Month
1. 📊 Add Google Analytics
2. 📧 Set up contact form
3. 📝 Write blog posts
4. 🔗 Add to all job applications

---

## 🆘 IF SOMETHING BREAKS

### Quick Fixes

**Website not loading?**
```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

**Projects not showing?**
```bash
python3 scripts/generate_projects.py
aws s3 cp website/projects.json s3://mvanslyke-ml.com/
```

**GitHub Actions failing?**
1. Check Actions tab for error messages
2. Verify GitHub Secrets are set correctly
3. Check AWS credentials are valid

**See DEBUGGING_GUIDE.md for complete troubleshooting**

---

## 📖 DOCUMENTATION REFERENCE

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| **README.md** | Overview | First read, general reference |
| **THIS FILE** | Complete instructions | Initial setup |
| **SETUP_GUIDE.md** | Detailed AWS setup | Step-by-step deployment |
| **DEPLOYMENT_CHECKLIST.md** | Verification | Before considering done |
| **DEBUGGING_GUIDE.md** | Troubleshooting | When things break |

---

## 💬 SUPPORT

**Have questions?**
1. Check DEBUGGING_GUIDE.md first
2. Review SETUP_GUIDE.md
3. Check GitHub Actions logs
4. Check AWS CloudWatch logs

**Still stuck?**
- Create an issue in your GitHub repository
- Include error messages and what you've tried
- Attach relevant logs

---

## 🎉 CONGRATULATIONS!

You now have a **professional, auto-deploying ML portfolio** that:

- 🚀 Deploys automatically on every git push
- 💰 Costs less than a coffee per month
- 🌐 Reaches global audiences via CDN
- 🔒 Is secure with HTTPS
- 📱 Works on all devices
- 🤖 Can showcase live ML demos
- 📝 Updates via simple markdown files

**This is YOUR platform to showcase amazing ML projects!**

**Start building and watch them deploy automatically! 🎊**

---

**Time to celebrate!** 🥳

Your ML portfolio is live and the world can see your work!

Share it everywhere:
- LinkedIn profile
- Resume
- Job applications
- Twitter/X
- ML communities

**Good luck with your ML career!** 🚀
