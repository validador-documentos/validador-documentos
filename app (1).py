import os
from flask import Flask, render_template, request, redirect, send_file, session
from datetime import datetime
import qrcode
import secrets

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "123456")
FLASK_SECRET = os.environ.get("FLASK_SECRET", secrets.token_hex(16))

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = FLASK_SECRET

documentos = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/validate")
def validate():
    codigo = request.args.get("codigo")
    doc = documentos.get(codigo)
    return render_template("validate.html", doc=doc)

@app.route("/file/<codigo>")
def get_file(codigo):
    doc = documentos.get(codigo)
    if doc and "pdf_path" in doc:
        return send_file(doc["pdf_path"])
    return "Arquivo não encontrado", 404

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

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["user"] == ADMIN_USER and request.form["pwd"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin/panel")
    return render_template("admin_login.html")

@app.route("/admin/panel")
def admin_panel():
    if not session.get("admin"):
        return redirect("/admin")
    return render_template("admin_panel.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

@app.route("/admin/register", methods=["POST"])
def admin_register():
    if not session.get("admin"):
        return redirect("/admin")

    nome = request.form.get("nome")
    instituicao_id = request.form.get("instituicao_id")
    codigo = f"{instituicao_id}.{secrets.token_hex(6)}"

    pdf = request.files.get("pdf")
    xml = request.files.get("xml")

    pdf_path = None
    xml_path = None

    if pdf:
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{codigo}.pdf")
        pdf.save(pdf_path)

    if xml:
        xml_path = os.path.join(UPLOAD_FOLDER, f"{codigo}.xml")
        xml.save(xml_path)

    documentos[codigo] = {
        "codigo": codigo,
        "nome": nome,
        "instituicao_id": instituicao_id,
        "pdf_path": pdf_path,
        "xml_path": xml_path,
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return redirect(f"/validate?codigo={codigo}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

git add app.py
git commit -m "Substituindo app.py antigo pelo corrigido"
git push origin main
