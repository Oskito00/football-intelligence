FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first
COPY requirements.txt ./chatbot/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Run the Flask API
CMD ["uvicorn", "chatbot.api:app", "--host", "0.0.0.0", "--port", "5000"]