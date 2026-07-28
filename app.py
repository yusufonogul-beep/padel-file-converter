import os
import uuid
import traceback
import subprocess
import io
from datetime import datetime
from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from PIL import Image
from pypdf import PdfReader, PdfWriter

# pillow-heif for HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
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
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'heic', 'heif'
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


# ==================== NEW PDF TOOLS ====================

def merge_pdfs(input_paths, output_path):
    """Merge multiple PDF files into one."""
    writer = PdfWriter()
    for path in input_paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


def split_pdf(input_path, output_dir, ranges=None):
    """Split PDF into separate files. ranges is list of (start, end) page tuples (0-indexed)."""
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    
    if not ranges:
        # Split into individual pages
        ranges = [(i, i+1) for i in range(total_pages)]
    
    output_files = []
    for i, (start, end) in enumerate(ranges):
        writer = PdfWriter()
        for page_num in range(start, min(end, total_pages)):
            writer.add_page(reader.pages[page_num])
        output_filename = f'split_{i+1}_pages_{start+1}-{min(end, total_pages)}.pdf'
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'wb') as f:
            writer.write(f)
        output_files.append(output_path)
    return output_files


def compress_pdf(input_path, output_path, quality=50):
    """Compress PDF by downsampling images. quality: 1-100."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        # Compress images on each page
        if '/Resources' in page:
            page.compress_content_streams()
        writer.add_page(page)
    
    # Additional compression by reducing image quality
    # Note: pypdf doesn't directly support image quality reduction
    # We save with compression
    with open(output_path, 'wb') as f:
        writer.write(f)


def remove_pdf_password(input_path, output_path, password):
    """Remove password from encrypted PDF."""
    reader = PdfReader(input_path)
    if reader.is_encrypted:
        try:
            reader.decrypt(password)
        except Exception as e:
            raise ValueError(f"Yanlış şifre: {str(e)}")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


def add_pdf_password(input_path, output_path, password):
    """Add password protection to PDF."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_path, 'wb') as f:
        writer.write(f)


def pdf_to_jpg(input_path, output_dir, dpi=150):
    """Convert each PDF page to JPG image. Returns list of output paths."""
    # Use pdf2image or convert via PIL
    # For simplicity, we'll use a different approach - convert via subprocess with pdftoppm or similar
    # But since we don't have poppler installed, we'll use a workaround
    # Actually, let's use pdf2image which requires poppler - we need to install it
    # For now, let's use a simple approach with fitz (PyMuPDF) if available
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(input_path)
        output_files = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            output_filename = f'page_{page_num+1}.jpg'
            output_path = os.path.join(output_dir, output_filename)
            pix.save(output_path)
            output_files.append(output_path)
        doc.close()
        return output_files
    except ImportError:
        # Fallback: try pdf2image
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(input_path, dpi=dpi)
            output_files = []
            for i, img in enumerate(images):
                output_filename = f'page_{i+1}.jpg'
                output_path = os.path.join(output_dir, output_filename)
                img.save(output_path, 'JPEG', quality=85)
                output_files.append(output_path)
            return output_files
        except ImportError:
            raise RuntimeError("PDF to JPG conversion requires PyMuPDF (fitz) or pdf2image with poppler")


def jpg_to_pdf(input_paths, output_path):
    """Convert one or more images to a single PDF."""
    images = []
    for path in input_paths:
        img = Image.open(path)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        images.append(img)
    
    if images:
        images[0].save(output_path, 'PDF', save_all=True, append_images=images[1:])


