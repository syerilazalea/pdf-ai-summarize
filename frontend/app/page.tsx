"use client";
import { useState } from "react";
import axios from "axios";

export default function Home() {
  const [mode, setMode] = useState("text");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [maxTokens, setMaxTokens] = useState(512);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const MAX_FILE_SIZE = 1 * 1024 * 1024; // 1 MB

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Validasi ukuran file
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError("❌ Ukuran file melebihi batas maksimum 1 MB.");
      setFile(null);
      e.target.value = "";
      return;
    }

    // Validasi ekstensi .pdf
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("❌ Hanya file dengan ekstensi .pdf yang diperbolehkan.");
      setFile(null);
      e.target.value = "";
      return;
    }

    setError("");
    setFile(selectedFile);
  };

  const handleSubmit = async () => {
    if (!text.trim() && !file) {
      setError("Masukkan teks atau upload file PDF terlebih dahulu.");
      return;
    }

    setLoading(true);
    setError("");
    setSummary("");

    const formData = new FormData();
    formData.append("max_tokens", maxTokens.toString());
    if (file) formData.append("file", file);
    if (text) formData.append("text", text);

    try {
      const res = await axios.post("http://localhost:5000/summarize", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Tangani pesan error dari backend (termasuk "bukan PDF asli")
      if (res.data.error) {
        setError("❌ " + res.data.error);
        return;
      }

      if (res.data.summary) {
        setSummary(res.data.summary);
      } else {
        setError("❌ Gagal menghasilkan ringkasan.");
      }
    } catch (err) {
      console.error(err);
      setError("❌ Terjadi kesalahan saat memanggil backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex flex-col items-center justify-center py-10 px-4">
      <div className="bg-white shadow-lg rounded-2xl p-8 max-w-2xl w-full">
        <h1 className="text-2xl font-bold text-blue-800 text-center">
          📄 Ringkas PDF atau Teks Milikmu
        </h1>
        <p className="text-gray-600 text-center mt-2">
          Pilih salah satu mode input untuk meringkas.
        </p>

        {/* Tombol pilihan mode */}
        <div className="flex justify-center gap-4 mt-6">
          <button
            onClick={() => setMode("text")}
            className={`px-4 py-2 rounded-lg font-medium ${
              mode === "text"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 hover:bg-gray-200"
            }`}
          >
            Teks
          </button>
          <button
            onClick={() => setMode("file")}
            className={`px-4 py-2 rounded-lg font-medium ${
              mode === "file"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 hover:bg-gray-200"
            }`}
          >
            PDF
          </button>
        </div>

        {/* Input sesuai mode */}
        <div className="mt-6">
          {mode === "text" && (
            <textarea
              placeholder="Tulis atau tempel teks di sini..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full border border-gray-300 rounded-xl p-3 min-h-[150px] focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          )}

          {mode === "file" && (
            <div>
              <label className="block font-semibold mb-2 text-gray-800">
                Upload PDF (maks. 1 MB):
              </label>
              <input
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                className="w-full text-sm text-gray-700"
              />

              {/* Keterangan tipe file */}
              <p className="text-gray-500 text-sm mt-2 flex items-start gap-1">
                <span className="text-blue-500 font-semibold">ℹ️</span>
                Hanya file PDF asli yang berisi teks 
                dengan ukuran maksimal 1 MB.
              </p>

              {/* Info file terpilih */}
              {file && (
                <p className="text-sm text-gray-500 mt-2">
                  📎 File terpilih: {file.name} (
                  {(file.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}

              {/* Pesan error untuk file */}
              {error && mode === "file" && (
                <p className="text-red-500 text-sm mt-2 whitespace-pre-line">
                  {error}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Slider token */}
        <div className="mt-6">
          <label className="block font-semibold text-gray-800">
            🔢 Batas Token Output:{" "}
            <span className="text-blue-700">{maxTokens}</span>
          </label>
          <input
            type="range"
            min="100"
            max="2048"
            step="50"
            value={maxTokens}
            onChange={(e) => setMaxTokens(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
        </div>

        {/* Tombol kirim */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className={`px-6 py-2 rounded-lg font-semibold text-white transition-transform ${
              loading
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 hover:scale-105"
            }`}
          >
            {loading ? " Meringkas..." : " Ringkas Sekarang"}
          </button>
        </div>

        {/* Pesan error umum */}
        {error && mode !== "file" && (
          <p className="text-red-500 mt-4 text-center whitespace-pre-line">
            {error}
          </p>
        )}

        {/* Hasil ringkasan */}
        {summary && (
          <div className="mt-8 border-t border-gray-200 pt-4">
            <h2 className="text-lg font-semibold text-blue-800 mb-2">
              📘 Hasil Ringkasan:
            </h2>
            <div className="bg-blue-50 p-4 rounded-xl whitespace-pre-wrap text-gray-800 leading-relaxed">
              {summary}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
