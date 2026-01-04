# 1. Use the full official Python image (Fixes "No matching distribution" error)
FROM python:3.11

# 2. Update system and install Oracle dependencies
# libaio1 is required for the Oracle Client libraries
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

# 4. Copy and install requirements
COPY requirements.txt .

# Upgrade pip and install libraries
# We use --verbose to see exactly what happens if it fails
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY . .

# 6. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
