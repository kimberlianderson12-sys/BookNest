"""
Тесты модуля dashboard (статистика)
"""
import pytest
from main import app


@pytest.fixture
def client():
    """Создание тестового клиента Flask"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    with app.test_client() as client:
        yield client


@pytest.fixture
def reader_client(client):
    """Клиент с авторизованным читателем"""
    client.post('/login', data={
        'username': 'ivanov',
        'password': 'A1b2c'
    })
    return client


@pytest.fixture
def librarian_client(client):
    """Клиент с авторизованным библиотекарем"""
    client.post('/login', data={
        'username': 'librarian',
        'password': 'J7k8I'
    })
    return client


class TestDashboard:
    """Тесты панели управления"""
    
    def test_dashboard_requires_auth(self, client):
        """Тест 5.1: Dashboard требует авторизации"""
        response = client.get('/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower() or 'Вход'.encode('utf-8') in response.data
    
    def test_reader_dashboard(self, reader_client):
        """Тест 5.2: Отображение статистики для читателя"""
        response = reader_client.get('/dashboard')
        assert response.status_code == 200
        # Проверяем наличие элементов dashboard для читателя
        # (зависит от структуры шаблона)
    
    def test_librarian_dashboard(self, librarian_client):
        """Тест 5.3: Отображение статистики для библиотекаря"""
        response = librarian_client.get('/dashboard')
        assert response.status_code == 200
        # Проверяем наличие элементов dashboard для библиотекаря
        # (зависит от структуры шаблона)