def rotate_pdf(input_path, output_path, rotations):
    """Rotate specific pages. rotations: dict of page_index -> rotation_angle (90, 180, 270)."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in rotations:
            page.rotate(rotations[i])
        writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)


# ==================== NEW IMAGE TOOLS ====================

def heic_to_jpg(input_path, output_path, quality=85):
    """Convert HEIC/HEIF to JPG."""
    img = Image.open(input_path)
    if img.mode in ('RGBA', 'LA', 'P'):
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = rgb_img
    img.save(output_path, 'JPEG', quality=quality)


def batch_resize_images(input_paths, output_dir, width=None, height=None, percentage=None):
    """Resize multiple images. Returns list of output paths."""
    output_files = []
    for i, path in enumerate(input_paths):
        img = Image.open(path)
        orig_width, orig_height = img.size
        
        if percentage:
            new_width = int(orig_width * percentage / 100)
            new_height = int(orig_height * percentage / 100)
        elif width and height:
            new_width, new_height = width, height
        elif width:
            new_width = width
            new_height = int(orig_height * width / orig_width)
        elif height:
            new_height = height
            new_width = int(orig_width * height / orig_height)
        else:
            raise ValueError("En az bir boyut (width, height veya percentage) belirtilmeli")
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            fmt = 'JPEG'
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
        elif ext == '.png':
            fmt = 'PNG'
        elif ext == '.webp':
            fmt = 'WEBP'
        else:
            fmt = 'PNG'
        
        output_filename = f'resized_{i+1}{ext}'
        output_path = os.path.join(output_dir, output_filename)
        save_params = {}
        if fmt in ('JPEG', 'WEBP'):
            save_params['quality'] = 85
        img.save(output_path, format=fmt, **save_params)
        output_files.append(output_path)
    return output_files


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


# ==================== NEW PDF TOOL FUNCTIONS ====================

def add_pdf_password(input_path, output_path, password):
    """Add password protection to PDF."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
    
    writer.encrypt(password)
    
    with open(output_path, 'wb') as f:
        writer.write(f)


def remove_pdf_password(input_path, output_path, password):
    """Remove password from encrypted PDF."""
    reader = PdfReader(input_path)
    if reader.is_encrypted:
        try:
            reader.decrypt(password)
        except:
            raise ValueError("Yanlış şifre veya şifreli değil")
    else:
        raise ValueError("Bu PDF şifreli değil")
    
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    
    with open(output_path, 'wb') as f:
        writer.write(f)


def pdf_to_jpg(input_path, output_dir, dpi=150):
    """Convert PDF pages to JPG images."""
    import fitz  # PyMuPDF
    doc = fitz.open(input_path)
    output_files = []
    
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        output_filename = f'page_{i+1}.jpg'
        output_path = os.path.join(output_dir, output_filename)
        pix.save(output_path)
        output_files.append(output_path)
    
    doc.close()
    return output_files


def jpg_to_pdf(input_paths, output_path):
    """Convert one or more images to PDF."""
    # Sort by filename to maintain order
    images = []
    for path in input_paths:
        img = Image.open(path)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        elif img.mode == 'P':
            img = img.convert('RGB')
        images.append(img)
    
    if images:
        images[0].save(output_path, save_all=True, append_images=images[1:])
    else:
        raise ValueError("No valid images provided")


