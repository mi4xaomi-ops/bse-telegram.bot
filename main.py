import os
import hashlib
import logging
import requests
import feedparser
from fastapi import FastAPI, HTTPException

# ==========================================================
# CONFIGURATION
# ==========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RSS_FEED_URL = "https://www.bseindia.com/data/xml/announcements.xml"

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN and CHAT_ID must be set as environment variables")

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BSE-Telegram-Bot")

# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(title="BSE Announcement Telegram Bot")

# ==========================================================
# DEDUP MEMORY
# ==========================================================

PROCESSED_HASHES = set()

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
# GENERATE ANNOUNCEMENT BASED ON XML DESCRIPTION
# ==========================================================

def generate_announcement(entry):
    # Extracting relevant fields from the RSS feed entry (assuming typical RSS structure)
    title = entry.title
    link = entry.link
    description = entry.description
    pub_date = entry.published  # or entry.updated depending on the feed

    # Create a more detailed and informative announcement
    message = (
        f"<b>{title}</b>\n\n"
        f"<i>{pub_date}</i>\n\n"
        f"<b>Description:</b>\n{description}\n\n"
        f"<a href='{link}'>View Filing</a>"
    )
    return message

# ==========================================================
# FETCH AND PROCESS RSS FEED (Simplified)
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
        
        # Generate the announcement based on the XML description
        message = generate_announcement(entry)

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
