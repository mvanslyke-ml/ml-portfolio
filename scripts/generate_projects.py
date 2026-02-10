#!/usr/bin/env python3
"""
Auto-generate projects.json from Markdown Blog Posts
Converts markdown files in projects/ directory to portfolio entries
"""

import json
import re
from pathlib import Path
from datetime import datetime
import yaml
import sys

PROJECTS_DIR = Path('projects')
OUTPUT_FILE = Path('website/projects.json')
BUILD_DIR = Path('.build')

def parse_frontmatter(content):
    """Extract YAML frontmatter from markdown"""
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = content[match.end():]
            return frontmatter, body
        except yaml.YAMLError as e:
            print(f"⚠️  YAML parsing error: {e}")
            return {}, content
    else:
        return {}, content

def extract_metrics_from_markdown(body):
    """Extract metrics from markdown tables or sections"""
    metrics = {}
    
    # Look for metrics in markdown tables
    # Format: | Metric | Value |
    table_pattern = r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
    matches = re.findall(table_pattern, body)
    
    for key, value in matches:
        key = key.strip()
        value = value.strip()
        # Skip table headers and separators
        if key.lower() not in ['metric', 'name', 'key'] and value.lower() not in ['value', '-', '--', '---']:
            metrics[key] = value
    
    return metrics

def generate_project_id(title):
    """Generate URL-safe project ID from title"""
    # Convert to lowercase, replace spaces with hyphens, remove special chars
    project_id = title.lower()
    project_id = re.sub(r'[^\w\s-]', '', project_id)
    project_id = re.sub(r'[-\s]+', '-', project_id)
    return project_id

