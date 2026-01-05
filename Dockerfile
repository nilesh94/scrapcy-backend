# 1. Use Python 3.11 Bookworm (Stable Linux)
FROM python:3.11-bookworm

# 2. Install System Dependencies
# libaio1 is required for Oracle.
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 3. Set Work Directory
WORKDIR /app

# 4. CRITICAL FIX: Install python-oracledb DIRECTLY
# We do this BEFORE copying requirements.txt to bypass any file formatting errors.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir python-oracledb

# 5. Copy requirements and install the rest
COPY requirements.txt .
# We use 'grep -v' to ignore python-oracledb in the file since we just installed it
RUN grep -v "python-oracledb" requirements.txt > reqs_clean.txt && \
    pip install --no-cache-dir -r reqs_clean.txt

# 6. Copy application code
COPY . .

# 7. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
