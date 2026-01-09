import bcrypt
# This is the password you want to use for Login
password = b"niLE$#1994" 

# Generate the Hash
hashed = bcrypt.hashpw(password, bcrypt.gensalt())

# Print the string to copy
print(hashed.decode())
print("NILESH")

