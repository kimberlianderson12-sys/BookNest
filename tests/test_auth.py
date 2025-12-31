"""
Тесты модуля аутентификации
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
def db():
    """Создание подключения к тестовой БД"""
    test_db = Database(host='localhost', database='library_db', user='postgres', password='1234')
    test_db.connect()
    yield test_db
    test_db.close()


class TestAuthentication:
    """Тесты аутентификации пользователей"""
    
    def test_login_page_loads(self, client):
        """Тест 1.1: Страница входа загружается"""
        response = client.get('/login')
        assert response.status_code == 200
        assert 'Вход'.encode('utf-8') in response.data or b'Login' in response.data
    
    def test_login_success(self, client, db):
        """Тест 1.2: Успешный вход с правильными данными"""
        # Предполагаем, что в БД есть пользователь с логином 'ivanov' и паролем 'A1b2c'
        response = client.post('/login', data={
            'username': 'ivanov',
            'password': 'A1b2c'
        }, follow_redirects=True)
        
        # Проверяем, что произошел редирект на dashboard
        assert response.status_code == 200
        # Проверяем, что сессия создана (косвенно через доступ к защищенной странице)
        response = client.get('/dashboard')
        assert response.status_code == 200
    
    def test_login_wrong_username(self, client):
        """Тест 1.3: Неудачный вход с неверным логином"""
        response = client.post('/login', data={
            'username': 'nonexistent_user',
            'password': 'any_password'
        })
        assert response.status_code == 200
        # Проверяем, что остались на странице входа
        assert 'Неверное имя пользователя или пароль'.encode('utf-8') in response.data or b'login' in response.data.lower()
    
    def test_login_wrong_password(self, client):
        """Тест 1.4: Неудачный вход с неверным паролем"""
        response = client.post('/login', data={
            'username': 'ivanov',
            'password': 'wrong_password'
        })
        assert response.status_code == 200
        # Проверяем, что остались на странице входа
        assert 'Неверное имя пользователя или пароль'.encode('utf-8') in response.data or b'login' in response.data.lower()
    
    def test_access_protected_page_without_login(self, client):
        """Тест 1.5: Доступ к защищенным страницам без авторизации"""
        # Пытаемся получить доступ к dashboard без входа
        response = client.get('/dashboard', follow_redirects=True)
        # Должен быть редирект на страницу входа
        assert response.status_code == 200
        assert b'login' in response.data.lower() or 'Вход'.encode('utf-8') in response.data
    
    def test_logout(self, client):
        """Тест 1.6: Выход из системы"""
        # Сначала входим
        client.post('/login', data={
            'username': 'ivanov',
            'password': 'A1b2c'
        })
        
        # Выходим
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверяем, что доступ к защищенной странице закрыт
        response = client.get('/dashboard', follow_redirects=True)
        assert b'login' in response.data.lower() or 'Вход'.encode('utf-8') in response.data

