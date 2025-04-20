import os
import firebase_admin
from firebase_admin import credentials, firestore
from converter import config

def connect_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(config.FIRESTORE_KEY_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


