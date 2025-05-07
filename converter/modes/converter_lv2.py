import json
from datetime import datetime
from converter.utils.firestore_utils import connect_firestore
from google.cloud import firestore
def get_info():
    file = open('../utils/firestore_export_20250422_155019/_schema_metadata.json')
    data = json.load(file)
    return data
def get_tables():
    # file = open('utils/firestore_export_20250422_155019/_schema_metadata.json')
    data = get_info()
    tables = data['tables']
    return tables

def get_primary_key(table):
    data = get_info()
    for i in data['indexes']:
        if i['TABLE_NAME'] == table:
            return i['COLUMN_NAME']
def get_foreign_keys(table):
    data = get_info()
    foreign_keys = []
    for i in data['foreign_keys']:
        if i['TABLE_NAME'] == table:
            foreign_keys.append(i)

    return foreign_keys
def get_column_types(table):
    return {
        col['COLUMN_NAME']: {
            'type': col['DATA_TYPE'].lower(),
            'max_length': col['CHARACTER_MAXIMUM_LENGTH']
        } for col in get_info()['data_types'] if col['TABLE_NAME'] == table
    }


def data_mapping(value, data_type, max_length):
    if value is None:
        return None
    try:
        if data_type in {'int', 'tinyint', 'smallint', 'mediumint', 'bigint'}:
            return int(value)
        if data_type in {'float', 'double', 'decimal'}:
            return float(value)

        if data_type == 'datetime':
            if value in {'CURRENT_TIMESTAMP', 'NOW()'}:
                return firestore.SERVER_TIMESTAMP
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y%m%d%H%M%S'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Nieznany format daty: {value}")

        if data_type == 'date':
            return datetime.strptime(value, '%Y-%m-%d')

        # true/false
        if data_type in {'boolean', 'bool'}:
            if str(value).isdigit():
                return bool(int(value))
            return str(value).lower() in ('true', 'yes', 't', 'y')

        if data_type in {'char', 'varchar', 'text'}:
            max_len = min(max_length, 1048487) if max_length else 1048487
            return str(value)[:max_len]

    except Exception as e:
        print(f'Błąd konwersji "{value}" ({data_type}): {str(e)}')
        return value


def convert_tables():
    db = connect_firestore()
    tables = get_tables()
    for table in tables:
        col_types = get_column_types(table)
        pk = get_primary_key(table)
    #     file = open(f'../utils/firestore_export_20250422_155019/{table}.json')
    #     data = json.load(file)
    #     # primary_key = get_primary_key(table)
    #     for document in data['documents']:
    #         primary_key_value = str(document[primary_key])
    #         db.collection(table).document(primary_key_value).set(document)
    #     print("Tabela " + table + " converted." )

        with open(f'../utils/firestore_export_20250422_155019/{table}.json') as f:
            batch = db.batch()
            collection_ref = db.collection(table)
            data = json.load(f)

            for idx, doc in enumerate(data['documents']):
                converted = {}
                for field, value in doc.items():
                    spec = col_types.get(field, {'type': 'varchar', 'max_length': None})
                    converted[field] = data_mapping(value, spec['type'], spec['max_length'])

                doc_ref = collection_ref.document(str(doc[pk]))
                batch.set(doc_ref, converted)

                if (idx + 1) % 500 == 0:
                    batch.commit()
                    batch = db.batch()

            if (idx + 1) % 500 != 0:
                batch.commit()

        print(f'Tabela {table} skonwertowana ({len(data["documents"])} dokumentów)')


def adding_foreign_key():
    db = connect_firestore()
    tables = get_tables()

    for table in tables:
        file = open(f'../utils/firestore_export_20250422_155019/{table}.json')
        data = json.load(file)
        primary_key = get_primary_key(table)
        foreign_keys = get_foreign_keys(table)

        for document in data['documents']:
            primary_key_value = str(document[primary_key])
            for fk in foreign_keys:

                if fk['TABLE_NAME'] == table:
                    doc_ref = db.collection(fk['REFERENCED_TABLE_NAME']).document(str(document[fk['COLUMN_NAME']]))
                    # print(str(fk['COLUMN_NAME']))
                    db.collection(table).document(str(primary_key_value)).update({str(fk['COLUMN_NAME']): doc_ref})
    print("Zakończono dodawanie fk")



convert_tables()
adding_foreign_key()