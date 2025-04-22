import os
import mysql.connector
from pandas.io.sql import table_exists
import json
from datetime import datetime

from converter import config

def connect_mysql():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASS,
        database=config.DB_NAME
    )
    return conn, conn.cursor(dictionary=True)

#wyciąganie
def get_all_tables():
    """
    Listuje wszystkie tabele z BD
    :return: lista tabel
    """
    try:
        conn, cursor = connect_mysql()
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        tables_names = [list(t.values())[0] for t in tables]
        return tables_names
    except Exception as e:
        print("Błąd połączenia z MySQL:", e)
        return []
print(get_all_tables())

def get_all_records_from_the_table(table_name):
    """
    Zwraca wszystkie rekordy wybranej tabeli
    :param table_name: nazwa tabeli, której rekordy chcemy wyciągnąć
    :return: wszystkie rekordy tabeli
    """
    try:
        conn, cursor = connect_mysql()
        sql_query = f'select * from {table_name}'
        cursor.execute(sql_query)
        records = cursor.fetchall()
        return records
    except mysql.connector.Error as e:
        print(e)

def get_records_for_all_tables():
    """
    Zwraca wszystkie rekordy wszystkich tabeli w BD

    """
    tables_data  = {}
    tables = get_all_tables()
    print(tables)
    if not tables:
        print('Brak tabel')
        return tables_data

    for table_name in tables:
        try:
            print(f"\nPrzetwarzanie tabeli: {table_name}")
            records = get_all_records_from_the_table(table_name)

            if records:
                tables_data[table_name] = records
                print(f"Pobrano {len(records)} rekordów z tabeli")
            else:
                print(f"Tabela '{table_name}' jest pusta")

        except Exception as e:
            print(f"Błąd podczas przetwarzania tabeli '{table_name}': {str(e)}")
            tables_data[table_name] = None

    return tables_data

def get_foreign_keys():
    """
    Pobiera informacje o kluczach obcych z bazy danych MySQL.

    Zwraca listę słowników, z których każdy zawiera:
    - 'table_name': nazwa tabeli zawierającej klucz obcy,
    - 'column_name': nazwa kolumny będącej kluczem obcym,
    - 'referenced_table_name': nazwa tabeli, do której odwołuje się klucz obcy,
    - 'referenced_column_name': nazwa kolumny w tabeli referencyjnej.

    Dane są pobierane z `information_schema.key_column_usage`.

    :return: Lista słowników z informacjami o kluczach obcych.
    """
    try:
        conn, cursor = connect_mysql()
        query = f"""
        SELECT
            table_name,
            column_name,
            referenced_table_name,
            referenced_column_name
        FROM
            information_schema.key_column_usage
            WHERE
                referenced_table_name IS NOT NULL
                AND table_schema = '{config.DB_NAME}';
        """
        cursor.execute(query)
        results = cursor.fetchall()
        foreign_keys = [dict(row) for row in results]
        return foreign_keys

    except Exception as e:
        print("Błąd pobierania relacji:", e)
    return []

def get_data_types():
    """
    Pobiera informacje o typach danych kolumn w tabelach bazy danych MySQL.
    :return: Lista słowników z informacjami o typach danych kolumn.
    """
    try:
        conn, cursor = connect_mysql()
        query = f"""
        SELECT
            table_name,
            column_name,
            data_type,
            character_maximum_length
        FROM
            information_schema.columns
        WHERE
            table_schema = '{config.DB_NAME}';
        """
        cursor.execute(query)
        results = cursor.fetchall()
        data_types = [dict(row) for row in results]
        return data_types

    except Exception as e:
        print("Błąd pobierania typów danych:", e)
    return []

def get_indexes():
    """
    Pobiera informacje o indeksach w tabelach bazy danych MySQL.

    Zwraca listę słowników, z których każdy zawiera:
    - 'table_name': nazwa tabeli,
    - 'index_name': nazwa indeksu,
    - 'column_name': kolumna objęta indeksem,
    - 'non_unique': flaga wskazująca, czy indeks dopuszcza duplikaty (1 = tak, 0 = nie).

    :return: Lista słowników z informacjami o indeksach.
    """
    try:
        conn, cursor = connect_mysql()
        query = f"""
        SELECT
            table_name,
            index_name,
            column_name,
            non_unique
        FROM
            information_schema.statistics
        WHERE
            table_schema = '{config.DB_NAME}';
        """
        cursor.execute(query)
        results = cursor.fetchall()
        data_types = [dict(row) for row in results]
        return data_types

    except Exception as e:
        print("Błąd pobierania typów danych:", e)
    return []


def export_to_firestore_format():
    """
    Zapis do jsonów

    Dla każdej tabeli generuje plik `.json`, który zawiera:
    - nazwę kolekcji (`collection_name`),
    - listę dokumentów z odpowiednio przekonwertowanymi rekordami.

    Dodatkowo tworzony jest plik `_schema_metadata.json` zawierający metadane schematu:
    - listę tabel,
    - klucze obce,
    - typy danych,
    - indeksy,
    - datę eksportu.

    :return: Ścieżka do folderu z wyeksportowanymi plikami.
    """

    export_dir = f"firestore_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(export_dir, exist_ok=True)

    tables_data = get_records_for_all_tables() # tabele
    foreign_keys = get_foreign_keys() # klucze obce
    data_types = get_data_types() # typy danych
    indexes = get_indexes() # indeksy


    schema_metadata = {
        "export_date": datetime.now().isoformat(),
        "tables": list(tables_data.keys()),
        "foreign_keys": foreign_keys,
        "data_types": data_types,
        "indexes": indexes
    }

    with open(f"{export_dir}/_schema_metadata.json", 'w') as f:
        json.dump(schema_metadata, f, indent=2, default=str)

    for table_name, records in tables_data.items():
        if records is None:
            continue

        firestore_data = {
            "collection_name": table_name,
            "documents": []
        }

        for record in records:
            converted_record = {}
            for key, value in record.items():
                if value is None:
                    converted_record[key] = None
                elif hasattr(value, 'isoformat'):
                    converted_record[key] = value.isoformat()
                else:
                    converted_record[key] = value

            for fk in foreign_keys:
                if fk.get('table_name') == table_name:
                    ref_key = f"{fk.get('referenced_table_name', 'unknown')}_ref"
                    col_name = fk.get('column_name')
                    if col_name in converted_record:
                        converted_record[ref_key] = {
                            "document_id": str(converted_record[col_name]),
                            "collection": fk.get('referenced_table_name')
                        }

            firestore_data["documents"].append(converted_record)

        with open(f"{export_dir}/{table_name}.json", 'w') as f:
            json.dump(firestore_data, f, indent=2, default=str)
        print(f"Zapisano dane tabeli {table_name} do {export_dir}/{table_name}.json")

    print(f"\nEksport zakończony. Dane zapisane w: {export_dir}")
    return export_dir


# print(get_foreign_keys())
# print(get_all_records_from_the_table('album'))
# print(get_data_types())
# print(get_indexes())
# print('!!!!!!!!')
# print(get_records_for_all_tables())
export_to_firestore_format()
