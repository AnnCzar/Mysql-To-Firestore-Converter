import json
from converter.utils.firestore_utils import connect_firestore


def get_info():
    file = open('../utils/firestore_export_20250422_155019/_schema_metadata.json')
    data = json.load(file)
    return data
def get_tables():
    # file = open('utils/firestore_export_20250422_155019/_schema_metadata.json')
    data = get_info()
    tables = data['tables']
    return tables
    # for table in tables:
    #     print(table)

def get_primary_key(table):
    data = get_info()
    for i in data['indexes']:
        if i['TABLE_NAME'] == table:
            return i['COLUMN_NAME']

def convert_tables():
    db = connect_firestore()
    tables = get_tables()
    for table in tables:
        file = open(f'../utils/firestore_export_20250422_155019/{table}.json')
        data = json.load(file)
        primary_key = get_primary_key(table)

        for document in data['documents']:
            primary_key_value = str(document[primary_key])
            db.collection(table).document(primary_key_value).set(document)
        print("Tabela " + table + " converted." )

        # collection = table
    print("Koniec Konwertowania")


convert_tables()