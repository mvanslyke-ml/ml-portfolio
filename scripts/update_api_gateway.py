#!/usr/bin/env python3
"""
Automated API Gateway Configuration
Creates/updates API Gateway routes for all deployed Lambda functions.
Falls back to AWS discovery if the deployment manifest is empty (e.g., after a
failed Lambda update that didn't change anything meaningful).
"""

import json
import boto3
from pathlib import Path
import sys

# AWS clients
apigateway_client = boto3.client('apigatewayv2')
lambda_client = boto3.client('lambda')

# Configuration
API_NAME = 'ML-Portfolio-API'
BUILD_DIR = Path('.build')
FUNCTION_PREFIX = 'ml-portfolio-'


# ---------------------------------------------------------------------------
# Fallback: discover already-deployed functions directly from AWS
# ---------------------------------------------------------------------------

def discover_deployed_functions():
    """
    Query Lambda for all functions whose name starts with FUNCTION_PREFIX.
    Returns a list in the same shape that deploy_lambda.py would have written
    to the manifest, so the rest of this script can treat them identically.
    """
    found = []
    paginator = lambda_client.get_paginator('list_functions')
    for page in paginator.paginate():
        for fn in page.get('Functions', []):
            name = fn['FunctionName']
            if not name.startswith(FUNCTION_PREFIX):
                continue

            model_id = name[len(FUNCTION_PREFIX):]
            arn = fn['FunctionArn']

            # Try to read api_route from env vars set during deployment
            env = fn.get('Environment', {}).get('Variables', {})
            api_route = env.get('API_ROUTE', f'/{model_id}')

            found.append({
                'function_name': name,
                'function_arn': arn,
                'api_route': api_route,
                'config': {
                    'description': fn.get('Description', ''),
                    'api_route': api_route,
                }
            })

    return found


# ---------------------------------------------------------------------------
# API Gateway helpers
# ---------------------------------------------------------------------------

def get_or_create_api():
    """Get existing API or create a new one."""
    try:
        response = apigateway_client.get_apis()
        for api in response.get('Items', []):
            if api['Name'] == API_NAME:
                print(f"✅ Found existing API: {api['ApiId']} ({api['ApiEndpoint']})")
                return api['ApiId'], api['ApiEndpoint']
    except Exception as e:
        print(f"Error listing APIs: {e}")

    print(f"Creating new API Gateway: {API_NAME}")
    try:
        response = apigateway_client.create_api(
            Name=API_NAME,
            ProtocolType='HTTP',
            CorsConfiguration={
                'AllowOrigins': ['https://mvanslyke-ml.com', 'https://www.mvanslyke-ml.com', 'http://localhost:8000', 'http://localhost:5000'],
                'AllowMethods': ['GET', 'POST', 'OPTIONS'],
                'AllowHeaders': ['Content-Type', 'Authorization'],
                'MaxAge': 300
            },
            Description='API for ML Portfolio live demos'
        )

        api_id = response['ApiId']
        api_endpoint = response['ApiEndpoint']

        apigateway_client.create_stage(
            ApiId=api_id,
            StageName='$default',
            AutoDeploy=True
        )

        print(f"✅ Created API: {api_id}")
        return api_id, api_endpoint
    except Exception as e:
        print(f"❌ Error creating API: {e}")
        sys.exit(1)


def get_existing_integrations(api_id):
    try:
        response = apigateway_client.get_integrations(ApiId=api_id)
        return {i['IntegrationUri']: i['IntegrationId'] for i in response.get('Items', [])}
    except Exception:
        return {}


def get_existing_routes(api_id):
    try:
        response = apigateway_client.get_routes(ApiId=api_id)
        return {r['RouteKey']: r['RouteId'] for r in response.get('Items', [])}
    except Exception:
        return {}


def create_lambda_integration(api_id, function_arn, function_name):
    """Create or return existing integration between API Gateway and Lambda."""
    existing_integrations = get_existing_integrations(api_id)

    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    integration_uri = (
        f"arn:aws:apigateway:{region}:lambda:path/2015-03-31"
        f"/functions/{function_arn}/invocations"
    )

    if integration_uri in existing_integrations:
        print(f"   Integration exists: {function_name}")
        return existing_integrations[integration_uri]

    try:
        response = apigateway_client.create_integration(
            ApiId=api_id,
            IntegrationType='AWS_PROXY',
            IntegrationUri=integration_uri,
            PayloadFormatVersion='2.0',
            TimeoutInMillis=30000
        )
        integration_id = response['IntegrationId']
        print(f"   ✅ Created integration for {function_name}")
        return integration_id
    except Exception as e:
        print(f"   ❌ Error creating integration: {e}")
        return None


