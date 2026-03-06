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
# =======================

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, data=data)
        print(f"✅ {text[:30]}...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def check_site():
    try:
        # Здесь будет код проверки сайта
        # Пока просто заглушка
        return []
    except:
        return []

# Загружаем принятые ID
accepted_ids = set()
if os.path.exists('accepted.txt'):
    with open('accepted.txt', 'r') as f:
        accepted_ids = set(f.read().splitlines())

send_telegram("🚀 Бот с проверкой выплат запущен!")

while True:
    try:
        # Проверяем сайт
        new_payouts = check_site()
        
        for payout in new_payouts:
            if payout['id'] not in accepted_ids:
                accepted_ids.add(payout['id'])
                msg = f"✅ НАЙДЕНА ВЫПЛАТА!\nID: {payout['id']}\nСумма: {payout['sum']} ₽"
                send_telegram(msg)
                
                # Сохраняем ID
                with open('accepted.txt', 'w') as f:
                    f.write('\n'.join(accepted_ids))
        
        send_telegram(f"📊 Проверка. Принято: {len(accepted_ids)}")
        time.sleep(30)  # Каждые 30 секунд
        
    except Exception as e:
        send_telegram(f"❌ Ошибка: {e}")
        time.sleep(10)
