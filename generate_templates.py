import os

base_template = '''{% extends "base_converter.html" %}
{% set title = "%TITLE%" %}
{% set meta_desc = "%META_DESC%" %}
{% set h1 = "%H1%" %}
{% set description = "%DESCRIPTION%" %}
{% set upload_icon = "%UPLOAD_ICON%" %}
{% set upload_text = "%UPLOAD_TEXT%" %}
{% set upload_hint = "%UPLOAD_HINT%" %}
{% set accept_ext = "%ACCEPT_EXT%" %}
{% set button_text = "%BUTTON_TEXT%" %}
{% set step2_desc = "%STEP2_DESC%" %}
{% set extra_fields = """
%EXTRA_FIELDS%
""" %}
{% set related_tools = [
%RELATED_TOOLS%
] %}
{% set schema_name = "%SCHEMA_NAME%" %}
{% set schema_desc = "%SCHEMA_DESC%" %}
{% block content %}{{ super() }}{% endblock %}
'''

converters = [
    {
        'file': 'compress_pdf.html',
        'title': 'Compress PDF - Snapverto',
        'meta_desc': 'Reduce PDF file size without losing quality. Free online PDF compressor.',
        'h1': 'Compress PDF',
        'description': 'Reduce PDF file size while maintaining quality. Perfect for sharing and storage.',
        'upload_icon': '📉',
        'upload_text': 'Select PDF File or Drag & Drop',
        'upload_hint': 'Upload the PDF to compress',
        'accept_ext': '.pdf',
        'button_text': 'Compress & Download',
        'step2_desc': 'Choose compression level',
        'extra_fields': '''
        <div class="form-group">
            <label>Compression Level (1-100, default 50)</label>
            <input type="number" name="quality" min="1" max="100" value="50">
        </div>
        ''',
        'related_tools': [
            {'url': '/merge-pdf', 'icon': '📋', 'name': 'Merge PDF', 'desc': 'Combine PDF files'},
            {'url': '/split-pdf', 'icon': '✂️', 'name': 'Split PDF', 'desc': 'Extract pages from PDF'},
            {'url': '/pdf-to-word', 'icon': '📄→📝', 'name': 'PDF to Word', 'desc': 'Convert PDF to editable DOC'}
        ],
        'schema_name': 'Compress PDF - Snapverto',
        'schema_desc': 'Reduce PDF file size without losing quality. Free online PDF compressor.'
    },
    {
        'file': 'pdf_password_remove.html',
        'title': 'Remove PDF Password - Snapverto',
        'meta_desc': 'Remove password protection from PDF files. Free online PDF unlocker.',
        'h1': 'Remove PDF Password',
        'description': 'Unlock password-protected PDF files quickly and easily.',
        'upload_icon': '🔓',
        'upload_text': 'Select PDF File or Drag & Drop',
        'upload_hint': 'Upload the encrypted PDF',
        'accept_ext': '.pdf',
        'button_text': 'Remove Password & Download',
        'step2_desc': 'Enter the password',
        'extra_fields': '''
        <div class="form-group">
            <label>File Password</label>
            <input type="password" name="password" required>
        </div>
        ''',
        'related_tools': [
            {'url': '/add-pdf-password', 'icon': '🔒', 'name': 'Add PDF Password', 'desc': 'Protect PDF with password'},
            {'url': '/merge-pdf', 'icon': '📋', 'name': 'Merge PDF', 'desc': 'Combine PDF files'},
            {'url': '/split-pdf', 'icon': '✂️', 'name': 'Split PDF', 'desc': 'Extract pages from PDF'}
        ],
        'schema_name': 'Remove PDF Password - Snapverto',
        'schema_desc': 'Remove password protection from PDF files. Free online PDF unlocker.'
    },
    {
        'file': 'pdf_password_protect.html',
        'title': 'Add PDF Password - Snapverto',
        'meta_desc': 'Add password protection to PDF files. Free online PDF protector.',
        'h1': 'Add PDF Password',
        'description': 'Secure your PDF files with password protection.',
        'upload_icon': '🔒',
        'upload_text': 'Select PDF File or Drag & Drop',
        'upload_hint': 'Upload the PDF to protect',
        'accept_ext': '.pdf',
        'button_text': 'Add Password & Download',
        'step2_desc': 'Set a strong password',
        'extra_fields': '''
        <div class="form-group">
            <label>New Password</label>
            <input type="password" name="password" required>
        </div>
        ''',
        'related_tools': [
            {'url': '/remove-pdf-password', 'icon': '🔓', 'name': 'Remove PDF Password', 'desc': 'Unlock PDF files'},
            {'url': '/merge-pdf', 'icon': '📋', 'name': 'Merge PDF', 'desc': 'Combine PDF files'},
            {'url': '/split-pdf', 'icon': '✂️', 'name': 'Split PDF', 'desc': 'Extract pages from PDF'}
        ],
        'schema_name': 'Add PDF Password - Snapverto',
        'schema_desc': 'Add password protection to PDF files. Free online PDF protector.'
    },
    {
        'file': 'pdf_to_jpg.html',
        'title': 'PDF to JPG - Snapverto',
        'meta_desc': 'Convert PDF pages to JPG images. Free online PDF to image converter.',
        'h1': 'PDF to JPG',
        'description': 'Convert each page of your PDF to high-quality JPG images.',
        'upload_icon': '📄↔️🖼️',
        'upload_text': 'Select PDF File or Drag & Drop',
        'upload_hint': 'Upload the PDF to convert',
        'accept_ext': '.pdf',
        'button_text': 'Convert & Download',
        'step2_desc': 'Choose image resolution (DPI)',
        'extra_fields': '''
        <div class="form-group">
            <label>Resolution (DPI, default 150)</label>
            <input type="number" name="dpi" min="72" max="300" value="150">
        </div>
        ''',
        'related_tools': [
            {'url': '/jpg-to-pdf', 'icon': '🖼️→📄', 'name': 'JPG to PDF', 'desc': 'Convert images to PDF'},
            {'url': '/pdf-to-word', 'icon': '📄→📝', 'name': 'PDF to Word', 'desc': 'Convert PDF to editable DOC'},
            {'url': '/compress-pdf', 'icon': '📉', 'name': 'Compress PDF', 'desc': 'Reduce PDF file size'}
        ],
        'schema_name': 'PDF to JPG - Snapverto',
        'schema_desc': 'Convert PDF pages to JPG images. Free online PDF to image converter.'
    },
    {
        'file': 'jpg_to_pdf.html',
        'title': 'JPG to PDF - Snapverto',
        'meta_desc': 'Convert JPG images to PDF. Free online image to PDF converter.',
        'h1': 'JPG to PDF',
        'description': 'Combine one or more JPG images into a single PDF document.',
        'upload_icon': '🖼️→📄',
        'upload_text': 'Select Image Files or Drag & Drop',
        'upload_hint': 'Upload one or more JPG files',
        'accept_ext': '.jpg,.jpeg',
        'button_text': 'Create PDF & Download',
        'step2_desc': 'Arrange your images in order',
        'extra_fields': '',
        'related_tools': [
            {'url': '/pdf-to-jpg', 'icon': '📄↔️🖼️', 'name': 'PDF to JPG', 'desc': 'Convert PDF to images'},
            {'url': '/image-converter', 'icon': '🎨', 'name': 'Image Converter', 'desc': 'Convert between image formats'},
            {'url': '/image-compressor', 'icon': '📦', 'name': 'Compress Images', 'desc': 'Reduce image file size'}
        ],
        'schema_name': 'JPG to PDF - Snapverto',
        'schema_desc': 'Convert JPG images to PDF. Free online image to PDF converter.'
    },
    {
        'file': 'rotate_pdf.html',
        'title': 'Rotate PDF - Snapverto',
        'meta_desc': 'Rotate PDF pages by 90, 180, or 270 degrees. Free online PDF rotator.',
        'h1': 'Rotate PDF',
        'description': 'Rotate specific pages or entire PDF documents with ease.',
        'upload_icon': '🔄',
        'upload_text': 'Select PDF File or Drag & Drop',
        'upload_hint': 'Upload the PDF to rotate',
        'accept_ext': '.pdf',
        'button_text': 'Rotate & Download',
        'step2_desc': 'Select rotation angle',
        'extra_fields': '''
        <div class="form-group">
            <label>Rotation Degree</label>
            <select name="rotation" required>
                <option value="90">90°</option>
                <option value="180">180°</option>
                <option value="270">270°</option>
            </select>
        </div>
        ''',
        'related_tools': [
            {'url': '/merge-pdf', 'icon': '📋', 'name': 'Merge PDF', 'desc': 'Combine PDF files'},
            {'url': '/split-pdf', 'icon': '✂️', 'name': 'Split PDF', 'desc': 'Extract pages from PDF'},
            {'url': '/compress-pdf', 'icon': '📉', 'name': 'Compress PDF', 'desc': 'Reduce PDF file size'}
        ],
        'schema_name': 'Rotate PDF - Snapverto',
        'schema_desc': 'Rotate PDF pages by 90, 180, or 270 degrees. Free online PDF rotator.'
    },
    {
        'file': 'heic_to_jpg.html',
        'title': 'HEIC to JPG - Snapverto',
        'meta_desc': 'Convert HEIC photos to JPG. Free online HEIC converter for iPhone photos.',
        'h1': 'HEIC to JPG',
        'description': 'Convert iPhone HEIC photos to universally compatible JPG format.',
        'upload_icon': '📱→🖼️',
        'upload_text': 'Select HEIC File or Drag & Drop',
        'upload_hint': 'Upload your iPhone photo',
        'accept_ext': '.heic,.heif',
        'button_text': 'Convert & Download',
        'step2_desc': 'Adjust image quality',
        'extra_fields': '''
        <div class="form-group">
            <label>Quality (1-100, default 85)</label>
            <input type="number" name="quality" min="1" max="100" value="85">
        </div>
        ''',
        'related_tools': [
            {'url': '/image-converter', 'icon': '🎨', 'name': 'Image Converter', 'desc': 'Convert between image formats'},
            {'url': '/image-compressor', 'icon': '📦', 'name': 'Compress Images', 'desc': 'Reduce image file size'},
            {'url': '/image-resize', 'icon': '📏', 'name': 'Resize Images', 'desc': 'Change image dimensions'}
        ],
        'schema_name': 'HEIC to JPG - Snapverto',
        'schema_desc': 'Convert HEIC photos to JPG. Free online HEIC converter for iPhone photos.'
    },
    {
        'file': 'image_resize.html',
        'title': 'Resize Images - Snapverto',
        'meta_desc': 'Resize images in batch. Change width, height, or percentage. Free online image resizer.',
        'h1': 'Resize Images',
        'description': 'Resize multiple images at once while maintaining aspect ratio if desired.',
        'upload_icon': '📏',
        'upload_text': 'Select Image Files or Drag & Drop',
        'upload_hint': 'PNG, JPG, GIF, WebP, BMP supported',
        'accept_ext': '.png,.jpg,.jpeg,.gif,.bmp,.webp',
        'button_text': 'Resize & Download',
        'step2_desc': 'Set dimensions or scale percentage',
        'extra_fields': '''
        <div class="form-group">
            <label>Width (px, optional)</label>
            <input type="number" name="width" min="1">
        </div>
        <div class="form-group">
            <label>Height (px, optional)</label>
            <input type="number" name="height" min="1">
        </div>
        <div class="form-group">
            <label>Scale (%, optional)</label>
            <input type="number" name="percentage" min="1" max="500">
        </div>
        ''',
        'related_tools': [
            {'url': '/image-converter', 'icon': '🎨', 'name': 'Image Converter', 'desc': 'Convert between image formats'},
            {'url': '/image-compressor', 'icon': '📦', 'name': 'Compress Images', 'desc': 'Reduce image file size'},
            {'url': '/heic-to-jpg', 'icon': '📱→🖼️', 'name': 'HEIC to JPG', 'desc': 'Convert iPhone photos'}
        ],
        'schema_name': 'Resize Images - Snapverto',
        'schema_desc': 'Resize images in batch. Change width, height, or percentage. Free online image resizer.'
    },
    {
        'file': 'image_converter.html',
        'title': 'Image Converter - Snapverto',
        'meta_desc': 'Convert images between PNG, JPG, WebP, GIF formats. Free online image converter.',
        'h1': 'Image Converter',
        'description': 'Convert between various image formats quickly and easily.',
        'upload_icon': '🎨',
        'upload_text': 'Select Image File or Drag & Drop',
        'upload_hint': 'Supported formats: PNG, JPG, GIF, BMP, WebP',
        'accept_ext': '.png,.jpg,.jpeg,.gif,.bmp,.webp',
        'button_text': 'Convert & Download',
        'step2_desc': 'Choose output format',
        'extra_fields': '''
        <div class="form-group">
            <label>Output Format</label>
            <select name="format" required>
                <option value="png">PNG (Lossless)</option>
                <option value="jpg">JPG (Compressed)</option>
                <option value="webp">WebP (Modern)</option>
                <option value="gif">GIF</option>
            </select>
        </div>
        ''',
        'related_tools': [
            {'url': '/image-resize', 'icon': '📏', 'name': 'Resize Images', 'desc': 'Change image dimensions'},
            {'url': '/image-compressor', 'icon': '📦', 'name': 'Compress Images', 'desc': 'Reduce image file size'},
            {'url': '/heic-to-jpg', 'icon': '📱→🖼️', 'name': 'HEIC to JPG', 'desc': 'Convert iPhone photos'}
        ],
        'schema_name': 'Image Converter - Snapverto',
        'schema_desc': 'Convert images between PNG, JPG, WebP, GIF formats. Free online image converter.'
    },
    {
        'file': 'image_compressor.html',
        'title': 'Compress Images - Snapverto',
        'meta_desc': 'Compress images without losing quality. Free online image compressor for web.',
        'h1': 'Compress Images',
        'description': 'Reduce image file size while preserving visual quality.',
        'upload_icon': '📦',
        'upload_text': 'Select Image Files or Drag & Drop',
        'upload_hint': 'PNG, JPG, GIF, WebP, BMP supported',
        'accept_ext': '.png,.jpg,.jpeg,.gif,.bmp,.webp',
        'button_text': 'Compress & Download',
        'step2_desc': 'Set compression quality',
        'extra_fields': '''
        <div class="form-group">
            <label>Compression Level (1-100, default 80)</label>
            <input type="number" name="quality" min="1" max="100" value="80">
        </div>
        ''',
        'related_tools': [
            {'url': '/image-resize', 'icon': '📏', 'name': 'Resize Images', 'desc': 'Change image dimensions'},
            {'url': '/image-converter', 'icon': '🎨', 'name': 'Image Converter', 'desc': 'Convert between image formats'},
            {'url': '/heic-to-jpg', 'icon': '📱→🖼️', 'name': 'HEIC to JPG', 'desc': 'Convert iPhone photos'}
        ],
        'schema_name': 'Compress Images - Snapverto',
        'schema_desc': 'Compress images without losing quality. Free online image compressor for web.'
    },
    {
        'file': 'pdf_to_word.html',
        'title': 'PDF to Word - Snapverto',
        'meta_desc': 'Convert PDF to editable Word document. Free online PDF to DOCX converter.',
        'h1': 'PDF to Word',
        'description': 'Convert PDF files to editable Word documents while preserving text and layout.',
        'upload_icon': '📄→📝',
        'upload_text': 'Select PDF File or Drag & Drop',
        'upload_hint': 'Upload the PDF to convert',
        'accept_ext': '.pdf',
        'button_text': 'Convert & Download',
        'step2_desc': 'Conversion happens automatically',
        'extra_fields': '',
        'related_tools': [
            {'url': '/word-to-pdf', 'icon': '📝→📄', 'name': 'Word to PDF', 'desc': 'Convert Word to PDF'},
            {'url': '/merge-pdf', 'icon': '📋', 'name': 'Merge PDF', 'desc': 'Combine PDF files'},
            {'url': '/compress-pdf', 'icon': '📉', 'name': 'Compress PDF', 'desc': 'Reduce PDF file size'}
        ],
        'schema_name': 'PDF to Word - Snapverto',
        'schema_desc': 'Convert PDF to editable Word document. Free online PDF to DOCX converter.'
    },
    {
        'file': 'word_to_pdf.html',
        'title': 'Word to PDF - Snapverto',
        'meta_desc': 'Convert Word to PDF. Free online DOCX to PDF converter.',
        'h1': 'Word to PDF',
        'description': 'Convert Word documents to universal PDF format with professional appearance.',
        'upload_icon': '📝→📄',
        'upload_text': 'Select Word File or Drag & Drop',
        'upload_hint': 'DOC and DOCX files supported',
        'accept_ext': '.doc,.docx',
        'button_text': 'Convert & Download',
        'step2_desc': 'Conversion happens automatically',
        'extra_fields': '',
        'related_tools': [
            {'url': '/pdf-to-word', 'icon': '📄→📝', 'name': 'PDF to Word', 'desc': 'Convert PDF to DOCX'},
            {'url': '/compress-pdf', 'icon': '📉', 'name': 'Compress PDF', 'desc': 'Reduce PDF file size'},
            {'url': '/merge-pdf', 'icon': '📋', 'name': 'Merge PDF', 'desc': 'Combine PDF files'}
        ],
        'schema_name': 'Word to PDF - Snapverto',
        'schema_desc': 'Convert Word to PDF. Free online DOCX to PDF converter.'
    }
]

