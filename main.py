from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests
import xml.etree.ElementTree as ET
import os
import hashlib
import re
import fitz  # PyMuPDF
import tempfile

app = FastAPI()

# --------------------------------
# CONFIG
# --------------------------------

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise Exception("BOT_TOKEN or CHANNEL_ID not set in environment")

POSTED = set()

# --------------------------------
# HELPERS
# --------------------------------

def generate_id(title, link):
    return hashlib.md5((title + link).encode()).hexdigest()


def extract_scrip_code(text):
    match = re.search(r"Scrip Code\s*:\s*(\d+)", text, re.I)
    return match.group(1) if match else None


def extract_text_from_pdf(url):
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return ""

        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp.flush()

            doc = fitz.open(tmp.name)

            text = ""
            for page in doc[:3]:  # Only first 3 pages for speed
                text += page.get_text()

            doc.close()
            return text

    except Exception:
        return ""


def extract_financials(text):
    results = []

    revenue = re.search(r"(Revenue|Total Income)[^\d]{0,25}([\d,]+\.*\d*)", text, re.I)
    profit = re.search(r"(Net Profit|PAT|Profit After Tax)[^\d\-]{0,25}([\d,\-]+\.*\d*)", text, re.I)
    eps = re.search(r"(EPS|Earnings Per Share)[^\d\-]{0,25}([\d\.\-]+)", text, re.I)
    dividend = re.search(r"Dividend[^\d]{0,25}([\d\.]+)", text, re.I)

    if revenue:
        results.append(f"Revenue: ₹{revenue.group(2)}")

    if profit:
        results.append(f"Net Profit: ₹{profit.group(2)}")

    if eps:
        results.append(f"EPS: ₹{eps.group(2)}")

    if dividend:
        results.append(f"Dividend: ₹{dividend.group(1)} per share")

    return results


def generate_corporate_summary(title):
    summary = []

    if "Board Meeting" in title:
        summary.append("Board meeting update released.")

    if "Acquisition" in title or "Investment" in title:
        summary.append("Strategic expansion update.")

    if "Resignation" in title:
        summary.append("Management personnel update.")

    if "Order" in title or "Contract" in title:
        summary.append("New order/contract secured.")

    if not summary:
        summary.append("Material corporate announcement released.")

    return summary[:3]


# --------------------------------
# ROUTES
# --------------------------------

@app.get("/")
async def health():
    return {"status": "running"}


@app.get("/run")
@app.get("/run/")
async def run_bot():

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(RSS_URL, headers=headers, timeout=20)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="RSS fetch failed")

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        raise HTTPException(status_code=500, detail="Invalid XML from BSE")

    channel = root.find("channel")
    if channel is None:
        raise HTTPException(status_code=500, detail="Invalid RSS structure")

    items = channel.findall("item")

    for item in items:
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        description = item.findtext("description", "")

        if not title or not link:
            continue

        scrip_code = extract_scrip_code(description)
        if not scrip_code:
            continue  # Equity only

        uid = generate_id(title, link)
        if uid in POSTED:
            continue

        pdf_text = extract_text_from_pdf(link)

        is_financial = any(k in title.lower() for k in [
            "result", "financial", "quarter", "standalone", "consolidated"
        ])

        if is_financial:
            summary_points = extract_financials(pdf_text)
        else:
            summary_points = generate_corporate_summary(title)

        if not summary_points:
            summary_points = ["Refer detailed filing for complete information."]

        summary_text = "\n".join([f"• {p}" for p in summary_points])

        message = (
            f"📢 <b>{title}</b>\n\n"
            f"🏷 Scrip Code: {scrip_code}\n\n"
            f"{summary_text}\n\n"
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
            timeout=15
        )

        if tg_response.status_code == 200:
            POSTED.add(uid)
            break

    return JSONResponse(content={"status": "checked"}, status_code=200)
