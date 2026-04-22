# mvanslyke-ml Portfolio

## Project Overview
Michael Van Slyke's ML portfolio site. Static HTML/JS/CSS served via AWS S3 + CloudFront. Live ML demos run on AWS SageMaker Serverless Inference, accessed through API Gateway + Lambda proxies.

## Architecture
- **Frontend:** Plain HTML/CSS/JS (no framework) in `website/`
- **Content pipeline:** `projects/*.md` → `scripts/generate_projects.py` → `website/projects.json` + `website/blog/*.html`
- **Live demos:** `models/<id>/lambda_function.py` proxies browser requests to SageMaker endpoints
- **CI/CD:** `.github/workflows/deploy.yml` syncs `website/` to S3 on push to main

## Key Files
- `website/index.html` — single-page app shell
- `website/app.js` — fetches projects.json, renders cards, handles demo modal
- `website/styles.css` — all styling including matrix rain canvas effect
- `projects/bone-fracture-detection.md` — project card + blog post source
- `models/fracture-detector/lambda_function.py` — Lambda proxy for SageMaker endpoint
- `scripts/generate_projects.py` — markdown → JSON + blog HTML pipeline
- `scripts/deploy_sagemaker.py` — deploys model artifact to SageMaker Serverless
- `scripts/deploy_lambda.py` — zips and uploads Lambda proxy; attaches SageMaker invoke policy
- `train_bone_fracture_model.py` — full PyTorch training pipeline (Faster R-CNN)

## Active Deployments
- **SageMaker endpoint:** `fracture-detector` (Serverless, 3072 MB, us-east-1)
- **Lambda:** `fracture-detector` (proxy with SageMakerInvokeEndpoint inline policy)
- **Model artifact:** `s3://mvanslyke-ml-models/fasterrcnn_fracture_v1/fasterrcnn_fracture_v1.tar.gz`

## Important Constraints
- SageMaker account quota: 3072 MB max per serverless endpoint (quota increase pending for 6144 MB)
- NUM_CLASSES = 7 (background handled internally — do not set to 8)
- Custom domain `api.mvanslyke-ml.com` is NOT mapped to API Gateway; demo URL is auto-discovered from the actual execute-api endpoint
- PyTorch model uses FP16 mixed precision during training; inference runs in FP32

## Content Guide
See `CONTRIBUTING.md` for step-by-step instructions on adding projects, demos, and educational docs.

## Dependencies
- Python: `pyyaml`, `markdown` (used by generate_projects.py; installed via pip)
- No Node.js / npm; site is plain static HTML
