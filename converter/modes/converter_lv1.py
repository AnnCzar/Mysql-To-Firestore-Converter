import json
from converter.utils.firestore_utils import connect_firestore
from decimal import Decimal
from datetime import datetime
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
    # for table in tables:
    #     print(table)

def get_primary_key(table):
    data = get_info()
    for i in data['indexes']:
        if i['TABLE_NAME'] == table:
            return i['COLUMN_NAME']

def get_colums_types(table):
    data = get_info()
    return {
        col['COLUMN_NAME']: {
            'type': col['DATA_TYPE'].lower(),
            'max_length': col['CHARACTER_MAXIMUM_LENGTH']
        } for col in data['data_types'] if col['TABLE_NAME'] == table
    }

def data_mapping(value, data_type, max_length):
    if value is None:
        return None
    try:
        # l.calkowite
        if data_type in {'int', 'tinyint', 'smallint', 'mediumint', 'bigint'}:
            return int(value)

        if data_type in {'float', 'double'}:
            return float(value)

        if data_type == 'decimal':
            return float(value)

        if data_type == 'datetime':
            if value in {'CURRENT_TIMESTAMP', 'NOW()'}:
                return firestore.SERVER_TIMESTAMP
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
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
            time_obj =  datetime.strptime(value, '%Y-%m-%d')
            return datetime.combine(datetime.min, time_obj)

        if data_type == 'time':
            return value #jak str bo to nizej daje przykladowa date
            # return datetime.strptime(value, '%H:%M:%S').time()

        # logiczne
        if data_type in {'boolean', 'bool'}:
            if str(value).isdigit():
                return bool(int(value))
            return str(value).lower() in ('true', 'yes', 't', 'y')

        # tesktowe
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
        col_types = get_colums_types(table)
        pk = get_primary_key(table)
        # file = open(f'../utils/firestore_export_20250422_155019/{table}.json')
        # data = json.load(file)
        with open(f'../utils/firestore_export_20250422_155019/{table}.json') as f:

        # for document in data['documents']:
        #     primary_key_value = str(document[primary_key])
        #     db.collection(table).document(primary_key_value).set(document)
        # print("Tabela " + table + " converted." )
            batch = db.batch()
            collection_ref = db.collection(table)
            data = json.load(f)

            for idx, doc in enumerate(data['documents']):
                converted = {}
                for field, value in doc.items():
                    spec = col_types.get(field, {'type': 'varchar', 'max_length': None})
                    converted[field] = data_mapping(
                        value,
                        spec['type'],
                        spec['max_length']
                    )

                doc_ref = collection_ref.document(str(doc[pk]))
                batch.set(doc_ref, converted)

                if (idx + 1) % 500 == 0:
                    batch.commit()
                    batch = db.batch()

            if (idx + 1) % 500 != 0:
                batch.commit()

        print(f'Skonwertowano: {table} ({len(data["documents"])} dokumentów)')
        # collection = table
    print("Koniec Konwertowania")


convert_tables()