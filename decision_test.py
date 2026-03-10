import urllib.request
import urllib.parse
import urllib.error
import json
import time
import random

BASE_URL = "http://localhost:8000"

def print_step(msg):
    print(f"\n{'='*60}")
    print(f"🔄 ШАГ: {msg}")
    print(f"{'='*60}")
    time.sleep(1)

def print_success(msg):
    print(f"✅ УСПЕХ: {msg}")

def print_info(msg):
    print(f"ℹ️ ИНФО: {msg}")

def print_error(msg):
    print(f"❌ ОШИБКА: {msg}")

def make_request(method, url, data=None, headers=None, is_form=False):
    if headers is None: headers = {}
    if data is not None:
        if is_form:
            req_data = urllib.parse.urlencode(data).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            req_data = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
    else: req_data = None

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

def run_decision_test():
    print("\n🚀 НАЧИНАЕМ ТЕСТ МЕХАНИЗМА ПРИНЯТИЯ РЕШЕНИЙ (DECISION ENGINE) 🚀\n")
    
    # Регистрация и получение токена
    rand_id = random.randint(1000, 9999)
    username = f"decision_tester_{rand_id}"
    password = "123"
    
    make_request("POST", "/auth/register", data={"username": username, "email": f"{username}@example.com", "password": password})
    _, auth_resp = make_request("POST", "/auth/login", data={"username": username, "password": password}, is_form=True)
    
    access_token = auth_resp['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    print_success("Авторизация прошла успешно.")

    # 1. Создаем Решение напрямую с критериями и вариантами (Batch Creation)
    print_step("Создаем Решение (Decision) + Критерии + Варианты в одном запросе")
    decision_payload = {
        "title": "Какой язык программирования выучить следующим?",
        "description": "Нужно выбрать между тремя топовыми языками.",
        "criteria": [
            {"name": "Зарплата", "weight": 9},
            {"name": "Сложность освоения", "weight": 6},
            {"name": "Востребованность ИИ", "weight": 10}
        ],
        "options": [
            {"name": "Python"},
            {"name": "Go"},
            {"name": "Rust"}
        ]
    }
    
    status, response = make_request("POST", "/decisions/", data=decision_payload, headers=headers)
    if status != 201:
        print_error(f"Не удалось создать Решение: {response}")
        return
        
    decision_id = response['id']
    criteria = response['criteria']
    options = response['options']
    
    print_success(f"Решение создано! ID: {decision_id}. Вытянуто критериев: {len(criteria)}, опций: {len(options)}")

    # 2. Выставление оценок
    print_step("Выставляем оценки вариантам по 10-балльной шкале...")
    
    # Для упрощения сопоставим ID по именам
    crit_map = {c['name']: c['id'] for c in criteria}
    opt_map = {o['name']: o['id'] for o in options}
    
    # Оценки: [Опция, Критерий, Балл (1-10)]
    scores_to_submit = [
        # Python
        ("Python", "Зарплата", 8),
        ("Python", "Сложность освоения", 10), # Легкий (10)
        ("Python", "Востребованность ИИ", 10),
        # Go
        ("Go", "Зарплата", 9),
        ("Go", "Сложность освоения", 7),
        ("Go", "Востребованность ИИ", 5),
        # Rust
        ("Rust", "Зарплата", 10),
        ("Rust", "Сложность освоения", 3), # Очень сложно (3)
        ("Rust", "Востребованность ИИ", 6)
    ]
    
    for opt_name, crit_name, score_val in scores_to_submit:
        status, _ = make_request("POST", f"/decisions/{decision_id}/scores", data={
            "score": score_val,
            "option_id": opt_map[opt_name],
            "criterion_id": crit_map[crit_name]
        }, headers=headers)
        if status == 201:
            print_info(f"✅ Оценка {score_val}/10 для '{opt_name}' по критерию '{crit_name}' выставлена.")
        else:
            print_error(f"Ошибка выставления оценки: {status}")

    # 3. Делаем запрос к Results (МАГИЯ)
    print_step("Запрашиваем результаты (Results)! Кто победит?")
    status, response = make_request("GET", f"/decisions/{decision_id}/results", headers=headers)
    
    if status == 200:
        print_success("Результаты рассчитаны!")
        winner = response['winner']
        print(f"\n🏆 ПОБЕДИТЕЛЬ: {winner['option_name']} (Total Score: {winner['total_score']})")
        
        print("\n📊 ПОЛНЫЙ РЕЙТИНГ:")
        for idx, rank in enumerate(response['ranking'], 1):
            print(f"  {idx}. {rank['option_name']} - {rank['total_score']} баллов")
            print(f"     Разбивка: {rank['breakdown']}")
        
    else:
        print_error(f"Ошибка получения результатов (Код {status}): {response}")

    print("\n🎉 ТЕСТ МЕХАНИЗМА ПРИНЯТИЯ РЕШЕНИЙ УСПЕШНО ЗАВЕРШЕН! 🎉\n")


if __name__ == "__main__":
    run_decision_test()
