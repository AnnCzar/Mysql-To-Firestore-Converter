from converter.modes.converter_lv1 import *

def get_foreign_keys(table, export_path):
    data = get_info(export_path)
    foreign_keys = []
    for i in data['foreign_keys']:
        if i['TABLE_NAME'] == table:
            foreign_keys.append(i)
    return foreign_keys



def adding_foreign_key(key, export_path):
    try:
        db = connect_firestore(key)
        tables = get_tables(export_path)
        convert_tables(key, export_path)

        for table in tables:
            try:
                try:
                    with open(f'{export_path}/{table}.json') as file:
                        data = json.load(file)
                except:
                    print(f"Błąd pliku dla tabeli: {table}")
                    continue

                primary_key = get_primary_key(table, export_path)
                foreign_keys = get_foreign_keys(table, export_path)

                for document in data['documents']:
                    try:
                        primary_key_value = str(document[primary_key])

                        for fk in foreign_keys:

                            if fk['TABLE_NAME'] == table:
                                doc_ref = db.collection(fk['REFERENCED_TABLE_NAME']).document(str(document[fk['COLUMN_NAME']]))
                                db.collection(table).document(str(primary_key_value)).update({str(fk['COLUMN_NAME']): doc_ref})
                    except:
                        print(f"Błąd dokumentu w tabeli: {table}")
                        continue
            except:
                print(f"Błąd tabeli: {table}")
                continue

        print("Zakończono dodawanie fk")

    except Exception as e:
        print(f"Błąd programu: {e}")

# convert_tables()
# adding_foreign_key()