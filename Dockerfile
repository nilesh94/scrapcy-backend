# 1. Use Python 3.9 Bullseye (Maximum Stability)
FROM python:3.9-slim-bullseye

# 2. Install Build Tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libaio1 \
    git \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip install --no-cache-dir git+https://github.com/oracle/python-oracledb.git@v2.5.1

RUN pip install --no-cache-dir email-validator

# 7. Copy requirements and install the rest
COPY requirements.txt .
# We remove 'python-oracledb' since we installed it above
RUN grep -v "python-oracledb" requirements.txt > reqs_clean.txt && \
    pip install --no-cache-dir -r reqs_clean.txt

# 8. Copy application code
COPY . .

# 9. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
