from converter.modes.converter_lv1 import *

def get_foreign_keys(table):
    data = get_info()
    foreign_keys = []
    for i in data['foreign_keys']:
        if i['TABLE_NAME'] == table:
            foreign_keys.append(i)
    return foreign_keys


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


# convert_tables()
# adding_foreign_key()