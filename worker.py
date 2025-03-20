import pika
import requests
import json
import psycopg2
import os
import logging
import sys

logging.basicConfig(level=logging.INFO)
pending_auth = {}

def get_chat_id(username):
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            dbname='authorization', 
            user='postgres',     
            password=' ',  
            host='localhost',
            port='5432'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users WHERE username = %s", (username,))
        chat_id = cursor.fetchone()
        return chat_id[0] if chat_id else None
    except Exception as e:
        logging.error(f"Ошибка при подключении к БД: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
def add_user_to_db(username, chat_id):
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            dbname='authorization', 
            user='postgres',     
            password=' ',  
            host='localhost',
            port='5432'
        )
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, chat_id) VALUES (%s, %s)", (username, chat_id))
        conn.commit()
        logging.info(f"Пользователь {username} добавлен в БД с chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя {username} в БД: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
def callback(ch, method, properties, body):
    user_data = json.loads(body)   
    username = user_data.get('username')
    chat_id = user_data.get('chat_id')  
    pending_auth[chat_id] = chat_id
    logging.info(f"Обработка сообщения для пользователя {username} с chat_id {chat_id}")
    if chat_id is not None:
        existing_chat_id = get_chat_id(username)      
        if existing_chat_id is None:
            add_user_to_db(username, chat_id)  
        else:
            logging.info(f"Пользователь {username} уже существует с chat_id {existing_chat_id}")
        token = os.getenv(' ')
        if not token:
            logging.error("Токен Telegram не установлен в переменной окружения.")
            return 
        stored_chat_id = pending_auth.get(chat_id)
        if stored_chat_id is None:
            logging.warning(f"Чат ID не найден для пользователя {username} в pending_auth.")
            return
        try:
            response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={
                "chat_id": stored_chat_id,
                "text": f"Привет, {username}! Добро пожаловать в приложение!"
            })  
            if response.ok:
                logging.info(f"Сообщение отправлено пользователю {username}")
            else:
                logging.error(f"Ошибка при отправке сообщения пользователю {username}: {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при выполнении запроса к Telegram API: {e}")
        pending_auth.pop(chat_id, None)
    else:
        logging.warning(f"Чат ID не найден для пользователя {username}")
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
except Exception as e:
    logging.critical(f"Не удалось подключиться к RabbitMQ: {e}")
    sys.exit(1)
try:
    channel.queue_declare(queue='registration_topic')
    logging.info("Очередь registration_topic успешно объявлена.")
except Exception as e:
    logging.error(f"Ошибка при объявлении очереди: {e}")
    sys.exit(1)
try:
    channel.basic_consume(queue='registration_topic', on_message_callback=callback, auto_ack=True)
    logging.info(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()
except KeyboardInterrupt:
    logging.info('Остановка работы...')
    channel.stop_consuming()
except Exception as e:
    logging.error(f"Ошибка при начале потребления сообщений: {e}")
finally:
    connection.close()
    logging.info('Соединение с RabbitMQ закрыто.')
