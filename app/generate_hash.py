import bcrypt
# Replace with your actual password
password = b"Admin@123" 

# Generate Hash
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode())
