# harness/Dockerfile
# Use an official lightweight Python image.
FROM python:3.11-slim

# Set the working directory inside the container.
WORKDIR /app

# Copy all files from the build context (ge_api_tester/) to the container's working directory.
# This includes harness/, requirements.txt.
COPY . .

# Install Python dependencies specified in requirements.txt.
# --no-cache-dir: Reduces image size.
# -r /app/requirements.txt: Specifies the requirements file copied in the previous step.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Make sure the run_discovery.py script is executable
RUN chmod +x /app/harness/run_discovery.py

# Define the command to run the discovery script when the container starts.
# This will run the evolution process and then analyze the results with pytest.
CMD ["python", "harness/run_discovery.py"]
