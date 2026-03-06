import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "✅ Payout Bot работает!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

TOKEN = '8466299743:AAGTJxAtDX_O-J4rdzV1VKIcgNLCzQ75jlA'
CHAT_ID = 6951775511

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, data=data)
        print(f"✅ Отправлено: {text[:30]}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

send_telegram("🚀 Бот запускается на Render!")

accepted_ids = set()

while True:
    try:
        send_telegram(f"💓 Бот работает. Принято: {len(accepted_ids)}")
        time.sleep(60)
    except:
        time.sleep(10)
