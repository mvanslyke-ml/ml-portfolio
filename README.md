# ML Portfolio - Auto-Deployment System
## Professional Machine Learning Portfolio with CI/CD

**Live Site**: [https://mvanslyke-ml.com](https://mvanslyke-ml.com)  
**Cost**: ~$1-3/month  
**Deployment**: Automatic on git push  

---

## 🌟 Features

### Dynamic Content Management
- **Blog-like updates** - Add projects via markdown files
- **Auto-generated portfolio** - Markdown → JSON → Website
- **Smart filtering** - Category-based project organization
- **Professional design** - Dark tech aesthetic with animations

### Live ML Demonstrations
- **AWS Lambda integration** - Deploy models as serverless APIs
- **Interactive demos** - Users test models in-browser
- **Real-time inference** - Production-ready endpoints
- **Auto-linking** - Demos automatically linked to projects

### Production-Ready Infrastructure
- **S3 + CloudFront** - Global CDN with HTTPS
- **GitHub Actions CI/CD** - Auto-deploy on push
- **Decoupled components** - Easy maintenance and debugging
- **Cost-optimized** - Pay only for what you use

---

## 📁 Project Structure

```
ml-portfolio/
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD
│
├── website/                        # Static website files
│   ├── index.html                  # Main page (separated HTML)
│   ├── styles.css                  # Separated CSS
│   ├── app.js                      # Separated JavaScript
│   └── projects.json               # Auto-generated from markdown
│
├── projects/                       # Blog posts as markdown
│   └── bone-fracture-detection.md  # Example project
│
├── models/                         # ML models for Lambda
│   └── [model-name]/
│       ├── config.yml              # Model configuration
│       ├── lambda_function.py      # Lambda handler
│       ├── model.pkl               # Trained model
│       └── requirements.txt        # Dependencies
│
├── scripts/                        # Deployment automation
│   ├── generate_projects.py        # Markdown → JSON
│   ├── deploy_lambda.py            # Deploy models
│   └── update_api_gateway.py       # Configure API Gateway
│
├── .build/                         # Build artifacts (git-ignored)
│   ├── deployment_manifest.json    # Deployed functions
│   └── api_docs.json               # API documentation
│
├── SETUP_GUIDE.md                  # Complete setup instructions
├── DEBUGGING_GUIDE.md              # Troubleshooting guide
├── DEPLOYMENT_CHECKLIST.md         # Verification checklist
└── README.md                       # This file
```

---

## 🚀 Quick Start

### Prerequisites
- AWS Account
- GitHub Account  
- Python 3.9+
- AWS CLI configured
- Domain name (mvanslyke-ml.com)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/mvanslyke/ml-portfolio.git
cd ml-portfolio

# 2. Install dependencies
pip install boto3 pyyaml

# 3. Configure AWS
aws configure

# 4. Follow setup guide
# See SETUP_GUIDE.md for complete instructions
```

---

## 📝 Adding Projects

### Method 1: Markdown Files (Recommended)

Create a `.md` file in `projects/` directory:

```markdown
---
title: My ML Project
date: Feb 2026
category: ml, cv
tags: Python, TensorFlow
github: https://github.com/mvanslyke/project
metrics:
  Accuracy: 95%
  Dataset: 10K images
---

## Overview

Project description here...
```

**Deploy:**
```bash
git add projects/my-project.md
git commit -m "Add: My ML Project"
git push origin main
```

**Result:** Auto-deployed in 2 minutes! ✅

---

## 🤖 Deploying ML Models

### Step 1: Create Model Directory

```bash
mkdir -p models/sentiment-analysis
```

### Step 2: Add Configuration

```yaml
# models/sentiment-analysis/config.yml
name: sentiment-analysis
description: Real-time sentiment classification
memory: 512
timeout: 30
model_file: model.pkl
api_route: /sentiment
```

### Step 3: Add Lambda Handler

```python
# models/sentiment-analysis/lambda_function.py
import json
import pickle

with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

def lambda_handler(event, context):
    body = json.loads(event['body'])
    prediction = model.predict([body['input']])[0]
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'prediction': prediction})
    }
```

### Step 4: Deploy

```bash
git add models/sentiment-analysis/
git commit -m "Deploy: Sentiment Analysis Model"
git push origin main
```

**Result:** Model deployed and API live in 3 minutes! ✅

---

## 🔄 How It Works

### Automatic Workflow

```
1. Developer pushes to GitHub
   ↓
2. GitHub Actions triggered
   ↓
3. Jobs execute in parallel:
   
   Job A: Website Deployment
   - Generate projects.json from markdown
   - Upload website files to S3
   - Invalidate CloudFront cache
   
   Job B: Lambda Deployment
   - Package each model with dependencies
   - Deploy/update Lambda functions
   - Configure API Gateway routes
   
   Job C: Link Projects to Demos
   - Match project IDs to Lambda functions
   - Update projects.json with demo URLs
   - Invalidate cache again
   ↓
4. Website live with updated content!
```

### Data Flow

```
Markdown → Generate Projects → projects.json → S3 → CloudFront → Website

Models → Package Lambda → Deploy → API Gateway → Live API

