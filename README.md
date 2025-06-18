# MySQL → Firestore Converter

Projekt zrealizowany na zajęcia **Zaawansowane Bazy Danych**.

---

Uniwersalny konwerter umożliwiający migrację danych z relacyjnej bazy MySQL do dokumentowej bazy Google Cloud Firestore z czterema poziomami zaawansowania konwersji.

## Funkcjonalności

- 4 poziomy konwersji (od prostego mapowania po pełną denormalizację)
- Interfejs webowy (Flask) do zarządzania procesem konwersji
- Automatyczne mapowanie typów danych MySQL → Firestore
- Obsługa relacji i referencji
- Bezpieczna obsługa plików i danych

##  Poziomy konwersji

| Poziom | Opis | Zastosowanie |
|--------|------|--------------|
| **1** | Każda tabela → kolekcja (bez relacji) | Proste migracje, prototypy |
| **2** | Zachowanie relacji przez referencje | Standardowe aplikacje |
| **3** | Subkolekcje dla relacji 1:N | Systemy hierarchiczne |
| **4** | Denormalizacja w jednym dokumencie | Małe bazy, read-only |

## Wymagania

- Python 3.8+
- MySQL z uprawnieniami odczytu
- Google Cloud Project z aktywnym Firestore
- Plik klucza serwisowego Firestore (JSON)

## Instalacja

1. Sklonuj repozytorium:

```
git clone https://github.com/your-username/mysql-firestore-converter.git
cd mysql-firestore-converter
```

2. Zainstaluj zależności:
```
pip install -r requirements.txt
```

3. Uruchom aplikację:
```aiignore
python app.py
```

4. Otwórz przeglądarkę:
```aiignore
http://localhost:8001
```


## Użytkowanie

1. Wgraj klucz Firestore (plik JSON z Google Cloud)
2. Wprowadź dane MySQL (host, nazwa bazy, użytkownik, hasło)
3. Wybierz poziom konwersji (1-4)
4. Uruchom konwersję i monitoruj postęp

---

**Projekt powstał w ramach kursu "Zaawansowane Bazy Danych".**

## Autorzy
- **Anna Czarnasiak** [GitHub: AnnCzar](https://github.com/AnnCzar)
- **Marta Prucnal** [GitHub: mpruc](https://github.com/mpruc)
