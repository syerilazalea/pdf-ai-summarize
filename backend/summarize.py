from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uvicorn
from io import BytesIO

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


# --- Middleware untuk membatasi ukuran upload ---
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


# --- Fungsi untuk validasi dan ekstraksi teks PDF ---
def extract_text_from_pdf(file):
    try:
        # Validasi awal: cek magic number PDF
        file_bytes = file.read()
        if not file_bytes.startswith(b"%PDF-"):
            return {"error": "File ini bukan PDF asli. Harap unggah file PDF yang valid."}

        # Kembalikan pointer ke awal agar bisa dibaca PyPDF2
        file.seek(0)
        reader = PdfReader(BytesIO(file_bytes))

        text = ""
        page_count = len(reader.pages)

        # Baca teks dari tiap halaman
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"

        # Jika tidak ada teks yang bisa diambil
        if not text.strip():
            return {"error": "PDF ini tidak mengandung teks. Kemungkinan merupakan hasil scan atau gambar."}

        # Validasi tambahan: metadata PDF
        metadata = reader.metadata
        if not metadata or "Producer" not in metadata:
            print("⚠️ Peringatan: PDF ini mungkin tidak memiliki metadata standar.")

        return {"text": text.strip(), "page_count": page_count}

    except Exception as e:
        return {"error": f"Gagal membaca file PDF: {str(e)}"}


# --- Endpoint ringkasan ---
@app.post("/summarize")
async def summarize_api(
    file: UploadFile = File(None),
    text: str = Form(""),
    max_tokens: int = Form(512)
):
    try:
        input_text = ""
        source_type = ""

        # Jika input berupa file PDF
        if file and file.filename:
            if file.filename.lower().endswith(".pdf"):
                result = extract_text_from_pdf(file.file)
                if "error" in result:
                    return {"error": result["error"]}
                input_text = result["text"]
                source_type = "PDF file"
            else:
                return {"error": "Hanya file PDF yang didukung."}

        # Jika input berupa teks langsung
        elif text.strip():
            input_text = text.strip()
            source_type = "Direct text"

        else:
            return {"error": "Masukkan teks atau upload file PDF terlebih dahulu."}

        if len(input_text.strip()) < 10:
            return {"error": "Teks terlalu pendek atau tidak dapat dibaca."}

        # Batasi panjang input untuk efisiensi
        max_input_length = 10000
        if len(input_text) > max_input_length:
            input_text = input_text[:max_input_length]

        # Gunakan model Gemini untuk membuat ringkasan
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"""
        Ringkas teks berikut dalam bahasa Indonesia yang jelas dan mudah dipahami. 
        Fokus pada ide utama dan poin-poin penting.
        Buat ringkasan dengan panjang sekitar {max_tokens} token.

        TEKS:
        {input_text}

        RINGKASAN:
        """

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens
            )
        )

        if not response.text or not response.text.strip():
            return {"error": "Gagal menghasilkan ringkasan."}

        return {
            "summary": response.text.strip(),
            "source_type": source_type,
            "original_length": len(input_text),
            "max_tokens_used": max_tokens
        }

    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}


# --- Root endpoint ---
@app.get("/")
def root():
    return {"message": "Backend is running ✅"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
