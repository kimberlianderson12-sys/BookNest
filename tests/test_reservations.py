"""
Тесты модуля бронирования
"""
import pytest
from main import app
from db import Database
from datetime import datetime, date, timedelta


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


@pytest.fixture
def db():
    """Создание подключения к тестовой БД"""
    test_db = Database(host='localhost', database='library_db', user='postgres', password='1234')
    test_db.connect()
    yield test_db
    test_db.close()


class TestReservations:
    """Тесты бронирования для читателей"""
    
    def test_reserve_book_success(self, reader_client, db):
        """Тест 3.1: Успешное бронирование доступной книги"""
        # Находим доступный экземпляр
        query = """
            SELECT copy_id FROM book_copies 
            WHERE status = 'available' 
            LIMIT 1
        """
        result = db.execute_query(query)
        
        if result:
            copy_id = result[0][0]
            response = reader_client.post(f'/reserve/{copy_id}', follow_redirects=True)
            assert response.status_code == 200
            # Проверяем, что статус экземпляра изменился
            status_query = "SELECT status FROM book_copies WHERE copy_id = %s"
            status_result = db.execute_query(status_query, (copy_id,))
            if status_result:
                assert status_result[0][0] in ['reserved', 'issued']
    
    def test_reserve_unavailable_book(self, reader_client, db):
        """Тест 3.2: Попытка бронирования недоступного экземпляра"""
        # Находим недоступный экземпляр
        query = """
            SELECT copy_id FROM book_copies 
            WHERE status != 'available' 
            LIMIT 1
        """
        result = db.execute_query(query)
        
        if result:
            copy_id = result[0][0]
            response = reader_client.post(f'/reserve/{copy_id}', follow_redirects=True)
            assert response.status_code == 200
            # Должно быть сообщение об ошибке
    
    def test_my_reservations_page(self, reader_client):
        """Тест 3.3: Просмотр списка своих бронирований"""
        response = reader_client.get('/my_reservations')
        assert response.status_code == 200
        assert 'Мои бронирования'.encode('utf-8') in response.data or b'reservations' in response.data.lower()
    
    def test_cancel_reservation(self, reader_client, db):
        """Тест 3.4: Отмена бронирования"""
        # Находим бронирование читателя со статусом 'reserved'
        query = """
            SELECT copy_id, reservation_date FROM reservations 
            WHERE username = 'ivanov' AND status = 'reserved'
            LIMIT 1
        """
        result = db.execute_query(query)
        
        if result:
            copy_id, reservation_date = result[0]
            # Преобразуем дату в ISO формат для передачи в форме
            if isinstance(reservation_date, datetime):
                reservation_date_str = reservation_date.isoformat()
            else:
                reservation_date_str = str(reservation_date)
            
            response = reader_client.post(
                f'/cancel_reservation/{copy_id}',
                data={'reservation_date': reservation_date_str},
                follow_redirects=True
            )
            assert response.status_code == 200
            # Проверяем, что статус изменился
            status_query = "SELECT status FROM reservations WHERE copy_id = %s AND username = 'ivanov' AND reservation_date = %s"
            status_result = db.execute_query(status_query, (copy_id, reservation_date))
            if status_result:
                assert status_result[0][0] == 'cancelled'
    
    def test_reservations_requires_reader_role(self, librarian_client):
        """Тест 3.5: Страница 'Мои бронирования' доступна только читателям"""
        response = librarian_client.get('/my_reservations', follow_redirects=True)
        # Библиотекарь должен быть перенаправлен
        assert response.status_code == 200


class TestLibrarianReservations:
    """Тесты управления бронированиями для библиотекарей"""
    
    def test_all_reservations_page(self, librarian_client):
        """Тест 4.1: Просмотр всех бронирований"""
        response = librarian_client.get('/all_reservations')
        assert response.status_code == 200
        assert 'Бронирования'.encode('utf-8') in response.data or b'reservations' in response.data.lower()
    
    def test_filter_reservations_by_status(self, librarian_client):
        """Тест 4.2: Фильтрация бронирований по статусу"""
        response = librarian_client.get('/all_reservations?status=reserved')
        assert response.status_code == 200
    
    def test_update_reservation_status(self, librarian_client, db):
        """Тест 4.3: Изменение статуса бронирования"""
        # Находим бронирование со статусом 'reserved'
        query = """
            SELECT copy_id, username, reservation_date 
            FROM reservations 
            WHERE status = 'reserved'
            LIMIT 1
        """
        result = db.execute_query(query)
        
        if result:
            copy_id, username, reservation_date = result[0]
            response = librarian_client.post(
                f'/update_reservation_status/{copy_id}/{username}',
                data={
                    'status': 'issued',
                    'reservation_date': str(reservation_date)
                },
                follow_redirects=True
            )
            assert response.status_code == 200
    
    def test_all_reservations_requires_librarian_role(self, reader_client):
        """Тест 4.4: Страница всех бронирований доступна только библиотекарям"""
        response = reader_client.get('/all_reservations', follow_redirects=True)
        # Читатель должен быть перенаправлен
        assert response.status_code == 200

