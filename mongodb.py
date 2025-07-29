# mongodb.py
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

def store_session(session_string):
    collection.update_one(
        {"session_string": session_string},
        {"$set": {"session_string": session_string, "status": "active"}},
        upsert=True
    )

def get_all_sessions():
    docs = collection.find({"status": "active"})
    return [doc["session_string"] for doc in docs]
  
