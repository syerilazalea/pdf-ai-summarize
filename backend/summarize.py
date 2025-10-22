from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uvicorn
import requests
from io import BytesIO

# 🔹 Inisialisasi FastAPI
app = FastAPI()

# 🔹 Middleware CORS (akses dari frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Load API key Gemini
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 🔹 Fungsi ekstrak teks PDF
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        page_count = 0
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
                page_count += 1
        
        if not text.strip():
            return "❌ Tidak ada teks yang dapat diekstrak dari PDF"
        
        print(f"DEBUG: Berhasil ekstrak {page_count} halaman, {len(text)} karakter")
        return text.strip()
        
    except Exception as e:
        return f"❌ Gagal membaca PDF: {str(e)}"

# 🔹 Fungsi download file dari URL
def download_file_from_url(url: str):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        print(f"DEBUG: Mengunduh dari URL: {url}")
        
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        print(f"DEBUG: Status code: {response.status_code}")
        print(f"DEBUG: Content-Type: {response.headers.get('content-type')}")
        print(f"DEBUG: Ukuran file: {len(response.content)} bytes")
        
        return response.content
        
    except Exception as e:
        raise Exception(f"Gagal mengunduh file: {str(e)}")

# 🔹 Fungsi proses URL
def process_url(url: str):
    try:
        # Download konten
        content = download_file_from_url(url)
        
        # Coba sebagai PDF terlebih dahulu
        try:
            file_bytes = BytesIO(content)
            text = extract_text_from_pdf(file_bytes)
            if not text.startswith("❌"):
                print("DEBUG: Berhasil ekstrak sebagai PDF")
                return text
        except Exception as pdf_error:
            print(f"DEBUG: Bukan PDF atau error PDF: {pdf_error}")
        
        # Jika bukan PDF, coba sebagai teks biasa
        try:
            text = content.decode('utf-8')[:15000]
            print("DEBUG: Diperlakukan sebagai teks biasa")
            return text
        except:
            # Jika decode gagal, mungkin binary file
            return "❌ URL tidak mengarah ke file PDF atau teks yang dapat diproses"
            
    except Exception as e:
        return f"❌ Error memproses URL: {str(e)}"

# 🔹 Endpoint ringkasan
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

        print(f"DEBUG: Input received - file: {file and file.filename}, text: {bool(text.strip())}, url: {url}")

        # 1️⃣ Prioritas input
        if file and file.filename:
            if file.filename.lower().endswith('.pdf'):
                input_text = extract_text_from_pdf(file.file)
                source_type = "PDF file"
            else:
                return {"error": "Hanya file PDF yang didukung"}
                
        elif url.strip():
            input_text = process_url(url.strip())
            source_type = "URL"
                
        elif text.strip():
            input_text = text.strip()
            source_type = "Direct text"
        else:
            return {"error": "Masukkan teks, upload file PDF, atau URL terlebih dahulu."}

        # 2️⃣ Validasi teks
        print(f"DEBUG: Hasil ekstraksi: {input_text[:100]}...")
        
        if not input_text or not input_text.strip():
            return {"error": "Tidak ada teks yang bisa diproses"}
            
        if input_text.startswith("❌"):
            return {"error": input_text}

        # 3️⃣ Pastikan teks tidak kosong sebelum ke Gemini
        if len(input_text.strip()) < 10:
            return {"error": "Teks terlalu pendek atau tidak dapat dibaca"}

        print(f"DEBUG: Panjang teks untuk diringkas: {len(input_text)}")

        # 4️⃣ Ringkas dengan Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Buat prompt yang lebih eksplisit
        prompt = f"""
        Ringkas teks berikut dalam bahasa Indonesia yang jelas dan mudah dipahami. 
        Fokus pada ide utama dan poin-poin penting.

        TEKS:
        {input_text[:10000]}

        RINGKASAN:
        """
        
        response = model.generate_content(prompt)
        
        # Validasi response Gemini
        if not response.text or not response.text.strip():
            return {"error": "Gagal menghasilkan ringkasan"}

        return {
            "summary": response.text.strip(),
            "source_type": source_type,
            "original_length": len(input_text)
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"error": f"Terjadi kesalahan: {str(e)}"}

# 🔹 Endpoint root
@app.get("/")
def root():
    return {"message": "Backend is running ✅"}

# 🔹 Jalankan server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)