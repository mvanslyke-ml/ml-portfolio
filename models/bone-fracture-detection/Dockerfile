FROM public.ecr.aws/lambda/python:3.9

# Install CPU-only PyTorch (much smaller than default, sufficient for inference)
RUN pip install --no-cache-dir \
    torch==2.0.1 torchvision==0.15.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir \
    pillow==10.0.0 \
    boto3==1.28.0 \
    numpy==1.24.3

# Copy Lambda handler
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_function.lambda_handler"]
