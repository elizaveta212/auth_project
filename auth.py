from flask import Flask, request, jsonify, redirect, make_response
import requests
import datetime 
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from database import add_user, get_user_by_username, update_user_last_activity 

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = ' '  
app.config['JWT_TOKEN_LOCATION'] = ['cookies']  
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token' 
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  
jwt = JWTManager(app)
CLIENT_ID = ' '
CLIENT_SECRET = ' '
REDIRECT_URL = 'http://localhost:5000/callback'
TOKEN_URL = 'https://oauth.yandex.ru/token'
AUTH_URL = 'https://oauth.yandex.ru/authorize'

@app.route('/')
def home_page():
    return "Добро пожаловать на главную страницу!"
@app.route('/login/yandex')
def login_yandex():
    chat_id = request.args.get('chat_id') 
    return redirect(f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URL}&chat_id={chat_id}")
@app.route('/callback')
def callback():
    code = request.args.get('code')
    chat_id = request.args.get('chat_id') 
    if not code:
        return jsonify({'error': 'Missing authorization code'}), 400
    response = requests.post(TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URL
    })
    if response.status_code != 200:
        return jsonify({"msg": "Invalid token"}), 401

    token_info = response.json()
    access_token = token_info.get('access_token')
    user_info_response = requests.get("https://login.yandex.ru/info", headers={
        'Authorization': f'OAuth {access_token}'
    })
    if user_info_response.status_code != 200:
        return jsonify({'error': 'Failed to retrieve user info'}), 400
    user_info = user_info_response.json()
    username = user_info.get('login')
    email = user_info.get('default_email', 'default_email@example.com') 
    role = user_info.get('role', 'user')
    last_activity = user_info.get('last_activity')
    if not username:
        return jsonify({'error': 'Missing username in user info'}), 400
    user = get_user_by_username(username)
    if not user:
        add_user(username, 'default_password', role, email, chat_id, last_activity) 
    access_token = create_access_token(identity=username)
    response = make_response(redirect('/user_info'))
    response.set_cookie('access_token', access_token)
    current_time = datetime.datetime.utcnow()  
    update_user_last_activity(username, current_time)  
    return response
@app.route('/user_info')
@jwt_required()
def user_info():
    try:
        username = get_jwt_identity()
        if not username:
            return jsonify({'error': 'User not found in token'}), 401
        user_details = get_user_details(username)
        return f"Информация о пользователе: {user_details}"
    except Exception as e:
        return jsonify({'error': str(e)}), 500
def get_user_details(username):
    user = get_user_by_username(username) 
    if user:
        user_data = {
            'username': user['username'],
            'email': user['email'],  
            'role': user['role'],
            'last_activity': user['last_activity'].isoformat() if user['last_activity'] else None,
            'chat_id': user['chat_id']
        }
        return user_data
    else:
        return {'error': 'User not found'}

@app.route('/login/vk', methods=['POST'])
def login_vk():
    token = request.json.get('token')
    vk_url = 'https://api.vk.com/method/users.get'
    app_id = 'ваш_vk_id'  
    version = '5.126'

    response = requests.get(f"{vk_url}?access_token={token}&v={version}")
    
    if response.status_code != 200 or 'error' in response.json():
        return jsonify({"msg": "Invalid token"}), 401

    user_info = response.json()
    if 'response' in user_info and len(user_info['response']) > 0:
        username = user_info['response'][0].get('first_name')
    else:
        return jsonify({"msg": "Could not retrieve user info"}), 400

    user = get_user_by_username(username)
    
    if not user:
        add_user(username, 'default_password', 'user', 'user@example.com')  

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Авторизация</title>
</head>
<body>
    <h1>Авторизация</h1>
    <a href="/login/yandex">Войти через Яндекс</a>
    <br>
    <a href="/login/vk">Войти через ВК</a>
</body>
</html>"""

@app.route('/login.html')
def login_page():
    return HTML_TEMPLATE

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
