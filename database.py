import psycopg2
from psycopg2 import sql
from hashlib import sha256
from datetime import datetime

DATABASE_NAME = 'authorization'

def create_connection(dbname):
    return psycopg2.connect(
        dbname=dbname,
        user='postgres',
        password=' ',
        host='localhost',
        port='5432'
    )

def create_database():
    try:
        conn = create_connection('postgres')
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE_NAME)))
            print(f"База данных {DATABASE_NAME} создана успешно.")
    except psycopg2.errors.DuplicateDatabase:
        print(f"База данных {DATABASE_NAME} уже существует.")
    except Exception as e:
        print(f"Ошибка при создании базы данных: {e}")
    finally:
        conn.close()

def create_tables():
    try:
        with create_connection(DATABASE_NAME) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE,
                    password TEXT,
                    role VARCHAR(20),
                    email VARCHAR(100),
                    chat_id BIGINT UNIQUE NOT NULL,
                    registration_date TIMESTAMP,
                    last_activity TIMESTAMP
                )
                ''')
    except Exception as e:
        print(f"Ошибка при создании таблицы: {e}")
def hash_password(password):
    return sha256(password.encode()).hexdigest()
def add_user(username, password, role, email=None, chat_id=None, last_activity=None):
    hashed_password = hash_password(password)
    registration_date = datetime.now()

    try:
        with create_connection(DATABASE_NAME) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                INSERT INTO users (username, password, role, email, chat_id, registration_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''', (username, hashed_password, role, email, chat_id, registration_date))
                conn.commit()  
                print(f"Пользователь {username} добавлен с chat_id {chat_id}.")
    except Exception as e:
        print(f"Произошла ошибка при добавлении пользователя: {e}")
def get_user_by_username(username):
    with create_connection(DATABASE_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
            SELECT * FROM users WHERE username = %s
            ''', (username,))
            user = cursor.fetchone()
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'password': user[2],
                    'role': user[3],
                    'email': user[4],
                    'chat_id': user[5],
                    'registration_date': user[6],
                    'last_activity': user[7]
                }
    return None
def update_user_last_activity(username, last_activity):
    with create_connection(DATABASE_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
            UPDATE users
            SET last_activity = %s
            WHERE username = %s
            ''', (last_activity, username))
create_database()
create_tables()
