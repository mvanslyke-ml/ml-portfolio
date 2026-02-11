#!/usr/bin/env python3
"""
Automated API Gateway Configuration
Automatically creates/updates API Gateway routes for all deployed Lambda functions
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
CUSTOM_DOMAIN = 'api.mvanslyke-ml.com'
BUILD_DIR = Path('.build')

def get_or_create_api():
    """Get existing API or create new one"""
    # List existing APIs
    try:
        response = apigateway_client.get_apis()
        
        for api in response.get('Items', []):
            if api['Name'] == API_NAME:
                print(f"✅ Found existing API: {api['ApiId']}")
                return api['ApiId'], api['ApiEndpoint']
    except Exception as e:
        print(f"Error listing APIs: {e}")
    
    # Create new API
    print(f"Creating new API Gateway: {API_NAME}")
    try:
        response = apigateway_client.create_api(
            Name=API_NAME,
            ProtocolType='HTTP',
            CorsConfiguration={
                'AllowOrigins': ['https://mvanslyke-ml.com', 'http://localhost:8000'],
                'AllowMethods': ['GET', 'POST', 'OPTIONS'],
                'AllowHeaders': ['Content-Type', 'Authorization'],
                'MaxAge': 300
            },
            Description='API for ML Portfolio live demos'
        )
        
        api_id = response['ApiId']
        api_endpoint = response['ApiEndpoint']
        
        # Create default stage
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
    """Get all existing integrations"""
    try:
        response = apigateway_client.get_integrations(ApiId=api_id)
        return {i['IntegrationUri']: i['IntegrationId'] for i in response.get('Items', [])}
    except:
        return {}

def get_existing_routes(api_id):
    """Get all existing routes"""
    try:
        response = apigateway_client.get_routes(ApiId=api_id)
        return {r['RouteKey']: r['RouteId'] for r in response.get('Items', [])}
    except:
        return {}

def create_lambda_integration(api_id, function_arn, function_name):
    """Create integration between API Gateway and Lambda"""
    existing_integrations = get_existing_integrations(api_id)
    
    # Check if integration already exists
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    integration_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{function_arn}/invocations"
    
    if integration_uri in existing_integrations:
        print(f"   Integration exists: {function_name}")
        return existing_integrations[integration_uri]
    
    # Create new integration
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

def create_route(api_id, route_key, integration_id):
    """Create or update API route"""
    existing_routes = get_existing_routes(api_id)
    
    try:
        if route_key in existing_routes:
            # Update existing route
            apigateway_client.update_route(
                ApiId=api_id,
                RouteId=existing_routes[route_key],
                Target=f"integrations/{integration_id}"
            )
            print(f"   ✅ Updated route: {route_key}")
        else:
            # Create new route
            apigateway_client.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f"integrations/{integration_id}"
            )
            print(f"   ✅ Created route: {route_key}")
    except Exception as e:
        print(f"   ❌ Error creating/updating route: {e}")

def generate_api_docs(api_endpoint, deployed_functions):
    """Generate API documentation"""
    docs = {
        'api_endpoint': api_endpoint,
        'endpoints': []
    }
    
    for func in deployed_functions:
        endpoint_info = {
            'path': func['api_route'],
            'method': 'POST',
            'url': f"{api_endpoint}{func['api_route']}",
            'description': func['config'].get('description', ''),
            'example_request': func['config'].get('example_request', {}),
            'example_response': func['config'].get('example_response', {})
        }
        docs['endpoints'].append(endpoint_info)
    
    # Save API docs
    docs_path = BUILD_DIR / 'api_docs.json'
    with open(docs_path, 'w') as f:
        json.dump(docs, f, indent=2)
    
    print(f"\n📄 API documentation saved: {docs_path}")
    return docs

def main():
    """Main API Gateway configuration"""
    print("=" * 60)
    print("🌐 API Gateway - Auto Configuration")
    print("=" * 60)
    
    # Load deployment manifest
    manifest_path = BUILD_DIR / 'deployment_manifest.json'
    if not manifest_path.exists():
        print("⚠️  No deployment manifest found.")
        print("   This is fine - no Lambda functions to configure!")
        print("   Creating empty API docs...")
        
        # Create empty API docs
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        empty_docs = {
            'api_endpoint': None,
            'endpoints': []
        }
        docs_path = BUILD_DIR / 'api_docs.json'
        with open(docs_path, 'w') as f:
            json.dump(empty_docs, f, indent=2)
        
        print(f"\n✅ Created empty API docs: {docs_path}")
        print("\n💡 Add models when ready:")
        print("   1. Create models/my-model/ directory")
        print("   2. Add config.yml and lambda_function.py")
        print("   3. Commit and push - deployment will happen automatically!")
        return
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    deployed_functions = manifest.get('functions', [])
    
    if not deployed_functions:
        print("⚠️  No functions to configure")
        print("   Creating empty API docs...")
        
        # Create empty API docs
        empty_docs = {
            'api_endpoint': None,
            'endpoints': []
        }
        docs_path = BUILD_DIR / 'api_docs.json'
        with open(docs_path, 'w') as f:
            json.dump(empty_docs, f, indent=2)
        
        print(f"\n✅ No Lambda functions deployed yet - this is fine!")
        return
    
    print(f"\n📋 Configuring API for {len(deployed_functions)} function(s)\n")
    
    # Get or create API
    api_id, api_endpoint = get_or_create_api()
    
    # Configure each function
    for func in deployed_functions:
        print(f"\n{'─' * 60}")
        print(f"Configuring: {func['function_name']}")
        print(f"{'─' * 60}")
        
        # Create integration
        integration_id = create_lambda_integration(
            api_id,
            func['function_arn'],
            func['function_name']
        )
        
        if integration_id:
            # Create route
            route_key = f"POST {func['api_route']}"
            create_route(api_id, route_key, integration_id)
    
    # Generate API documentation
    docs = generate_api_docs(api_endpoint, deployed_functions)
    
    print("\n" + "=" * 60)
    print("✅ API Gateway Configuration Complete!")
    print("=" * 60)
    print(f"\n🌐 API Endpoint: {api_endpoint}")
    print("\n📝 Available Routes:")
    for func in deployed_functions:
        print(f"   POST {api_endpoint}{func['api_route']}")
    
    print(f"\n💡 To use custom domain ({CUSTOM_DOMAIN}):")
    print(f"   1. Create ACM certificate for {CUSTOM_DOMAIN}")
    print(f"   2. In API Gateway console, configure custom domain")
    print(f"   3. Update Route 53 A record to point to API Gateway")

if __name__ == '__main__':
    main()
