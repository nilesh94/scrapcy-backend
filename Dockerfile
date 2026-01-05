# 1. Use Python 3.10 (Highly stable with Oracle drivers)
# We use 'slim-bookworm' to get the correct Debian version for libaio
FROM python:3.10-slim-bookworm

# 2. Install System Dependencies
# 'build-essential': Contains GCC compilers (Critical for building from source)
# 'libaio1': Required for Oracle Database communication
RUN apt-get update && apt-get install -y \
    build-essential \
    libaio1 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

# 4. Copy requirements and install them
COPY requirements.txt .

# Upgrade pip and build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 5. Install Dependencies (Verbose mode)
# If binary wheels fail, build-essential allows pip to compile from source
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
