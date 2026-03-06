import requests
import time
from flask import Flask
from threading import Thread
import json
import os
import base64

app = Flask('')

@app.route('/')
def home():
    return "✅ Бот с браузером работает!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

# ===== ТВОИ ДАННЫЕ =====
TOKEN = '8466299743:AAGTJxAtDX_O-J4rdzV1VKIcgNLCzQ75jlA'
CHAT_ID = 6951775511
BROWSERLESS_KEY = '2U63bRUrQjg7HY44e0b1bcc2197284a881f89dff0bcf1927a'
SITE_LOGIN = 'mottik'
SITE_PASSWORD = 'motttikrosplat!'
# =======================

# Куки с твоего браузера
COOKIES = [
    {'name': 'KH12OLAy2GRlhjYu', 'value': 'rXLPRgp7mMkvynWq'},
    {'name': 'hruiS5hV67zLL85TFWWP', 'value': 'q23hgOKZvORSOO8t'},
    {'name': '5.253.31.92', 'value': '1772776156'},
]

def send_telegram(text):
    """Отправка текстового сообщения"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, json=data)
        print(f"✅ {text[:30]}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def send_telegram_photo(photo_base64):
    """Отправка фото в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        
        # Декодируем base64 в бинарные данные
        photo_data = base64.b64decode(photo_base64)
        
        # Отправляем как файл
        files = {'photo': ('screenshot.jpg', photo_data, 'image/jpeg')}
        data = {'chat_id': CHAT_ID}
        
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            print("✅ Скриншот отправлен")
        else:
            print(f"❌ Ошибка отправки фото: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка отправки фото: {e}")

def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        r = requests.get(url, params=params)
        return r.json()
    except:
        return {"result": []}

