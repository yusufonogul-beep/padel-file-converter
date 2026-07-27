# File Converter Web App

A professional, ad-supported file conversion website with the following features:

- PDF ➜ Word (DOCX) conversion
- Word (DOC/DOCX) ➜ PDF conversion
- Image format conversion (PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP)
- Image compression (quality configurable)
- Separate SEO‑friendly routes: `/pdf-to-word`, `/word-to-pdf`, `/image-converter`, `/image-compressor`
- Modern, clean SaaS UI (inspired by TinyPNG, iLovePDF, CloudConvert)
- Fully responsive design
- Ad spaces integrated into the layout (header banner and inline rectangle)

## 📦 Requirements

- Python 3.11+
- LibreOffice (for DOCX ➜ PDF conversion) – installed via the Dockerfile
- See `requirements.txt` for Python dependencies

## 🐳 Docker

The provided `Dockerfile` builds a production‑ready image:

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKDIR=/app

# Install system dependencies (LibreOffice for document conversion)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice \
        libreoffice-core \
        fonts-dejavu-core \
        fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

# Create a non‑root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app
COPY --chown=appuser:appuser . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non‑root user
USER appuser

# Expose the port the app runs on (default 8000, overridable via PORT env)
EXPOSE 8000
ENV PORT=8000

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "app:app"]
```

## 🚀 Local Development

1. Clone the repository.
2. Create a virtual environment:  
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Install LibreOffice locally for DOCX→PDF conversion.
5. Run the app:  
   ```bash
   python app.py
   ```
   The server will be available at `http://localhost:5000`.

## ☁️ Deployment on Render.com

1. Push this repository to GitHub (or any Git provider).
2. In Render.com, create a **New Web Service** and connect your repository.
3. Choose **Environment: Docker**.
4. Leave the **Build Command** blank (the Dockerfile handles the build).
5. The **Start Command** will be taken from the Dockerfile (`CMD`).  
   You can also explicitly set it to `gunicorn --bind 0.0.0.0:$PORT app:app`.
6. (Optional) Add environment variables if you integrate third‑party services (e.g., ad scripts, analytics).
7. Click **Create Web Service**. Render will build the Docker image and deploy it.
8. Once deployed, visit the provided `.onrender.com` URL to use the app.

## 📂 Project Structure

```
.
├── app.py                 # Main Flask application
├── Dockerfile             # Container build instructions
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── templates/
    ├── base.html          # Base template with UI and ad placeholders
    ├── index.html         # Landing page
    ├── pdf_to_word.html
    ├── word_to_pdf.html
    ├── image_converter.html
    └── image_compressor.html
```

## 🎨 Design Choices

- **Typography**: Inter font (Google Fonts) for a clean, modern look.
- **Color Palette**: Blues (`#2563eb` primary) with gray backgrounds – calm and professional.
- **Layout**: Centered content, generous whitespace, consistent card‑style sections.
- **Responsiveness**: Flexbox/Grid layout, mobile‑first breakpoints (Tailwind CDN).
- **Ad Integration**: Placeholder blocks (`header` banner and `inline rectangle`) are styled to blend naturally; replace the placeholder text with actual ad code (e.g., Google AdSense) when ready to monetize.
- **User Experience**: Single‑file upload per conversion, instant feedback, automatic cleanup of temporary files.

## ✅ Tested Features (local)

| Feature                     | Status |
|-----------------------------|--------|
| Home page (`/`)             | ✅ 200 |
| PDF → Word (`/pdf-to-word`) | ✅ 200, returns DOCX |
| Word → PDF (`/word-to-pdf`) | ⚠️ Requires LibreOffice (available in Docker) |
| Image converter (PNG→JPG)   | ✅ 200 |
| Image compressor (PNG, q=50) | ✅ 200 |
| File size limit (50 MB)     | ✅ Enforced |
| Error handling (missing file, wrong type) | ✅ Flash messages |

## 📝 Notes

- The `docx2pdf` package has been **removed** because it depends on Microsoft Word (Windows/macOS). Linux‑based DOCX→PDF conversion is handled via LibreOffice’s `soffice` command.
- The app automatically cleans up uploaded and output files after the response is sent (using `response.call_on_close`).
- All routes protect against path‑traversal and enforce allowed extensions.
- The Docker image runs as a non‑root user for security.

---

**Ready for deployment!** 🎉# Rebuild trigger
Last rebuild trigger: Mon Jul 27 14:16:59 UTC 2026
