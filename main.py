# ==========================================================
# BSE ANNOUNCEMENT TELEGRAM BOT
# ==========================================================

import os
import hashlib
import logging
import requests
import feedparser
from typing import Dict
from fastapi import FastAPI, HTTPException

# ==========================================================
# CONFIGURATION
# ==========================================================

BOT_TOKEN = os.getenv("8536725493:AAFSdPtNKJEMFsapJGfH5sh9XtIc-lbruCA")
CHAT_ID = os.getenv("-1003545287392")
RSS_FEED_URL = "https://www.bseindia.com/data/xml/announcements.xml"

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN and CHAT_ID must be set as environment variables")

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BSE-Telegram-Bot")

# ==========================================================
# FASTAPI
# ==========================================================

app = FastAPI(title="BSE Announcement Telegram Bot")

# ==========================================================
# CATEGORY MASTER (CLEAN)
# ==========================================================

CATEGORY_MASTER = [
    {
        "main": "Financial Results",
        "emoji": "📊",
        "priority": 1,
        "subcategories": [
            {"name": "Quarterly Results", "keywords": ["Quarterly Results", "Q1", "Q2", "Q3", "Q4"]},
            {"name": "Annual Results", "keywords": ["Annual Results"]},
            {"name": "Regulation 33 Filing", "keywords": ["Regulation 33"]},
        ],
    },
    {
        "main": "Corporate Action",
        "emoji": "💰",
        "priority": 2,
        "subcategories": [
            {"name": "Dividend", "keywords": ["Dividend"]},
            {"name": "Bonus Issue", "keywords": ["Bonus"]},
            {"name": "Stock Split", "keywords": ["Stock Split", "Subdivision"]},
            {"name": "Buyback", "keywords": ["Buyback"]},
        ],
    },
    {
        "main": "Company Update",
        "emoji": "🚀",
        "priority": 3,
        "subcategories": [
            {"name": "Order Win", "keywords": ["Order Received", "LOA", "LOI"]},
            {"name": "Press Release", "keywords": ["Press Release"]},
        ],
    },
    {
        "main": "Other",
        "emoji": "📌",
        "priority": 99,
        "subcategories": [],
    },
]

# ==========================================================
# DEDUP MEMORY
# ==========================================================

PROCESSED_HASHES = set()

# ==========================================================
# CLASSIFIER
# ==========================================================

def classify(title: str) -> Dict[str, str]:
    title_lower = title.lower()
    matches = []

    for category in CATEGORY_MASTER:
        for sub in category["subcategories"]:
            for keyword in sub["keywords"]:
                if keyword.lower() in title_lower:
                    matches.append((category, sub))
                    break

    if not matches:
        return {"main": "Other", "sub": "", "emoji": "📌"}

    matches.sort(key=lambda x: x[0]["priority"])
    best_category, best_sub = matches[0]

    return {
        "main": best_category["main"],
        "sub": best_sub["name"],
        "emoji": best_category["emoji"],
    }

# ==========================================================
# TELEGRAM SENDER
# ==========================================================

def send_to_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    response = requests.post(url, json=payload, timeout=10)

    if response.status_code != 200:
        logger.error(response.text)
        raise HTTPException(status_code=500, detail="Telegram API Error")

# ==========================================================
# FETCH
# ==========================================================

def fetch_and_process(limit: int = 5):
    feed = feedparser.parse(RSS_FEED_URL)

    if not feed.entries:
        return {"status": "No announcements"}

    posted = 0

    for entry in feed.entries[:limit]:
        title = entry.title
        link = entry.link

        announcement_hash = hashlib.sha256(title.encode()).hexdigest()

        if announcement_hash in PROCESSED_HASHES:
            continue

        classification = classify(title)

        message = (
            f"{classification['emoji']} <b>{classification['main']}</b>\n"
            f"<b>{classification['sub']}</b>\n\n"
            f"{title}\n\n"
            f"<a href='{link}'>View Filing</a>"
        )

        send_to_telegram(message)

        PROCESSED_HASHES.add(announcement_hash)
        posted += 1

    return {"posted": posted}

# ==========================================================
# ROUTES
# ==========================================================

@app.get("/")
def health():
    return {"status": "Bot Live"}

@app.get("/run")
def run():
    return fetch_and_process()
