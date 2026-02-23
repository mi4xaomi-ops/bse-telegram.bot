import os
import re
import requests
import feedparser
import hashlib
from datetime import datetime
from typing import Dict, List, Any
from fastapi import FastAPI

# ==========================================================
# CONFIGURATION
# ==========================================================

BOT_TOKEN = os.getenv("8536725493:AAFSdPtNKJEMFsapJGfH5sh9XtIc-lbruCA")
CHAT_ID = os.getenv("-1003545287392")
RSS_FEED_URL = os.getenv("https://www.bseindia.com/data/xml/announcements.xml")

app = FastAPI()

# ==========================================================
# CATEGORY MASTER (DEDUPED & PRIORITY SAFE)
# ==========================================================

CATEGORY_MASTER = [

    {"main": "Financial Results",
     "priority": 1,
     "keywords": [
         "Quarterly Results", "Annual Results", "Financial Results",
         "Audited Results", "Unaudited Results",
         "Standalone Results", "Consolidated Results",
         "Q1", "Q2", "Q3", "Q4"
     ],
     "emoji": "📊"},

    {"main": "Dividend",
     "priority": 2,
     "keywords": ["Interim Dividend", "Final Dividend", "Special Dividend", "Dividend"],
     "emoji": "💰"},

    {"main": "Bonus / Split",
     "priority": 2,
     "keywords": ["Bonus", "Stock Split", "Subdivision"],
     "emoji": "🎁"},

    {"main": "Buyback",
     "priority": 2,
     "keywords": ["Buyback"],
     "emoji": "🔄"},

    {"main": "Rights Issue / Fund Raising",
     "priority": 2,
     "keywords": ["Rights Issue", "QIP", "Warrants", "Debenture", "Bond", "Preferential Issue"],
     "emoji": "🏦"},

    {"main": "Merger / Acquisition",
     "priority": 3,
     "keywords": ["Merger", "Acquisition", "Amalgamation"],
     "emoji": "🤝"},

    {"main": "Order Win / Contract",
     "priority": 3,
     "keywords": ["Order Win", "Contract", "Awarded"],
     "emoji": "📦"},

    {"main": "Board Meeting",
     "priority": 4,
     "keywords": ["Board Meeting", "Outcome of Board Meeting", "Board Meeting Intimation"],
     "emoji": "📋"},

    {"main": "Corporate Governance",
     "priority": 4,
     "keywords": ["Corporate Governance Report", "Regulation 27"],
     "emoji": "🏛"},

    {"main": "AGM / EGM",
     "priority": 4,
     "keywords": ["AGM", "EGM", "Postal Ballot", "Voting Results"],
     "emoji": "🗳"},

    {"main": "Appointment / Resignation",
     "priority": 4,
     "keywords": ["Appointment", "Resignation", "CFO", "CEO", "Director"],
     "emoji": "👤"},

    {"main": "Listing",
     "priority": 5,
     "keywords": ["Listing", "Trading Approval", "Commencement of Trading"],
     "emoji": "🆕"},

    {"main": "Exchange Action",
     "priority": 5,
     "keywords": ["Suspension", "Delisting", "GSM", "ASM", "Price Band"],
     "emoji": "🚨"},

    {"main": "Press Release",
     "priority": 6,
     "keywords": ["Press Release", "Media Release"],
     "emoji": "📰"},

    {"main": "Business Update",
     "priority": 6,
     "keywords": ["Operational Update", "Business Update", "Sales Update"],
     "emoji": "🚀"},

    {"main": "Other",
     "priority": 99,
     "keywords": [],
     "emoji": "📌"},
]

# ==========================================================
# DUPLICATE SUPPRESSION
# ==========================================================

PROCESSED_HASHES = set()

def is_duplicate(title: str) -> bool:
    title_hash = hashlib.md5(title.encode()).hexdigest()
    if title_hash in PROCESSED_HASHES:
        return True
    PROCESSED_HASHES.add(title_hash)
    return False

# ==========================================================
# CLASSIFICATION ENGINE
# ==========================================================

def classify(title: str) -> Dict[str, Any]:
    title_lower = title.lower()
    matched = []

    for category in CATEGORY_MASTER:
        for keyword in category["keywords"]:
            if keyword.lower() in title_lower:
                matched.append(category)
                break

    if not matched:
        return CATEGORY_MASTER[-1]

    matched_sorted = sorted(matched, key=lambda x: x["priority"])
    return matched_sorted[0]

# ==========================================================
# RECORD DATE DETECTION (SEPARATE – NO DUPLICATION)
# ==========================================================

def detect_record_date(text: str) -> str:
    match = re.search(r"Record Date[:\s]*([\d\-\/]+)", text, re.I)
    if match:
        return match.group(1)
    return ""

# ==========================================================
# FINANCIAL EXTRACTION
# ==========================================================

def extract_financials(text: str) -> List[str]:
    results = []

    revenue = re.search(r"(Revenue|Total Income)[^\d]{0,25}([\d,]+\.*\d*)", text, re.I)
    profit = re.search(r"(Net Profit|PAT)[^\d\-]{0,25}([\d,\-]+\.*\d*)", text, re.I)
    eps = re.search(r"(EPS)[^\d\-]{0,25}([\d\.\-]+)", text, re.I)

    if revenue:
        results.append(f"Revenue: ₹{revenue.group(2)}")

    if profit:
        results.append(f"Net Profit: ₹{profit.group(2)}")

    if eps:
        results.append(f"EPS: ₹{eps.group(2)}")

    return results

# ==========================================================
# TELEGRAM SENDER
# ==========================================================

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# ==========================================================
# MAIN RSS PROCESSOR
# ==========================================================

@app.get("/run")
def run_bot():

    feed = feedparser.parse(https://www.bseindia.com/data/xml/announcements.xml)

    for entry in feed.entries:

        title = entry.title.strip()

        if is_duplicate(title):
            continue

        summary = entry.summary if "summary" in entry else ""
        link = entry.link

        category = classify(title)
        record_date = detect_record_date(summary)
        financials = extract_financials(summary)

        message = (
            f"{category['emoji']} <b>{category['main']}</b>\n\n"
            f"🏢 {title}\n"
        )

        if record_date:
            message += f"📅 Record Date: {record_date}\n"

        if financials:
            message += "\n".join(financials) + "\n"

        message += f"\n🔗 {link}"

        send_telegram(message)

    return {"status": "Bot executed successfully"}
