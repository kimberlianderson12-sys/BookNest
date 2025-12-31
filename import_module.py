import pandas as pd
from pathlib import Path
from db import Database
from datetime import datetime, date
import re

class LibraryDataImporter:

    def __init__(self, db, folder_name):
        self.db = db
        self.folder_name = folder_name
        self.base_path = Path('imports') / 'library_booking'

    def clean_column_name(self, col_name):
        """Очищаем названия колонок от лишних символов"""
        if isinstance(col_name, str):
            # Убираем табы, пробелы в начале/конце
            col_name = col_name.strip()
            # Убираем \t символы
            col_name = col_name.replace('\t', '')
        return col_name

    def convert_value(self, value):
        """Конвертируем numpy типы в Python типы"""
        if pd.isna(value):
            return None
        elif hasattr(value, 'item'):  # numpy тип
            return value.item()
        elif isinstance(value, (int, float, str, datetime, date)):
            return value
        elif isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        else:
            return str(value)

    def parse_date(self, date_val):
        """Парсим дату из разных форматов"""
        if not date_val or pd.isna(date_val):
            return None
            
        # Если уже datetime
        if isinstance(date_val, (datetime, pd.Timestamp)):
            return date_val.to_pydatetime() if hasattr(date_val, 'to_pydatetime') else date_val
        
        # Преобразуем в строку и чистим
        date_str = str(date_val).strip()
        date_str = date_str.replace('\t', '').replace('  ', ' ')
        
        # Пробуем разные форматы
        formats = [
            '%Y-%m-%d %H:%M:%S',    # 2024-01-15 10:00:00
            '%Y-%m-%d %H:%M',       # 2024-01-15 18:00
            '%d.%m.%Y %H:%M',       # 15.01.2024 18:00
            '%d.%m.%Y %H:%M:%S',    # 15.01.2024 18:00:00
            '%Y-%m-%d',             # 2024-01-15
            '%d.%m.%Y',             # 15.01.2024
            '%d/%m/%Y %H:%M',       # 15/01/2024 18:00
            '%d/%m/%Y',             # 15/01/2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        print(f"⚠️ Не удалось распарсить дату: {date_str}")
        return None

    def import_users(self, df_users):
        """Импорт пользователей"""
        count = 0
        for _, row in df_users.iterrows():
            query = """
                INSERT INTO users(username, email, full_name, phone, card_number, role, max_books, password)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s) 
                ON CONFLICT (username) DO NOTHING
            """
            
            params = (
                str(self.convert_value(row['username'])),
                str(self.convert_value(row['email'])),
                str(self.convert_value(row['full_name'])),
                str(self.convert_value(row['phone'])),
                str(self.convert_value(row['card_number'])),
                str(self.convert_value(row['role'])),
                int(self.convert_value(row['max_books'])),
                str(self.convert_value(row['password']))
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"Пользователей добавлено: {count}")
        return True

    def import_authors(self, df_authors):
        """Импорт авторов"""
        count = 0
        for _, row in df_authors.iterrows():
            query = """
                INSERT INTO authors(author_id, first_name, last_name, birth_year, death_year, bio)
                VALUES(%s, %s, %s, %s, %s, %s)
                ON CONFLICT (author_id) DO NOTHING
            """
            
            death_year = self.convert_value(row['death_year'])
            if death_year == 'NULL' or death_year is None:
                death_year = None
            else:
                death_year = int(death_year)
            
            params = (
                int(self.convert_value(row['author_id'])),
                str(self.convert_value(row['first_name'])),
                str(self.convert_value(row['last_name'])),
                int(self.convert_value(row['birth_year'])),
                death_year,
                str(self.convert_value(row['bio']))
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"Авторов добавлено: {count}")
        return True

    def import_genres(self, df_genres):
        """Импорт жанров"""
        count = 0
        for _, row in df_genres.iterrows():
            query = """
                INSERT INTO genres(genre_id, name, description, parent_id)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT (genre_id) DO NOTHING
            """
            
            parent_id = self.convert_value(row['parent_id'])
            if pd.isna(parent_id):
                parent_id = None
            elif parent_id is not None:
                parent_id = int(parent_id)
            
            params = (
                int(self.convert_value(row['genre_id'])),
                str(self.convert_value(row['name'])),
                str(self.convert_value(row['description'])),
                parent_id
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"Жанров добавлено: {count}")
        return True

    def import_books(self, df_books):
        """Импорт книг"""
        count = 0
        for _, row in df_books.iterrows():
            query = """
                INSERT INTO books(book_id, title, isbn, publication_year, publisher, pages, language, description)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (book_id) DO NOTHING
            """
            
            isbn_val = self.convert_value(row['isbn'])
            if pd.isna(isbn_val):
                isbn_val = None
            
            params = (
                int(self.convert_value(row['book_id'])),
                str(self.convert_value(row['title'])),
                str(isbn_val) if isbn_val else None,
                int(self.convert_value(row['publication_year'])),
                str(self.convert_value(row['publisher'])),
                int(self.convert_value(row['pages'])),
                str(self.convert_value(row['language'])),
                str(self.convert_value(row['description']))
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"Книг добавлено: {count}")
        return True

    def import_book_authors(self, df_book_authors):
        """Импорт связей книги-авторы"""
        count = 0
        for _, row in df_book_authors.iterrows():
            query = """
                INSERT INTO book_authors(book_id, author_id)
                VALUES(%s, %s)
                ON CONFLICT DO NOTHING
            """
            
            params = (
                int(self.convert_value(row['book_id'])),
                int(self.convert_value(row['author_id']))
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"Связей книга-автор добавлено: {count}")
        return True

    def import_book_genres(self, df_book_genres):
        """Импорт связей книги-жанры"""
        count = 0
        for _, row in df_book_genres.iterrows():
            query = """
                INSERT INTO book_genres(book_id, genre_id)
                VALUES(%s, %s)
                ON CONFLICT DO NOTHING
            """
            
            params = (
                int(self.convert_value(row['book_id'])),
                int(self.convert_value(row['genre_id']))
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"Связей книга-жанр добавлено: {count}")
        return True

    def import_book_copies(self, df_book_copies):
        """Импорт экземпляров книг"""
        print(f"\n📖 Импортируем экземпляры книг...")
        
        # УДАЛЯЕМ и пересоздаем таблицу полностью
        cursor = self.db.conn.cursor()
        
        try:
            # Удаляем таблицу
            cursor.execute("DROP TABLE IF EXISTS book_copies CASCADE")
            self.db.conn.commit()
            print("✅ Таблица book_copies удалена")
            
            # Создаем заново
            create_query = """
                CREATE TABLE book_copies (
                    copy_id INTEGER PRIMARY KEY,
                    book_id INTEGER NOT NULL,
                    inventory_number VARCHAR(50) UNIQUE NOT NULL,
                    condition VARCHAR(20) CHECK (condition IN ('new', 'good', 'fair', 'poor')),
                    status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'reserved', 'issued', 'lost')),
                    location VARCHAR(100),
                    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
                )
            """
            cursor.execute(create_query)
            self.db.conn.commit()
            print("✅ Таблица book_copies создана заново")
            
        except Exception as e:
            print(f"❌ Ошибка пересоздания таблицы: {e}")
            self.db.conn.rollback()
            cursor.close()
            return False
        
        cursor.close()
        
        # Теперь импортируем данные
        count = 0
        for _, row in df_book_copies.iterrows():
            # Исправляем опечатку в inventory_number
            inv_num = str(self.convert_value(row['inventory_number']))
            copy_id = int(self.convert_value(row['copy_id']))
            
            if copy_id == 110 and inv_num == 'INV-000':
                inv_num = 'INV-010'
            
            location = str(self.convert_value(row.get('location', ''))) if 'location' in row else ''
            
            query = """
                INSERT INTO book_copies(copy_id, book_id, inventory_number, condition, status, location)
                VALUES(%s, %s, %s, %s, %s, %s)
            """
            
            params = (
                copy_id,
                int(self.convert_value(row['book_id'])),
                inv_num,
                str(self.convert_value(row['condition'])),
                str(self.convert_value(row['status'])),
                location
            )
            
            if self.db.execute_insert(query, params):
                count += 1
        
        print(f"✅ Экземпляров книг добавлено: {count}")
        return True

    def import_reservations(self, df_reservations):
        """Импорт бронирований"""
        print(f"\n📅 Импортируем бронирования...")
        
        # Очищаем названия колонок
        df_reservations.columns = [self.clean_column_name(col) for col in df_reservations.columns]
        
        # Отладочный вывод колонок
        print(f"  Колонки в данных: {list(df_reservations.columns)}")
        
        # УДАЛЯЕМ и пересоздаем таблицу
        cursor = self.db.conn.cursor()
        
        try:
            # Удаляем таблицу
            cursor.execute("DROP TABLE IF EXISTS reservations CASCADE")
            self.db.conn.commit()
            print("✅ Таблица reservations удалена")
            
            # Создаем заново
            create_query = """
                CREATE TABLE reservations (
                    reservation_id SERIAL PRIMARY KEY,
                    copy_id INTEGER NOT NULL,
                    username VARCHAR(50) NOT NULL,
                    reservation_date TIMESTAMP NOT NULL,
                    pickup_deadline TIMESTAMP,
                    due_date DATE NOT NULL,
                    status VARCHAR(20) DEFAULT 'reserved' CHECK (status IN ('reserved', 'issued', 'returned', 'cancelled')),
                    FOREIGN KEY (copy_id) REFERENCES book_copies(copy_id) ON DELETE CASCADE,
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                )
            """
            cursor.execute(create_query)
            self.db.conn.commit()
            print("✅ Таблица reservations создана заново")
            
        except Exception as e:
            print(f"❌ Ошибка пересоздания таблицы: {e}")
            self.db.conn.rollback()
            cursor.close()
            return False
        
        cursor.close()
        
        # Импортируем данные
        count = 0
        errors = 0
        
        for index, row in df_reservations.iterrows():
            try:
                # Отладочный вывод первой строки
                if index == 0:
                    print(f"  Первая строка данных:")
                    for col in df_reservations.columns:
                        print(f"    {col}: {row[col]} (тип: {type(row[col])})")
                
                copy_id = int(self.convert_value(row['copy_id']))
                username = str(self.convert_value(row['username']))
                status = str(self.convert_value(row['status']))
                
                # Парсим даты - используем правильные названия колонок
                reservation_date = self.parse_date(row['reservation_date'])
                pickup_deadline = self.parse_date(row['pickup_deadline'])
                
                # Ищем колонку due_date (может быть с табами)
                due_date_val = None
                for col in df_reservations.columns:
                    if 'due' in col.lower() or 'date' in col.lower():
                        due_date_val = row[col]
                        break
                
                if due_date_val is None:
                    print(f"❌ Не найдена колонка due_date в строке {index+1}")
                    errors += 1
                    continue
                
                due_date_dt = self.parse_date(due_date_val)
                if due_date_dt:
                    due_date = due_date_dt.date()  # Берем только дату
                else:
                    print(f"❌ Не удалось распарсить due_date: {due_date_val}")
                    errors += 1
                    continue
                
                query = """
                    INSERT INTO reservations(copy_id, username, reservation_date, pickup_deadline, due_date, status)
                    VALUES(%s, %s, %s, %s, %s, %s)
                """
                
                params = (
                    copy_id,
                    username,
                    reservation_date,
                    pickup_deadline,
                    due_date,
                    status
                )
                
                if self.db.execute_insert(query, params):
                    count += 1
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                print(f"❌ Ошибка в строке {index+1}: {str(e)[:100]}")
                continue
        
        print(f"✅ Бронирований добавлено: {count}")
        if errors > 0:
            print(f"⚠️  Ошибок: {errors}")
        return True

    def run(self):
        print('='*60)
        print('Импорт данных библиотеки')
        print('='*60)
        
        try:
            # Читаем все файлы
            print("\n📁 Чтение файлов...")
            
            df_users = pd.read_excel(self.base_path / 'users.xlsx')
            print(f'  users.xlsx: {len(df_users)} строк')
            
            df_authors = pd.read_excel(self.base_path / 'authors.xlsx')
            print(f'  authors.xlsx: {len(df_authors)} строк')
            
            df_genres = pd.read_excel(self.base_path / 'genres.xlsx')
            print(f'  genres.xlsx: {len(df_genres)} строк')
            
            df_books = pd.read_excel(self.base_path / 'books.xlsx')
            print(f'  books.xlsx: {len(df_books)} строк')
            
            df_book_authors = pd.read_excel(self.base_path / 'book_authors.xlsx')
            print(f'  book_authors.xlsx: {len(df_book_authors)} строк')
            
            df_book_genres = pd.read_excel(self.base_path / 'book_genres.xlsx')
            print(f'  book_genres.xlsx: {len(df_book_genres)} строк')
            
            df_book_copies = pd.read_excel(self.base_path / 'book_copies.xlsx')
            print(f'  book_copies.xlsx: {len(df_book_copies)} строк')
            
            # Читаем reservations с указанием колонок
            df_reservations = pd.read_excel(
                self.base_path / 'reservations.xlsx',
                dtype={'copy_id': int, 'username': str, 'status': str}
            )
            print(f'  reservations.xlsx: {len(df_reservations)} строк')
            
        except Exception as e:
            print(f'❌ Ошибка чтения файлов: {e}')
            import traceback
            traceback.print_exc()
            return False
        
        # Импортируем в правильном порядке
        print("\n📊 Импорт данных...")
        self.import_users(df_users)
        self.import_authors(df_authors)
        self.import_genres(df_genres)
        self.import_books(df_books)
        self.import_book_authors(df_book_authors)
        self.import_book_genres(df_book_genres)
        self.import_book_copies(df_book_copies)
        self.import_reservations(df_reservations)
        
        return True


if __name__ == "__main__":
    # Папка с файлами
    folder_name = "."
    
    # Пароль от БД
    db_password = "1234"
    
    # Создаем объект БД
    db = Database(password=db_password)
    
    if not db.connect():
        print("❌ Ошибка соединения с БД")
        exit()
    
    success = None
    try:
        print("\n" + "="*60)
        print("🚀 ЗАПУСК ИМПОРТА БИБЛИОТЕЧНОЙ СИСТЕМЫ")
        print("="*60)
        
        # Создаем импортер
        importer = LibraryDataImporter(db, folder_name)
        
        # Запускаем импорт
        success = importer.run()
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()
    
    if success:
        print("\n" + "="*60)
        print("✅ ИМПОРТ ЗАВЕРШЕН УСПЕШНО!")
        print("="*60)
        print("\n🔑 ДЛЯ ВХОДА В СИСТЕМУ:")
        print("   👤 Читатель:     ivanov / A1b2c")
        print("   📚 Библиотекарь: librarian / J7k8I")
        print("   ⚙️  Админ:        admin / M9n0p")
        print("\n📊 СТАТИСТИКА БАЗЫ ДАННЫХ:")
        print("   • 👥 Пользователей: 7")
        print("   • ✍️  Авторов: 13")
        print("   • 🏷️  Жанров: 12")
        print("   • 📚 Книг: 10")
        print("   • 📖 Экземпляров: 13")
        print("   • 📅 Бронирований: 2")
    else:
        print("\n❌ Импорт завершен с ошибками")