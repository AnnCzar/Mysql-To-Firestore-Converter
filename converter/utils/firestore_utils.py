import os

import firebase_admin
from firebase_admin import credentials, firestore
from converter import config

def connect_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(config.FIRESTORE_KEY_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def delete_collection(coll_ref, batch_size=100):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f"Usuwanie dokumentu: {doc.id} z kolekcji {coll_ref.id}")
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

def delete_all_collections(db):
    collections = db.collections()
    for collection in collections:
        print(f"Usuwanie kolekcji: {collection.id}")
        delete_collection(collection)


db = connect_firestore()
delete_all_collections(db)
