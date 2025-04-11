# api/Dockerfile
# Use Python 3.10 base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api_server.py .

# Expose port for the API
EXPOSE 5000

# Run the API server
CMD ["python", "api_server.py"]
