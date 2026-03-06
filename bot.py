import requests
import time
from flask import Flask
from threading import Thread
import json
import os
import re

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
SITE_PASSWORD = 'motttikrosplat!'
SITE_URL = 'https://trade.rosplat.cash'
# =======================

# Настройки
settings = {
    'min_sum': 0,
    'max_sum': 999999,
    'active': True
}

# Загружаем настройки
if os.path.exists('settings.json'):
    with open('settings.json', 'r') as f:
        settings.update(json.load(f))

# Загружаем принятые ID
accepted_ids = set()
if os.path.exists('accepted.txt'):
    with open('accepted.txt', 'r') as f:
        accepted_ids = set(f.read().splitlines())

def send_telegram(text):
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, json=data)
        print(f"✅ {text[:50]}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

def get_updates(offset=None):
    """Получение новых сообщений"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        response = requests.get(url, params=params)
        return response.json()
    except:
        return {"result": []}

def save_settings():
    """Сохранение настроек"""
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

def login_to_site():
    """Вход на сайт"""
    session = requests.Session()
    try:
        # Добавляем заголовки как у браузера
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': SITE_URL,
            'Referer': f'{SITE_URL}/login',
        })
        
        # Получаем страницу логина для CSRF токена
        login_page = session.get(f'{SITE_URL}/login')
        
        # Ищем CSRF токен
        csrf_match = re.search(r'name="_token".*?value="([^"]+)"', login_page.text)
        csrf_token = csrf_match.group(1) if csrf_match else ''
        
        # Данные для входа
        login_data = {
            'login': SITE_LOGIN,
            'password': SITE_PASSWORD,
            '_token': csrf_token,
            'remember': 'on'
        }
        
        # Отправляем POST запрос на вход
        result = session.post(f'{SITE_URL}/login', data=login_data, allow_redirects=True)
        
        # Проверяем успешность входа
        if 'dashboard' in result.url or 'payoutrequests' in result.text or 'Выйти' in result.text:
            print("✅ Успешный вход на сайт")
            return session
        else:
            print("❌ Ошибка входа на сайт")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при входе: {e}")
        return None

def check_payouts(session):
    """Проверка выплат на сайте"""
    try:
        # Переходим на страницу выплат
        response = session.get(f'{SITE_URL}/dashboard/payoutrequests/pending')
        
        # Ищем все карточки выплат
        payouts = []
        
        # Ищем ID выплат
        id_matches = re.findall(r'ID[:\s]*(\d+)', response.text)
        sum_matches = re.findall(r'Сумма[:\s]*([\d\s]+)₽', response.text)
        
        for i, payout_id in enumerate(id_matches):
            if i < len(sum_matches):
                # Очищаем сумму от пробелов
                sum_str = sum_matches[i].replace(' ', '')
                try:
                    payout_sum = int(sum_str)
                    # Проверяем диапазон
                    if settings['min_sum'] <= payout_sum <= settings['max_sum']:
                        payouts.append({
                            'id': payout_id,
                            'sum': payout_sum
                        })
                except:
                    continue
        
        return payouts
        
    except Exception as e:
        print(f"❌ Ошибка проверки выплат: {e}")
        return []

def accept_payout(session, payout_id):
    """Принятие выплаты"""
    try:
        # Пробуем разные варианты URL для принятия
        urls = [
            f'{SITE_URL}/dashboard/payoutrequests/accept/{payout_id}',
            f'{SITE_URL}/dashboard/payoutrequests/{payout_id}/accept',
            f'{SITE_URL}/api/payoutrequests/{payout_id}/accept'
        ]
        
        for url in urls:
            result = session.post(url)
            if result.status_code == 200:
                print(f"✅ Выплата {payout_id} принята")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Ошибка принятия: {e}")
        return False

def process_command(text):
    """Обработка команд"""
    global settings, accepted_ids
    
    cmd = text.lower().strip()
    
    if cmd == '/start':
        send_telegram("""🤖 <b>Бот для выплат запущен!</b>

Доступные команды:
/status - текущий статус
/on - включить мониторинг
/off - выключить мониторинг
/setrange 1000 50000 - установить диапазон сумм
/history - история выплат
/clear - очистить историю
/test - проверить вход на сайт
/help - помощь""")
    
    elif cmd == '/status':
        status = "🔴 АКТИВЕН" if settings['active'] else "⚫ ОСТАНОВЛЕН"
        msg = f"""📊 <b>ТЕКУЩИЙ СТАТУС</b>
        
Статус: {status}
💰 Диапазон: {settings['min_sum']} - {settings['max_sum']} ₽
📋 Принято выплат: {len(accepted_ids)}
👤 Пользователь: {SITE_LOGIN}
🌐 Сайт: {SITE_URL}"""
        send_telegram(msg)
    
    elif cmd == '/on':
        settings['active'] = True
        save_settings()
        send_telegram("✅ <b>Мониторинг ВКЛЮЧЕН</b>\nБот начинает проверку сайта...")
    
    elif cmd == '/off':
        settings['active'] = False
        save_settings()
        send_telegram("⏸️ <b>Мониторинг ВЫКЛЮЧЕН</b>")
    
    elif cmd == '/test':
        send_telegram("🔄 Проверяю вход на сайт...")
        session = login_to_site()
        if session:
            send_telegram("✅ Вход на сайт успешен!")
        else:
            send_telegram("❌ Ошибка входа на сайт")
    
    elif cmd == '/history':
        if len(accepted_ids) == 0:
            send_telegram("📭 История выплат пуста")
        else:
            last = list(accepted_ids)[-10:]
            msg = "📋 <b>Последние выплаты:</b>\n"
            for i, pid in enumerate(reversed(last), 1):
                msg += f"{i}. ID: {pid}\n"
            send_telegram(msg)
    
    elif cmd == '/clear':
        accepted_ids.clear()
        with open('accepted.txt', 'w') as f:
            f.write('')
        send_telegram("🗑️ История выплат очищена")
    
    elif cmd.startswith('/setrange'):
        try:
            parts = cmd.split()
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
            send_telegram("❌ Ошибка. Используй: /setrange 1000 50000")
    
    elif cmd == '/help':
        send_telegram("""📚 <b>СПИСОК КОМАНД:</b>
        
/start - приветствие
/status - статус бота
/on - включить мониторинг
/off - выключить мониторинг
/setrange min max - диапазон сумм
/history - история выплат
/clear - очистить историю
/test - проверить вход на сайт
/help - это сообщение""")
    
    else:
        send_telegram(f"❌ Неизвестная команда: {text}\nНапиши /help")

# Приветствие при запуске
send_telegram("🚀 <b>Бот перезапущен!</b>\nНапиши /start для начала работы")

# Основной цикл
last_update_id = 0
last_site_check = 0
session = None

while True:
    try:
        # Проверяем новые команды
        updates = get_updates(last_update_id + 1)
        
        if "result" in updates and updates["result"]:
            for update in updates["result"]:
                last_update_id = update["update_id"]
                
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"]
                    chat_id = update["message"]["chat"]["id"]
                    
                    print(f"📩 Получено: {text} от {chat_id}")
                    
                    if chat_id == CHAT_ID:
                        process_command(text)
        
        # Если мониторинг включен - проверяем сайт
        if settings['active']:
            current_time = time.time()
            
            # Обновляем сессию раз в 10 минут
            if not session or current_time - last_site_check > 600:
                session = login_to_site()
            
            if session:
                # Проверяем выплаты раз в 30 секунд
                if current_time - last_site_check > 30:
                    payouts = check_payouts(session)
                    
                    for payout in payouts:
                        if payout['id'] not in accepted_ids:
                            # Пробуем принять выплату
                            if accept_payout(session, payout['id']):
                                msg = f"""✅ <b>ВЫПЛАТА ПРИНЯТА!</b>
                                
ID: {payout['id']}
Сумма: {payout['sum']} ₽
Статус: Успешно"""
                                send_telegram(msg)
                                accepted_ids.add(payout['id'])
                                
                                # Сохраняем
                                with open('accepted.txt', 'w') as f:
                                    f.write('\n'.join(accepted_ids))
                    
                    last_site_check = current_time
                    print(f"🔄 Проверка сайта: найдено {len(payouts)} выплат")
        
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ Ошибка в цикле: {e}")
        time.sleep(5)
