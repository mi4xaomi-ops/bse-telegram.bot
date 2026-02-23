from fastapi import FastAPI
import requests
import xml.etree.ElementTree as ET
import os
import hashlib
import re

app = FastAPI()

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID not set in environment")

POSTED = set()

# -----------------------------
# CONFIGURATION
# -----------------------------

ALLOWED_CATEGORIES = [
    "Financial Results",
    "Board Meeting",
    "Outcome of Board Meeting",
    "Corporate Action",
    "Shareholding Pattern",
    "Disclosure under Regulation",
    "Press Release"
]

# -----------------------------
# HELPERS
# -----------------------------

def generate_id(title, link):
    return hashlib.md5((title + link).encode()).hexdigest()


def extract_scrip_code(text):
    match = re.search(r"Scrip Code\s*:\s*(\d+)", text, re.I)
    return match.group(1) if match else None


def extract_category(text):
    match = re.search(r"Category\s*:\s*(.+?)(?:<|$)", text, re.I)
    return match.group(1).strip() if match else ""


def generate_summary(title):
    """
    Simple investor-friendly summary logic.
    You can make this smarter later.
    """
    summary = []

    if "Result" in title:
        summary.append("Company reported financial results.")
    if "Dividend" in title:
        summary.append("Dividend announcement made.")
    if "Board Meeting" in title:
        summary.append("Board meeting update released.")
    if "Acquisition" in title or "Investment" in title:
        summary.append("Strategic business update announced.")

    if not summary:
        summary.append("Material corporate announcement released.")

    return summary[:3]


# -----------------------------
# ROUTES
# -----------------------------

@app.get("/")
def home():
    return {"status": "running"}


@app.get("/run")
def run():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(RSS_URL, headers=headers, timeout=15)

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
            description = item.findtext("description", "")

            if not title or not link:
                continue

            # -----------------------------
            # EQUITY CHECK
            # -----------------------------
            scrip_code = extract_scrip_code(description)
            if not scrip_code:
                continue

            # -----------------------------
            # CATEGORY CHECK
            # -----------------------------
            category = extract_category(description)
            if category and category not in ALLOWED_CATEGORIES:
                continue

            uid = generate_id(title, link)
            if uid in POSTED:
                continue

            # -----------------------------
            # MESSAGE FORMAT
            # -----------------------------
            summary_points = generate_summary(title)

            summary_text = ""
            for point in summary_points:
                summary_text += f"• {point}\n"

            message = (
                f"📢 <b>{title}</b>\n\n"
                f"🏷 Scrip Code: {scrip_code}\n\n"
                f"{summary_text}\n"
                f"🔗 Raw Filing: {link}"
            )

            telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

            tg_response = requests.post(
                telegram_url,
                json={
                    "chat_id": CHANNEL_ID,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=10
            )

            if tg_response.status_code != 200:
                return {"error": "Telegram send failed"}

            POSTED.add(uid)

            # Send only one per run
            break

        return {"status": "checked"}

    except Exception as e:
        return {"error": str(e)}
