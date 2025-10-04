FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests boto3
COPY app.py /app/app.py
EXPOSE 8016
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD curl -fsS http://localhost:8016/health || exit 1
CMD ["python", "/app/app.py"]