Projects + APIs → Auto-link → Updated projects.json → Demo Buttons
```

---

## 💰 Cost Breakdown

### Free Tier (First 12 Months)
- S3: 5 GB storage, 20,000 GET requests
- CloudFront: 50 GB transfer, 2M requests
- Lambda: 1M requests, 400,000 GB-seconds
- API Gateway: 1M requests

### After Free Tier

| Component | Monthly Cost |
|-----------|-------------|
| S3 Storage (10 MB) | $0.23 |
| CloudFront (10K visitors) | $0.50 |
| Lambda (100 demos) | $0.02 |
| Route 53 (DNS) | $0.50 |
| **Total** | **~$1.25** |

**Scaling:**
- 100K visitors: ~$5-10/month
- 1M requests: ~$15-20/month

---

## 🎨 Customization

### Update Personal Information

Edit `website/index.html`:

```html
<!-- Name and title -->
<h1>Michael Van Slyke</h1>
<h2><span class="typing">Building intelligent systems</span></h2>

<!-- Bio -->
<p>Transforming complex data into actionable insights...</p>

<!-- Contact -->
<a href="mailto:michael@mvanslyke-ml.com">michael@mvanslyke-ml.com</a>
```

### Change Color Scheme

Edit `website/styles.css`:

```css
:root {
    --accent: #00D9FF;        /* Primary color */
    --purple: #B794F6;        /* Secondary color */
    --green: #00FF88;         /* Success color */
}
```

### Update Stats

Edit `website/index.html`:

```html
<div class="stat-number">15+</div>
<div class="stat-label">ML Models Deployed</div>
```

---

## 🧪 Testing

### Local Development

```bash
# Start local server
cd website
python3 -m http.server 8000

# Visit: http://localhost:8000
```

### Validate JSON

```bash
# Check syntax
python3 -m json.tool website/projects.json
```

### Test Scripts

```bash
# Generate projects
python3 scripts/generate_projects.py

# Deploy Lambda (locally)
python3 scripts/deploy_lambda.py

# Configure API Gateway
python3 scripts/update_api_gateway.py
```

### Health Check

```bash
# Run complete system check
bash health_check.sh
```

---

## 🔧 Troubleshooting

### Common Issues

**Projects not appearing:**
```bash
# Regenerate and upload
python3 scripts/generate_projects.py
aws s3 cp website/projects.json s3://mvanslyke-ml.com/
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

**Lambda deployment failed:**
```bash
# Check package size
du -sh .build/*.zip

# If > 50 MB, upload model to S3 separately
aws s3 cp models/your-model/model.pkl s3://mvanslyke-ml-models/your-model/
```

**Old content showing:**
```bash
# Force cache invalidation
aws cloudfront create-invalidation \
  --distribution-id YOUR_ID \
  --paths "/*"
```

**See DEBUGGING_GUIDE.md for complete troubleshooting**

---

## 📚 Documentation

- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** - Complete setup instructions (30-45 min)
- **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Verification checklist
- **[DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md)** - Troubleshooting guide
- **[AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md)** - Manual AWS setup
- **[AWS_LAMBDA_ML_DEPLOYMENT.md](./AWS_LAMBDA_ML_DEPLOYMENT.md)** - Lambda deep-dive

---

## 🎯 Roadmap

### Completed ✅
- [x] Separated HTML, CSS, JavaScript
- [x] GitHub Actions CI/CD
- [x] Markdown to JSON conversion
- [x] Lambda auto-deployment
- [x] API Gateway auto-configuration
- [x] Auto-linking demos to projects
- [x] CloudFront with HTTPS
- [x] Comprehensive documentation

### In Progress 🚧
- [ ] Custom domain for API (api.mvanslyke-ml.com)
- [ ] Blog section with full posts
- [ ] Google Analytics integration
- [ ] Contact form with AWS SES

### Future Ideas 💡
- [ ] Admin panel for easy editing
- [ ] Jupyter notebook viewer
- [ ] Video demo embeds
- [ ] GitHub contribution graph
- [ ] Kaggle API integration
- [ ] Dark/light theme toggle

---

## 🤝 Contributing

Improvements welcome! To contribute:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

MIT License - feel free to use for your own portfolio!

---

## 🙏 Acknowledgments

- Design inspired by terminal interfaces
- Built for the ML/DS community
- Optimized for AWS infrastructure
- Decoupled architecture for maintainability

---

## 📧 Contact

**Michael Van Slyke**

- Website: [https://mvanslyke-ml.com](https://mvanslyke-ml.com)
- Email: [michael@mvanslyke-ml.com](mailto:michael@mvanslyke-ml.com)
- GitHub: [@mvanslyke](https://github.com/mvanslyke)
- LinkedIn: [Michael Van Slyke](https://linkedin.com/in/michaelvanslyke)

---

## 🎓 Learning Resources

### AWS Documentation
- [S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

### Tools
- [YAML Validator](https://www.yamllint.com/)
- [JSON Validator](https://jsonlint.com/)
- [Markdown Guide](https://www.markdownguide.org/)

---

## ⚡ Quick Commands

```bash
# Add new project
vim projects/my-project.md
git add . && git commit -m "Add: My Project" && git push

# Deploy new model
mkdir models/my-model
# Add config.yml, lambda_function.py, model.pkl
git add . && git commit -m "Deploy: My Model" && git push

# Update website
vim website/index.html
git add . && git commit -m "Update: Homepage" && git push

# Invalidate cache manually
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"

# Check deployment status
git log --oneline -5
# Then visit: https://github.com/mvanslyke/ml-portfolio/actions

# Monitor costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -v-30d +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost
```

---

**Made with 🤖 and ☕ for the ML community**

*Last Updated: February 2026*

---

## 📊 Project Stats

- **Deployment Time**: 30-45 minutes
- **Monthly Cost**: $1-3
- **Auto-Deploy Time**: 2-3 minutes
- **Components**: 12 AWS services
- **Lines of Code**: ~2,000
- **Documentation**: 5 comprehensive guides
- **Maintenance**: < 1 hour/month

**Start building your portfolio today!** 🚀
