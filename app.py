from flask import Flask, render_template, request, send_file, redirect, url_for, session
import os
import qrcode
import secrets
from datetime import datetime

# Configurações básicas
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "123456")
FLASK_SECRET = os.environ.get("FLASK_SECRET", secrets.token_hex(16))

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = FLASK_SECRET

# Banco de dados em memória
documentos = {}

# Página inicial
@app.route("/")
def index():
    return render_template("index.html")

# Página de validação
@app.route("/validate")
def validate():
    codigo = request.args.get("codigo")
    doc = documentos.get(codigo)
    return render_template("validate.html", doc=doc)

# Download de arquivo
@app.route("/file/<codigo>")
def get_file(codigo):
    doc = documentos.get(codigo)
    if doc and "pdf_path" in doc:
        return send_file(doc["pdf_path"])
    return "Arquivo não encontrado", 404

# Geração de QR Code
@app.route("/qr/<codigo>")
def get_qr(codigo):
    img_path = os.path.join(UPLOAD_FOLDER, f"{codigo}_qr.png")
    if not os.path.exists(img_path):
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(f"{BASE_URL}/validate?codigo={codigo}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_path)
    return send_file(img_path, mimetype="image/png")

# Login admin
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            return "Usuário ou senha inválidos", 403
    return render_template("admin_login.html")

# Painel admin
@app.route("/admin/panel")
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return render_template("admin_panel.html")

# Upload de documentos
@app.route("/admin/upload", methods=["POST"])
def admin_upload():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    nome = request.form.get("nome")
    arquivo = request.files.get("arquivo")

    if arquivo:
        codigo = secrets.token_hex(4).upper()
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{codigo}.pdf")
        arquivo.save(pdf_path)
        documentos[codigo] = {
            "codigo": codigo,
            "nome": nome,
            "data": datetime.now().strftime("%d/%m/%Y"),
            "pdf_path": pdf_path
        }
        return f"Documento enviado com sucesso! Código: {codigo}"
    return "Erro ao enviar documento", 400

if __name__ == "__main__":
    app.run(debug=True)
