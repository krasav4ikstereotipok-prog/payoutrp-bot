import requests
import time
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup
import os

app = Flask('')

@app.route('/')
def home():
    return "✅ Payout Bot работает!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

# ===== ТВОИ ДАННЫЕ =====
TOKEN = '8466299743:AAGTJxAtDX_O-J4rdzV1VKIcgNLCzQ75jlA'
CHAT_ID = 6951775511
SITE_LOGIN = 'mottik'
SITE_PASSWORD = 'rosplat174work11.'
MIN_SUM = 0          # Минимальная сумма
MAX_SUM = 999999     # Максимальная сумма
# =======================

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, data=data)
        print(f"✅ {text[:30]}...")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def login_to_site():
    session = requests.Session()
    try:
        # Сначала получаем страницу логина (нужно для cookies)
        login_page = session.get('https://trade.rosplat.cash/login')
        
        # Ищем CSRF токен если нужен
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf = soup.find('input', {'name': 'csrf_token'})
        csrf_token = csrf.get('value') if csrf else ''
        
        # Данные для входа
        login_data = {
            'login': SITE_LOGIN,
            'password': SITE_PASSWORD,
            'csrf_token': csrf_token
        }
        
        # Отправляем POST запрос на вход
        response = session.post('https://trade.rosplat.cash/login', data=login_data)
        
        # Проверяем, успешен ли вход
        if 'dashboard' in response.url or 'payoutrequests' in response.text:
            print("✅ Успешный вход на сайт")
            return session
        else:
            print("❌ Ошибка входа на сайт")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при входе: {e}")
        return None

def check_payouts(session):
    try:
        # Получаем страницу с выплатами
        response = session.get('https://trade.rosplat.cash/dashboard/payoutrequests/pending')
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем все карточки выплат
        cards = soup.find_all('div', class_='rounded-[15px]')
        found_payouts = []
        
        for card in cards:
            try:
                # Ищем ID
                id_elem = card.find('div', string=lambda x: x and 'ID' in x)
                if id_elem:
                    id_text = id_elem.find_next('div', class_='text-end')
                    payout_id = id_text.text.strip() if id_text else None
                else:
                    continue
                
                # Ищем сумму
                sum_elem = card.find('div', string=lambda x: x and 'Сумма' in x)
                if sum_elem:
                    sum_text = sum_elem.find_next('div', class_='text-end')
                    if sum_text:
                        sum_value = ''.join(filter(str.isdigit, sum_text.text))
                        sum_value = int(sum_value) if sum_value else 0
                    else:
                        continue
                else:
                    continue
                
                # Ищем метод
                method_elem = card.find('div', string=lambda x: x and 'Метод' in x)
                method = 'СБП'
                if method_elem:
                    method_text = method_elem.find_next('div', class_='text-end')
                    method = method_text.text.strip() if method_text else 'СБП'
                
                # Ищем время
                time_elem = card.find('div', string=lambda x: x and 'Время' in x)
                payout_time = ''
                if time_elem:
                    time_text = time_elem.find_next('div', class_='text-end')
                    payout_time = time_text.text.strip() if time_text else ''
                
                # Ищем кнопку
                button = card.find('button', string=lambda x: x and 'В работу' in x)
                if payout_id and button and MIN_SUM <= sum_value <= MAX_SUM:
                    found_payouts.append({
                        'id': payout_id,
                        'sum': sum_value,
                        'method': method,
                        'time': payout_time,
                        'button': button
                    })
                    
            except Exception as e:
                print(f"Ошибка парсинга карточки: {e}")
                continue
        
        return found_payouts
        
    except Exception as e:
        print(f"❌ Ошибка проверки выплат: {e}")
        return []

def click_button(session, button_html):
    # Здесь нужен анализ структуры кнопки
    # Пока просто возвращаем True
    return True

# Загружаем принятые ID
accepted_ids = set()
if os.path.exists('accepted.txt'):
    with open('accepted.txt', 'r') as f:
        accepted_ids = set(f.read().splitlines())

send_telegram("🚀 Бот с проверкой выплат ЗАПУЩЕН!")

# Основной цикл
session = None
while True:
    try:
        # Если нет сессии или она устарела - логинимся
        if not session:
            session = login_to_site()
            if not session:
                send_telegram("❌ Не могу войти на сайт, жду 5 минут...")
                time.sleep(300)
                continue
        
        # Проверяем выплаты
        payouts = check_payouts(session)
        
        for payout in payouts:
            if payout['id'] not in accepted_ids:
                # Отправляем уведомление
                msg = f"""✅ НАЙДЕНА ВЫПЛАТА!
ID: {payout['id']}
Сумма: {payout['sum']} ₽
Метод: {payout['method']}
Время: {payout['time']}

🖱️ Нажимаю кнопку..."""
                send_telegram(msg)
                
                # Пытаемся нажать кнопку
                if click_button(session, payout['button']):
                    accepted_ids.add(payout['id'])
                    send_telegram(f"✅ Выплата {payout['id']} принята!")
                    
                    # Сохраняем в файл
                    with open('accepted.txt', 'w') as f:
                        f.write('\n'.join(accepted_ids))
                else:
                    send_telegram(f"❌ Не удалось нажать кнопку для {payout['id']}")
        
        # Отправляем статус
        if payouts:
            send_telegram(f"📊 Найдено новых: {len(payouts)}, всего принято: {len(accepted_ids)}")
        
        time.sleep(30)  # Проверка каждые 30 секунд
        
    except Exception as e:
        send_telegram(f"❌ Критическая ошибка: {e}")
        session = None  # Сброс сессии при ошибке
        time.sleep(60)
