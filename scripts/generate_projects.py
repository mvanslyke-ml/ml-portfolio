#!/usr/bin/env python3
"""
Auto-generate projects.json from Markdown Blog Posts
AND create HTML blog posts from markdown files
"""

import json
import re
from pathlib import Path
from datetime import datetime
import yaml
import sys

try:
    import markdown
    from markdown.extensions import fenced_code, tables, toc
except ImportError:
    print("Installing markdown...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'markdown', '--quiet'])
    import markdown

PROJECTS_DIR = Path('projects')
OUTPUT_FILE = Path('website/projects.json')
BLOG_OUTPUT_DIR = Path('website/blog')
BUILD_DIR = Path('.build')

def parse_frontmatter(content):
    """Extract YAML frontmatter from markdown, or extract from content if missing"""
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
        # No frontmatter - try to extract from content
        print(f"   ℹ️  No frontmatter found - extracting from content")
        
        # Extract title from first H1 heading
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            
            # Extract subtitle/description from italic text or first paragraph
            description = ''
            desc_match = re.search(r'^\*(.+?)\*$', content, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()
            
            # Try to infer category from keywords in title/content
            categories = ['ml']  # Default
            title_lower = title.lower()
            content_lower = content.lower()
            
            if any(word in title_lower or word in content_lower[:500] for word in ['nlp', 'text', 'sentiment', 'language']):
                categories.append('nlp')
            if any(word in title_lower or word in content_lower[:500] for word in ['vision', 'image', 'detection', 'classification', 'cnn', 'resnet']):
                categories.append('cv')
            if any(word in title_lower or word in content_lower[:500] for word in ['deploy', 'production', 'api', 'lambda', 'live demo']):
                categories.append('deploy')
            
            # Extract tags from common technical terms
            tags = []
            tech_terms = ['pytorch', 'tensorflow', 'keras', 'scikit-learn', 'aws', 'lambda', 
                         'bert', 'resnet', 'yolo', 'cnn', 'rnn', 'lstm', 'gpt', 'transformer']
            for term in tech_terms:
                if term in content_lower[:1000]:
                    tags.append(term.upper() if term in ['aws', 'bert', 'yolo', 'cnn', 'rnn', 'lstm', 'gpt'] else term.title())
            
            frontmatter = {
                'title': title,
                'category': categories
            }
            if description:
                frontmatter['description'] = description
            if tags:
                frontmatter['tags'] = tags
            
            return frontmatter, content
        else:
            return {}, content

def extract_metrics_from_markdown(body):
    """Extract metrics from markdown tables or sections"""
    metrics = {}
    
    table_pattern = r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
    matches = re.findall(table_pattern, body)
    
    for key, value in matches:
        key = key.strip()
        value = value.strip()
        if key.lower() not in ['metric', 'name', 'key'] and value.lower() not in ['value', '-', '--', '---']:
            metrics[key] = value
    
    return metrics

def generate_project_id(title):
    """Generate URL-safe project ID from title"""
    project_id = title.lower()
    project_id = re.sub(r'[^\w\s-]', '', project_id)
    project_id = re.sub(r'[-\s]+', '-', project_id)
    return project_id

def markdown_to_html(md_content, title, frontmatter):
    """Convert markdown to styled HTML blog post"""
    
    md = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc', 'nl2br', 'sane_lists'])
    body_html = md.convert(md_content)
    
    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | ML Portfolio</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Sora:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --primary: #0A0E27;
            --secondary: #1A1F3A;
            --accent: #00D9FF;
            --purple: #B794F6;
            --green: #00FF88;
            --text: #E8EEF2;
            --text-muted: #8B95A5;
            --border: rgba(0, 217, 255, 0.2);
            --code-bg: #0D1117;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Sora', sans-serif; background: var(--primary); color: var(--text); line-height: 1.8; padding: 2rem; }}
        .container {{ max-width: 900px; margin: 0 auto; background: var(--secondary); padding: 3rem; border: 1px solid var(--border); }}
        .back-link {{ display: inline-block; color: var(--accent); text-decoration: none; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; margin-bottom: 2rem; transition: all 0.3s ease; }}
        .back-link:hover {{ text-shadow: 0 0 10px var(--accent); }}
        .back-link::before {{ content: '← '; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; color: var(--accent); }}
        .meta {{ display: flex; gap: 2rem; margin-bottom: 2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text-muted); }}
        .tags {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 2rem; }}
        .tag {{ padding: 0.4rem 0.8rem; background: rgba(0, 217, 255, 0.1); color: var(--accent); font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; border: 1px solid rgba(0, 217, 255, 0.3); }}
        .content {{ font-size: 1.05rem; line-height: 1.9; }}
        .content h2 {{ font-size: 2rem; margin: 2.5rem 0 1rem 0; color: var(--accent); }}
        .content h3 {{ font-size: 1.5rem; margin: 2rem 0 1rem 0; color: var(--purple); }}
        .content p {{ margin-bottom: 1.5rem; }}
        .content ul, .content ol {{ margin: 1.5rem 0 1.5rem 2rem; }}
        .content li {{ margin-bottom: 0.75rem; }}
        .content code {{ background: var(--code-bg); padding: 0.2rem 0.5rem; border-radius: 3px; font-family: 'JetBrains Mono', monospace; font-size: 0.9em; color: var(--green); }}
        .content pre {{ background: var(--code-bg); padding: 1.5rem; border-radius: 4px; overflow-x: auto; margin: 1.5rem 0; border: 1px solid var(--border); }}
        .content pre code {{ background: none; padding: 0; color: var(--text); }}
        .content table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; }}
        .content table th, .content table td {{ padding: 1rem; border: 1px solid var(--border); text-align: left; }}
        .content table th {{ background: var(--code-bg); color: var(--accent); font-weight: 600; }}
        .content a {{ color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: all 0.3s ease; }}
        .content a:hover {{ border-bottom-color: var(--accent); }}
        .content blockquote {{ border-left: 4px solid var(--accent); padding-left: 1.5rem; margin: 1.5rem 0; color: var(--text-muted); font-style: italic; }}
        .content img {{ max-width: 100%; height: auto; display: block; margin: 2rem auto; border: 1px solid var(--border); border-radius: 4px; }}
        .project-links {{ display: flex; gap: 1rem; margin: 3rem 0; flex-wrap: wrap; }}
        .project-link {{ padding: 1rem 2rem; text-decoration: none; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; border: 1px solid var(--border); color: var(--text); transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 0.5rem; }}
        .project-link:hover {{ border-color: var(--accent); color: var(--accent); background: rgba(0, 217, 255, 0.05); }}
        .project-link.demo {{ background: rgba(0, 255, 136, 0.1); border-color: var(--green); color: var(--green); }}
        .project-link.demo:hover {{ background: rgba(0, 255, 136, 0.2); }}
        @media (max-width: 768px) {{ body {{ padding: 1rem; }} .container {{ padding: 1.5rem; }} h1 {{ font-size: 2rem; }} .project-links {{ flex-direction: column; }} .project-link {{ width: 100%; justify-content: center; }} }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">Back to Portfolio</a>
        <h1>{title}</h1>
        <div class="meta">
            <span>📅 {frontmatter.get('date', '')}</span>
            <span>🏷️ {', '.join(frontmatter.get('category', []))}</span>
        </div>
        <div class="tags">
            {''.join([f'<span class="tag">{tag}</span>' for tag in frontmatter.get('tags', [])])}
        </div>
        <div class="project-links">
            {f'<a href="{frontmatter.get("github")}" class="project-link" target="_blank">📂 View Code on GitHub</a>' if frontmatter.get('github') else ''}
            {f'<a href="{frontmatter.get("demo_url")}" class="project-link demo" target="_blank">🚀 Try Live Demo</a>' if frontmatter.get('demo_url') else ''}
        </div>
        <div class="content">
            {body_html}
        </div>
        <div class="project-links">
            <a href="/" class="project-link">← Back to Portfolio</a>
        </div>
    </div>
</body>
</html>'''
    
    return html_template

def create_blog_post(md_file, project_id, frontmatter, body):
    """Create HTML blog post from markdown"""
    BLOG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html_content = markdown_to_html(body, frontmatter['title'], frontmatter)
    blog_file = BLOG_OUTPUT_DIR / f"{project_id}.html"
    with open(blog_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"   ✅ Created blog post: blog/{project_id}.html")
    return f"/blog/{project_id}.html"

def markdown_to_project(md_file):
    """Convert markdown file to project JSON entry"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    frontmatter, body = parse_frontmatter(content)
    
    if 'title' not in frontmatter:
        print(f"⚠️  Skipping {md_file.name}: could not extract title from frontmatter or content")
        print(f"   Add YAML frontmatter with 'title:' field, or start file with '# Title'")
        return None
    
    project_id = frontmatter.get('id', generate_project_id(frontmatter['title']))
    
    date_str = frontmatter.get('date')
    if not date_str:
        mod_time = datetime.fromtimestamp(md_file.stat().st_mtime)
        date_str = mod_time.strftime('%b %Y')
    
    description = frontmatter.get('description', '')
    if not description:
        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip() and not p.startswith('#')]
        if paragraphs:
            description = paragraphs[0][:200]
    
    categories = frontmatter.get('category', frontmatter.get('categories', ['ml']))
    if isinstance(categories, str):
        categories = [cat.strip() for cat in categories.split(',')]
    
    tags = frontmatter.get('tags', [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(',')]
    
    metrics = frontmatter.get('metrics', extract_metrics_from_markdown(body))
    
    blog_url = create_blog_post(md_file, project_id, frontmatter, body)
    
    # Check for Lambda function — demo_url discovery order:
    # 1. Explicit demo_url in frontmatter
    # 2. Matched via deployment manifest + api_docs.json
    # 3. Fallback: api_docs.json directly (handles re-deploy failures gracefully)
    demo_url = frontmatter.get('demo_url')
    if not demo_url:
        expected_route = f"/{project_id}"
        api_docs_path = BUILD_DIR / 'api_docs.json'

        # Try manifest match first
        manifest_path = BUILD_DIR / 'deployment_manifest.json'
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                lambda_function_name = f"ml-portfolio-{project_id}"
                for func in manifest.get('functions', []):
                    if func['function_name'] == lambda_function_name:
                        if api_docs_path.exists():
                            with open(api_docs_path) as f:
                                api_docs = json.load(f)
                            for endpoint in api_docs['endpoints']:
                                if func['api_route'] in endpoint['path']:
                                    demo_url = endpoint['url']
                                    break
            except Exception as e:
                print(f"   ⚠️  Error checking manifest: {e}")

        # Fallback: search api_docs.json directly by expected route
        # This picks up the URL even when a re-deploy fails but the
        # Lambda + API Gateway are still live from a previous run.
        if not demo_url and api_docs_path.exists():
            try:
                with open(api_docs_path) as f:
                    api_docs = json.load(f)
                for endpoint in api_docs.get('endpoints', []):
                    if endpoint.get('path', '').rstrip('/') == expected_route:
                        demo_url = endpoint['url']
                        break
            except Exception as e:
                print(f"   ⚠️  Error reading api_docs fallback: {e}")
    
    project = {
        'id': project_id,
        'title': frontmatter['title'],
        'date': date_str,
        'description': description,
        'category': categories,
        'tags': tags,
        'blog_url': blog_url
    }
    
    if metrics:
        project['metrics'] = metrics
    
    # GitHub URL - auto-generate if not provided in frontmatter
    if frontmatter.get('github'):
        project['github'] = frontmatter['github']
    else:
        # Auto-generate URL to project directory in monorepo
        project['github'] = f"https://github.com/mvanslyke-ml/ml-portfolio/tree/main/projects/{project_id}"
    
    if demo_url:
        project['demo_url'] = demo_url
        project['demo_description'] = frontmatter.get('demo_description', f"Live demo of {frontmatter['title']}")
    if frontmatter.get('article'):
        project['article'] = frontmatter['article']
    
    return project

def generate_projects_json():
    """Generate projects.json from all markdown files"""
    print("=" * 60)
    print("📝 Generating projects.json and blog posts")
    print("=" * 60)
    
    if not PROJECTS_DIR.exists():
        PROJECTS_DIR.mkdir(parents=True)
        return
    
    md_files = list(PROJECTS_DIR.glob('*.md'))
    if not md_files:
        print(f"⚠️  No markdown files found in {PROJECTS_DIR}")
        return
    
    print(f"\n📂 Found {len(md_files)} markdown file(s)\n")
    projects = []
    
    for md_file in sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True):
        print(f"{'─' * 60}")
        print(f"Processing: {md_file.name}")
        project = markdown_to_project(md_file)
        if project:
            projects.append(project)
            print(f"✅ Added: {project['title']}")
            print(f"   Blog: {project['blog_url']}")
            if project.get('github'):
                print(f"   GitHub: {project['github']}")
            if project.get('demo_url'):
                print(f"   🟢 Demo: {project['demo_url']}")
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"✅ Generated projects.json with {len(projects)} project(s)")
    print(f"✅ Created {len(projects)} blog post(s) in {BLOG_OUTPUT_DIR}/")
    print(f"{'=' * 60}")

def main():
    try:
        generate_projects_json()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
