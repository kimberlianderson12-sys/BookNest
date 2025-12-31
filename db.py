import psycopg2
from psycopg2 import Error


class Database:
    def __init__(self, host='localhost', database='library_db', user='postgres', password='1234'):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return True
        except Error as e:
            print(f"Ошибка подключения к БД: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=None):
        if not self.conn:
            return None
        try:
            cur = self.conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            result = cur.fetchall()
            cur.close()
            return result
        except Error as e:
            print(f'Ошибка выполнения запроса: {e}')
            return None

    def execute_insert(self, query, params=None):
        if not self.conn:
            return False
        try:
            cur = self.conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            self.conn.commit()
            cur.close()
            return True
        except Error as e:
            self.conn.rollback()
            print(f'Произошла ошибка вставки данных: {e}')
            return False

    def get_id_by_name(self, table, name_column, name_value):
        query = f"SELECT id FROM {table} WHERE {name_column} = %s"
        result = self.execute_query(query, (name_value,))
        return result[0][0] if result else None