from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import pdfplumber
import io
import re

app = FastAPI()

class PDFRequest(BaseModel):
    pdf_url: str

@app.get("/")
def home():
    return {"status": "API running"}

def clean_text(text):
    return re.sub(r"\s+", " ", text)

def extract_key_points(text):

    bullets = []

    revenue = re.search(r"(Revenue|Total Income)[^0-9]{0,20}([\d,]+\.*\d*)", text, re.I)
    if revenue:
        bullets.append(f"Revenue reported at ₹{revenue.group(2)}")

    profit = re.search(r"(Net Profit|PAT|Profit After Tax)[^0-9\-]{0,20}([\d,\-]+\.*\d*)", text, re.I)
    if profit:
        bullets.append(f"Net Profit at ₹{profit.group(2)}")

    if not bullets:
        bullets.append("Material corporate update announced.")

    return bullets[:3]

@app.post("/summarize")
def summarize(data: PDFRequest):

    try:
        headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(data.pdf_url, headers=headers, timeout=15)

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="PDF download failed")

        pdf_bytes = io.BytesIO(response.content)

        full_text = ""

        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages[:2]:   # LIMIT pages for safety
                text = page.extract_text()
                if text:
                    full_text += text

        if not full_text:
            return {"bullets": ["Unable to extract readable text from PDF."]}

        full_text = clean_text(full_text)

        bullets = extract_key_points(full_text)

        return {"bullets": bullets}

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
