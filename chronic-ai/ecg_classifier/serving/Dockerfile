FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy serving code
COPY serve.py .

# Vertex AI uses port 8080 by default
ENV AIP_HTTP_PORT=8080
EXPOSE 8080

# Start the server
CMD ["python", "serve.py"]
