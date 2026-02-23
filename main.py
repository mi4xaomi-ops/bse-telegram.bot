import os
import re
import requests
import feedparser
import hashlib
from datetime import datetime
from typing import Dict, List, Any
from fastapi import FastAPI
import uvicorn

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

    # ======================================================
    # 1️⃣ FINANCIAL RESULTS (Highest Priority)
    # ======================================================
    {
        "main": "Financial Results",
        "priority": 1,
        "keywords": [
            "Quarterly Results",
            "Annual Results",
            "Financial Results",
            "Audited Results",
            "Unaudited Results",
            "Standalone Results",
            "Consolidated Results",
            "Q1", "Q2", "Q3", "Q4",
            "Regulation 33"
        ],
        "emoji": "📊"
    },

    # ======================================================
    # 2️⃣ DIVIDEND
    # ======================================================
    {
        "main": "Dividend",
        "priority": 2,
        "keywords": [
            "Dividend",
            "Interim Dividend",
            "Final Dividend",
            "Special Dividend"
        ],
        "emoji": "💰"
    },

    # ======================================================
    # 3️⃣ BONUS / SPLIT
    # ======================================================
    {
        "main": "Bonus / Split",
        "priority": 2,
        "keywords": [
            "Bonus",
            "Stock Split",
            "Subdivision",
            "Face Value Split"
        ],
        "emoji": "🎁"
    },

    # ======================================================
    # 4️⃣ BUYBACK
    # ======================================================
    {
        "main": "Buyback",
        "priority": 2,
        "keywords": [
            "Buyback",
            "Buy Back"
        ],
        "emoji": "🔄"
    },

    # ======================================================
    # 5️⃣ FUND RAISING / CAPITAL ISSUE
    # ======================================================
    {
        "main": "Fund Raising / Capital Issue",
        "priority": 2,
        "keywords": [
            "Rights Issue",
            "QIP",
            "Qualified Institutions Placement",
            "Preferential Issue",
            "Warrants",
            "Debentures",
            "NCD",
            "Bond Issue",
            "Allotment",
            "ESOP",
            "Employee Stock Option"
        ],
        "emoji": "🏦"
    },

    # ======================================================
    # 6️⃣ MERGER / ACQUISITION
    # ======================================================
    {
        "main": "Merger / Acquisition",
        "priority": 3,
        "keywords": [
            "Merger",
            "Acquisition",
            "Amalgamation",
            "Scheme of Arrangement",
            "Takeover"
        ],
        "emoji": "🤝"
    },

    # ======================================================
    # 7️⃣ ORDER WIN / CONTRACT
    # ======================================================
    {
        "main": "Order Win / Contract",
        "priority": 3,
        "keywords": [
            "Order Win",
            "Order Received",
            "Contract Awarded",
            "Letter of Award",
            "LOA",
            "LOI",
            "MoU"
        ],
        "emoji": "📦"
    },

    # ======================================================
    # 8️⃣ BOARD MEETING
    # ======================================================
    {
        "main": "Board Meeting",
        "priority": 4,
        "keywords": [
            "Board Meeting",
            "Outcome of Board Meeting",
            "Board Meeting Intimation"
        ],
        "emoji": "📋"
    },

    # ======================================================
    # 9️⃣ AGM / EGM / VOTING
    # ======================================================
    {
        "main": "AGM / EGM / Voting",
        "priority": 4,
        "keywords": [
            "AGM",
            "EGM",
            "Postal Ballot",
            "Voting Results",
            "Regulation 44"
        ],
        "emoji": "🗳"
    },

    # ======================================================
    # 🔟 MANAGEMENT CHANGES
    # ======================================================
    {
        "main": "Management Change",
        "priority": 4,
        "keywords": [
            "Appointment",
            "Resignation",
            "CFO",
            "CEO",
            "Managing Director",
            "Independent Director",
            "Company Secretary"
        ],
        "emoji": "👤"
    },

    # ======================================================
    # 1️⃣1️⃣ GOVERNANCE / COMPLIANCE
    # ======================================================
    {
        "main": "Corporate Governance / Compliance",
        "priority": 5,
        "keywords": [
            "Corporate Governance Report",
            "Regulation 27",
            "Shareholding Pattern",
            "Related Party Transaction",
            "Regulation 30",
            "Disclosure under Regulation"
        ],
        "emoji": "🏛"
    },

    # ======================================================
    # 1️⃣2️⃣ BUSINESS UPDATE
    # ======================================================
    {
        "main": "Business Update",
        "priority": 6,
        "keywords": [
            "Operational Update",
            "Business Update",
            "Sales Update",
            "Capacity Expansion",
            "New Project",
            "Expansion"
        ],
        "emoji": "🚀"
    },

    # ======================================================
    # 1️⃣3️⃣ EXCHANGE / REGULATORY ACTION
    # ======================================================
    {
        "main": "Exchange / Regulatory Action",
        "priority": 7,
        "keywords": [
            "Suspension",
            "Delisting",
            "GSM",
            "ASM",
            "Price Band",
            "Clarification",
            "Reply to Exchange Query"
        ],
        "emoji": "🚨"
    },

    # ======================================================
    # 1️⃣4️⃣ INVESTOR / PRESS COMMUNICATION
    # ======================================================
    {
        "main": "Investor / Press Communication",
        "priority": 8,
        "keywords": [
            "Press Release",
            "Media Release",
            "Investor Presentation",
            "Earnings Call",
            "Analyst Meet",
            "Transcript"
        ],
        "emoji": "📰"
    },

    # ======================================================
    # DEFAULT
    # ======================================================
    {
        "main": "Other",
        "priority": 99,
        "keywords": [],
        "emoji": "📌"
    }
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
    url = f"https://api.telegram.org/bot{8536725493:AAFSdPtNKJEMFsapJGfH5sh9XtIc-lbruCA}/sendMessage"
    payload = {
        "chat_id": -1003545287392,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# ==========================================================
# MAIN RSS PROCESSOR
# ==========================================================

@app.get("/run")
def run_bot():

    feed = feedparser.parse("https://www.bseindia.com/data/xml/announcements.xml")

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