def check_site_with_browser():
    """Запускаем браузер в облаке и делаем скриншот"""
    try:
        # Код для выполнения в браузере
        browser_code = """
        const puppeteer = require('puppeteer-core');
        
        async function main() {
            const browser = await puppeteer.connect({
                browserWSEndpoint: 'wss://chrome.browserless.io?token=' + process.env.KEY
            });
            
            const page = await browser.newPage();
            
            // Устанавливаем куки
            const cookies = JSON.parse(process.env.COOKIES);
            await page.setCookie(...cookies);
            
            console.log('Перехожу на страницу выплат...');
            await page.goto('https://trade.rosplat.cash/dashboard/payoutrequests/pending', {
                waitUntil: 'networkidle2',
                timeout: 30000
            });
            
            // Ждем загрузки
            await page.waitForTimeout(5000);
            
            // Делаем скриншот всей страницы
            const screenshot = await page.screenshot({
                encoding: 'base64',
                fullPage: true
            });
            
            // Отправляем скриншот обратно
            console.log('SCREENSHOT:' + screenshot);
            
            // Проверяем, есть ли капча
            const pageText = await page.content();
            if (pageText.includes('captcha') || pageText.includes('капча')) {
                console.log('CAPTCHA_DETECTED');
            }
            
            // Собираем выплаты если есть
            const payouts = await page.evaluate((minSum, maxSum) => {
                const cards = document.querySelectorAll('div.rounded-\\[15px\\].p-4.space-y-3.mb-4');
                const results = [];
                
                cards.forEach(card => {
                    const text = card.innerText;
                    const idMatch = text.match(/ID[\\s:]+(\\d+)/);
                    const sumMatch = text.match(/Сумма[\\s:]+([\\d\\s]+)₽/);
                    
                    if (idMatch && sumMatch) {
                        const id = idMatch[1];
                        const sum = parseInt(sumMatch[1].replace(/\\s/g, ''));
                        
                        if (sum >= minSum && sum <= maxSum) {
                            results.push({id, sum});
                        }
                    }
                });
                
                return results;
            }, parseInt(process.env.MIN_SUM), parseInt(process.env.MAX_SUM));
            
            console.log('PAYOUTS:' + JSON.stringify(payouts));
            
            await browser.close();
            return {screenshot, payouts, hasCaptcha: pageText.includes('captcha')};
        }
        
        main();
        """
        
        # Отправляем в browserless
        response = requests.post(
            'https://chrome.browserless.io/function',
            json={
                'code': browser_code,
                'context': {
                    'KEY': BROWSERLESS_KEY,
                    'COOKIES': json.dumps(COOKIES),
                    'MIN_SUM': str(settings['min_sum']),
                    'MAX_SUM': str(settings['max_sum'])
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Ищем скриншот в выводе
            output = result.get('stdout', '')
            
            # Парсим вывод
            screenshot_data = None
            payouts_data = []
            
            for line in output.split('\n'):
                if line.startswith('SCREENSHOT:'):
                    screenshot_data = line.replace('SCREENSHOT:', '')
                elif line.startswith('PAYOUTS:'):
                    try:
                        payouts_data = json.loads(line.replace('PAYOUTS:', ''))
                    except:
                        pass
                elif 'CAPTCHA_DETECTED' in line:
                    send_telegram("⚠️ Обнаружена капча на сайте!")
            
            # Отправляем скриншот если есть
            if screenshot_data:
                send_telegram_photo(screenshot_data)
                send_telegram("📸 Скриншот страницы отправлен")
            
            return payouts_data
        else:
            send_telegram(f"❌ Ошибка browserless: {response.status_code}")
            return []
            
    except Exception as e:
        send_telegram(f"❌ Ошибка: {str(e)[:50]}")
        return []

# Настройки
settings = {
    'min_sum': 0,
    'max_sum': 999999,
    'active': True
}

accepted_ids = set()
if os.path.exists('accepted.txt'):
    with open('accepted.txt', 'r') as f:
        accepted_ids = set(f.read().splitlines())

def process_command(text):
    cmd = text.lower().strip()
    
    if cmd == '/start':
        send_telegram("""🤖 Бот с браузером готов!

Команды:
/status - статус
/test - проверить сайт и получить скриншот
/on - включить мониторинг
/off - выключить
/setrange 1000 50000 - диапазон
/history - история
/help - помощь""")
    
    elif cmd == '/status':
        status = "🔴 АКТИВЕН" if settings['active'] else "⚫ ОСТАНОВЛЕН"
        send_telegram(f"Статус: {status}\nДиапазон: {settings['min_sum']} - {settings['max_sum']}₽\nПринято: {len(accepted_ids)}")
    
    elif cmd == '/test':
        send_telegram("🔄 Запускаю браузер и делаю скриншот...")
        result = check_site_with_browser()
        if result:
            send_telegram(f"✅ Найдено выплат: {len(result)}")
        else:
            send_telegram("ℹ️ Выплат не найдено или ошибка")
    
    elif cmd == '/on':
        settings['active'] = True
        send_telegram("✅ Мониторинг ВКЛЮЧЕН")
    
    elif cmd == '/off':
        settings['active'] = False
        send_telegram("⏸️ Мониторинг ВЫКЛЮЧЕН")
    
    elif cmd == '/history':
        if len(accepted_ids) == 0:
            send_telegram("📭 История пуста")
        else:
            last = list(accepted_ids)[-5:]
            send_telegram("📋 Последние:\n" + "\n".join(last))
    
    elif cmd.startswith('/setrange'):
        try:
            parts = cmd.split()
            if len(parts) == 3:
                min_s = int(parts[1])
                max_s = int(parts[2])
                if min_s <= max_s:
                    settings['min_sum'] = min_s
                    settings['max_sum'] = max_s
                    send_telegram(f"✅ Диапазон: {min_s} - {max_s}₽")
        except:
            send_telegram("❌ Ошибка")
    
    elif cmd == '/help':
        send_telegram("/status, /test, /on, /off, /setrange, /history")

send_telegram("🚀 Бот с браузером запущен! Отправь /test для скриншота")

# Основной цикл
last_update_id = 0

while True:
    try:
        # Проверяем команды
        updates = get_updates(last_update_id + 1)
        if updates and "result" in updates:
            for update in updates["result"]:
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    if chat_id == CHAT_ID:
                        process_command(update["message"]["text"])
        
        # Проверяем сайт
        if settings['active']:
            payouts = check_site_with_browser()
            for p in payouts:
                if p['id'] not in accepted_ids:
                    accepted_ids.add(p['id'])
                    send_telegram(f"✅ ПРИНЯТА!\nID: {p['id']}\nСумма: {p['sum']}₽")
                    with open('accepted.txt', 'w') as f:
                        f.write('\n'.join(accepted_ids))
        
        time.sleep(60)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(60)
