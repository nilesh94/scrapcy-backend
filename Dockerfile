# 1. Force the platform to x86_64 (amd64)
# This guarantees compatibility with Oracle's pre-compiled wheels.
FROM --platform=linux/amd64 python:3.11-bookworm

# 2. Install system dependencies
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

# 4. Debug Step: Install python-oracledb explicitly FIRST
# This isolates the error. If this works, the issue was your requirements file.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir python-oracledb

# 5. Copy requirements and install the rest
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
