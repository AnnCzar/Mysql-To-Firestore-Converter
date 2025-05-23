import json
from collections import defaultdict

from converter.modes.converter_lv1 import data_mapping
from converter.modes.converter_lv2 import (get_info, connect_firestore, get_tables, get_colums_types, get_primary_key)

def detect_1_to_N_relations():
    data = get_info()
    print(data)
    primary_keys = {}
    for idx in data['indexes']:
        if idx.get('INDEX_NAME') == 'PRIMARY' or idx.get('INDEX_TYPE') == 'PRIMARY':
            table = idx['TABLE_NAME']
            col = idx['COLUMN_NAME']
            if table not in primary_keys:
                primary_keys[table] = set()
            primary_keys[table].add(col)

    one_to_many = []

    for fk in data['foreign_keys']:
        from_table = fk['TABLE_NAME']
        to_table = fk['REFERENCED_TABLE_NAME']
        from_column = fk['COLUMN_NAME']
        to_column = fk['REFERENCED_COLUMN_NAME']

        if to_table in primary_keys and to_column in primary_keys[to_table]:
            relation = {
                'parent': to_table,
                'child': from_table,
                'referenced_column': to_column,
                'fk_column': from_column
            }

            one_to_many.append(relation)

    print(one_to_many)
    return one_to_many

#
# def convert_db_with_subcollections(): # to nie zapisuje subkolekcji w subkolekcjach
#     db = connect_firestore()
#     one_to_many_rels = detect_1_to_N_relations()
#     tables = get_tables()
#
#     child_tables = {rel['child'] for rel in one_to_many_rels}
#     parent_rels = defaultdict(list)
#
#     for rel in one_to_many_rels:
#         parent_rels[rel['parent']].append(rel)
#
#     for table in tables:
#         if table in child_tables:
#             print(f"Pominięto {table} jako root – będzie tylko subkolekcją.")
#             continue
#
#         col_types = get_colums_types(table)
#         pk = get_primary_key(table)
#         path = f'../utils/firestore_export_20250422_155019/{table}.json'
#
#         try:
#             with open(path) as f:
#                 data = json.load(f)
#                 documents = data.get('documents', [])
#         except Exception as e:
#             print(f" Błąd przy wczytywaniu {table}: {e}")
#             continue
#
#         if not documents:
#             print(f" Brak danych dla {table}")
#             continue
#
#         collection_ref = db.collection(table)
#         batch = db.batch()
#
#         for idx, doc in enumerate(documents):
#             converted = {
#                 field: data_mapping(
#                     value,
#                     col_types.get(field, {}).get('type', 'varchar'),
#                     col_types.get(field, {}).get('max_length')
#                 ) for field, value in doc.items()
#             }
#
#             doc_id = str(doc[pk])
#             doc_ref = collection_ref.document(doc_id)
#             batch.set(doc_ref, converted)
#
#             if (idx + 1) % 500 == 0:
#                 batch.commit()
#                 batch = db.batch()
#
#         if len(documents) % 500 != 0:
#             batch.commit()
#
#         if table in parent_rels:
#             for rel in parent_rels[table]:
#                 child_table = rel['child']
#                 fk_column = rel['fk_column']
#                 ref_column = rel['referenced_column']
#
#                 print(f" Przetwarzanie subkolekcji: {child_table} do {table}/{ref_column}")
#
#                 child_path = f'../utils/firestore_export_20250422_155019/{child_table}.json'
#                 try:
#                     with open(child_path) as f:
#                         child_data = json.load(f).get('documents', [])
#                 except Exception as e:
#                     print(f" Błąd przy wczytywaniu dzieci ({child_table}): {e}")
#                     continue
#
#                 if not child_data:
#                     print(f"Brak dzieci w tabeli {child_table}")
#                     continue
#
#                 child_pk = get_primary_key(child_table)
#                 child_col_types = get_colums_types(child_table)
#
#                 children_map = defaultdict(list)
#                 for child_doc in child_data:
#                     key = str(child_doc.get(fk_column))
#                     if key:
#                         children_map[key].append(child_doc)
#
#                 for parent_doc in documents:
#                     parent_id = str(parent_doc[pk])
#                     parent_key_value = str(parent_doc[ref_column])
#                     parent_ref = collection_ref.document(parent_id)
#
#                     children = children_map.get(parent_key_value, [])
#                     if not children:
#                         continue
#
#                     batch = db.batch()
#                     count = 0
#
#                     for child_doc in children:
#                         converted_child = {
#                             field: data_mapping(
#                                 value,
#                                 child_col_types.get(field, {}).get('type', 'varchar'),
#                                 child_col_types.get(field, {}).get('max_length')
#                             ) for field, value in child_doc.items()
#                         }
#
#                         child_id = str(child_doc[child_pk])
#                         sub_ref = parent_ref.collection(child_table).document(child_id)
#                         batch.set(sub_ref, converted_child)
#                         count += 1
#
#                         if count % 500 == 0:
#                             batch.commit()
#                             batch = db.batch()
#
#                     if count % 500 != 0:
#                         batch.commit()
#
#                     print(f"Dodano {len(children)} do {table}/{parent_id}/{child_table}")
#
#     print("Zakończono konwersję z subkolekcjami.")

