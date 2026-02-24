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
# FASTAPI
# ==========================================================

app = FastAPI(title="BSE Announcement Telegram Bot")

# ==========================================================
# DEDUP MEMORY
# ==========================================================

PROCESSED_HASHES = set()

# ==========================================================
# CLASSIFIER
# ==========================================================

def classify(title: str) -> Dict[str, str]:
    title_lower = title.lower()

    # Prioritize and classify based on multiple possible keywords
    if "dividend" in title_lower or "profit sharing" in title_lower:
        return {"main": "💰 Dividend", "sub": "", "emoji": "💰"}
    elif "bonus" in title_lower and "issue" in title_lower:
        return {"main": "💰 Bonus Issue", "sub": "", "emoji": "💰"}
    elif "quarterly" in title_lower or "annual" in title_lower:
        return {"main": "📊 Financial Results", "sub": "", "emoji": "📊"}
    elif "ipo" in title_lower or "initial public offering" in title_lower:
        return {"main": "📈 IPO Announcement", "sub": "", "emoji": "📈"}
    elif "stock split" in title_lower or "subdivision" in title_lower:
        return {"main": "📈 Stock Split", "sub": "", "emoji": "📈"}
    elif "fpo" in title_lower or "follow-on public offering" in title_lower:
        return {"main": "📈 FPO", "sub": "", "emoji": "📈"}
    elif "buyback" in title_lower:
        return {"main": "💰 Buyback", "sub": "", "emoji": "💰"}
    elif "regulation 33" in title_lower:
        return {"main": "📊 Regulation 33 Filing", "sub": "", "emoji": "📊"}
    elif "regulation 30" in title_lower:
        return {"main": "📌 Regulation 30 Disclosure", "sub": "", "emoji": "📌"}
    elif "merger" in title_lower or "acquisition" in title_lower or "takeover" in title_lower:
        return {"main": "📌 Corporate Action (Merger/Acquisition)", "sub": "", "emoji": "📌"}
    elif "shareholding" in title_lower or "stockholding" in title_lower:
        return {"main": "👥 Shareholding Pattern", "sub": "", "emoji": "👥"}
    elif "new listing" in title_lower or "listed on bse" in title_lower:
        return {"main": "📃 New Listing", "sub": "", "emoji": "📃"}
    elif "delisting" in title_lower:
        return {"main": "📃 Delisting of Securities", "sub": "", "emoji": "📃"}
    elif "press release" in title_lower:
        return {"main": "📌 Press Release", "sub": "", "emoji": "📌"}
    elif "company update" in title_lower:
        return {"main": "📌 Company Update", "sub": "", "emoji": "📌"}
    elif "leadership change" in title_lower or "board changes" in title_lower:
        return {"main": "📌 Leadership Changes", "sub": "", "emoji": "📌"}
    elif "csr" in title_lower or "corporate social responsibility" in title_lower:
        return {"main": "📌 CSR Announcement", "sub": "", "emoji": "📌"}
    else:
        # Fallback category for unclear titles
        return {"main": "📌 General Announcement", "sub": "", "emoji": "📌"}

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
# FETCH AND PROCESS RSS FEED
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
