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
    return hashlib.md5((title+link).encode()).hexdigest()

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/run")
def run():

    response = requests.get(RSS_URL)
    root = ET.fromstring(response.content)

    for item in root.find("channel").findall("item"):

        title = item.find("title").text
        link = item.find("link").text
        description = item.find("description").text or ""

        if "Scrip Code" not in description:
            continue

        uid = generate_id(title, link)
        if uid in POSTED:
            continue

        message = f"📢 <b>{title}</b>\n\n🔗 {link}"

        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(telegram_url, json={
            "chat_id": CHANNEL_ID,
            "text": message,
            "parse_mode": "HTML"
        })

        POSTED.add(uid)
        break

    return {"status": "checked"}