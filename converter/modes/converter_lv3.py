from collections import defaultdict

from converter.modes.converter_lv1 import *

def detect_1_to_N_relations(export_path):
    data = get_info(export_path)
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

def process_table(table, key, export_path, parent_ref=None, parent_key=None, one_to_many_rels=None, parent_docs=None):
    db = connect_firestore(key)
    col_types = get_columns_types(table, export_path)
    pk = get_primary_key(table, export_path)

    # Budowanie ścieżki do pliku JSON dla konkretnej tabeli
    table_file_path = os.path.join(export_path, f'{table}.json')

    try:
        with open(table_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            documents = data.get('documents', [])
    except FileNotFoundError:
        print(f"Plik {table_file_path} nie został znaleziony")
        return
    except PermissionError:
        print(f"Brak uprawnień do odczytu pliku {table_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Błąd dekodowania JSON w pliku {table_file_path}")
        return
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
            key_value = str(doc.get(parent_key))
            if key_value:
                children_map[key_value].append(doc)

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
                    key=key,
                    export_path=export_path,
                    parent_ref=doc_ref,
                    parent_key=fk_column,
                    one_to_many_rels=one_to_many_rels,
                    parent_docs=[parent_doc]
                )

def convert_db_with_recursive_subcollections(key, export_path):
    one_to_many_raw = detect_1_to_N_relations(export_path)

    one_to_many_rels = defaultdict(list)
    for rel in one_to_many_raw:
        one_to_many_rels[rel['parent']].append(rel)

    tables = get_tables(export_path)
    child_tables = {rel['child'] for rel in one_to_many_raw}

    for table in tables:
        if table in child_tables:
            print(f"Pominięto {table} jako root – będzie tylko subkolekcją.")
            continue

        print(f"Przetwarzanie kolekcji głównej: {table}")
        process_table(table, key = key, export_path=export_path, one_to_many_rels=one_to_many_rels)

    print("Zakończono rekurencyjną konwersję.")


# convert_db_with_recursive_subcollections()





