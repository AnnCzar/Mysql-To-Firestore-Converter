import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

FIRESTORE_KEY_PATH = os.getenv("FIRESTORE_KEY", "key.json")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")

