import base64
import json
from converter.utils.firestore_utils import connect_firestore
from decimal import Decimal
from datetime import datetime
from google.cloud import firestore
from datetime import timezone

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

            value_str = str(value)

            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y%m%d%H%M%S'
            ]
            formats_with_fractional_sec = [
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y%m%d%H%M%S.%f'
            ]


            for fmt in formats:
                try:
                    # return datetime.strptime(value_str, fmt)
                    dt = datetime.strptime(value_str, fmt)
                    return str(dt)
                except ValueError:
                    continue

            for fmt in formats_with_fractional_sec:
                try:
                    dt = datetime.strptime(value_str, fmt)
                    return str(dt)  # Zwróć jako string # w fs nie ma obslugi setnych sekund dlatego str
                except ValueError:
                    continue

            raise ValueError(f"Nieznany format daty: {value_str}")

        if data_type == 'date':
            # date_obj =  datetime.strptime(value, '%Y-%m-%d')
            # return datetime.combine(date_obj, datetime.min.time())
            return str(value)

        if data_type == 'time':
            return str(value) #jak str bo to nizej daje przykladowa date

        if data_type == 'year':
             return int(value)
        # logiczne
        if data_type in {'boolean', 'bool'}:
            if str(value).isdigit():
                return bool(int(value))
            return str(value).lower() in ('true', 'yes', 't', 'y')

        # tesktowe
        if data_type in {'char', 'varchar', 'text'}:
            max_len = min(max_length, 1048487) if max_length else 1048487
            return str(value)[:max_len]
        if data_type == 'enum':
            return str(value)
        if data_type in {'blob', 'binary', 'varbinary', 'longblob', 'mediumblob', 'tinyblob'}:
            if isinstance(value, (bytes, bytearray)):
                # Zakoduj dane binarne do base64 string
                return base64.b64encode(value).decode('utf-8')
            elif isinstance(value, str):
                return value
            else:
                return base64.b64encode(bytes(str(value), 'utf-8')).decode('utf-8')
        if data_type == 'json':
            if isinstance(value, (dict, list)):
                return value
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError) as e:
                print(f'Błąd dekodowania JSON: {e}')
                return str(value)
        raise ValueError(f"Nieobsługiwany typ danych: {data_type}")
    except Exception as e:
        print(f'Błąd konwersji "{value}" ({data_type}): {str(e)}')
        return value


def convert_tables():
    db = connect_firestore()
    tables = get_tables()
    for table in tables:
        col_types = get_colums_types(table)
        pk = get_primary_key(table)
        with open(f'../utils/firestore_export_20250422_155019/{table}.json') as f:

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

# convert_tables()