def markdown_to_project(md_file):
    """Convert markdown file to project JSON entry"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    frontmatter, body = parse_frontmatter(content)
    
    # Required fields
    if 'title' not in frontmatter:
        print(f"⚠️  Skipping {md_file.name}: missing 'title' in frontmatter")
        return None
    
    # Extract or generate fields
    project_id = frontmatter.get('id', generate_project_id(frontmatter['title']))
    
    # Get date (from frontmatter or file modification time)
    if 'date' in frontmatter:
        date_str = frontmatter['date']
    else:
        mod_time = datetime.fromtimestamp(md_file.stat().st_mtime)
        date_str = mod_time.strftime('%b %Y')
    
    # Extract description (first paragraph or from frontmatter)
    description = frontmatter.get('description', '')
    if not description:
        # Get first paragraph from body
        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip() and not p.startswith('#')]
        if paragraphs:
            description = paragraphs[0][:200]  # First 200 chars
    
    # Get categories (default to 'ml')
    categories = frontmatter.get('category', frontmatter.get('categories', ['ml']))
    if isinstance(categories, str):
        categories = [cat.strip() for cat in categories.split(',')]
    
    # Get tags
    tags = frontmatter.get('tags', [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(',')]
    
    # Get metrics (from frontmatter or parse from markdown)
    metrics = frontmatter.get('metrics', extract_metrics_from_markdown(body))
    
    # Check if Lambda function exists for this project
    lambda_function_name = f"ml-portfolio-{project_id}"
    manifest_path = BUILD_DIR / 'deployment_manifest.json'
    demo_url = None
    
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            for func in manifest.get('functions', []):
                if func['function_name'] == lambda_function_name:
                    # Get API endpoint
                    api_docs_path = BUILD_DIR / 'api_docs.json'
                    if api_docs_path.exists():
                        with open(api_docs_path) as f:
                            api_docs = json.load(f)
                        
                        for endpoint in api_docs['endpoints']:
                            if func['api_route'] in endpoint['path']:
                                demo_url = endpoint['url']
                                break
        except Exception as e:
            print(f"⚠️  Error checking Lambda functions: {e}")
    
    # Override with manual demo_url if provided
    demo_url = frontmatter.get('demo_url', demo_url)
    
    # Build project entry
    project = {
        'id': project_id,
        'title': frontmatter['title'],
        'date': date_str,
        'description': description,
        'category': categories,
        'tags': tags
    }
    
    # Optional fields
    if metrics:
        project['metrics'] = metrics
    
    if frontmatter.get('github'):
        project['github'] = frontmatter['github']
    
    if demo_url:
        project['demo_url'] = demo_url
        project['demo_description'] = frontmatter.get('demo_description', f"Live demo of {frontmatter['title']}")
    
    if frontmatter.get('article'):
        project['article'] = frontmatter['article']
    
    return project

def generate_projects_json():
    """Generate projects.json from all markdown files"""
    print("=" * 60)
    print("📝 Generating projects.json from Markdown")
    print("=" * 60)
    
    if not PROJECTS_DIR.exists():
        print(f"⚠️  Projects directory not found: {PROJECTS_DIR}")
        print(f"   Creating directory...")
        PROJECTS_DIR.mkdir(parents=True)
        # Create a default example project
        create_example_project()
        return
    
    # Find all markdown files
    md_files = list(PROJECTS_DIR.glob('*.md'))
    
    if not md_files:
        print(f"⚠️  No markdown files found in {PROJECTS_DIR}")
        print(f"   Create .md files with project frontmatter")
        # Create a default example
        create_example_project()
        md_files = list(PROJECTS_DIR.glob('*.md'))
    
    print(f"\n📂 Found {len(md_files)} markdown file(s)\n")
    
    projects = []
    
    for md_file in sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True):
        print(f"{'─' * 60}")
        print(f"Processing: {md_file.name}")
        
        project = markdown_to_project(md_file)
        
        if project:
            projects.append(project)
            print(f"✅ Added: {project['title']}")
            print(f"   ID: {project['id']}")
            print(f"   Categories: {', '.join(project['category'])}")
            if project.get('demo_url'):
                print(f"   🟢 Live demo: {project['demo_url']}")
        else:
            print(f"⚠️  Skipped")
    
    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Write projects.json
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"✅ Generated projects.json with {len(projects)} project(s)")
    print(f"{'=' * 60}")
    print(f"\n📄 Output: {OUTPUT_FILE}")
    print(f"📊 Projects by category:")
    
    # Count by category
    category_counts = {}
    for project in projects:
        for cat in project['category']:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    
    for cat, count in sorted(category_counts.items()):
        print(f"   • {cat}: {count}")

def create_example_project():
    """Create an example project markdown file"""
    example_path = PROJECTS_DIR / 'bone-fracture-detection.md'
    
    example_content = '''---
title: AI-Powered Bone Fracture Detection
date: Feb 2026
category: ml, cv, deploy
tags: Deep Learning, Computer Vision, PyTorch, Faster R-CNN, Medical AI, LIVE
github: https://github.com/mvanslyke/bone-fracture-detection
demo_url: https://huggingface.co/spaces/mvanslyke/bone-fracture-detection
demo_description: Upload an X-ray image to detect and localize bone fractures with bounding boxes
article: https://mvanslyke-ml.com/blog/bone-fracture-detection
metrics:
  Accuracy: 88.6%
  Loss: 11.4%
  Model: ResNet50 FPN
  Training Time: 1 week
---

## Overview

Developed a deep learning system to detect and localize bone fractures in X-ray images of upper extremities using Faster R-CNN with ResNet50 FPN V2 backbone. The model achieved 88.6% accuracy, exceeding the initial 85% target.

## Problem Statement

Medical facilities process thousands of X-rays daily. Accurate fracture identification is challenging, especially for trainees and in emergency settings. Small hairline fractures can be easily missed, yet timely detection is critical for proper treatment.

## Solution

Built a production-grade AI system using:

- **Model**: Faster R-CNN with ResNet50 FPN V2 backbone
- **Training**: 5 epochs on 3,000+ annotated X-ray images
- **Optimization**: Aggressive data augmentation for real-world robustness
- **Deployment**: Interactive demo on Hugging Face Spaces

## Key Results

| Metric | Value |
|--------|-------|
| Final Loss | 11.4% |
| Accuracy | 88.6% |
| Target | 85% ✅ |
| Dataset | 3,000+ images |

## Technical Highlights

### Data Augmentation
Implemented multiple augmentation techniques to simulate real-world conditions:
- Random AutoContrast (10%)
- Random Sharpness (10%)
- Random Horizontal Flip (10%)
- Random Inversion (10%)
- Random Erasing (10%)

### Model Comparison
Trained and compared 4 model variants:
1. Faster R-CNN + ResNet50 FPN
2. Faster R-CNN + ResNet50 FPN V2 (Winner)
3. Faster R-CNN + MobileNet V3 Large
4. Faster R-CNN + MobileNet V3 Large 320

## Real-World Impact

### For Medical Professionals
- **Second Opinion Tool**: Automated verification system
- **Triage Support**: Prioritize urgent cases in busy ERs
- **Training Aid**: Educational tool for medical students

### For Healthcare Systems
- **Faster Diagnosis**: Reduced time from imaging to treatment
- **Error Reduction**: Catch subtle fractures that might be missed
- **Cost Efficiency**: Optimize specialist consultation time

## Live Demo

Try the interactive demo on Hugging Face Spaces:
- Upload X-ray images (JPEG, PNG)
- Real-time fracture detection with bounding boxes
- Confidence scores for each prediction
- Support for multiple fractures per image

**[Launch Demo →](https://huggingface.co/spaces/mvanslyke/bone-fracture-detection)**

## Technical Stack

**Languages & Frameworks:**
- Python 3.10
- PyTorch & TorchVision
- OpenCV

**Training:**
- Kaggle GPU acceleration
- Adam optimizer (lr: 0.0001)
- Batch size: 12
- 5 training epochs

## Future Work

- Extend to lower extremities and spine
- Integration with hospital PACS systems
- Severity classification
- Real-time model retraining pipeline
'''
    
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not example_path.exists():
        with open(example_path, 'w', encoding='utf-8') as f:
            f.write(example_content)
        
        print(f"\n📝 Created example project: {example_path}")
        print(f"   Edit this file and create more .md files in {PROJECTS_DIR}/")

def main():
    """Main entry point"""
    # Create example if projects directory is empty
    if not PROJECTS_DIR.exists() or not list(PROJECTS_DIR.glob('*.md')):
        print("Creating example project...")
        create_example_project()
    
    # Generate projects.json
    try:
        generate_projects_json()
    except Exception as e:
        print(f"\n❌ Error generating projects.json: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
