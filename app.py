import os
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def summarize_text(text):
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"Ringkas teks berikut dalam bahasa Indonesia yang jelas dan terstruktur:\n\n{text[:15000]}"
    response = model.generate_content(prompt)
    return response.text

st.set_page_config(page_title="Ringkas PDF/Teks dengan Gemini", page_icon="📄")
st.title("📄 Ringkas PDF atau Teks Milikmu !")
st.write("Unggah file PDF **atau** tulis teks langsung untuk diringkas otomatis menggunakan model Gemini AI.")

input_mode = st.radio("Pilih mode input:", ("✍️ Input Teks Manual", "📁 Upload PDF"))

text = ""

if input_mode == "✍️ Input Teks Manual":
    text = st.text_area(
        "Masukkan teks di bawah ini:",
        height=250,
        placeholder="Tulis atau tempel teks di sini..."
    )

elif input_mode == "📁 Upload PDF":
    uploaded_file = st.file_uploader("Pilih file PDF", type=["pdf"])
    if uploaded_file is not None:
        with st.spinner("📖 Membaca dan memproses PDF..."):
            text = extract_text_from_pdf(uploaded_file)

if text.strip():
    if st.button("🚀 Ringkas Sekarang"):
        with st.spinner("🤖 Sedang meringkas dengan Gemini..."):
            summary = summarize_text(text)
        st.success("✅ Ringkasan selesai!")
        st.subheader("📘 Hasil Ringkasan:")
        st.write(summary)
else:
    st.info("Silakan masukkan teks atau upload file PDF terlebih dahulu.")
