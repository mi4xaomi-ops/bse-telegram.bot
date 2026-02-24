# ==========================================================
# BSE ANNOUNCEMENT TELEGRAM BOT
# FULLY AUDITED – EXCHANGE GRADE STRUCTURE
# ==========================================================

import os
import requests
import feedparser
import hashlib
from typing import Dict
from fastapi import FastAPI

# ==========================================================
# CONFIGURATION
# ==========================================================

BOT_TOKEN = os.getenv("8536725493:AAFSdPtNKJEMFsapJGfH5sh9XtIc-lbruCA")
CHAT_ID = os.getenv("-1003545287392")
RSS_FEED_URL = "https://www.bseindia.com/data/xml/announcements.xml"

app = FastAPI()

# ==========================================================
# CATEGORY MASTER (EXCHANGE-ALIGNED)
# ==========================================================

CATEGORY_MASTER = [

    # 1️⃣ FINANCIAL RESULTS
    {
        "main": "Financial Results",
        "emoji": "📊",
        "priority": 1,
        "subcategories": [
            {"name": "Quarterly Results", "keywords": ["Quarterly Results", "Q1", "Q2", "Q3", "Q4"]},
            {"name": "Annual Results", "keywords": ["Annual Results"]},
            {"name": "Audited Results", "keywords": ["Audited Results"]},
            {"name": "Unaudited Results", "keywords": ["Unaudited Results"]},
            {"name": "Limited Review Report", "keywords": ["Limited Review"]},
            {"name": "Standalone Results", "keywords": ["Standalone"]},
            {"name": "Consolidated Results", "keywords": ["Consolidated"]},
            {"name": "Regulation 33 Filing", "keywords": ["Regulation 33"]}
        ]
    },

    # 2️⃣ CORPORATE ACTION
    {
        "main": "Corporate Action",
        "emoji": "💰",
        "priority": 2,
        "subcategories": [
            {"name": "Dividend Recommendation", "keywords": ["Recommended Dividend"]},
            {"name": "Dividend Declaration", "keywords": ["Declared Dividend"]},
            {"name": "Interim Dividend", "keywords": ["Interim Dividend"]},
            {"name": "Final Dividend", "keywords": ["Final Dividend"]},
            {"name": "Bonus Issue", "keywords": ["Bonus"]},
            {"name": "Stock Split", "keywords": ["Stock Split", "Subdivision"]},
            {"name": "Buyback", "keywords": ["Buyback"]},
            {"name": "Record Date", "keywords": ["Record Date"]},
            {"name": "Book Closure", "keywords": ["Book Closure"]},
            {"name": "Corporate Action Amendment", "keywords": ["Revised Record Date", "Amendment"]}
        ]
    },

    # 3️⃣ FUND RAISING
    {
        "main": "Fund Raising",
        "emoji": "🏦",
        "priority": 3,
        "subcategories": [
            {"name": "Rights Issue", "keywords": ["Rights Issue"]},
            {"name": "QIP", "keywords": ["QIP"]},
            {"name": "Preferential Issue", "keywords": ["Preferential Issue"]},
            {"name": "Preferential Allotment", "keywords": ["Preferential Allotment"]},
            {"name": "Warrants Issue", "keywords": ["Warrants"]},
            {"name": "Warrant Conversion", "keywords": ["Conversion of Warrants"]},
            {"name": "NCD / Debentures", "keywords": ["NCD", "Debentures"]},
            {"name": "FCCB", "keywords": ["FCCB"]},
            {"name": "Commercial Paper", "keywords": ["Commercial Paper"]},
            {"name": "Allotment Update", "keywords": ["Allotment"]},
            {"name": "ESOP", "keywords": ["ESOP"]}
        ]
    },

    # 4️⃣ MERGER / RESTRUCTURING
    {
        "main": "Merger / Restructuring",
        "emoji": "🤝",
        "priority": 3,
        "subcategories": [
            {"name": "Merger", "keywords": ["Merger"]},
            {"name": "Acquisition", "keywords": ["Acquisition"]},
            {"name": "Scheme of Arrangement", "keywords": ["Scheme of Arrangement"]},
            {"name": "NCLT Order", "keywords": ["NCLT"]},
            {"name": "Insolvency / IBC", "keywords": ["Insolvency", "CIRP", "IBC"]}
        ]
    },

    # 5️⃣ BOARD & SHAREHOLDER MATTERS
    {
        "main": "Board / Shareholder Matters",
        "emoji": "📋",
        "priority": 4,
        "subcategories": [
            {"name": "Board Meeting Intimation", "keywords": ["Regulation 29", "Board Meeting Intimation"]},
            {"name": "Outcome of Board Meeting", "keywords": ["Outcome of Board Meeting"]},
            {"name": "AGM", "keywords": ["AGM"]},
            {"name": "EGM", "keywords": ["EGM"]},
            {"name": "Postal Ballot", "keywords": ["Postal Ballot"]},
            {"name": "Voting Results", "keywords": ["Voting Results", "Regulation 44"]}
        ]
    },

    # 6️⃣ MANAGEMENT & GOVERNANCE
    {
        "main": "Management / Governance",
        "emoji": "👤",
        "priority": 5,
        "subcategories": [
            {"name": "Appointment", "keywords": ["Appointment"]},
            {"name": "Resignation", "keywords": ["Resignation"]},
            {"name": "Change in Designation", "keywords": ["Change in Designation"]},
            {"name": "Corporate Governance Report", "keywords": ["Regulation 27"]},
            {"name": "Shareholding Pattern", "keywords": ["Regulation 31"]},
            {"name": "Reconciliation Audit", "keywords": ["Reconciliation of Share Capital"]},
            {"name": "Trading Window Closure", "keywords": ["Trading Window Closure"]},
            {"name": "Related Party Transactions", "keywords": ["Related Party Transaction"]}
        ]
    },

    # 7️⃣ COMPANY UPDATE (REGULATION 30 DRIVEN)
    {
        "main": "Company Update",
        "emoji": "🚀",
        "priority": 6,
        "subcategories": [
            {"name": "Business Update", "keywords": ["Business Update"]},
            {"name": "Operational Update", "keywords": ["Operational Update"]},
            {"name": "Order Win", "keywords": ["Order Received", "Contract Awarded", "LOA", "LOI"]},
            {"name": "Press Release", "keywords": ["Press Release"]},
            {"name": "Investor Presentation", "keywords": ["Investor Presentation"]},
            {"name": "Earnings Call", "keywords": ["Earnings Call"]},
            {"name": "Transcript", "keywords": ["Transcript"]},
            {"name": "Credit Rating", "keywords": ["Credit Rating"]},
            {"name": "Clarification", "keywords": ["Clarification"]},
            {"name": "Reply to Exchange Query", "keywords": ["Reply to Exchange"]},
            {"name": "ESG / Sustainability Report", "keywords": ["Sustainability Report", "BRSR"]}
        ]
    },

    # 8️⃣ REGULATORY / LEGAL
    {
        "main": "Regulatory / Legal",
        "emoji": "⚖️",
        "priority": 7,
        "subcategories": [
            {"name": "Litigation", "keywords": ["Litigation", "Court Order"]},
            {"name": "Disclosure of Default", "keywords": ["Default"]},
            {"name": "Exchange Action", "keywords": ["Suspension", "Delisting", "GSM", "ASM"]}
        ]
    },

    # DEFAULT
    {
        "main": "Other",
        "emoji": "📌",
        "priority": 99,
        "subcategories": []
    }
]

# ==========================================================
# CLASSIFICATION ENGINE
# ==========================================================

def classify(title: str) -> Dict[str, str]:

    title_lower = title.lower()
    matched = []

    for category in CATEGORY_MASTER:
        for sub in category["subcategories"]:
            for keyword in sub["keywords"]:
                if keyword.lower() in title_lower:
                    matched.append((category, sub))
                    break

    if not matched:
        return {"main": "Other", "sub": "", "emoji": "📌"}

    matched_sorted = sorted(matched, key=lambda x: x[0]["priority"])
    best_category, best_sub = matched_sorted[0]

    return {
        "main": best_category["main"],
        "sub": best_sub["name"],
        "emoji": best_category["emoji"]
    }
