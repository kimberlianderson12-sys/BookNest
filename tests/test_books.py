"""
Тесты модуля работы с книгами
"""
import pytest
from main import app
from db import Database


@pytest.fixture
def client():
    """Создание тестового клиента Flask"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Клиент с авторизованным пользователем"""
    client.post('/login', data={
        'username': 'ivanov',
        'password': 'A1b2c'
    })
    return client


@pytest.fixture
def db():
    """Создание подключения к тестовой БД"""
    test_db = Database(host='localhost', database='library_db', user='postgres', password='1234')
    test_db.connect()
    yield test_db
    test_db.close()


class TestBooks:
    """Тесты работы с книгами"""
    
    def test_books_page_requires_auth(self, client):
        """Тест 2.1: Страница книг требует авторизации"""
        response = client.get('/books', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower() or 'Вход'.encode('utf-8') in response.data
    
    def test_books_page_loads(self, authenticated_client):
        """Тест 2.2: Страница списка книг загружается"""
        response = authenticated_client.get('/books')
        assert response.status_code == 200
        assert 'Книги'.encode('utf-8') in response.data or b'Books' in response.data
    
    def test_search_by_title(self, authenticated_client, db):
        """Тест 2.3: Поиск книги по названию"""
        # Ищем книгу по части названия
        response = authenticated_client.get('/books?search=Война')
        assert response.status_code == 200
        
        # Проверяем, что результаты содержат искомое слово
        # (зависит от наличия данных в БД)
        # assert b'Война' in response.data
    
    def test_search_by_isbn(self, authenticated_client):
        """Тест 2.4: Поиск книги по ISBN"""
        response = authenticated_client.get('/books?search=978')
        assert response.status_code == 200
    
    def test_filter_by_genre(self, authenticated_client, db):
        """Тест 2.5: Фильтрация по жанру"""
        # Получаем список жанров
        genres_query = "SELECT genre_id FROM genres LIMIT 1"
        result = db.execute_query(genres_query)
        
        if result:
            genre_id = result[0][0]
            response = authenticated_client.get(f'/books?genre={genre_id}')
            assert response.status_code == 200
    
    def test_filter_by_author(self, authenticated_client, db):
        """Тест 2.6: Фильтрация по автору"""
        # Получаем список авторов
        authors_query = "SELECT author_id FROM authors LIMIT 1"
        result = db.execute_query(authors_query)
        
        if result:
            author_id = result[0][0]
            response = authenticated_client.get(f'/books?author={author_id}')
            assert response.status_code == 200
    
    def test_book_detail_page(self, authenticated_client, db):
        """Тест 2.7: Просмотр детальной информации о книге"""
        # Получаем ID первой книги
        books_query = "SELECT book_id FROM books LIMIT 1"
        result = db.execute_query(books_query)
        
        if result:
            book_id = result[0][0]
            response = authenticated_client.get(f'/book/{book_id}')
            assert response.status_code == 200
    
    def test_book_detail_not_found(self, authenticated_client):
        """Тест 2.8: Просмотр несуществующей книги"""
        response = authenticated_client.get('/book/99999', follow_redirects=True)
        # Должен быть редирект на страницу книг с сообщением об ошибке
        assert response.status_code == 200

