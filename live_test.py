import urllib.request
import urllib.parse
import urllib.error
import json
import time
import random

BASE_URL = "http://localhost:8000"

def print_step(msg):
    print(f"\n{'='*50}")
    print(f"🔄 ШАГ: {msg}")
    print(f"{'='*50}")
    time.sleep(1) # небольшая пауза для эффекта "прямого эфира"

def print_success(msg):
    print(f"✅ УСПЕХ: {msg}")

def print_info(msg):
    print(f"ℹ️ ИНФО: {msg}")

def print_error(msg):
    print(f"❌ ОШИБКА: {msg}")

def make_request(method, url, data=None, headers=None, is_form=False):
    if headers is None:
        headers = {}
    
    if data is not None:
        if is_form:
            # Для OAuth2 формы логина (application/x-www-form-urlencoded)
            req_data = urllib.parse.urlencode(data).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            # Для JSON
            req_data = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
    else:
        req_data = None

    req = urllib.request.Request(f"{BASE_URL}{url}", data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            return status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return e.code, json.loads(body) if body else str(e)
    except Exception as e:
        return 500, str(e)

def run_live_test():
    print("\n🚀 НАЧИНАЕМ АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ API 'ВТОРОЙ МОЗГ' 🚀")
    
    # 1. Регистрация
    rand_id = random.randint(1000, 9999)
    username = f"live_tester_{rand_id}"
    email = f"tester_{rand_id}@example.com"
    password = "super_password"
    
    print_step(f"Регистрируем нового пользователя (username: {username})")
    status, response = make_request("POST", "/auth/register", data={
        "username": username,
        "email": email,
        "password": password
    })
    
    if status in [200, 201]:
        print_success(f"Пользователь создан в БД! ID в базе: {response['id']}")
    else:
        print_error(f"Регистрация не удалась (Код {status}): {response}")
        return

    # 2. Логин
    print_step("Авторизация (Получаем ключи доступа / Токены)...")
    status, response = make_request("POST", "/auth/login", data={
        "username": username,
        "password": password
    }, is_form=True)
    
    if status == 200:
        access_token = response['access_token']
        print_success(f"Токен успешно получен! (длина: {len(access_token)} символов)")
        print_info(f"Начало токена: {access_token[:20]}...")
    else:
        print_error(f"Логин не удался (Код {status}): {response}")
        return

    # 3. Создание заметки
    print_step("Создаем новую мысль (Brain Entry)...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    note_data = {
        "title": "Мысль из авто-теста",
        "content": "Этот текст написан роботом, который проверяет API на лету. Всё работает шикарно!",
        "category": "Testing",
        "summary": "Проверка создания заметок"
    }
    
    status, response = make_request("POST", "/brain/", data=note_data, headers=headers)
    
    if status == 201:
        print_success(f"Заметка сохранена! Присвоен ID: {response['id']}")
        print_info(f"Заголовок: {response['title']}")
        print_info(f"Контент: {response['content']}")
    else:
        print_error(f"Создание заметки упало (Код {status}): {response}")
        return

    # 4. Получение списка заметок
    print_step("Запрашиваем список всех заметок пользователя...")
    status, response = make_request("GET", "/brain/", headers=headers)
    
    if status == 200:
        print_success(f"Список получен! Найдено заметок: {len(response)}")
        print_info(f"Первая заметка в списке: '{response[0]['title']}'")
    else:
        print_error(f"Получение списка не удалось (Код {status}): {response}")
        return

    print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! API РАБОТАЕТ ИДЕАЛЬНО! 🎉\n")

if __name__ == "__main__":
    run_live_test()
