import shutil

from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from converter.modes.converter_lv1 import convert_tables
from converter.modes.converter_lv2 import adding_foreign_key
from converter.modes.converter_lv3 import convert_db_with_recursive_subcollections
from converter.modes.converter_lv4 import convert_all_table_into_documnet
from converter.utils.firestore_utils import connect_firestore, delete_all_collections
from converter.utils.mysql_utils import export_to_firestore_format, connect_mysql

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    try:
        # Pobieranie danych z formularza
        firestore_file = request.files['firestore_key']
        mysql_host = request.form.get('mysql_host')
        mysql_db = request.form.get('mysql_db')
        mysql_user = request.form.get('mysql_user')
        mysql_password = request.form.get('mysql_password')
        conversion_level = int(request.form.get('conversion_level'))
        print(f"Wybrany poziom konwersji: {conversion_level}")

        # Sprawdzenie czy plik został przesłany
        if not firestore_file or firestore_file.filename == '':
            return "Nie wybrano pliku Firestore", 400

        # Zapis pliku Firestore
        firestore_key_path = os.path.join(app.config['UPLOAD_FOLDER'], firestore_file.filename)
        firestore_file.save(firestore_key_path)

        # Połączenie z MySQL
        try:
            conn, cursor = connect_mysql(mysql_host, mysql_user, mysql_password, mysql_db)
            if conn is None or cursor is None:
                return "Nie udało się połączyć z MySQL", 500
            print("Połączono z MySQL pomyślnie")
        except Exception as e:
            print(f"Błąd połączenia z MySQL: {e}")
            if firestore_key_path and os.path.exists(firestore_key_path):
                try:
                    os.remove(firestore_key_path)
                    print(f"Usunięto plik klucza Firestore po błędzie MySQL: {firestore_key_path}")
                except Exception as cleanup_error:
                    print(f"Błąd podczas usuwania klucza po błędzie MySQL: {str(cleanup_error)}")
            return f"Nie udało się połączyć z MySQL: {str(e)}", 500

        # Połączenie z Firestore
        try:
            firestore_db = connect_firestore(firestore_key_path)
            if not firestore_db:
                if firestore_key_path and os.path.exists(firestore_key_path):
                    try:
                        os.remove(firestore_key_path)
                        print(f"Usunięto plik klucza Firestore po błędzie połączenia: {firestore_key_path}")
                    except Exception as cleanup_error:
                        print(f"Błąd podczas usuwania klucza po błędzie połączenia: {str(cleanup_error)}")

                return "Nie udało się połączyć z Firestore", 500

            print("Połączono z Firestore pomyślnie")
            delete_all_collections(firestore_db)
            print("Usunięto istniejące kolekcje")


        except Exception as e:
            print(f"Błąd połączenia z Firestore aaaa: {e}")
            if firestore_key_path and os.path.exists(firestore_key_path):
                try:
                    os.remove(firestore_key_path)
                    print(f"Usunięto plik klucza Firestore po błędzie połączenia: {firestore_key_path}")
                except Exception as cleanup_error:
                    print(f"Błąd podczas usuwania klucza po błędzie połączenia: {str(cleanup_error)}")
            return f"Nie udało się połączyć z Firestore: {str(e)}", 500

        # Eksport danych z MySQL
        try:
            export_data_path = export_to_firestore_format(mysql_host, mysql_user, mysql_password, mysql_db)
            if not export_data_path:
                return "Nie udało się wyeksportować danych z MySQL", 500
            print(f"Wyeksportowano dane z MySQL do: {export_data_path}")
        except Exception as e:
            print(f"Błąd eksportu z MySQL: {e}")
            return f"Nie udało się wyeksportować danych z MySQL: {str(e)}", 500

        try:
            print(f"Rozpoczynanie konwersji na poziomie {conversion_level}")
            if conversion_level == 1:
                print("Wykonywanie konwersji Level 1")
                convert_tables(firestore_key_path, export_data_path)
            elif conversion_level == 2:
                print("Wykonywanie konwersji Level 2")
                adding_foreign_key(firestore_key_path, export_data_path)
            elif conversion_level == 3:
                print("Wykonywanie konwersji Level 3")
                convert_db_with_recursive_subcollections(firestore_key_path, export_data_path)
            elif conversion_level == 4:
                print("Wykonywanie konwersji Level 4")
                convert_all_table_into_documnet(firestore_key_path, export_data_path)
            else:
                return f"Nieprawidłowy poziom konwersji: {conversion_level}", 400

            print('Konwersja zakończona')

            return "Konwersja zakończona pomyślnie! Wszystkie dane zostały przeniesione do Firestore.", 200

        except Exception as e:
            print(f"Błąd podczas konwersji: {e}")
            return f"Błąd podczas konwersji: {str(e)}", 500
        finally:
            if 'export_data_path' in locals() and export_data_path:
                try:
                    shutil.rmtree(export_data_path)
                    print(f"Usunięto folder eksportu: {export_data_path}")
                except Exception as e:
                    print(f"Błąd podczas usuwania folderu: {str(e)}")

            if firestore_key_path and os.path.exists(firestore_key_path):
                try:
                    os.remove(firestore_key_path)
                    print(f"Usunięto plik klucza Firestore: {firestore_key_path}")
                except Exception as e:
                    print(f"Błąd podczas usuwania pliku klucza: {str(e)}")

    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {e}")
        return f"Wystąpił nieoczekiwany błąd: {str(e)}", 500


@app.route('/status')
def get_status():
    return jsonify({"status": "ready"})


if __name__ == '__main__':
    # serve(app, host="0.0.0.0", port=8001)
    app.run(host="0.0.0.0", port=8001, debug=True)