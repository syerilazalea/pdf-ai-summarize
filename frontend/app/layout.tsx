import "./globals.css";

export const metadata = {
  title: "PDF Summarizer",
  description: "Summarize PDFs using Gemini AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
