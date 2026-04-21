import io
import os
import re
import requests
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

app = Flask(__name__)

# --- TU LLAVE DE GEMINI (Sácale el provecho) ---
API_KEY = os.environ.get("GEMINI_API_KEY")

# --- INTERFAZ LIMPIA Y FUNCIONAL ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Generador UCATECI | Fernando Sánchez</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
        body { font-family: 'Inter', sans-serif; background: #f3f4f6; display: flex; justify-content: center; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 500px; }
        h1 { color: #111827; text-align: center; font-size: 22px; margin-bottom: 20px; }
        label { display: block; margin: 10px 0 5px; font-weight: 700; font-size: 13px; color: #374151; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 14px; background: #1f2937; color: white; border: none; border-radius: 6px; font-weight: 700; margin-top: 20px; cursor: pointer; }
        #msg { display: none; text-align: center; color: #2563eb; margin-top: 10px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Generador de Reportes UCATECI</h1>
        <form id="f" action="/generar" method="POST">
            <label>Tema del Trabajo:</label>
            <input type="text" name="tema" required>
            <label>Asignatura:</label>
            <input type="text" name="asignatura" required>
            <label>Docente:</label>
            <input type="text" name="profesor" required>
            <label>Integrantes:</label>
            <textarea name="estudiantes" rows="3" required></textarea>
            <button type="submit" id="btn">GENERAR PDF</button>
            <div id="msg">Redactando contenido verídico...</div>
        </form>
    </div>
    <script>
        document.getElementById('f').onsubmit = () => {
            document.getElementById('btn').style.display = 'none';
            document.getElementById('msg').style.display = 'block';
        };
    </script>
</body>
</html>
"""

def redactar_con_ia(tema, asignatura):
    # Conexión manual por HTTP para evitar errores de librerías viejas
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": f"Escribe un informe académico formal y verídico sobre: {tema}. Para la materia: {asignatura}. Usa un tono universitario, primera persona del plural e incluye bibliografía APA al final. No saludes, empieza directo con el contenido."}]
        }]
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        res = r.json()
        # Extraemos el texto del laberinto de Google
        return res['candidates']['content']['parts']['text']
    except Exception as e:
        return f"Error al conectar con la IA: {str(e)}. Verifica que tu API_KEY sea válida en Render."

def generar_pdf(datos, texto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Estilos de la UCATECI
    st_cent = ParagraphStyle('C', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
    st_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, leading=14)
    
    elements = [
        Paragraph("<b>UNIVERSIDAD CATÓLICA DEL CIBAO (UCATECI)</b>", st_cent),
        Spacer(1, 4*cm),
        Paragraph(f"<b>TEMA: {datos['tema'].upper()}</b>", st_cent),
        Spacer(1, 4*cm),
        Paragraph(f"<b>Presentado por:</b><br/>{datos['estudiantes']}", st_cent),
        Spacer(1, 1*cm),
        Paragraph(f"<b>Asignatura:</b> {datos['asignatura']}", st_cent),
        Paragraph(f"<b>Docente:</b> {datos['profesor']}", st_cent),
        PageBreak(),
        # Contenido de la IA
        Paragraph(texto.replace('\n', '<br/>').replace('**', '<b>'), st_body)
    ]
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    d = request.form.to_dict()
    contenido = redactar_con_ia(d['tema'], d['asignatura'])
    pdf = generar_pdf(d, contenido)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Trabajo_Final.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
