# You might need to run: pip install passlib bcrypt
from passlib.context import CryptContext

# 1. Setup the hashing configuration (Same as your backend)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Define your Admin Password
admin_password = "Admin@123"

# 3. Generate Hash
hashed_password = pwd_context.hash(admin_password)

print("--- COPY THIS HASH ---")
print(hashed_password)
print("----------------------")