def create_or_update_route(api_id, route_key, integration_id):
    """Create or update an API route."""
    existing_routes = get_existing_routes(api_id)
    try:
        if route_key in existing_routes:
            apigateway_client.update_route(
                ApiId=api_id,
                RouteId=existing_routes[route_key],
                Target=f"integrations/{integration_id}"
            )
            print(f"   ✅ Updated route: {route_key}")
        else:
            apigateway_client.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f"integrations/{integration_id}"
            )
            print(f"   ✅ Created route: {route_key}")
    except Exception as e:
        print(f"   ❌ Error creating/updating route: {e}")


def generate_api_docs(api_endpoint, deployed_functions):
    """Write api_docs.json consumed by the website's app.js."""
    docs = {
        'api_endpoint': api_endpoint,
        'endpoints': []
    }

    for func in deployed_functions:
        docs['endpoints'].append({
            'path': func['api_route'],
            'method': 'POST',
            'url': f"{api_endpoint}{func['api_route']}",
            'description': func['config'].get('description', ''),
            'example_request': func['config'].get('example_request', {}),
            'example_response': func['config'].get('example_response', {})
        })

    docs_path = BUILD_DIR / 'api_docs.json'
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    with open(docs_path, 'w') as f:
        json.dump(docs, f, indent=2)

    print(f"\n📄 API docs saved: {docs_path}")
    return docs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("🌐 API Gateway - Auto Configuration")
    print("=" * 60)

    # Load manifest written by deploy_lambda.py
    manifest_path = BUILD_DIR / 'deployment_manifest.json'
    deployed_functions = []

    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        deployed_functions = manifest.get('functions', [])
        if manifest.get('failed', 0) > 0:
            print(f"⚠️  Manifest reports {manifest['failed']} failed deployment(s).")
    else:
        print("⚠️  No deployment manifest found.")

    # If the manifest has no functions, fall back to live AWS discovery.
    # This handles the case where a re-deploy fails partway through but the
    # Lambda functions already exist and are still running.
    if not deployed_functions:
        print("\n🔍 Manifest is empty — querying AWS for existing functions...")
        deployed_functions = discover_deployed_functions()

        if deployed_functions:
            print(f"   Found {len(deployed_functions)} existing function(s) via AWS discovery:")
            for f in deployed_functions:
                print(f"     • {f['function_name']}")
        else:
            print("\n   No existing ml-portfolio-* functions found in AWS.")
            print("   Creating empty API docs and exiting.")
            generate_api_docs('', [])
            print("\n✅ Nothing to configure — add a model and re-run.")
            return

    print(f"\n📋 Configuring API for {len(deployed_functions)} function(s)\n")

    api_id, api_endpoint = get_or_create_api()

    for func in deployed_functions:
        print(f"\n{'─' * 60}")
        print(f"Configuring: {func['function_name']}")
        print(f"{'─' * 60}")

        integration_id = create_lambda_integration(
            api_id,
            func['function_arn'],
            func['function_name']
        )

        if integration_id:
            route_key = f"POST {func['api_route']}"
            create_or_update_route(api_id, route_key, integration_id)

    # Also copy api_docs.json to website/ so it can be deployed to S3
    docs = generate_api_docs(api_endpoint, deployed_functions)

    website_docs_path = Path('website') / 'api_docs.json'
    import shutil
    shutil.copy(BUILD_DIR / 'api_docs.json', website_docs_path)
    print(f"📄 Also copied to: {website_docs_path}")

    print("\n" + "=" * 60)
    print("✅ API Gateway Configuration Complete!")
    print("=" * 60)
    print(f"\n🌐 API Endpoint: {api_endpoint}")
    print("\n📝 Available Routes:")
    for func in deployed_functions:
        print(f"   POST {api_endpoint}{func['api_route']}")


if __name__ == '__main__':
    main()
