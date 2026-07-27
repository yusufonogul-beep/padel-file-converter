import os
import uuid
import traceback
import subprocess
from datetime import datetime
from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# Context processor to inject current year into all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'
}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ext(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def convert_pdf_to_docx(input_path, output_path):
    cv = Converter(input_path)
    cv.convert(output_path, start=0, end=None)
    cv.close()

def convert_docx_to_pdf(input_path, output_path):
    """
    Convert DOCX to PDF using LibreOffice's soffice command.
    Requires soffice to be in the PATH.
    """
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # The output file name will be the same as input but with .pdf
    # We'll let soffice put the file in the output directory and then rename if needed.
    # Use a temporary directory to avoid conflicts? We'll just use the output directory.
    # Run soffice in headless mode
    try:
        subprocess.run([
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(output_path),
            input_path
        ], check=True, timeout=30)
    except FileNotFoundError:
        raise RuntimeError("LibreOffice's soffice command not found. Please install LibreOffice to enable DOCX to PDF conversion.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"LibreOffice conversion failed with exit code {e.returncode}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("LibreOffice conversion timed out.")

    # Determine the actual output file produced by soffice
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    expected_path = os.path.join(os.path.dirname(output_path), base_name + '.pdf')
    if expected_path != output_path:
        # If the expected path is different from the desired output path, rename
        if os.path.exists(expected_path):
            os.rename(expected_path, output_path)
        else:
            raise FileNotFoundError(f"Expected PDF file not found at {expected_path}")
    # Ensure the output file exists
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output PDF file not found at {output_path}")

def convert_image(input_path, output_path, target_format, quality=None):
    img = Image.open(input_path)
    fmt = target_format.upper()
    if fmt == 'JPG':
        fmt = 'JPEG'
    if fmt in ('JPEG', 'BMP', 'TIFF'):
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
    elif fmt in ('PNG', 'WEBP', 'GIF'):
        if img.mode == 'P':
            img = img.convert('RGBA')
    save_params = {}
    if quality is not None and fmt in ('JPEG', 'WEBP'):
        save_params['quality'] = quality
    img.save(output_path, format=fmt, **save_params)

def compress_image(input_path, output_path, ext, quality):
    img = Image.open(input_path)
    fmt = ext.upper()
    if fmt == 'JPG':
        fmt = 'JPEG'
    save_params = {}
    if fmt in ('JPEG', 'WEBP'):
        save_params['quality'] = quality
        # For JPEG, ensure RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
    elif fmt == 'PNG':
        # PNG compression via optimize
        save_params['optimize'] = True
    elif fmt == 'GIF':
        # GIF: reduce colors? keep simple
        pass
    img.save(output_path, format=fmt, **save_params)

def cleanup_files(*paths):
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

@app.route('/')
def index():
    return render_template('index.html')

# PDF <-> Word
@app.route('/pdf-to-word', methods=['GET', 'POST'])
def pdf_to_word():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyaları yükleyebilirsiniz', 'error')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}.docx'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        try:
            convert_pdf_to_docx(input_path, output_path)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}.docx')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Dönüştürme hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('pdf_to_word.html')

@app.route('/word-to-pdf', methods=['GET', 'POST'])
def word_to_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        ext = get_ext(file.filename)
        if not allowed_file(file.filename) or ext not in ('docx', 'doc'):
            flash('Sadece DOC/DOCX dosyaları yükleyebilirsiniz', 'error')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        try:
            convert_docx_to_pdf(input_path, output_path)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Dönüştürme hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('word_to_pdf.html')

# Image conversion
@app.route('/image-converter', methods=['GET', 'POST'])
def image_converter():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        ext = get_ext(file.filename)
        if not allowed_file(file.filename) or ext not in ('png','jpg','jpeg','gif','bmp','tiff','webp'):
            flash('Sadece resim dosyaları yükleyebilirsiniz', 'error')
            return redirect(request.url)
        target_format = request.form.get('target_format', '').lower()
        if target_format not in ('png','jpg','jpeg','gif','bmp','tiff','webp'):
            flash('Geçerli hedef format seçin', 'error')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}.{target_format}'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        try:
            convert_image(input_path, output_path, target_format)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}.{target_format}')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Dönüştürme hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('image_converter.html')

# Image compression
@app.route('/image-compressor', methods=['GET', 'POST'])
def image_compressor():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        ext = get_ext(file.filename)
        if not allowed_file(file.filename) or ext not in ('png','jpg','jpeg','gif','bmp','tiff','webp'):
            flash('Sadece resim dosyaları yükleyebilirsiniz', 'error')
            return redirect(request.url)
        try:
            quality = int(request.form.get('quality', 85))
            if quality < 1 or quality > 100:
                raise ValueError
        except:
            flash('Kalite değeri 1-100 arasında olmalı', 'error')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}_compressed.{ext}'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        try:
            compress_image(input_path, output_path, ext, quality)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_compressed.{ext}')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Sıkıştırma hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('image_compressor.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)