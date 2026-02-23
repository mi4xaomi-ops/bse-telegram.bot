from fastapi import FastAPI
import requests
import xml.etree.ElementTree as ET
import os
import hashlib

app = FastAPI()

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

POSTED = set()

def generate_id(title, link):
    return hashlib.md5((title + link).encode()).hexdigest()

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/run")
def run():
    try:
        response = requests.get(RSS_URL, timeout=10)
        root = ET.fromstring(response.content)

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

            requests.post(
                telegram_url,
                json={
                    "chat_id": CHANNEL_ID,
                    "text": message,
                    "parse_mode": "HTML"
                }
            )

            POSTED.add(uid)
            break

        return {"status": "checked"}

    except Exception as e:
        return {"error": str(e)}