def process_table(table, parent_ref=None, parent_key=None, one_to_many_rels=None, parent_docs=None):
    db = connect_firestore()
    col_types = get_colums_types(table)
    pk = get_primary_key(table)
    path = f'../utils/firestore_export_20250422_155019/{table}.json'

    try:
        with open(path) as f:
            data = json.load(f)
            documents = data.get('documents', [])
    except Exception as e:
        print(f"Błąd przy wczytywaniu {table}: {e}")
        return

    if not documents:
        print(f"Brak danych dla {table}")
        return

    if parent_ref:
        collection_ref = parent_ref.collection(table)
    else:
        collection_ref = db.collection(table)

    children_map = defaultdict(list)

    if parent_key:
        for doc in documents:
            key = str(doc.get(parent_key))
            if key:
                children_map[key].append(doc)

        documents = []
        for parent_doc in parent_docs:
            p_id = str(parent_doc.get(parent_key))
            documents.extend(children_map.get(p_id, []))

    batch = db.batch()
    doc_map = {}

    for idx, doc in enumerate(documents):
        converted = {
            field: data_mapping(
                value,
                col_types.get(field, {}).get('type', 'varchar'),
                col_types.get(field, {}).get('max_length')
            ) for field, value in doc.items()
        }

        doc_id = str(doc[pk])
        doc_ref = collection_ref.document(doc_id)
        batch.set(doc_ref, converted)
        doc_map[doc_id] = doc

        if (idx + 1) % 500 == 0:
            batch.commit()
            batch = db.batch()

    if len(documents) % 500 != 0:
        batch.commit()

    if table in one_to_many_rels:
        for rel in one_to_many_rels[table]:
            child_table = rel['child']
            fk_column = rel['fk_column']
            ref_column = rel['referenced_column']

            print(f"  -> Przetwarzanie subkolekcji: {child_table} dla {table}")

            for doc_id, parent_doc in doc_map.items():
                doc_ref = collection_ref.document(doc_id)
                process_table(
                    child_table,
                    parent_ref=doc_ref,
                    parent_key=fk_column,
                    one_to_many_rels=one_to_many_rels,
                    parent_docs=[parent_doc]
                )


def convert_db_with_recursive_subcollections():
    db = connect_firestore()
    one_to_many_raw = detect_1_to_N_relations()

    one_to_many_rels = defaultdict(list)
    for rel in one_to_many_raw:
        one_to_many_rels[rel['parent']].append(rel)

    tables = get_tables()
    child_tables = {rel['child'] for rel in one_to_many_raw}

    for table in tables:
        if table in child_tables:
            print(f"Pominięto {table} jako root – będzie tylko subkolekcją.")
            continue

        print(f"Przetwarzanie kolekcji głównej: {table}")
        process_table(table, one_to_many_rels=one_to_many_rels)

    print("Zakończono rekurencyjną konwersję.")


convert_db_with_recursive_subcollections()





