import io, os, re, requests
from datetime import datetime
from flask import Flask, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

app = Flask(__name__)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Generador UCATECI | Fernando Sánchez</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #f1f5f9; display: flex; justify-content: center; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 500px; text-align: center; }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #0f172a; color: white; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Redactor Académico Pro</h2>
        <p style="color: #2563eb; font-weight: bold; font-size: 12px;">CONEXIÓN DIRECTA POR HTTP (SIN LIBRERÍAS)</p>
        <form action="/generar" method="POST">
            <input type="text" name="tema" placeholder="Tema del trabajo" required>
            <input type="text" name="asignatura" placeholder="Asignatura" required>
            <input type="text" name="profesor" placeholder="Docente" required>
            <textarea name="estudiantes" placeholder="Integrantes y matrículas" rows="3" required></textarea>
            <button type="submit">GENERAR PDF FINAL</button>
        </form>
    </div>
</body>
</html>
"""

def llamar_gemini_directo(tema, asignatura):
    # Hablamos con Google directamente por su API REST
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": f"Redacta un informe académico formal sobre {tema} para la asignatura {asignatura}. Usa primera persona del plural. Bibliografía APA 7."}]
        }]
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        res = r.json()
        # Navegamos el JSON manualmente para sacar el texto
        return res['candidates']['content']['parts']['text']
    except Exception as e:
        return f"Error en la redacción: {str(e)}"

def crear_pdf(datos, contenido):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    st_cent = ParagraphStyle('C', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
    st_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, leading=14)
    
    elements = [
        Paragraph("<b>UNIVERSIDAD CATÓLICA DEL CIBAO (UCATECI)</b>", st_cent),
        Spacer(1, 4*cm),
        Paragraph(f"<b>TEMA: {datos['tema'].upper()}</b>", st_cent),
        Spacer(1, 4*cm),
        Paragraph(f"Presentado por: {datos['estudiantes']}", st_cent),
        Spacer(1, 1*cm),
        Paragraph(f"Docente: {datos['profesor']}", st_cent),
        PageBreak(),
        Paragraph(contenido.replace('\n', '<br/>'), st_body)
    ]
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index(): return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    d = request.form.to_dict()
    texto = llamar_gemini_directo(d['tema'], d['asignatura'])
    pdf = crear_pdf(d, texto)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Trabajo.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
