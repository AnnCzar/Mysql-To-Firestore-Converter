from converter.utils.mysql_utils import connect_mysql
from converter.utils.firestore_utils import connect_firestore

def test_connections():
    # Test MySQL
    try:
        conn, cursor = connect_mysql()
        cursor.execute("SHOW TABLES;")  # albo SELECT * FROM your_table LIMIT 5;
        tables = cursor.fetchall()
        print("Połączenie z MySQL działa. Tabele:")
        for t in tables:
            print(t)
    except Exception as e:
        print("Błąd połączenia z MySQL:", e)

    # Test Firestore
    try:
        db = connect_firestore()
        test_doc = {"test": "Firestore działa!"}
        db.collection("test_collection").add(test_doc)
        print("Połączenie z Firestore działa. Testowy dokument dodany.")
    except Exception as e:
        print("Błąd połączenia z Firestore:", e)

if __name__ == "__main__":
    test_connections()
