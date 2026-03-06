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
/help - помощь""")
    
    elif cmd == '/status':
        status = "🔴 АКТИВЕН" if settings['active'] else "⚫ ОСТАНОВЛЕН"
        msg = f"""📊 <b>ТЕКУЩИЙ СТАТУС</b>
        
Статус: {status}
💰 Диапазон: {settings['min_sum']} - {settings['max_sum']} ₽
📋 Принято выплат: {len(accepted_ids)}
👤 Пользователь: {SITE_LOGIN}"""
        send_telegram(msg)
    
    elif cmd == '/on':
        settings['active'] = True
        save_settings()
        send_telegram("✅ <b>Мониторинг ВКЛЮЧЕН</b>\nБот начинает проверку сайта...")
    
    elif cmd == '/off':
        settings['active'] = False
        save_settings()
        send_telegram("⏸️ <b>Мониторинг ВЫКЛЮЧЕН</b>")
    
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
/help - это сообщение""")
    
    else:
        send_telegram(f"❌ Неизвестная команда: {text}\nНапиши /help")

def check_site():
    """Проверка сайта (заглушка для теста)"""
    # Здесь будет реальный код проверки
    return []

# Приветствие при запуске
send_telegram("🚀 <b>Бот перезапущен!</b>\nНапиши /start для начала работы")

# Основной цикл
last_update_id = 0
last_site_check = 0

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
            if current_time - last_site_check > 60:  # Раз в минуту
                payouts = check_site()
                if payouts:
                    for p in payouts:
                        if p['id'] not in accepted_ids:
                            msg = f"""✅ <b>НАЙДЕНА ВЫПЛАТА!</b>
                            
ID: {p['id']}
Сумма: {p['sum']} ₽"""
                            send_telegram(msg)
                            accepted_ids.add(p['id'])
                            
                            # Сохраняем
                            with open('accepted.txt', 'w') as f:
                                f.write('\n'.join(accepted_ids))
                
                last_site_check = current_time
                print("🔄 Проверка сайта выполнена")
        
        time.sleep(1)
        
    except Exception as e:
        print(f"❌ Ошибка в цикле: {e}")
        time.sleep(5)
        