def rotate_pdf(input_path, output_path, rotations):
    """Rotate specific pages in PDF. rotations: {page_index: angle}"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for i, page in enumerate(reader.pages):
        if i in rotations:
            page.rotate(rotations[i])
        writer.add_page(page)
    
    with open(output_path, 'wb') as f:
        writer.write(f)


def heic_to_jpg(input_path, output_path, quality=85):
    """Convert HEIC/HEIF to JPG."""
    img = Image.open(input_path)
    if img.mode in ('RGBA', 'LA', 'P'):
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = rgb_img
    img.save(output_path, format='JPEG', quality=quality)


def batch_resize_images(input_paths, output_dir, width=None, height=None, percentage=None):
    """Resize multiple images."""
    output_files = []
    
    for i, path in enumerate(input_paths):
        img = Image.open(path)
        original_width, original_height = img.size
        
        if percentage:
            new_width = int(original_width * percentage / 100)
            new_height = int(original_height * percentage / 100)
        elif width and height:
            new_width = width
            new_height = height
        elif width:
            ratio = width / original_width
            new_width = width
            new_height = int(original_height * ratio)
        elif height:
            ratio = height / original_height
            new_height = height
            new_width = int(original_width * ratio)
        else:
            new_width, new_height = original_width, original_height
        
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Preserve format
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            fmt = 'JPEG'
            if resized.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', resized.size, (255, 255, 255))
                rgb_img.paste(resized, mask=resized.split()[-1] if resized.mode == 'RGBA' else None)
                resized = rgb_img
        elif ext == '.png':
            fmt = 'PNG'
        elif ext == '.webp':
            fmt = 'WEBP'
        elif ext in ('.heic', '.heif'):
            fmt = 'JPEG'
            if resized.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', resized.size, (255, 255, 255))
                rgb_img.paste(resized, mask=resized.split()[-1] if resized.mode == 'RGBA' else None)
                resized = rgb_img
        else:
            fmt = 'JPEG'
            if resized.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', resized.size, (255, 255, 255))
                rgb_img.paste(resized, mask=resized.split()[-1] if resized.mode == 'RGBA' else None)
                resized = rgb_img
        
        output_filename = f'resized_{i+1}_{os.path.basename(path).rsplit(".",1)[0]}.{ext.lstrip(".")}'
        if fmt == 'JPEG' and ext not in ('.jpg', '.jpeg'):
            output_filename = output_filename.rsplit('.', 1)[0] + '.jpg'
        elif fmt == 'PNG' and ext != '.png':
            output_filename = output_filename.rsplit('.', 1)[0] + '.png'
        
        output_path = os.path.join(output_dir, output_filename)
        resized.save(output_path, format=fmt, quality=85)
        output_files.append(output_path)
    
    return output_files


# ==================== NEW PDF TOOL ROUTES ====================

@app.route('/merge-pdf', methods=['GET', 'POST'])
def merge_pdf():
    if request.method == 'POST':
        if 'files' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        
        pdf_files = []
        for file in files:
            if file and allowed_file(file.filename) and get_ext(file.filename) == 'pdf':
                filename = secure_filename(file.filename)
                uid = uuid.uuid4().hex
                input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
                file.save(input_path)
                pdf_files.append(input_path)
            else:
                flash('Sadece PDF dosyaları yükleyebilirsiniz', 'error')
                cleanup_files(*pdf_files)
                return redirect(request.url)
        
        if len(pdf_files) < 2:
            flash('En az 2 PDF dosyası seçmelisiniz', 'error')
            cleanup_files(*pdf_files)
            return redirect(request.url)
        
        uid = uuid.uuid4().hex
        output_filename = f'{uid}_merged.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            merge_pdfs(pdf_files, output_path)
            response = send_file(output_path, as_attachment=True, download_name='merged.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(*pdf_files, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Birleştirme hatası: {str(e)}', 'error')
            cleanup_files(*pdf_files, output_path)
            return redirect(request.url)
    return render_template('merge_pdf.html')


@app.route('/split-pdf', methods=['GET', 'POST'])
def split_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyası yükleyebilirsiniz', 'error')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        
        # Parse page ranges
        ranges_input = request.form.get('ranges', '').strip()
        ranges = None
        if ranges_input:
            try:
                ranges = []
                for part in ranges_input.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = part.split('-')
                        ranges.append((int(start)-1, int(end)))
                    else:
                        page = int(part)
                        ranges.append((page-1, page))
            except:
                flash('Sayfa aralıkları geçersiz (örnek: 1-3,5,7-9)', 'error')
                cleanup_files(input_path)
                return redirect(request.url)
        
        try:
            output_files = split_pdf(input_path, OUTPUT_FOLDER, ranges)
            # Create a zip file with all split PDFs
            import zipfile
            zip_uid = uuid.uuid4().hex
            zip_filename = f'{zip_uid}_split.zip'
            zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for f in output_files:
                    zf.write(f, os.path.basename(f))
            
            response = send_file(zip_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_split.zip')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, zip_path, *output_files)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Bölme hatası: {str(e)}', 'error')
            cleanup_files(input_path)
            return redirect(request.url)
    return render_template('split_pdf.html')


@app.route('/compress-pdf', methods=['GET', 'POST'])
def compress_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyası yükleyebilirsiniz', 'error')
            return redirect(request.url)
        
        try:
            quality = int(request.form.get('quality', 50))
            if quality < 1 or quality > 100:
                raise ValueError
        except:
            flash('Kalite değeri 1-100 arasında olmalı', 'error')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}_compressed.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            compress_pdf(input_path, output_path, quality)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_compressed.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Sıkıştırma hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('compress_pdf.html')


@app.route('/pdf-password-remove', methods=['GET', 'POST'])
def pdf_password_remove():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyası yükleyebilirsiniz', 'error')
            return redirect(request.url)
        
        password = request.form.get('password', '').strip()
        if not password:
            flash('Şifre girilmeli', 'error')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}_unlocked.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            remove_pdf_password(input_path, output_path, password)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_unlocked.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except ValueError as e:
            print(traceback.format_exc())
            flash(str(e), 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Şifre kaldırma hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('pdf_password_remove.html')


@app.route('/pdf-password-protect', methods=['GET', 'POST'])
def pdf_password_protect():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyası yükleyebilirsiniz', 'error')
            return redirect(request.url)
        
        password = request.form.get('password', '').strip()
        if not password:
            flash('Şifre girilmeli', 'error')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}_protected.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            add_pdf_password(input_path, output_path, password)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_protected.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Şifre ekleme hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('pdf_password_protect.html')


@app.route('/pdf-to-jpg', methods=['GET', 'POST'])
def pdf_to_jpg_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyası yükleyebilirsiniz', 'error')
            return redirect(request.url)
        
        try:
            dpi = int(request.form.get('dpi', 150))
            if dpi < 72 or dpi > 300:
                raise ValueError
        except:
            flash('DPI 72-300 arasında olmalı', 'error')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        
        try:
            output_files = pdf_to_jpg(input_path, OUTPUT_FOLDER, dpi)
            # Create zip
            import zipfile
            zip_uid = uuid.uuid4().hex
            zip_filename = f'{zip_uid}_jpg.zip'
            zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for f in output_files:
                    zf.write(f, os.path.basename(f))
            
            response = send_file(zip_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_pages.zip')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, zip_path, *output_files)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'PDF to JPG hatası: {str(e)}', 'error')
            cleanup_files(input_path)
            return redirect(request.url)
    return render_template('pdf_to_jpg.html')


@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf_route():
    if request.method == 'POST':
        if 'files' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        
        img_files = []
        for file in files:
            if file and allowed_file(file.filename) and get_ext(file.filename) in ('png','jpg','jpeg','gif','bmp','tiff','webp','heic','heif'):
                filename = secure_filename(file.filename)
                uid = uuid.uuid4().hex
                input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
                file.save(input_path)
                img_files.append(input_path)
            else:
                flash('Sadece resim dosyaları yükleyebilirsiniz', 'error')
                cleanup_files(*img_files)
                return redirect(request.url)
        
        if not img_files:
            flash('En az 1 resim dosyası seçmelisiniz', 'error')
            return redirect(request.url)
        
        uid = uuid.uuid4().hex
        output_filename = f'{uid}_images.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            jpg_to_pdf(img_files, output_path)
            response = send_file(output_path, as_attachment=True, download_name='images.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(*img_files, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'JPG to PDF hatası: {str(e)}', 'error')
            cleanup_files(*img_files, output_path)
            return redirect(request.url)
    return render_template('jpg_to_pdf.html')


@app.route('/rotate-pdf', methods=['GET', 'POST'])
def rotate_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename) or get_ext(file.filename) != 'pdf':
            flash('Sadece PDF dosyası yükleyebilirsiniz', 'error')
            return redirect(request.url)
        
        # Parse rotations
        rotations = {}
        for key, value in request.form.items():
            if key.startswith('rotate_'):
                try:
                    page_idx = int(key.split('_')[1])
                    angle = int(value)
                    if angle in (90, 180, 270):
                        rotations[page_idx] = angle
                except:
                    pass
        
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
        file.save(input_path)
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}_rotated.pdf'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            rotate_pdf(input_path, output_path, rotations)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}_rotated.pdf')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Döndürme hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('rotate_pdf.html')


# ==================== NEW IMAGE TOOL ROUTES ====================

@app.route('/heic-to-jpg', methods=['GET', 'POST'])
def heic_to_jpg_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        ext = get_ext(file.filename)
        if not allowed_file(file.filename) or ext not in ('heic', 'heif'):
            flash('Sadece HEIC/HEIF dosyaları yükleyebilirsiniz', 'error')
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
        output_filename = f'{uid}_{filename.rsplit(".",1)[0]}.jpg'
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        try:
            heic_to_jpg(input_path, output_path, quality)
            response = send_file(output_path, as_attachment=True, download_name=f'{filename.rsplit(".",1)[0]}.jpg')
            @response.call_on_close
            def cleanup():
                cleanup_files(input_path, output_path)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Dönüştürme hatası: {str(e)}', 'error')
            cleanup_files(input_path, output_path)
            return redirect(request.url)
    return render_template('heic_to_jpg.html')


@app.route('/image-resize', methods=['GET', 'POST'])
def image_resize_route():
    if request.method == 'POST':
        if 'files' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        
        img_files = []
        for file in files:
            if file and allowed_file(file.filename) and get_ext(file.filename) in ('png','jpg','jpeg','gif','bmp','tiff','webp','heic','heif'):
                filename = secure_filename(file.filename)
                uid = uuid.uuid4().hex
                input_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
                file.save(input_path)
                img_files.append(input_path)
            else:
                flash('Sadece resim dosyaları yükleyebilirsiniz', 'error')
                cleanup_files(*img_files)
                return redirect(request.url)
        
        if not img_files:
            flash('En az 1 resim dosyası seçmelisiniz', 'error')
            return redirect(request.url)
        
        # Get resize parameters
        try:
            width = request.form.get('width')
            height = request.form.get('height')
            percentage = request.form.get('percentage')
            
            if width:
                width = int(width)
            if height:
                height = int(height)
            if percentage:
                percentage = int(percentage)
            
            if not any([width, height, percentage]):
                flash('En az bir boyut (genişlik, yükseklik veya yüzde) girilmeli', 'error')
                cleanup_files(*img_files)
                return redirect(request.url)
        except:
            flash('Geçersiz boyut değerleri', 'error')
            cleanup_files(*img_files)
            return redirect(request.url)
        
        try:
            output_files = batch_resize_images(img_files, OUTPUT_FOLDER, width, height, percentage)
            # Create zip
            import zipfile
            zip_uid = uuid.uuid4().hex
            zip_filename = f'{zip_uid}_resized.zip'
            zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for f in output_files:
                    zf.write(f, os.path.basename(f))
            
            response = send_file(zip_path, as_attachment=True, download_name='resized_images.zip')
            @response.call_on_close
            def cleanup():
                cleanup_files(*img_files, zip_path, *output_files)
            return response
        except Exception as e:
            print(traceback.format_exc())
            flash(f'Yeniden boyutlandırma hatası: {str(e)}', 'error')
            cleanup_files(*img_files)
            return render_template('image_resize.html')
    
    return render_template('image_resize.html')


# ==================== LEGAL PAGES ====================

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


# ==================== STATIC PAGES ====================

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
