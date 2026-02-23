from fastapi import FastAPI
from pydantic import BaseModel
import requests
import pdfplumber
import io
import re

app = FastAPI()

class PDFRequest(BaseModel):
    pdf_url: str

def clean_text(text):
    return re.sub(r"\s+", " ", text)

def extract_key_points(text):

    bullets = []

    # Revenue
    revenue = re.search(r"(Revenue|Total Income)[^0-9]{0,20}([\d,]+\.*\d*)", text, re.I)
    if revenue:
        bullets.append(f"Revenue reported at ₹{revenue.group(2)}")

    # Net Profit
    profit = re.search(r"(Net Profit|PAT|Profit After Tax)[^0-9\-]{0,20}([\d,\-]+\.*\d*)", text, re.I)
    if profit:
        bullets.append(f"Net Profit at ₹{profit.group(2)}")

    # EBITDA
    ebitda = re.search(r"(EBITDA)[^0-9]{0,20}([\d,]+\.*\d*)", text, re.I)
    if ebitda:
        bullets.append(f"EBITDA at ₹{ebitda.group(2)}")

    # Dividend
    dividend = re.search(r"Dividend[^0-9]{0,20}([\d\.]+)", text, re.I)
    if dividend:
        bullets.append(f"Dividend announced: ₹{dividend.group(1)} per share")

    # Order win
    order = re.search(r"order[^₹]{0,40}₹?\s?([\d,]+\.*\d*)", text, re.I)
    if order:
        bullets.append(f"New order worth ₹{order.group(1)}")

    if not bullets:
        bullets.append("Material corporate update announced.")

    return bullets[:3]

@app.post("/summarize")
def summarize(data: PDFRequest):

    response = requests.get(data.pdf_url)
    pdf_bytes = io.BytesIO(response.content)

    full_text = ""

    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages[:5]:  # first 5 pages for speed
            full_text += page.extract_text() or ""

    full_text = clean_text(full_text)

    bullets = extract_key_points(full_text)

    return {"bullets": bullets}