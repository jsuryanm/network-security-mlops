from pymongo import MongoClient
from app.core.config import get_settings

settings = get_settings()
client = MongoClient(settings.mongodb_uri)

try:
    client.admin.command("ping")
    print("Connected successfully")
    client.close()

except Exception as e:
    raise Exception(
        "The following error occurred: ", e)