"""
Lambda proxy for the fracture-detector SageMaker Serverless endpoint.

The frontend POSTs JSON: { "image": "<base64>", "filename": "xray.jpg" }
We decode the image bytes, forward them to SageMaker as application/octet-stream,
parse the JSON response, and return it with CORS headers.
"""

import base64
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Structured logging makes CloudWatch Insights queries easier
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Be explicit about region so the client always targets the right endpoint
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "fracture-detector")

runtime = boto3.client("sagemaker-runtime", region_name=REGION)

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
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod", "POST")
    ).upper()

    logger.info("Received %s request — endpoint=%s region=%s", method, ENDPOINT_NAME, REGION)

    if method == "OPTIONS":
        return _response(200, {"ok": True})

    # ── Parse body ────────────────────────────────────────────────────
    try:
        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        payload = json.loads(raw_body)
    except (ValueError, TypeError) as e:
        logger.error("Invalid JSON body: %s", e)
        return _response(400, {"error": f"Invalid JSON body: {e}"})

    b64_image = payload.get("image")
    if not b64_image:
        return _response(400, {"error": "Missing 'image' field (base64-encoded image bytes)"})

    try:
        image_bytes = base64.b64decode(b64_image)
    except Exception as e:
        logger.error("Base64 decode failed: %s", e)
        return _response(400, {"error": f"Could not decode base64 image: {e}"})

    logger.info("Decoded image — %d bytes — invoking SageMaker endpoint", len(image_bytes))

    # ── Invoke SageMaker ──────────────────────────────────────────────
    try:
        sm_response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/octet-stream",
            Accept="application/json",
            Body=image_bytes,
        )
        result_bytes = sm_response["Body"].read()
        logger.info("SageMaker responded — %d bytes", len(result_bytes))

        try:
            result = json.loads(result_bytes)
        except ValueError:
            result = {"raw": result_bytes.decode("utf-8", errors="replace")}

    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"]["Message"]
        logger.error("SageMaker ClientError %s: %s", code, msg)

        # Surface a human-readable message for the most common failures
        if code == "ValidationError" and "not found" in msg.lower():
            return _response(503, {
                "error": "SageMaker endpoint not found",
                "detail": f"Endpoint '{ENDPOINT_NAME}' does not exist or is not InService. "
                          "Check the SageMaker console.",
            })
        if code in ("AccessDeniedException", "UnauthorizedOperation"):
            return _response(403, {
                "error": "Lambda lacks permission to invoke the SageMaker endpoint",
                "detail": "Attach the SageMakerInvokeEndpoint inline policy to MLPortfolioLambdaRole.",
            })
        return _response(502, {"error": f"SageMaker error ({code})", "detail": msg})

    except Exception as e:
        logger.exception("Unexpected error during SageMaker invocation")
        return _response(500, {"error": "Inference failed", "detail": str(e)})

    return _response(200, {
        "filename": payload.get("filename"),
        "endpoint": ENDPOINT_NAME,
        "predictions": result,
    })
