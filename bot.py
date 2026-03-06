import requests
import time
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup
import os
import json

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
SITE_PASSWORD = 'motttikrosplat!.'
# =======================

# Настройки по умолчанию
settings = {
    'min_sum': 0,
    'max_sum': 999999,
    'active': True
}

# Загружаем настройки если есть
if os.path.exists('settings.json'):
    with open('settings.json', 'r') as f:
        settings.update(json.load(f))

# Загружаем принятые ID
accepted_ids = set()
if os.path.exists('accepted.txt'):
    with open('accepted.txt', 'r') as f:
        accepted_ids = set(f.read().splitlines())

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, data=data)
        print(f"✅ {text[:30]}...")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def check_updates():
    """Проверяем входящие сообщения (команды)"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        response = requests.get(url).json()
        
        if 'result' in response:
            for update in response['result']:
                if 'message' in update and 'text' in update['message']:
                    chat_id = update['message']['chat']['id']
                    text = update['message']['text']
                    
                    if chat_id == CHAT_ID:
                        process_command(text)
                        
                    # Отмечаем сообщение как прочитанное
                    offset = update['update_id'] + 1
                    requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", 
                               params={"offset": offset})
    except Exception as e:
        print(f"Ошибка проверки команд: {e}")

def process_command(text):
    """Обработка команд"""
    global settings
    
    if text == '/start':
        send_telegram("""🤖 Бот для выплат запущен!

Доступные команды:
/status - текущий статус
/setrange 1000 50000 - установить диапазон сумм
/on - включить мониторинг
/off - выключить мониторинг
/history - история выплат
/help - помощь""")
    
    elif text == '/status':
        status = "🔴" if settings['active'] else "⚫"
        send_telegram(f"""📊 ТЕКУЩИЙ СТАТУС:
{status} Мониторинг: {'АКТИВЕН' if settings['active'] else 'ОСТАНОВЛЕН'}
💰 Диапазон: {settings['min_sum']} - {settings['max_sum']} ₽
📋 Принято выплат: {len(accepted_ids)}""")
    
    elif text == '/on':
        settings['active'] = True
        save_settings()
        send_telegram("✅ Мониторинг ВКЛЮЧЕН")
    
    elif text == '/off':
        settings['active'] = False
        save_settings()
        send_telegram("⏸️ Мониторинг ВЫКЛЮЧЕН")
    
    elif text == '/history':
        if len(accepted_ids) == 0:
            send_telegram("📭 История пуста")
        else:
            last = list(accepted_ids)[-5:]
            msg = "📋 Последние 5 выплат:\n"
            for i, pid in enumerate(reversed(last), 1):
                msg += f"{i}. ID: {pid}\n"
            send_telegram(msg)
    
    elif text.startswith('/setrange'):
        try:
            parts = text.split()
            if len(parts) == 3:
                min_s = int(parts[1])
                max_s = int(parts[2])
                if min_s <= max_s:
                    settings['min_sum'] = min_s
                    settings['max_sum'] = max_s
                    save_settings()
                    send_telegram(f"✅ Диапазон установлен: {min_s} - {max_s} ₽")
                else:
                    send_telegram("❌ Минимум не может быть больше максимума")
            else:
                send_telegram("❌ Используй: /setrange 1000 50000")
        except:
            send_telegram("❌ Ошибка.
                          Используй: /setrange 1000 50000")
    
    elif text == '/help':
        send_telegram("""📚 КОМАНДЫ:
/status - статус
/setrange min max - диапазон сумм
/on - включить
/off - выключить
/history - история
/help - помощь""")
    
    else:
        send_telegram("❌ Неизвестная команда. Напиши /help")

def save_settings():
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

def login_to_site():
    session = requests.Session()
    try:
        # Получаем главную
        session.get('https://trade.rosplat.cash')
        
        # Идем на логин
        login_page = session.get('https://trade.rosplat.cash/login')
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # Ищем CSRF
        csrf = soup.find('input', {'name': '_token'}) or soup.find('input', {'name': 'csrf_token'})
        csrf_token = csrf.get('value') if csrf else ''
        
        # Логинимся
        login_data = {
            'login': SITE_LOGIN,
            'password': SITE_PASSWORD,
            '_token': csrf_token
        }
        
        result = session.post('https://trade.rosplat.cash/login', data=login_data)
        
        # Переходим на выплаты
        session.get('https://trade.rosplat.cash/dashboard/payoutrequests/pending')
        
        print("✅ Вошли на сайт")
        return session
    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        return None

def check_payouts(session):
    """Проверка выплат на сайте"""
    try:
        response = session.get('https://trade.rosplat.cash/dashboard/payoutrequests/pending')
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем карточки
        cards = soup.find_all('div', class_='rounded-[15px]')
        found = []
        
        for card in cards:
            try:
                text = card.text
                
                # Ищем ID
                import re
                id_match = re.search(r'ID\s*(\d+)', text)
                if not id_match:
                    continue
                payout_id = id_match.group(1)
                
                # Ищем сумму
                sum_match = re.search(r'Сумма\s*([\d\s]+)₽', text)
                if not sum_match:
                    continue
                sum_str = sum_match.group(1).replace(' ', '')
                payout_sum = int(sum_str)
                
                # Проверяем диапазон
                if settings['min_sum'] <= payout_sum <= settings['max_sum']:
                    found.append({
                        'id': payout_id,
                        'sum': payout_sum
                    })
                    
            except Exception as e:
                continue
                
        return found
        
    except Exception as e:
        print(f"Ошибка проверки: {e}")
        return []

def accept_payout(session, payout_id):
    """Принять выплату"""
    try:
        url = f"https://trade.rosplat.cash/dashboard/payoutrequests/accept/{payout_id}"
        result = session.post(url)
        return result.status_code == 200
    except:
        return False

# Запускаем
send_telegram("🚀 Бот запущен! Напиши /help для списка команд")

# Основной цикл
session = None
last_check = 0

while True:
    try:
        # Проверяем команды каждые 2 секунды
        check_updates()
        
        # Если мониторинг выключен - просто ждем
        if not settings['active']:
            time.sleep(2)
            continue
        
        # Обновляем сессию раз в 5 минут
        if not session or time.time() - last_check > 300:
            session = login_to_site()
            last_check = time.time()
        
        if session:
            # Проверяем выплаты
            payouts = check_payouts(session)
            
            for payout in payouts:
                if payout['id'] not in accepted_ids:
                    # Пробуем принять
                    if accept_payout(session, payout['id']):
                        accepted_ids.add(payout['id'])
                        
                        # Сохраняем
                        with open('accepted.txt', 'w') as f:
                            f.write('\n'.join(accepted_ids))
                        
                        # Уведомление
                        msg = f"""✅ ПРИНЯТА ВЫПЛАТА!
ID: {payout['id']}
Сумма: {payout['sum']} ₽"""
                        send_telegram(msg)
                        
                        time.sleep(1)  # Пауза между кликами
        
        time.sleep(10)  # Проверка каждые 10 секунд
        
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(30)
