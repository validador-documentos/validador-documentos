
import os
import secrets
from flask import Flask, request, redirect, url_for, render_template, render_template_string, send_file, abort, session, flash
from pathlib import Path
from datetime import datetime
import sqlite3
import qrcode
import io
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

BASE_DIR = Path(__file__).resolve().parent
UPLOADS = BASE_DIR / 'uploads'
UPLOADS.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / 'database.db'

BASE_URL = os.environ.get('BASE_URL', 'https://consultadocumentosacademicosestacio.onrender.com')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'adminpass')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        instituicao_id TEXT,
        nome TEXT,
        pdf_path TEXT,
        xml_path TEXT,
        qr_path TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def db_insert(record):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''INSERT INTO documents (codigo, instituicao_id, nome, pdf_path, xml_path, qr_path, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (record['codigo'], record['instituicao_id'], record['nome'], record['pdf_path'], record.get('xml_path'), record.get('qr_path'), record['created_at']))
    conn.commit()
    conn.close()

def db_get_by_codigo(codigo):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT codigo, instituicao_id, nome, pdf_path, xml_path, qr_path, created_at FROM documents WHERE codigo=?', (codigo,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    keys = ['codigo','instituicao_id','nome','pdf_path','xml_path','qr_path','created_at']
    return dict(zip(keys, row))

def gerar_codigo(instituicao_id):
    hash_part = secrets.token_hex(6)[:12]
    return f"{instituicao_id}.{hash_part}"

def gerar_qr(url, dest_path):
    img = qrcode.make(url)
    img.save(dest_path)

def inserir_qr_no_pdf(pdf_origem, qr_path, pdf_destino):
    reader = PdfReader(str(pdf_origem))
    writer = PdfWriter()
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    qr_img = ImageReader(str(qr_path))
    qr_w, qr_h = 120, 120
    x_pos = 595 - qr_w - 40
    y_pos = 40
    c.drawImage(qr_img, x_pos, y_pos, width=qr_w, height=qr_h)
    c.save()
    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        if i == len(reader.pages) - 1:
            try:
                page.merge_page(overlay_pdf.pages[0])
            except Exception:
                page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)
    with open(pdf_destino, 'wb') as f_out:
        writer.write(f_out)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', secrets.token_hex(16))
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validate')
def validate_query():
    codigo = request.args.get('codigo')
    if not codigo:
        return redirect(url_for('index'))
    return redirect(url_for('view_document', codigo=codigo))

@app.route('/hed/<path:codigo>')
def view_document(codigo):
    doc = db_get_by_codigo(codigo)
    return render_template('validate.html', doc=doc)

@app.route('/file/<path:codigo>')
def serve_file(codigo):
    doc = db_get_by_codigo(codigo)
    if not doc or not doc.get('pdf_path') or not Path(doc['pdf_path']).exists():
        abort(404)
    return send_file(doc['pdf_path'], mimetype='application/pdf')

@app.route('/qr/<path:codigo>')
def serve_qr(codigo):
    doc = db_get_by_codigo(codigo)
    if not doc or not doc.get('qr_path') or not Path(doc['qr_path']).exists():
        abort(404)
    return send_file(doc['qr_path'], mimetype='image/png')

def is_logged_in():
    return session.get('admin') == True

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('user','')
        pwd = request.form.get('pwd','')
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        flash('Credenciais inválidas', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_panel():
    if not is_logged_in():
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html')

@app.route('/admin/register', methods=['POST'])
def admin_register():
    if not is_logged_in():
        return redirect(url_for('admin_login'))
    nome = request.form.get('nome') or '---'
    instituicao_id = request.form.get('instituicao_id') or '1660'
    pdf = request.files.get('pdf')
    xml = request.files.get('xml')
    if not pdf:
        flash('PDF obrigatório', 'danger')
        return redirect(url_for('admin_panel'))
    codigo = gerar_codigo(instituicao_id)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    safe_pdf = UPLOADS / f"{codigo}_{timestamp}.pdf"
    safe_xml = None
    safe_qr = UPLOADS / f"qr_{codigo}_{timestamp}.png"
    final_pdf = UPLOADS / f"final_{codigo}_{timestamp}.pdf"
    pdf.save(safe_pdf)
    if xml:
        safe_xml = UPLOADS / f"{codigo}_{timestamp}.xml"
        xml.save(safe_xml)
    validate_url = f"{BASE_URL}/hed/{codigo}"
    gerar_qr(validate_url, safe_qr)
    try:
        inserir_qr_no_pdf(safe_pdf, safe_qr, final_pdf)
    except Exception:
        final_pdf = safe_pdf
    record = {
        'codigo': codigo,
        'instituicao_id': instituicao_id,
        'nome': nome,
        'pdf_path': str(final_pdf),
        'xml_path': str(safe_xml) if safe_xml else None,
        'qr_path': str(safe_qr),
        'created_at': datetime.utcnow().isoformat()
    }
    db_insert(record)
    flash(f'Documento registrado com código: {codigo}', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
