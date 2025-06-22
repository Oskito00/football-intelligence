FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY .. .

# Run the scheduler
CMD ["python", "-m", "scheduler.scheduler"]