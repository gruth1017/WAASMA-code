from pymongo import MongoClient
import bcrypt

client = MongoClient("mongodb://localhost:27017/")

# This is a MongoDB database
db = client.WAASMA_flaskdb

# Collection names
user_collection = db.user_collection
settings_collection = db.settings_collection
sensor_collection = db.sensor_collection
test_sensor_collection = db.test_sensor_collection
sensor_config_collection = db.sensor_config_collection

def get_user(username):
    return user_collection.find_one({"username": username})

def create_user(username, password, role):
    # Hash the password before storing it
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    
    # Insert the user into the database with the hashed password and role
    user_collection.insert_one({
        "username": username,
        "password": hashed_pw.decode("utf-8"),  # Store password as a string
        "role": role
    })

def authenticate_user(username, password):
    # Retrieve the user from the database
    user = user_collection.find_one({"username": username})
    
    if user:
        stored_pw = user["password"].encode("utf-8")
        
        # Check if the password matches the hashed password in the database
        if bcrypt.checkpw(password.encode("utf-8"), stored_pw):
            return user["role"]  # Return the role if the password is correct
    
    return None  # Return None if authentication fails

def get_all_users():
    # Fetch all users with their usernames and roles
    return list(user_collection.find({}, {"_id": 0, "username": 1, "role": 1}))
