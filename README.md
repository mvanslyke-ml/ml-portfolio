# mvanslyke-ml — ML Portfolio

Personal ML portfolio site for Michael Van Slyke. Static website deployed to AWS S3 + CloudFront, with live ML demos powered by AWS SageMaker Serverless Inference via Lambda proxies.

**Live site:** [mvanslyke-ml.com](https://mvanslyke-ml.com)

---

## Repository Structure

```
├── website/                  # Static site served to users
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── projects.json         # Auto-generated — do not edit directly
│   └── blog/                 # Auto-generated HTML blog posts
│
├── projects/                 # One .md file per project card + blog post
│   └── bone-fracture-detection.md
│
├── models/                   # Lambda proxy for each deployed model
│   └── fracture-detector/
│       ├── lambda_function.py
│       ├── config.yml
│       └── requirements.txt
│
├── scripts/                  # Deployment and build tooling
│   ├── generate_projects.py  # Converts projects/*.md → projects.json + blog HTML
│   ├── deploy_sagemaker.py   # Deploys a model to SageMaker Serverless
│   ├── deploy_lambda.py      # Zips and deploys a Lambda proxy
│   └── update_api_gateway.py # Updates API Gateway routes
│
├── docs/                     # Educational reference documents
│   ├── cnn-explained.md
│   └── rcnn-explained.md
│
├── ds_studies/               # Coursework capstone projects (source material)
│
└── train_bone_fracture_model.py   # Full training pipeline for fracture detector
```

---

## Adding Content

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for step-by-step instructions on adding:
- Project cards and blog posts
- New ML demos with live endpoints
- Educational/study write-ups

---

## Deployment

Pushes to `main` trigger GitHub Actions (`.github/workflows/deploy.yml`), which syncs `website/` to S3 and invalidates the CloudFront cache.

To deploy a new model endpoint manually:
```bash
python3 scripts/deploy_sagemaker.py
python3 scripts/deploy_lambda.py
python3 scripts/generate_projects.py
```
