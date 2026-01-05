# 1. Use Python 3.9 Bullseye (Maximum Stability)
FROM python:3.9-slim-bullseye

# 2. Install Build Tools
# We add 'git' (to download source) and 'python3-dev' (to compile it)
RUN apt-get update && apt-get install -y \
    build-essential \
    libaio1 \
    git \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Set work directory
WORKDIR /app

# 4. Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 5. 🔥 THE FIX: Install directly from GitHub
# We bypass PyPI search and download the code straight from Oracle
RUN pip install --no-cache-dir git+https://github.com/oracle/python-oracledb.git@v2.5.1

# 6. Copy requirements and install the rest
COPY requirements.txt .
# We remove 'python-oracledb' from the list because we just installed it manually above
RUN grep -v "python-oracledb" requirements.txt > reqs_clean.txt && \
    pip install --no-cache-dir -r reqs_clean.txt

# 7. Copy application code
COPY . .

# 8. Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
