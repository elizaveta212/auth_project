from aiogram import Bot, F, Dispatcher, Router, types
from aiogram.filters import CommandStart
from flask_jwt_extended import create_access_token
from auth import login_yandex, get_jwt_identity, AUTH_URL, CLIENT_ID, REDIRECT_URL, requests
import pika
import json
import asyncio
from flask import Flask, request, redirect

app = Flask(__name__)
bot = Bot('bot_token')
dp = Dispatcher()
router = Router()
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='registration_topic')
pending_auth = {}

@app.route('/login/yandex')
def login_yandex_route():
    chat_id = request.args.get('chat_id') 
    return redirect(f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URL}&chat_id={chat_id}")
@app.route('/callback/yandex')
def yandex_callback():
    code = request.args.get('code')
    chat_id = request.args.get('chat_id')
    try:
        token = login_yandex(code)
        user_id = get_jwt_identity(token)
        if not user_id:
            return "Ошибка получения идентификатора пользователя.", 400
        pending_auth[chat_id] = user_id
        return "Вы успешно авторизованы!", 200
    except Exception as e:
        print(e)
        return "Ошибка авторизации. Попробуйте еще раз.", 400
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    print("Команда /start получена")
    chat_id = message.chat.id
    auth_url = f'http://localhost:5000/login/yandex?chat_id={chat_id}'
    pending_auth[chat_id] = None
    await message.answer(f"Добро пожаловать! Для авторизации перейдите по ссылке: {auth_url}")
@router.callback_query(F.data.startswith('oauth_'))
async def oauth_handler(query: types.CallbackQuery):
    code = query.data.split('_')[1]
    chat_id = query.message.chat.id 
    try:
        if query.data.startswith('oauth_yandex'):
            yandex_callback_url = f"http://localhost:5000/callback/yandex?code={code}&chat_id={chat_id}"
            response = requests.get(yandex_callback_url)
            if response.status_code == 200:
                await query.answer('Вы успешно авторизованы!')
            else:
                await query.answer('Ошибка авторизации. Попробуйте еще раз.')
        elif query.data.startswith('oauth_vk'):
            token = login_vk(code)
            user_id = get_jwt_identity(token)
            if not user_id:
                await query.answer('Ошибка получения идентификатора пользователя.')
                return
            stored_chat_id = pending_auth.get(chat_id)
            jwt_token = create_access_token(user_id)
            user_data = {
                'username': user_id,
                'chat_id': stored_chat_id 
            }
            channel.basic_publish(exchange='', routing_key='registration_topic', body=json.dumps(user_data))
            await query.answer('Вы успешно авторизованы!')
    except Exception as e:
        await query.answer('Ошибка авторизации. Попробуйте еще раз.')
        print(e)
dp.include_router(router)
async def main():
    await dp.start_polling(bot)
if __name__ == '__main__':  
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
