from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests
import xml.etree.ElementTree as ET
import os
import hashlib
import re
import fitz  # PyMuPDF
import tempfile
from typing import Dict, List, Any

app = FastAPI()

# ==========================================================
# CONFIGURATION
# ==========================================================

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID not set properly")

HEADERS = {"User-Agent": "Mozilla/5.0"}

POSTED = set()

# ==========================================================
# PRIORITY ENGINE
# ==========================================================

PRIORITY_MAP = {
    "Trading Suspension": 1,
    "Compulsory Delisting": 1,
    "Delisting Action": 1,

    "Board Meeting Intimation": 2,
    "Financial Results": 2,
    "Listing Update": 2,
    "Corporate Action - Record Date": 2,

    "Outcome of Board Meeting": 3,
    "Dividend": 3,
    "Bonus Issue": 3,
    "Stock Split": 3,
    "Rights Issue": 3,
    "Buyback": 3,
    "Acquisition / Investment": 3,
    "Order / Contract": 3,

    "Management Change": 4,
    "Regulation 30 - Press/Media Release": 4,
    "Regulation 30 Disclosure": 4,
    "Investor Presentation": 4,
    "Shareholding Pattern": 4,

    "General Corporate Disclosure": 5
}

# ==========================================================
# HELPERS
# ==========================================================

def generate_id(title: str, link: str) -> str:
    return hashlib.md5((title + link).encode()).hexdigest()


def extract_scrip_code(text: str) -> str:
    match = re.search(r"Scrip Code\s*:\s*(\d+)", text, re.I)
    return match.group(1) if match else ""


def extract_text_from_pdf(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return ""

        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp.flush()

            doc = fitz.open(tmp.name)
            text = ""

            for page in doc[:3]:
                text += page.get_text()

            doc.close()
            return text

    except Exception:
        return ""


# ==========================================================
# FINANCIAL EXTRACTION
# ==========================================================

def extract_financials(text: str) -> List[str]:
    results = []

    patterns = {
        "Revenue": r"(Revenue|Total Income)[^\d]{0,40}([\d,]+\.*\d*)",
        "Net Profit": r"(Net Profit|PAT|Profit After Tax)[^\d\-]{0,40}([\d,\-]+\.*\d*)",
        "EBITDA": r"(EBITDA)[^\d\-]{0,40}([\d,\-]+\.*\d*)",
        "EPS": r"(EPS|Earnings Per Share)[^\d\-]{0,40}([\d\.\-]+)",
        "Dividend": r"Dividend[^\d]{0,25}([\d\.]+)"
    }

    for label, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            value = match.group(2) if label != "Dividend" else match.group(1)
            if label == "Dividend":
                results.append(f"Dividend: ₹{value} per share")
            else:
                results.append(f"{label}: ₹{value}")

    return results


def extract_record_date(text: str) -> str:
    patterns = [
        r"Record Date[^\d]{0,20}(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"Record Date[^\d]{0,20}(\d{1,2}\s?[A-Za-z]+\s?\d{4})"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)

    return ""


# ==========================================================
# CLASSIFICATION ENGINE
# ==========================================================

def classify_bse(title: str, text: str) -> Dict[str, Any]:

    categories = []
    title_lower = title.lower()

    # Exchange Actions
    exchange_actions = {
        "compulsory delisting": "Compulsory Delisting",
        "delisting": "Delisting Action",
        "suspension": "Trading Suspension",
        "gsm": "GSM Surveillance",
        "asm": "ASM Surveillance"
    }

    for key, value in exchange_actions.items():
        if key in title_lower:
            categories.append(value)

    # Listing
    if any(k in title_lower for k in [
        "listing of equity shares",
        "listing approval",
        "trading approval",
        "ipo listing",
        "commencement of trading"
    ]):
        categories.append("Listing Update")

    # Board Meeting
    if any(k in title_lower for k in [
        "board meeting intimation",
        "intimation of board meeting",
        "notice of board meeting"
    ]):
        categories.append("Board Meeting Intimation")

    elif "outcome of board meeting" in title_lower:
        categories.append("Outcome of Board Meeting")

    elif "board meeting" in title_lower:
        categories.append("Board Meeting")

    # Financial Results
    if any(k in title_lower for k in [
        "financial results",
        "quarterly results",
        "annual results",
        "audited",
        "unaudited",
        "q1", "q2", "q3", "q4"
    ]):
        categories.append("Financial Results")

    # Corporate Actions
    corporate = {
        "dividend": "Dividend",
        "bonus": "Bonus Issue",
        "split": "Stock Split",
        "rights": "Rights Issue",
        "buyback": "Buyback"
    }

    for key, value in corporate.items():
        if key in title_lower:
            categories.append(value)

    # Regulation 30
    if "regulation 30" in title_lower:
        if "press release" in title_lower or "media release" in title_lower:
            categories.append("Regulation 30 - Press/Media Release")
        else:
            categories.append("Regulation 30 Disclosure")

    if not categories:
        categories.append("General Corporate Disclosure")

    categories = list(set(categories))
    priority = min([PRIORITY_MAP.get(cat, 5) for cat in categories])

    financials = extract_financials(text)
    record_date = extract_record_date(text)

    return {
        "categories": categories,
        "priority": priority,
        "financials": financials,
        "record_date": record_date
    }


# ==========================================================
# ROUTES
# ==========================================================

@app.get("/")
async def health():
    return {"status": "BSE bot running"}

@app.get("/run")
async def run_bot():

    response = requests.get(RSS_URL, headers=HEADERS, timeout=20)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="RSS fetch failed")

    root = ET.fromstring(response.content)
    channel = root.find("channel")
    items = channel.findall("item")

    for item in items:

        title = item.findtext("title", "")
        link = item.findtext("link", "")
        description = item.findtext("description", "")

        if not title or not link:
            continue

        scrip_code = extract_scrip_code(description)
        if not scrip_code:
            continue

        uid = generate_id(title, link)
        if uid in POSTED:
            continue

        pdf_text = extract_text_from_pdf(link)

        classification = classify_bse(title, pdf_text)

        summary_lines = []

        if classification["financials"]:
            summary_lines.extend(classification["financials"])

        if classification["record_date"]:
            summary_lines.append(f"Record Date: {classification['record_date']}")

        if not summary_lines:
            summary_lines.append("Refer detailed filing for complete disclosure.")

        summary_text = "\n".join([f"• {line}" for line in summary_lines])

        message = (
            f"📢 <b>{title}</b>\n\n"
            f"🏷 Scrip Code: {scrip_code}\n"
            f"📂 Categories: {', '.join(classification['categories'])}\n\n"
            f"{summary_text}\n\n"
            f"🔗 <a href='{link}'>View Filing</a>"
        )

        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        tg_response = requests.post(
            telegram_url,
            json={
                "chat_id": CHANNEL_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=15
        )

        if tg_response.status_code == 200:
            POSTED.add(uid)
            break

    return JSONResponse(content={"status": "checked"}, status_code=200)
