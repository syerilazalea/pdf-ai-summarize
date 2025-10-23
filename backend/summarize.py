from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uvicorn
import requests
from io import BytesIO
from pdf2image import convert_from_bytes
import pytesseract
from bs4 import BeautifulSoup

# Inisialisasi FastAPI
app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

MAX_FILE_SIZE_MB = 1
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "error": f"Ukuran file terlalu besar. Maksimal {MAX_FILE_SIZE_MB} MB."
                },
            )
    response = await call_next(request)
    return response

# Fungsi ekstrak teks PDF
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
        if text.strip():
            return text.strip()
        else:
            return None
    except Exception:
        return None

# Fungsi download file dari URL
def download_file_from_url(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, timeout=30, headers=headers)
    response.raise_for_status()
    return response.content

# Fungsi proses URL dengan PDF, OCR, HTML, teks
def process_url(url: str):
    try:
        content = download_file_from_url(url)

        # Coba PDF teks
        pdf_text = extract_text_from_pdf(BytesIO(content))
        if pdf_text:
            print("DEBUG: Berhasil ekstrak PDF teks")
            return pdf_text

        # PDF scan → OCR
        try:
            images = convert_from_bytes(content)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img, lang="eng+ind") + "\n"
            if ocr_text.strip():
                print("DEBUG: Berhasil ekstrak PDF scan dengan OCR")
                return ocr_text.strip()
        except Exception as e_ocr:
            print(f"DEBUG: OCR gagal: {e_ocr}")

        # Coba decode sebagai teks plain
        try:
            text = content.decode("utf-8")
            if text.strip():
                print("DEBUG: Berhasil ekstrak sebagai teks plain")
                return text[:15000]
        except:
            pass

        # Coba ekstrak dari HTML
        try:
            soup = BeautifulSoup(content, "lxml")
            html_text = soup.get_text(separator="\n")
            if html_text.strip():
                print("DEBUG: Berhasil ekstrak teks dari HTML")
                return html_text[:15000]
        except Exception as e_html:
            print(f"DEBUG: HTML parse gagal: {e_html}")

        return "❌ URL tidak mengarah ke PDF, teks, atau halaman web yang dapat diproses"

    except Exception as e:
        return f"❌ Error memproses URL: {str(e)}"

# Endpoint ringkasan
@app.post("/summarize")
async def summarize_api(
    file: UploadFile = File(None),
    text: str = Form(""),
    url: str = Form(""),
    max_tokens: int = Form(512)
):
    try:
        input_text = ""
        source_type = ""

        if file and file.filename:
            if file.filename.lower().endswith('.pdf'):
                input_text = extract_text_from_pdf(file.file)
                if not input_text:
                    return {"error": "PDF tidak memiliki teks yang bisa diproses"}
                source_type = "PDF file"
            else:
                return {"error": "Hanya file PDF yang didukung"}

        elif url.strip():
            input_text = process_url(url.strip())
            if not input_text or input_text.startswith("❌"):
                return {"error": input_text}
            source_type = "URL"

        elif text.strip():
            input_text = text.strip()
            source_type = "Direct text"
        else:
            return {"error": "Masukkan teks, upload file PDF, atau URL terlebih dahulu."}

        if len(input_text.strip()) < 10:
            return {"error": "Teks terlalu pendek atau tidak dapat dibaca"}

        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""
        Ringkas teks berikut dalam bahasa Indonesia yang jelas dan mudah dipahami. 
        Fokus pada ide utama dan poin-poin penting.

        TEKS:
        {input_text[:10000]}

        RINGKASAN:
        """
        response = model.generate_content(prompt)
        if not response.text or not response.text.strip():
            return {"error": "Gagal menghasilkan ringkasan"}

        return {
            "summary": response.text.strip(),
            "source_type": source_type,
            "original_length": len(input_text)
        }

    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}

@app.get("/")
def root():
    return {"message": "Backend is running ✅"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
