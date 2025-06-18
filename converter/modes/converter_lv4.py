from converter.modes.converter_lv1 import *


def convert_all_table_into_documnet(key, export_path):
    db = connect_firestore(key)
    tables = get_tables(export_path)

    all_tables = {}

    for table in tables:
        try:
            with open(f'{export_path}/{table}.json') as f:


                data = json.load(f)

                col_types = get_columns_types(table, export_path)
                converted_records = []

                for doc in data['documents']:
                    converted_record = {}
                    for field, value in doc.items():
                        spec = col_types.get(field, {'type': 'varchar', 'max_length': None})
                        converted_record[field] = data_mapping(
                            value,
                            spec['type'],
                            spec['max_length']
                        )
                    converted_records.append(converted_record)

                all_tables[table] = converted_records
                print(f'Skonwertowano: {table} ({len(data["documents"])} dokumentów)')
        except FileNotFoundError:
            print(f"Nie znaleziono pliku dla tabeli: {table}")
            continue
        except Exception as e:
            print(f"Błąd podczas przetwarzania {table}: {e}")
            continue

    doc_size = len(json.dumps(all_tables, default=str).encode('utf-8'))  #obliczenie rozmiaru dok
    print(f"Rozmiar dokumentu: {doc_size/ 1024:.1f} KB")

    if doc_size > 1048576:  # 1MB limit Firestore
        print("Dokument przekracza limit 1MB")
        return False
        # ewentulana optyamlizacja

        # Zapisz jeden dokument z całą bazą
    try:
        doc_ref = db.collection('complete_database').document('all_tables')
        doc_ref.set(all_tables)

        print("Baza dabych przekonwertowana")
        print(f" Łączna liczba rekordów: {sum(len(records) for records in all_tables.values())}")

        return True

    except Exception as e:
        print(f"Błąd podczas zapisu: {e}")
        return False


# convert_all_table_into_documnet()