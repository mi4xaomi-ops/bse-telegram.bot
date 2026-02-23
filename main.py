from fastapi import FastAPI
import requests
import xml.etree.ElementTree as ET
import os
import hashlib

app = FastAPI()

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

POSTED = set()

def generate_id(title, link):
    return hashlib.md5((title + link).encode()).hexdigest()

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/run")
def run():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(RSS_URL, headers=headers, timeout=10)

        if response.status_code != 200:
            return {"error": f"RSS fetch failed: {response.status_code}"}

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            return {"error": "Invalid XML received from BSE"}

        channel = root.find("channel")
        if channel is None:
            return {"error": "Invalid RSS structure"}

        items = channel.findall("item")

        for item in items:
            title = item.findtext("title", "")
            link = item.findtext("link", "")

            if not title or not link:
                continue

            uid = generate_id(title, link)
            if uid in POSTED:
                continue

            message = f"📢 <b>{title}</b>\n\n🔗 {link}"

            telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

            tg_response = requests.post(
                telegram_url,
                json={
                    "chat_id": CHANNEL_ID,
                    "text": message,
                    "parse_mode": "HTML"
                }
            )

            if tg_response.status_code != 200:
                return {"error": "Telegram send failed"}

            POSTED.add(uid)
            break

        return {"status": "checked"}

    except Exception as e:
        return {"error": str(e)}