output_dir = '/opt/data/file_converter/templates'
for conv in converters:
    tpl = base_template
    tpl = tpl.replace('%TITLE%', conv['title'])
    tpl = tpl.replace('%META_DESC%', conv['meta_desc'])
    tpl = tpl.replace('%H1%', conv['h1'])
    tpl = tpl.replace('%DESCRIPTION%', conv['description'])
    tpl = tpl.replace('%UPLOAD_ICON%', conv['upload_icon'])
    tpl = tpl.replace('%UPLOAD_TEXT%', conv['upload_text'])
    tpl = tpl.replace('%UPLOAD_HINT%', conv['upload_hint'])
    tpl = tpl.replace('%ACCEPT_EXT%', conv['accept_ext'])
    tpl = tpl.replace('%BUTTON_TEXT%', conv['button_text'])
    tpl = tpl.replace('%STEP2_DESC%', conv['step2_desc'])
    tpl = tpl.replace('%EXTRA_FIELDS%', conv['extra_fields'].strip())
    
    # Build related_tools list as Python list of dicts string
    related_items = []
    for tool in conv['related_tools']:
        related_items.append("{'url': '" + tool['url'] + "', 'icon': '" + tool['icon'] + "', 'name': '" + tool['name'] + "', 'desc': '" + tool['desc'] + "'}")
    related_str = ',\n'.join(related_items)
    tpl = tpl.replace('%RELATED_TOOLS%', related_str)
    
    tpl = tpl.replace('%SCHEMA_NAME%', conv['schema_name'])
    tpl = tpl.replace('%SCHEMA_DESC%', conv['schema_desc'])
    
    path = os.path.join(output_dir, conv['file'])
    with open(path, 'w') as f:
        f.write(tpl)
    print(f'Generated {path}')