# Adding Content to the Portfolio

Everything visible on the site — project cards, blog posts, demos, metrics — flows from three places:

1. **`projects/`** — Markdown files that drive project cards and blog posts
2. **`models/`** — Lambda proxy code for each live ML demo
3. **`docs/`** — Educational/reference write-ups (not shown on site yet, but linkable)

Run `python3 scripts/generate_projects.py` after any change to `projects/` to rebuild `website/projects.json` and `website/blog/`.

---

## Adding a Project Card + Blog Post

### Step 1 — Create the markdown file

Create `projects/your-project-slug.md`. The filename becomes the blog post URL slug.

Every file starts with a YAML front matter block between `---` lines:

```markdown
---
title: My New Project
id: my-model-id
date: May 2026
category: ml, nlp
tags: Deep Learning, NLP, AWS SageMaker, LIVE
github: https://github.com/mvanslyke-ml/ml-portfolio
demo_description: One sentence describing what the demo does
article: https://mvanslyke-ml.com/blog/my-project
metrics:
  mAP@0.5:0.95: "0.72"
  Architecture: Transformer
  Dataset: "10,000 samples"
  Deployment: AWS SageMaker Serverless
---

## What This Project Does

Write freely in Markdown from here down. This content becomes the blog post.
```

**Front matter fields:**

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Shown on the project card and blog page |
| `id` | Yes | Must match the Lambda function name for the demo auto-discovery to work (see below) |
| `date` | Yes | Displayed on the card |
| `category` | Yes | Comma-separated; used for filtering |
| `tags` | Yes | Shown as pills on the card. Add `LIVE` if there's a working demo |
| `github` | No | Links to source repo |
| `demo_description` | No | One sentence shown in the demo modal |
| `article` | No | URL to the blog post (auto-set to `/blog/<slug>.html` if omitted) |
| `metrics` | No | Key-value pairs shown in the card's metrics grid |

### Step 2 — Regenerate the site files

```bash
python3 scripts/generate_projects.py
```

This outputs:
- `website/projects.json` — read by `app.js` to render all project cards
- `website/blog/<slug>.html` — the standalone blog post page

### Step 3 — Push to main

GitHub Actions will sync `website/` to S3 automatically on push.

---

## Adding a Live ML Demo

A live demo requires two things: a running SageMaker endpoint and a Lambda proxy in front of it.

### Step 1 — Deploy the model to SageMaker

Make sure your model is packaged as `model.tar.gz` and uploaded to S3, then run:

```bash
python3 scripts/deploy_sagemaker.py
```

Edit the script's variables at the top (`MODEL_NAME`, `S3_BUCKET`, etc.) before running.

### Step 2 — Create the Lambda proxy

Create a folder under `models/` matching the project's `id` field exactly (this is how the site auto-discovers your demo endpoint):

```
models/
└── your-model-id/
    ├── lambda_function.py    # Forwards browser requests to SageMaker
    ├── config.yml            # model_name, memory_mb, timeout_s
    └── requirements.txt      # Python deps for Lambda (usually just boto3)
```

**`config.yml` format:**
```yaml
model_name: your-sagemaker-endpoint-name
memory_mb: 512
timeout_s: 60
```

**`lambda_function.py` minimal template:**
```python
import json, boto3, base64

ENDPOINT = "your-sagemaker-endpoint-name"
client = boto3.client("sagemaker-runtime", region_name="us-east-1")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}

def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS, "body": ""}

    body = json.loads(event.get("body", "{}"))
    image_bytes = base64.b64decode(body["image"])

    response = client.invoke_endpoint(
        EndpointName=ENDPOINT,
        ContentType="application/octet-stream",
        Body=image_bytes,
    )
    result = json.loads(response["Body"].read())

    return {"statusCode": 200, "headers": CORS, "body": json.dumps(result)}
```

### Step 3 — Deploy the Lambda

```bash
python3 scripts/deploy_lambda.py
```

### Step 4 — Update the project's front matter

Add `LIVE` to `tags` and set `id` to match the Lambda/endpoint name. Run `generate_projects.py` again.

---

## Adding an Educational Write-Up

Place Markdown files in `docs/`. They are not auto-rendered on the site today, but they can be:
- Linked directly from project blog posts using relative URLs
- Committed as reference material alongside the code

**Naming convention:** `docs/topic-name.md` (e.g., `docs/transformers-explained.md`)

There is no front matter required — just write in standard Markdown.

---

## Adding a Study / Coursework Project

Place notebooks, reports, and data under `ds_studies/Your_Project_Name/`. These are tracked in git as source material but are not automatically surfaced on the website. To add one as a project card, create a corresponding `projects/*.md` file pointing to the GitHub URL.

---

## Quick Reference

```
Add a project card:     projects/slug.md  →  generate_projects.py  →  push
Add a live demo:        models/id/lambda_function.py + deploy_lambda.py
Add an educational doc: docs/topic.md
Add a study/notebook:   ds_studies/Project_Name/
```
