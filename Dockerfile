# 1. Use the "bookworm" tag to ensure we get the stable Debian OS
# This guarantees that 'libaio1' exists.
FROM python:3.11-bookworm

# 2. Install system dependencies
# libaio1 is required for Oracle, and it IS available in bookworm
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

# 4. Copy requirements and install them
COPY requirements.txt .

# Upgrade pip and install libraries
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY . .

# 6. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
