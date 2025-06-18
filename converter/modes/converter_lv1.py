import base64
import json
import os
from converter.utils.firestore_utils import connect_firestore
from datetime import datetime
from google.cloud import firestore


def get_info(export_path):
    """Pobiera informacje o schemacie z podanej ścieżki"""
    schema_file = os.path.join(export_path, '_schema_metadata.json')
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Nie znaleziono pliku schematu: {schema_file}")

    with open(schema_file, 'r') as file:
        data = json.load(file)
    return data


def get_tables(export_path):
    """Pobiera listę tabel z metadanych"""
    data = get_info(export_path)
    tables = data['tables']
    return tables


def get_primary_key(table, export_path):
    """Pobiera klucz główny dla podanej tabeli"""
    data = get_info(export_path)
    for i in data['indexes']:
        if i['TABLE_NAME'] == table and i['INDEX_NAME'] == 'PRIMARY':
            return i['COLUMN_NAME']
    # Fallback - jeśli nie znajdzie PRIMARY KEY, użyj pierwszej kolumny
    return 'id'


def get_columns_types(table, export_path):
    """Pobiera typy kolumn dla podanej tabeli"""
    data = get_info(export_path)
    return {
        col['COLUMN_NAME']: {
            'type': col['DATA_TYPE'].lower(),
            'max_length': col['CHARACTER_MAXIMUM_LENGTH']
        } for col in data['data_types'] if col['TABLE_NAME'] == table
    }


def data_mapping(value, data_type, max_length):
    """Mapuje dane z MySQL na format Firestore"""
    if value is None:
        return None
    try:
        # Liczby całkowite
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
                    dt = datetime.strptime(value_str, fmt)
                    return str(dt)
                except ValueError:
                    continue

            for fmt in formats_with_fractional_sec:
                try:
                    dt = datetime.strptime(value_str, fmt)
                    return str(dt)
                except ValueError:
                    continue

            raise ValueError(f"Nieznany format daty: {value_str}")

        if data_type == 'date':
            return str(value)

        if data_type == 'time':
            return str(value)

        if data_type == 'year':
            return int(value)

        # Logiczne
        if data_type in {'boolean', 'bool'}:
            if str(value).isdigit():
                return bool(int(value))
            return str(value).lower() in ('true', 'yes', 't', 'y')

        # Tekstowe
        if data_type in {'char', 'varchar', 'text'}:
            max_len = min(max_length, 1048487) if max_length else 1048487
            return str(value)[:max_len]

        if data_type == 'enum':
            return str(value)

        if data_type in {'blob', 'binary', 'varbinary', 'longblob', 'mediumblob', 'tinyblob'}:
            if isinstance(value, (bytes, bytearray)):
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


def convert_tables(firestore_key_path, export_data_path=None):
    """
    Konwertuje tabele MySQL do kolekcji Firestore

    Args:
        firestore_key_path: Ścieżka do klucza Firestore
        export_data_path: Ścieżka do folderu z wyeksportowanymi danymi MySQL
    """
    try:
        # Jeśli nie podano ścieżki, użyj domyślnej
        if export_data_path is None:
            export_data_path = 'firestore_export_20250422_155019'

        # Sprawdź czy folder istnieje
        if not os.path.exists(export_data_path):
            raise FileNotFoundError(f"Folder z danymi nie istnieje: {export_data_path}")

        db = connect_firestore(firestore_key_path)
        tables = get_tables(export_data_path)

        for table in tables:
            try:
                col_types = get_columns_types(table, export_data_path)
                pk = get_primary_key(table, export_data_path)

                # Plik z danymi tabeli
                table_file = os.path.join(export_data_path, f'{table}.json')

                try:
                    with open(table_file, 'r') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    print(f'Nie znaleziono pliku dla tabeli: {table_file}')
                    continue

                batch = db.batch()
                collection_ref = db.collection(table)

                for idx, doc in enumerate(data['documents']):
                    try:
                        converted = {}
                        for field, value in doc.items():
                            try:
                                spec = col_types.get(field, {'type': 'varchar', 'max_length': None})
                                converted[field] = data_mapping(
                                    value,
                                    spec['type'],
                                    spec['max_length']
                                )
                            except Exception as e:
                                print(f"Błąd konwersji pola '{field}' w dokumencie {idx}: {e}")
                                # Jeżeli problem z konwersją typu to daje string
                                converted[field] = str(value) if value is not None else None

                        # Użyj klucza głównego jako ID dokumentu
                        doc_id = str(doc.get(pk, idx))  # Fallback na indeks jeśli brak pk
                        doc_ref = collection_ref.document(doc_id)
                        batch.set(doc_ref, converted)

                        # Commit co 500 dokumentów
                        if (idx + 1) % 500 == 0:
                            try:
                                batch.commit()
                                batch = db.batch()
                                print(f"Zapisano {idx + 1} dokumentów z tabeli {table}")
                            except Exception as e:
                                print(f"Błąd zapisu batch: {e}")
                                break
                    except Exception as e:
                        print(f"Błąd przetwarzania dokumentu {idx}: {e}")
                        continue

                # Commit pozostałych dokumentów
                if (len(data['documents'])) % 500 != 0:
                    batch.commit()

                print(f'Skonwertowano: {table} ({len(data["documents"])} dokumentów)')
            except Exception as e:
                print(f'Błąd podczas konwersji tabeli {table}: {e}')
                continue

        print("Koniec konwertowania")
    except Exception as e:
        print(f"Błąd z połączeniem z bazą danych: {e}")

#  convert_tables()