# 1. Use "slim-bookworm" to ensure a stable Debian OS version
FROM python:3.11-slim-bookworm

# 2. Install system dependencies
# (libaio1 is definitely available in this version)
RUN apt-get update && apt-get install -y \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory
WORKDIR /app

# 4. Copy requirements and install them
COPY requirements.txt .
# Upgrade pip tools first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application
COPY . .

# 6. Command to start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
