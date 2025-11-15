# Use official Python 3.11 slim image
FROM python:3.11-slim

# Install system packages needed for building Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy all project files into the container
COPY . /app

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install -r requirements.txt

# Create data directories
RUN mkdir -p /app/data/bronze /app/data/silver /app/data/gold

# Ensure entrypoint script is executable
RUN chmod +x /app/docker-entrypoint.sh

# Set timezone & Python logging behavior
ENV TZ=Asia/Kolkata
ENV PYTHONUNBUFFERED=1

# Entrypoint + default command
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "src/runner.py"]
