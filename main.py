from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from db import Database
from datetime import datetime, date, timedelta
from functools import wraps
import hashlib
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'booknest_secret_key_2024'

# Инициализация БД
db = Database()

# Путь к папке с изображениями
IMAGES_DIR = Path('imports/library_booking/images')
ASSETS_DIR = Path('imports/library_booking/assets')

def get_book_image_path(title):
    """Находит путь к изображению книги по названию"""
    if not title or not IMAGES_DIR.exists():
        return None
    
    # Нормализуем название для поиска (убираем лишние пробелы, приводим к нижнему регистру)
    normalized_title = title.strip().lower()
    
    # Пробуем разные варианты расширений
    extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    
    # Сначала пробуем точное совпадение
    for ext in extensions:
        image_path = IMAGES_DIR / f"{title}{ext}"
        if image_path.exists():
            return image_path.name
    
    # Если не найдено, ищем по всем файлам в папке
    try:
        for image_file in IMAGES_DIR.iterdir():
            if image_file.is_file():
                # Сравниваем нормализованные названия
                file_name = image_file.stem.lower()
                if normalized_title == file_name or normalized_title in file_name or file_name in normalized_title:
                    return image_file.name
    except Exception:
        pass
    
    # Если не найдено, возвращаем None
    return None

def init_db():
    """Инициализация подключения к БД"""
    if not db.conn:
        db.connect()

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Декоратор для проверки роли пользователя"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('Пожалуйста, войдите в систему', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('У вас нет доступа к этой странице', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    """Главная страница"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Сервис для обслуживания изображений книг"""
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/assets/<path:filename>')
def serve_asset(filename):
    """Сервис для обслуживания статических ресурсов (логотип и т.д.)"""
    return send_from_directory(ASSETS_DIR, filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        init_db()
        query = "SELECT username, password, role, full_name FROM users WHERE username = %s"
        result = db.execute_query(query, (username,))
        
        if result and result[0][1] == password:
            session['username'] = username
            session['role'] = result[0][2]
            session['full_name'] = result[0][3]
            flash(f'Добро пожаловать, {result[0][3]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная панель пользователя"""
    init_db()
    username = session['username']
    role = session['role']
    
    # Статистика для читателя
    if role == 'reader':
        # Количество активных бронирований
        query = """
            SELECT COUNT(*) FROM reservations 
            WHERE username = %s AND status IN ('reserved', 'issued')
        """
        active_reservations = db.execute_query(query, (username,))
        active_count = active_reservations[0][0] if active_reservations else 0
        
        # Максимальное количество книг
        query = "SELECT max_books FROM users WHERE username = %s"
        max_books = db.execute_query(query, (username,))
        max_count = max_books[0][0] if max_books else 5
        
        return render_template('dashboard.html', 
                             active_reservations=active_count,
                             max_books=max_count)
    
    # Статистика для библиотекаря
    elif role == 'librarian':
        # Общая статистика
        stats = {}
        
        query = "SELECT COUNT(*) FROM books"
        stats['total_books'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM book_copies WHERE status = 'available'"
        stats['available_copies'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM reservations WHERE status = 'reserved'"
        stats['pending_reservations'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM users WHERE role = 'reader'"
        stats['total_readers'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        return render_template('dashboard.html', stats=stats, role=role)
    
    # Статистика для администратора (расширенная)
    elif role == 'admin':
        stats = {}
        
        query = "SELECT COUNT(*) FROM books"
        stats['total_books'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM book_copies WHERE status = 'available'"
        stats['available_copies'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM reservations WHERE status = 'reserved'"
        stats['pending_reservations'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM users WHERE role = 'reader'"
        stats['total_readers'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM users"
        stats['total_users'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        query = "SELECT COUNT(*) FROM book_copies"
        stats['total_copies'] = db.execute_query(query)[0][0] if db.execute_query(query) else 0
        
        return render_template('dashboard.html', stats=stats, role=role)
    
    return render_template('dashboard.html')

@app.route('/books')
@login_required
def books():
    """Список книг с поиском"""
    init_db()
    
    search = request.args.get('search', '')
    genre_id = request.args.get('genre', '')
    author_id = request.args.get('author', '')
    
    # Базовый запрос
    query = """
        SELECT DISTINCT b.book_id, b.title, b.isbn, b.publication_year, 
               b.publisher, b.description,
               COUNT(DISTINCT bc.copy_id) FILTER (WHERE bc.status = 'available') as available_copies
        FROM books b
        LEFT JOIN book_copies bc ON b.book_id = bc.book_id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (b.title ILIKE %s OR b.isbn ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    if genre_id:
        query += " AND EXISTS (SELECT 1 FROM book_genres bg WHERE bg.book_id = b.book_id AND bg.genre_id = %s)"
        params.append(genre_id)
    
    if author_id:
        query += " AND EXISTS (SELECT 1 FROM book_authors ba WHERE ba.book_id = b.book_id AND ba.author_id = %s)"
        params.append(author_id)
    
    query += " GROUP BY b.book_id ORDER BY b.title"
    
    books_list = db.execute_query(query, tuple(params) if params else None)
    
    # Получаем авторов для каждой книги
    books_with_authors = []
    for book in books_list:
        book_id = book[0]
        authors_query = """
            SELECT a.first_name, a.last_name 
            FROM authors a
            JOIN book_authors ba ON a.author_id = ba.author_id
            WHERE ba.book_id = %s
        """
        authors = db.execute_query(authors_query, (book_id,))
        authors_str = ', '.join([f"{a[0]} {a[1]}" for a in authors]) if authors else 'Неизвестен'
        
        genres_query = """
            SELECT g.name 
            FROM genres g
            JOIN book_genres bg ON g.genre_id = bg.genre_id
            WHERE bg.book_id = %s
        """
        genres = db.execute_query(genres_query, (book_id,))
        genres_str = ', '.join([g[0] for g in genres]) if genres else 'Не указан'
        
        # Ищем изображение книги
        image_path = get_book_image_path(book[1])
        
        books_with_authors.append({
            'book_id': book[0],
            'title': book[1],
            'isbn': book[2],
            'publication_year': book[3],
            'publisher': book[4],
            'description': book[5],
            'available_copies': book[6] or 0,
            'authors': authors_str,
            'genres': genres_str,
            'image_path': image_path
        })
    
    # Получаем список жанров для фильтра
    genres_query = "SELECT genre_id, name FROM genres ORDER BY name"
    genres_list = db.execute_query(genres_query)
    
    # Получаем список авторов для фильтра
    authors_query = "SELECT author_id, first_name, last_name FROM authors ORDER BY last_name, first_name"
    authors_list = db.execute_query(authors_query)
    
    return render_template('books.html', 
                         books=books_with_authors,
                         genres=genres_list or [],
                         authors=authors_list or [],
                         search=search,
                         selected_genre=genre_id,
                         selected_author=author_id)

@app.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    """Детальная информация о книге"""
    init_db()
    
    # Информация о книге
    query = """
        SELECT book_id, title, isbn, publication_year, publisher, pages, language, description
        FROM books WHERE book_id = %s
    """
    book = db.execute_query(query, (book_id,))
    
    if not book:
        flash('Книга не найдена', 'danger')
        return redirect(url_for('books'))
    
    book = book[0]
    
    # Авторы
    authors_query = """
        SELECT a.author_id, a.first_name, a.last_name, a.birth_year, a.death_year
        FROM authors a
        JOIN book_authors ba ON a.author_id = ba.author_id
        WHERE ba.book_id = %s
    """
    authors = db.execute_query(authors_query, (book_id,))
    
    # Жанры
    genres_query = """
        SELECT g.genre_id, g.name, g.description
        FROM genres g
        JOIN book_genres bg ON g.genre_id = bg.genre_id
        WHERE bg.book_id = %s
    """
    genres = db.execute_query(genres_query, (book_id,))
    
    # Доступные экземпляры
    copies_query = """
        SELECT copy_id, inventory_number, condition, status, location
        FROM book_copies
        WHERE book_id = %s AND status = 'available'
        ORDER BY inventory_number
    """
    copies = db.execute_query(copies_query, (book_id,))
    
    # Ищем изображение книги
    image_path = get_book_image_path(book[1])
    
    return render_template('book_detail.html',
                         book={
                             'book_id': book[0],
                             'title': book[1],
                             'isbn': book[2],
                             'publication_year': book[3],
                             'publisher': book[4],
                             'pages': book[5],
                             'language': book[6],
                             'description': book[7],
                             'image_path': image_path
                         },
                         authors=authors or [],
                         genres=genres or [],
                         copies=copies or [])

@app.route('/reserve/<int:copy_id>', methods=['POST'])
@login_required
@role_required('reader')
def reserve_book(copy_id):
    """Бронирование книги"""
    init_db()
    username = session['username']
    
    # Проверяем, не превышен ли лимит книг
    query = """
        SELECT max_books FROM users WHERE username = %s
    """
    user_info = db.execute_query(query, (username,))
    max_books = user_info[0][0] if user_info else 5
    
    query = """
        SELECT COUNT(*) FROM reservations 
        WHERE username = %s AND status IN ('reserved', 'issued')
    """
    current_count = db.execute_query(query, (username,))
    current = current_count[0][0] if current_count else 0
    
    if current >= max_books:
        flash(f'Вы достигли лимита бронирований ({max_books} книг)', 'warning')
        return redirect(request.referrer or url_for('books'))
    
    # Проверяем доступность экземпляра
    query = "SELECT status FROM book_copies WHERE copy_id = %s"
    copy_status = db.execute_query(query, (copy_id,))
    
    if not copy_status or copy_status[0][0] != 'available':
        flash('Этот экземпляр недоступен для бронирования', 'danger')
        return redirect(request.referrer or url_for('books'))
    
    # Создаем бронирование
    reservation_date = datetime.now()
    due_date = date.today() + timedelta(days=30)
    pickup_deadline = reservation_date + timedelta(days=7)
    
    query = """
        INSERT INTO reservations (copy_id, username, reservation_date, pickup_deadline, due_date, status)
        VALUES (%s, %s, %s, %s, %s, 'reserved')
    """
    success = db.execute_insert(query, (copy_id, username, reservation_date, pickup_deadline, due_date))
    
    if success:
        # Обновляем статус экземпляра
        query = "UPDATE book_copies SET status = 'reserved' WHERE copy_id = %s"
        db.execute_insert(query, (copy_id,))
        flash('Книга успешно забронирована!', 'success')
    else:
        flash('Ошибка при бронировании книги', 'danger')
    
    return redirect(request.referrer or url_for('books'))

@app.route('/my_reservations')
@login_required
@role_required('reader')
def my_reservations():
    """Мои бронирования"""
    init_db()
    username = session['username']
    
    # Получаем фильтр статуса из параметров запроса (по умолчанию показываем все)
    status_filter = request.args.get('status', '')
    
    query = """
        SELECT r.copy_id, r.reservation_date, r.pickup_deadline, r.due_date, r.status,
               b.title, bc.inventory_number
        FROM reservations r
        JOIN book_copies bc ON r.copy_id = bc.copy_id
        JOIN books b ON bc.book_id = b.book_id
        WHERE r.username = %s
    """
    params = [username]
    
    # Добавляем фильтр по статусу, если указан
    if status_filter:
        query += " AND r.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY r.reservation_date DESC"
    
    reservations = db.execute_query(query, tuple(params))
    
    reservations_list = []
    for res in reservations or []:
        reservations_list.append({
            'copy_id': res[0],
            'reservation_date': res[1],
            'pickup_deadline': res[2],
            'due_date': res[3],
            'status': res[4],
            'title': res[5],
            'inventory_number': res[6]
        })
    
    return render_template('my_reservations.html', 
                         reservations=reservations_list,
                         status_filter=status_filter)

@app.route('/cancel_reservation/<int:copy_id>', methods=['POST'])
@login_required
@role_required('reader')
def cancel_reservation(copy_id):
    """Отмена бронирования"""
    init_db()
    username = session['username']
    reservation_date = request.form.get('reservation_date')
    
    if not reservation_date:
        flash('Ошибка: не указана дата бронирования', 'danger')
        return redirect(url_for('my_reservations'))
    
    # Проверяем, что это бронирование пользователя со статусом 'reserved' или 'issued'
    query = """
        SELECT status FROM reservations 
        WHERE copy_id = %s AND username = %s AND reservation_date = %s AND status IN ('reserved', 'issued')
    """
    reservation = db.execute_query(query, (copy_id, username, reservation_date))
    
    if not reservation:
        flash('Бронирование не найдено или уже обработано', 'warning')
        return redirect(url_for('my_reservations'))
    
    # Отменяем бронирование (используем все три поля составного ключа)
    # Разрешаем отмену для статусов 'reserved' и 'issued'
    query = """
        UPDATE reservations SET status = 'cancelled' 
        WHERE copy_id = %s AND username = %s AND reservation_date = %s AND status IN ('reserved', 'issued')
    """
    db.execute_insert(query, (copy_id, username, reservation_date))
    
    # Автоматически возвращаем экземпляр в доступные
    query = "UPDATE book_copies SET status = 'available' WHERE copy_id = %s"
    db.execute_insert(query, (copy_id,))
    
    flash('Бронирование отменено', 'success')
    return redirect(url_for('my_reservations'))

@app.route('/all_reservations')
@login_required
@role_required('librarian', 'admin')
def all_reservations():
    """Все бронирования (для библиотекарей)"""
    init_db()
    
    status_filter = request.args.get('status', '')
    
    query = """
        SELECT r.copy_id, r.username, r.reservation_date, r.pickup_deadline, 
               r.due_date, r.status, b.title, bc.inventory_number, u.full_name
        FROM reservations r
        JOIN book_copies bc ON r.copy_id = bc.copy_id
        JOIN books b ON bc.book_id = b.book_id
        JOIN users u ON r.username = u.username
        WHERE 1=1
    """
    params = []
    
    if status_filter:
        query += " AND r.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY r.reservation_date DESC"
    
    reservations = db.execute_query(query, tuple(params) if params else None)
    
    reservations_list = []
    for res in reservations or []:
        reservations_list.append({
            'copy_id': res[0],
            'username': res[1],
            'reservation_date': res[2],
            'pickup_deadline': res[3],
            'due_date': res[4],
            'status': res[5],
            'title': res[6],
            'inventory_number': res[7],
            'full_name': res[8]
        })
    
    return render_template('all_reservations.html', 
                         reservations=reservations_list,
                         status_filter=status_filter)

@app.route('/update_reservation_status/<int:copy_id>/<username>', methods=['POST'])
@login_required
@role_required('librarian', 'admin')
def update_reservation_status(copy_id, username):
    """Обновление статуса бронирования"""
    init_db()
    
    new_status = request.form.get('status')
    reservation_date = request.form.get('reservation_date')
    
    if new_status not in ['reserved', 'issued', 'returned', 'cancelled']:
        flash('Неверный статус', 'danger')
        return redirect(url_for('all_reservations'))
    
    # Обновляем статус бронирования
    query = """
        UPDATE reservations 
        SET status = %s 
        WHERE copy_id = %s AND username = %s AND reservation_date = %s
    """
    db.execute_insert(query, (new_status, copy_id, username, reservation_date))
    
    # Обновляем статус экземпляра
    if new_status == 'returned' or new_status == 'cancelled':
        copy_status = 'available'
    elif new_status == 'issued':
        copy_status = 'issued'
    else:
        copy_status = 'reserved'
    
    query = "UPDATE book_copies SET status = %s WHERE copy_id = %s"
    db.execute_insert(query, (copy_status, copy_id))
    
    flash('Статус обновлен', 'success')
    return redirect(url_for('all_reservations'))

# ==================== АДМИНИСТРАТОРСКИЕ ФУНКЦИИ ====================

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    """Управление пользователями (только для админа)"""
    init_db()
    
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    
    query = "SELECT username, email, full_name, phone, card_number, role, max_books FROM users WHERE 1=1"
    params = []
    
    if search:
        query += " AND (username ILIKE %s OR full_name ILIKE %s OR email ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    
    if role_filter:
        query += " AND role = %s"
        params.append(role_filter)
    
    query += " ORDER BY username"
    
    users = db.execute_query(query, tuple(params) if params else None)
    
    users_list = []
    for user in users or []:
        users_list.append({
            'username': user[0],
            'email': user[1],
            'full_name': user[2],
            'phone': user[3],
            'card_number': user[4],
            'role': user[5],
            'max_books': user[6]
        })
    
    return render_template('admin_users.html', users=users_list, search=search, role_filter=role_filter)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_user():
    """Добавление нового пользователя"""
    init_db()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if len(username) > 50:
            username = username[:50]
        
        email = request.form.get('email', '').strip()
        if len(email) > 100:
            email = email[:100]
        
        full_name = request.form.get('full_name', '').strip()
        if len(full_name) > 150:
            full_name = full_name[:150]
        
        phone = request.form.get('phone', '').strip() or None
        if phone and len(phone) > 20:
            phone = phone[:20]
        
        card_number = request.form.get('card_number', '').strip() or None
        if card_number and len(card_number) > 20:
            card_number = card_number[:20]
        
        role = request.form.get('role')
        max_books = int(request.form.get('max_books', 5))
        password = request.form.get('password', '').strip()
        if len(password) > 50:
            password = password[:50]
        
        # Проверка существования username
        check_query = "SELECT username FROM users WHERE username = %s"
        existing = db.execute_query(check_query, (username,))
        if existing:
            flash('Пользователь с таким логином уже существует', 'danger')
            return render_template('admin_user_form.html', action='add')
        
        # Добавление пользователя
        insert_query = """
            INSERT INTO users (username, email, full_name, phone, card_number, role, max_books, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        success = db.execute_insert(insert_query, (username, email, full_name, phone, card_number, role, max_books, password))
        
        if success:
            flash('Пользователь успешно добавлен', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('Ошибка при добавлении пользователя', 'danger')
    
    return render_template('admin_user_form.html', action='add')

@app.route('/admin/users/edit/<username>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_user(username):
    """Редактирование пользователя"""
    init_db()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if len(email) > 100:
            email = email[:100]
        
        full_name = request.form.get('full_name', '').strip()
        if len(full_name) > 150:
            full_name = full_name[:150]
        
        phone = request.form.get('phone', '').strip() or None
        if phone and len(phone) > 20:
            phone = phone[:20]
        
        card_number = request.form.get('card_number', '').strip() or None
        if card_number and len(card_number) > 20:
            card_number = card_number[:20]
        
        role = request.form.get('role')
        max_books = int(request.form.get('max_books', 5))
        password = request.form.get('password', '').strip()
        if password and len(password) > 50:
            password = password[:50]
        
        if password:
            update_query = """
                UPDATE users SET email = %s, full_name = %s, phone = %s, card_number = %s, 
                role = %s, max_books = %s, password = %s WHERE username = %s
            """
            success = db.execute_insert(update_query, (email, full_name, phone, card_number, role, max_books, password, username))
        else:
            update_query = """
                UPDATE users SET email = %s, full_name = %s, phone = %s, card_number = %s, 
                role = %s, max_books = %s WHERE username = %s
            """
            success = db.execute_insert(update_query, (email, full_name, phone, card_number, role, max_books, username))
        
        if success:
            flash('Пользователь успешно обновлен', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('Ошибка при обновлении пользователя', 'danger')
    
    # Получение данных пользователя
    query = "SELECT username, email, full_name, phone, card_number, role, max_books FROM users WHERE username = %s"
    user_data = db.execute_query(query, (username,))
    
    if not user_data:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('admin_users'))
    
    user = user_data[0]
    return render_template('admin_user_form.html', action='edit', user={
        'username': user[0],
        'email': user[1],
        'full_name': user[2],
        'phone': user[3],
        'card_number': user[4],
        'role': user[5],
        'max_books': user[6]
    })

@app.route('/admin/books/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_book():
    """Добавление новой книги"""
    init_db()
    
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Название книги обязательно', 'danger')
            authors = db.execute_query("SELECT author_id, first_name, last_name FROM authors ORDER BY last_name, first_name")
            genres = db.execute_query("SELECT genre_id, name FROM genres ORDER BY name")
            return render_template('admin_book_form.html', action='add', authors=authors or [], genres=genres or [])
        
        isbn = request.form.get('isbn', '').strip() or None
        publication_year_str = request.form.get('publication_year', '').strip()
        try:
            publication_year = int(publication_year_str) if publication_year_str else None
        except (ValueError, TypeError):
            publication_year = None
        
        publisher = request.form.get('publisher', '').strip() or None
        pages_str = request.form.get('pages', '').strip()
        try:
            pages = int(pages_str) if pages_str else None
        except (ValueError, TypeError):
            pages = None
        language = request.form.get('language', 'Русский').strip() or 'Русский'
        if language and len(language) > 50:
            language = language[:50]  # Обрезаем до 50 символов
        
        description = request.form.get('description', '').strip() or None
        authors_text = request.form.get('authors', '').strip()
        genres_text = request.form.get('genres', '').strip()
        
        if not authors_text:
            flash('Необходимо указать хотя бы одного автора', 'danger')
            return render_template('admin_book_form.html', action='add')
        
        if not genres_text:
            flash('Необходимо указать хотя бы один жанр', 'danger')
            return render_template('admin_book_form.html', action='add')
        
        # Получаем следующий ID
        max_id_query = "SELECT COALESCE(MAX(book_id), 0) + 1 FROM books"
        result = db.execute_query(max_id_query)
        book_id = result[0][0] if result else 1
        
        # Добавление книги
        insert_query = """
            INSERT INTO books (book_id, title, isbn, publication_year, publisher, pages, language, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            success = db.execute_insert(insert_query, (book_id, title, isbn, publication_year, publisher, pages, language, description))
        except Exception as e:
            flash(f'Ошибка при добавлении книги: {str(e)}', 'danger')
            return render_template('admin_book_form.html', action='add')
        
        if success:
            # Обработка авторов
            if authors_text:
                authors_lines = [line.strip() for line in authors_text.split('\n') if line.strip()]
                for author_line in authors_lines:
                    # Парсинг формата "Имя Фамилия" или "Фамилия, Имя"
                    if ',' in author_line:
                        parts = [p.strip() for p in author_line.split(',', 1)]
                        if len(parts) == 2:
                            last_name, first_name = parts[0], parts[1]
                        else:
                            continue
                    else:
                        parts = author_line.split()
                        if len(parts) >= 2:
                            first_name = parts[0]
                            last_name = ' '.join(parts[1:])
                        else:
                            continue
                    
                    # Обрезаем имена авторов до 100 символов
                    first_name = first_name[:100] if len(first_name) > 100 else first_name
                    last_name = last_name[:100] if len(last_name) > 100 else last_name
                    
                    # Проверка существования автора
                    check_author = db.execute_query(
                        "SELECT author_id FROM authors WHERE first_name = %s AND last_name = %s",
                        (first_name, last_name)
                    )
                    
                    if check_author:
                        author_id = check_author[0][0]
                    else:
                        # Создание нового автора
                        max_author_id = db.execute_query("SELECT COALESCE(MAX(author_id), 0) + 1 FROM authors")
                        new_author_id = max_author_id[0][0] if max_author_id else 1
                        insert_success = db.execute_insert(
                            "INSERT INTO authors (author_id, first_name, last_name) VALUES (%s, %s, %s)",
                            (new_author_id, first_name, last_name)
                        )
                        if insert_success:
                            author_id = new_author_id
                        else:
                            continue
                    
                    # Добавление связи, если еще нет
                    check_link = db.execute_query(
                        "SELECT book_id FROM book_authors WHERE book_id = %s AND author_id = %s",
                        (book_id, author_id)
                    )
                    if not check_link:
                        db.execute_insert("INSERT INTO book_authors (book_id, author_id) VALUES (%s, %s)", (book_id, author_id))
            
            # Обработка жанров
            if genres_text:
                genres_lines = [line.strip() for line in genres_text.split('\n') if line.strip()]
                for genre_name in genres_lines:
                    # Обрезаем название жанра до 50 символов
                    genre_name = genre_name[:50] if len(genre_name) > 50 else genre_name
                    
                    # Проверка существования жанра
                    check_genre = db.execute_query("SELECT genre_id FROM genres WHERE name = %s", (genre_name,))
                    
                    if check_genre:
                        genre_id = check_genre[0][0]
                    else:
                        # Создание нового жанра
                        max_genre_id = db.execute_query("SELECT COALESCE(MAX(genre_id), 0) + 1 FROM genres")
                        new_genre_id = max_genre_id[0][0] if max_genre_id else 1
                        insert_success = db.execute_insert(
                            "INSERT INTO genres (genre_id, name) VALUES (%s, %s)",
                            (new_genre_id, genre_name)
                        )
                        if insert_success:
                            genre_id = new_genre_id
                        else:
                            continue
                    
                    # Добавление связи, если еще нет
                    check_link = db.execute_query(
                        "SELECT book_id FROM book_genres WHERE book_id = %s AND genre_id = %s",
                        (book_id, genre_id)
                    )
                    if not check_link:
                        db.execute_insert("INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)", (book_id, genre_id))
            
            flash('Книга успешно добавлена', 'success')
            return redirect(url_for('book_detail', book_id=book_id))
        else:
            flash('Ошибка при добавлении книги', 'danger')
    
    return render_template('admin_book_form.html', action='add')

@app.route('/admin/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_book(book_id):
    """Редактирование книги"""
    init_db()
    
    if request.method == 'POST':
        title = request.form.get('title')
        if not title or not title.strip():
            flash('Название книги обязательно', 'danger')
            # Получение данных книги для повторного отображения формы
            book_query = "SELECT book_id, title, isbn, publication_year, publisher, pages, language, description FROM books WHERE book_id = %s"
            book_data = db.execute_query(book_query, (book_id,))
            if not book_data:
                return redirect(url_for('books'))
            book = book_data[0]
            
            # Получение текущих авторов и жанров для отображения в текстовых полях
            current_authors_query = """
                SELECT a.first_name, a.last_name 
                FROM authors a
                JOIN book_authors ba ON a.author_id = ba.author_id
                WHERE ba.book_id = %s
                ORDER BY a.last_name, a.first_name
            """
            current_authors = db.execute_query(current_authors_query, (book_id,))
            authors_text = '\n'.join([f"{a[0]} {a[1]}" for a in (current_authors or [])])
            
            current_genres_query = """
                SELECT g.name 
                FROM genres g
                JOIN book_genres bg ON g.genre_id = bg.genre_id
                WHERE bg.book_id = %s
                ORDER BY g.name
            """
            current_genres = db.execute_query(current_genres_query, (book_id,))
            genres_text = '\n'.join([g[0] for g in (current_genres or [])])
            
            return render_template('admin_book_form.html', action='edit', book={
                'book_id': book[0], 'title': book[1], 'isbn': book[2], 'publication_year': book[3],
                'publisher': book[4], 'pages': book[5], 'language': book[6], 'description': book[7],
                'authors_text': authors_text, 'genres_text': genres_text
            })
        
        isbn = request.form.get('isbn', '').strip() or None
        if isbn and len(isbn) > 20:
            isbn = isbn[:20]  # Обрезаем до 20 символов
        
        publication_year_str = request.form.get('publication_year', '').strip()
        try:
            publication_year = int(publication_year_str) if publication_year_str else None
        except (ValueError, TypeError):
            publication_year = None
        
        publisher = request.form.get('publisher', '').strip() or None
        if publisher and len(publisher) > 200:
            publisher = publisher[:200]  # Обрезаем до 200 символов
        
        pages_str = request.form.get('pages', '').strip()
        try:
            pages = int(pages_str) if pages_str else None
        except (ValueError, TypeError):
            pages = None
        
        language = request.form.get('language', 'Русский').strip() or 'Русский'
        if language and len(language) > 50:
            language = language[:50]  # Обрезаем до 50 символов
        
        description = request.form.get('description', '').strip() or None
        authors_text = request.form.get('authors', '').strip()
        genres_text = request.form.get('genres', '').strip()
        
        # Обновление книги
        update_query = """
            UPDATE books SET title = %s, isbn = %s, publication_year = %s, publisher = %s, 
            pages = %s, language = %s, description = %s WHERE book_id = %s
        """
        success = db.execute_insert(update_query, (title, isbn, publication_year, publisher, pages, language, description, book_id))
        
        if success:
            # Удаление старых связей
            db.execute_insert("DELETE FROM book_authors WHERE book_id = %s", (book_id,))
            db.execute_insert("DELETE FROM book_genres WHERE book_id = %s", (book_id,))
            
            # Обработка авторов
            if authors_text:
                authors_lines = [line.strip() for line in authors_text.split('\n') if line.strip()]
                for author_line in authors_lines:
                    # Парсинг формата "Имя Фамилия" или "Фамилия, Имя"
                    if ',' in author_line:
                        parts = [p.strip() for p in author_line.split(',', 1)]
                        if len(parts) == 2:
                            last_name, first_name = parts[0], parts[1]
                        else:
                            continue
                    else:
                        parts = author_line.split()
                        if len(parts) >= 2:
                            first_name = parts[0]
                            last_name = ' '.join(parts[1:])
                        else:
                            continue
                    
                    # Обрезаем имена авторов до 100 символов
                    first_name = first_name[:100] if len(first_name) > 100 else first_name
                    last_name = last_name[:100] if len(last_name) > 100 else last_name
                    
                    # Проверка существования автора
                    check_author = db.execute_query(
                        "SELECT author_id FROM authors WHERE first_name = %s AND last_name = %s",
                        (first_name, last_name)
                    )
                    
                    if check_author:
                        author_id = check_author[0][0]
                    else:
                        # Создание нового автора
                        max_author_id = db.execute_query("SELECT COALESCE(MAX(author_id), 0) + 1 FROM authors")
                        new_author_id = max_author_id[0][0] if max_author_id else 1
                        insert_success = db.execute_insert(
                            "INSERT INTO authors (author_id, first_name, last_name) VALUES (%s, %s, %s)",
                            (new_author_id, first_name, last_name)
                        )
                        if insert_success:
                            author_id = new_author_id
                        else:
                            continue
                    
                    # Добавление связи
                    db.execute_insert("INSERT INTO book_authors (book_id, author_id) VALUES (%s, %s)", (book_id, author_id))
            
            # Обработка жанров
            if genres_text:
                genres_lines = [line.strip() for line in genres_text.split('\n') if line.strip()]
                for genre_name in genres_lines:
                    # Обрезаем название жанра до 50 символов
                    genre_name = genre_name[:50] if len(genre_name) > 50 else genre_name
                    
                    # Проверка существования жанра
                    check_genre = db.execute_query("SELECT genre_id FROM genres WHERE name = %s", (genre_name,))
                    
                    if check_genre:
                        genre_id = check_genre[0][0]
                    else:
                        # Создание нового жанра
                        max_genre_id = db.execute_query("SELECT COALESCE(MAX(genre_id), 0) + 1 FROM genres")
                        new_genre_id = max_genre_id[0][0] if max_genre_id else 1
                        insert_success = db.execute_insert(
                            "INSERT INTO genres (genre_id, name) VALUES (%s, %s)",
                            (new_genre_id, genre_name)
                        )
                        if insert_success:
                            genre_id = new_genre_id
                        else:
                            continue
                    
                    # Добавление связи
                    db.execute_insert("INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)", (book_id, genre_id))
            
            flash('Книга успешно обновлена', 'success')
            return redirect(url_for('book_detail', book_id=book_id))
        else:
            flash('Ошибка при обновлении книги', 'danger')
    
    # Получение данных книги
    book_query = "SELECT book_id, title, isbn, publication_year, publisher, pages, language, description FROM books WHERE book_id = %s"
    book_data = db.execute_query(book_query, (book_id,))
    
    if not book_data:
        flash('Книга не найдена', 'danger')
        return redirect(url_for('books'))
    
    book = book_data[0]
    
    # Получение текущих авторов и жанров для отображения в текстовых полях
    current_authors_query = """
        SELECT a.first_name, a.last_name 
        FROM authors a
        JOIN book_authors ba ON a.author_id = ba.author_id
        WHERE ba.book_id = %s
        ORDER BY a.last_name, a.first_name
    """
    current_authors = db.execute_query(current_authors_query, (book_id,))
    authors_text = '\n'.join([f"{a[0]} {a[1]}" for a in (current_authors or [])])
    
    current_genres_query = """
        SELECT g.name 
        FROM genres g
        JOIN book_genres bg ON g.genre_id = bg.genre_id
        WHERE bg.book_id = %s
        ORDER BY g.name
    """
    current_genres = db.execute_query(current_genres_query, (book_id,))
    genres_text = '\n'.join([g[0] for g in (current_genres or [])])
    
    return render_template('admin_book_form.html', action='edit', book={
        'book_id': book[0],
        'title': book[1],
        'isbn': book[2],
        'publication_year': book[3],
        'publisher': book[4],
        'pages': book[5],
        'language': book[6],
        'description': book[7],
        'authors_text': authors_text,
        'genres_text': genres_text
    })

@app.route('/admin/copies/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_copy():
    """Добавление нового экземпляра книги"""
    init_db()
    
    # Получаем book_id из параметров, если есть
    selected_book_id = request.args.get('book_id')
    
    if request.method == 'POST':
        book_id = int(request.form.get('book_id'))
        inventory_number = request.form.get('inventory_number', '').strip()
        if len(inventory_number) > 50:
            inventory_number = inventory_number[:50]  # Обрезаем до 50 символов
        
        condition = request.form.get('condition', 'good')
        location = request.form.get('location', '').strip() or None
        if location and len(location) > 100:
            location = location[:100]  # Обрезаем до 100 символов
        
        # Проверка уникальности инвентарного номера
        check_query = "SELECT copy_id FROM book_copies WHERE inventory_number = %s"
        existing = db.execute_query(check_query, (inventory_number,))
        if existing:
            flash('Экземпляр с таким инвентарным номером уже существует', 'danger')
            books = db.execute_query("SELECT book_id, title FROM books ORDER BY title")
            return render_template('admin_copy_form.html', action='add', books=books or [])
        
        # Получаем следующий ID
        max_id_query = "SELECT COALESCE(MAX(copy_id), 0) + 1 FROM book_copies"
        result = db.execute_query(max_id_query)
        copy_id = result[0][0] if result else 1
        
        # Добавление экземпляра
        insert_query = """
            INSERT INTO book_copies (copy_id, book_id, inventory_number, condition, status, location)
            VALUES (%s, %s, %s, %s, 'available', %s)
        """
        success = db.execute_insert(insert_query, (copy_id, book_id, inventory_number, condition, location))
        
        if success:
            flash('Экземпляр успешно добавлен', 'success')
            return redirect(url_for('book_detail', book_id=book_id))
        else:
            flash('Ошибка при добавлении экземпляра', 'danger')
    
    books = db.execute_query("SELECT book_id, title FROM books ORDER BY title")
    return render_template('admin_copy_form.html', action='add', books=books or [], selected_book_id=selected_book_id)

@app.route('/admin/statistics')
@login_required
@role_required('admin')
def admin_statistics():
    """Расширенная статистика для администратора"""
    init_db()
    
    stats = {}
    
    # Базовая статистика
    stats['total_books'] = db.execute_query("SELECT COUNT(*) FROM books")[0][0] if db.execute_query("SELECT COUNT(*) FROM books") else 0
    stats['total_copies'] = db.execute_query("SELECT COUNT(*) FROM book_copies")[0][0] if db.execute_query("SELECT COUNT(*) FROM book_copies") else 0
    stats['available_copies'] = db.execute_query("SELECT COUNT(*) FROM book_copies WHERE status = 'available'")[0][0] if db.execute_query("SELECT COUNT(*) FROM book_copies WHERE status = 'available'") else 0
    stats['total_users'] = db.execute_query("SELECT COUNT(*) FROM users")[0][0] if db.execute_query("SELECT COUNT(*) FROM users") else 0
    stats['total_readers'] = db.execute_query("SELECT COUNT(*) FROM users WHERE role = 'reader'")[0][0] if db.execute_query("SELECT COUNT(*) FROM users WHERE role = 'reader'") else 0
    stats['total_reservations'] = db.execute_query("SELECT COUNT(*) FROM reservations")[0][0] if db.execute_query("SELECT COUNT(*) FROM reservations") else 0
    stats['active_reservations'] = db.execute_query("SELECT COUNT(*) FROM reservations WHERE status IN ('reserved', 'issued')")[0][0] if db.execute_query("SELECT COUNT(*) FROM reservations WHERE status IN ('reserved', 'issued')") else 0
    
    # Популярные книги (по количеству бронирований)
    popular_books_query = """
        SELECT b.book_id, b.title, COUNT(r.copy_id) as reservation_count
        FROM books b
        LEFT JOIN book_copies bc ON b.book_id = bc.book_id
        LEFT JOIN reservations r ON bc.copy_id = r.copy_id
        GROUP BY b.book_id, b.title
        ORDER BY reservation_count DESC
        LIMIT 10
    """
    stats['popular_books'] = db.execute_query(popular_books_query) or []
    
    # Статистика по жанрам
    genre_stats_query = """
        SELECT g.name, COUNT(DISTINCT bg.book_id) as book_count
        FROM genres g
        LEFT JOIN book_genres bg ON g.genre_id = bg.genre_id
        GROUP BY g.genre_id, g.name
        ORDER BY book_count DESC
    """
    stats['genre_stats'] = db.execute_query(genre_stats_query) or []
    
    # Статистика по авторам
    author_stats_query = """
        SELECT a.first_name, a.last_name, COUNT(DISTINCT ba.book_id) as book_count
        FROM authors a
        LEFT JOIN book_authors ba ON a.author_id = ba.author_id
        GROUP BY a.author_id, a.first_name, a.last_name
        ORDER BY book_count DESC
        LIMIT 10
    """
    stats['author_stats'] = db.execute_query(author_stats_query) or []
    
    # Статистика по статусам бронирований
    reservation_status_query = """
        SELECT status, COUNT(*) as count
        FROM reservations
        GROUP BY status
    """
    stats['reservation_status'] = db.execute_query(reservation_status_query) or []
    
    # Статистика по ролям пользователей
    user_roles_query = """
        SELECT role, COUNT(*) as count
        FROM users
        GROUP BY role
    """
    stats['user_roles'] = db.execute_query(user_roles_query) or []
    
    return render_template('admin_statistics.html', stats=stats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)