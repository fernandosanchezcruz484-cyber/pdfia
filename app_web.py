import io
import os
import re
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURACIÓN GEMINI ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

# Usamos gemini-1.5-flash que es el más rápido y estable
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INTERFAZ UCATECI ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Generador Académico | UCATECI</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #f0f4f8; display: flex; justify-content: center; padding: 20px; }
        .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 100%; max-width: 650px; }
        h1 { text-align: center; color: #1e293b; margin-bottom: 5px; }
        .status { text-align: center; color: #2563eb; font-weight: 800; font-size: 12px; margin-bottom: 25px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 13px; color: #475569; }
        input, textarea { width: 100%; padding: 12px; border: 1.5px solid #e2e8f0; border-radius: 10px; box-sizing: border-box; margin-bottom: 15px; }
        button { width: 100%; padding: 16px; background: #1e293b; color: white; border: none; border-radius: 12px; font-weight: 700; cursor: pointer; transition: 0.3s; }
        button:hover { background: #2563eb; }
        #loading { display: none; text-align: center; margin-top: 15px; color: #2563eb; font-weight: 700; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Redactor Académico</h1>
        <p class="status">● VERSIÓN FINAL CON GEMINI 1.5</p>
        <form id="f" action="/generar" method="POST">
            <label>Tema del Trabajo:</label>
            <input type="text" name="tema" placeholder="Ej. Arquitectura de Redes en Rep. Dom." required>
            <label>Asignatura:</label>
            <input type="text" name="asignatura" required>
            <label>Docente:</label>
            <input type="text" name="profesor" required>
            <label>Estudiantes y Matrículas:</label>
            <textarea name="estudiantes" rows="3" required></textarea>
            <button type="submit" id="btn">GENERAR PDF AHORA</button>
            <div id="loading">Gemini está redactando tu trabajo... no cierres la página.</div>
        </form>
    </div>
    <script>
        document.getElementById('f').onsubmit = () => {
            document.getElementById('btn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
        };
    </script>
</body>
</html>
"""

def llamar_gemini(tema, asignatura):
    try:
        prompt = f"Redacta un informe académico universitario formal sobre: {tema}. Para la asignatura: {asignatura}. Usa primera persona del plural. Incluye Bibliografía APA 7."
        response = model.generate_content(prompt)
        
        # Si Gemini bloquea el contenido por seguridad, intentamos sacarlo de otra forma
        if response.text:
            return response.text
        return "El contenido fue generado pero no se pudo mostrar por filtros de seguridad de Google."
    except Exception as e:
        return f"Error técnico con Gemini: {str(e)}"

def crear_pdf(datos, contenido_ia):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    st_cent = ParagraphStyle('C', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
    st_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=11, leading=16, alignment=TA_JUSTIFY)
    
    elements = []
    # Portada UCATECI
    elements.append(Paragraph("<b>UNIVERSIDAD CATÓLICA DEL CIBAO (UCATECI)</b>", st_cent))
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(f"<b>TEMA: {datos['tema'].upper()}</b>", st_cent))
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(f"<b>Presentado por:</b><br/>{datos['estudiantes'].replace('\\n', '<br/>')}", st_cent))
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<b>Docente:</b> {datos['profesor']}", st_cent))
    elements.append(PageBreak())
    
    # Contenido con limpieza de negritas
    texto = contenido_ia.replace('\n', '<br/>')
    texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    elements.append(Paragraph(texto, st_body))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index(): return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    try:
        d = request.form.to_dict()
        texto = llamar_gemini(d['tema'], d['asignatura'])
        pdf = crear_pdf(d, texto)
        return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Informe_Final.pdf")
    except Exception as e:
        return f"Error crítico: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
