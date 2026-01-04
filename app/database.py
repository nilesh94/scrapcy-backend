from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys

# 1. Get the DB URL from Render Environment Variables
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    print("❌ DATABASE_URL missing! Set it in Render.")
    sys.exit(1)

print(f"🔌 Connecting to Oracle DB...")

# 2. Create Engine using 'python-oracledb'
try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        # 'thick_mode=False' is the default, which is what we want for Render
    )
    print("✅ Engine created successfully.")
except Exception as e:
    print(f"❌ Error connecting to Oracle DB: {e}")
    sys.exit(1)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
