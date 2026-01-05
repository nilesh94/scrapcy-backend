# 1. Use Python 3.9 on Debian Bullseye
# This is the "Gold Standard" for stability. It avoids the "too new" issues of Debian 12/13.
FROM python:3.9-slim-bullseye

# 2. Install System Dependencies
# We include 'build-essential' to allow compiling from source if needed
RUN apt-get update && apt-get install -y \
    build-essential \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

# 4. Upgrade pip explicitly
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 5. Install python-oracledb explicitly (Verbose mode for safety)
RUN pip install --no-cache-dir -v python-oracledb

# 6. Copy requirements and install the rest
COPY requirements.txt .
# Remove python-oracledb from requirements.txt to avoid double-install
RUN grep -v "python-oracledb" requirements.txt > reqs_clean.txt && \
    pip install --no-cache-dir -r reqs_clean.txt

# 7. Copy application code
COPY . .

# 8. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
