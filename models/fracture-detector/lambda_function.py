"""
Lambda proxy for the fracture-detector SageMaker Serverless endpoint.

The frontend POSTs JSON: { "image": "<base64>", "filename": "xray.jpg" }
We decode the image bytes, forward them to SageMaker as application/octet-stream,
parse the JSON response, and return it with CORS headers.
"""

import base64
import json
import os

import boto3

ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "fracture-detector")
runtime = boto3.client("sagemaker-runtime")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def _response(status, body):
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    method = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod", "POST")).upper()

    if method == "OPTIONS":
        return _response(200, {"ok": True})

    try:
        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        payload = json.loads(raw_body)
    except (ValueError, TypeError) as e:
        return _response(400, {"error": f"Invalid JSON body: {e}"})

    b64_image = payload.get("image")
    if not b64_image:
        return _response(400, {"error": "Missing 'image' field (base64-encoded image bytes)"})

    try:
        image_bytes = base64.b64decode(b64_image)
    except Exception as e:
        return _response(400, {"error": f"Could not decode base64 image: {e}"})

    try:
        sm_response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/octet-stream",
            Accept="application/json",
            Body=image_bytes,
        )
        result_bytes = sm_response["Body"].read()
        try:
            result = json.loads(result_bytes)
        except ValueError:
            result = {"raw": result_bytes.decode("utf-8", errors="replace")}
    except runtime.exceptions.ModelError as e:
        return _response(502, {"error": "SageMaker model error", "detail": str(e)})
    except Exception as e:
        return _response(500, {"error": "Inference failed", "detail": str(e)})

    return _response(200, {
        "filename": payload.get("filename"),
        "endpoint": ENDPOINT_NAME,
        "predictions": result,
    })
