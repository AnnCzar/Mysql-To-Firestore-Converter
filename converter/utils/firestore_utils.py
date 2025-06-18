import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

def connect_firestore(key_path):
    # Sprawdź czy plik istnieje
    if not os.path.exists(key_path):
        print(f"Plik klucza nie istnieje: {key_path}")
        return None

    # Sprawdź czy to prawidłowy JSON
    try:
        with open(key_path, 'r') as f:
            key_data = json.load(f)
        if 'type' not in key_data or key_data['type'] != 'service_account':
            print("Nieprawidłowy format klucza serwisowego")
            return None
    except json.JSONDecodeError:
        print("Plik klucza zawiera nieprawidłowy JSON")
        return None
    try:
        # Usuń wszystkie istniejące aplikacje Firebase
        for app in list(firebase_admin._apps.values()):
            firebase_admin.delete_app(app)

        # Wyczyść słownik aplikacji
        firebase_admin._apps.clear()

        # Inicjalizuj nową aplikację z nowym kluczem
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

        print(f"Zainicjalizowano Firebase z kluczem: {key_path}")
        return firestore.client()

    except Exception as e:
        print(f"Błąd połączenia z Firestoreeeeee: {e}")
        return None
def delete_collection(coll_ref, batch_size=100):
    try:
        docs = coll_ref.limit(batch_size).stream()
        deleted = 0

        for doc in docs:
            try:
                print(f"Usuwanie dokumentu: {doc.id} z kolekcji {coll_ref.id}")
                doc.reference.delete()
                deleted += 1
            except Exception as e:
                print(f"Błąd usuwania dokumentu {doc.id}: {e}")
                continue
        if deleted >= batch_size:
            return delete_collection(coll_ref, batch_size)
    except Exception as e:

        print(f"Błąd usuwania kolekcji {coll_ref.id}: {e}")
        raise e

def delete_all_collections(db):
    try:
        collections = db.collections()
        for collection in collections:
            try:
                print(f"Usuwanie kolekcji: {collection.id}")
                delete_collection(collection)
            except Exception as e:
                print(f"Błąd przy kolekcji {collection.id}: {e}")
                continue

        print("Zakończono usuwanie wszystkich kolekcji")

    except Exception as e:
        print(f"Błąd pobierania kolekcji: {e}")
        raise e

# db = connect_firestore()
# delete_all_collections(db)
