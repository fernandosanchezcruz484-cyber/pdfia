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
# Asegúrate de poner tu llave en Render con el nombre: GEMINI_API_KEY
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
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
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #f8fafc; display: flex; justify-content: center; padding: 20px; }
        .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 650px; }
        h1 { text-align: center; color: #0f172a; margin-bottom: 5px; }
        .status { text-align: center; color: #059669; font-weight: 800; font-size: 12px; margin-bottom: 25px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 13px; color: #64748b; }
        input, textarea { width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; box-sizing: border-box; }
        button { width: 100%; padding: 16px; background: #0f172a; color: white; border: none; border-radius: 12px; font-weight: 700; cursor: pointer; margin-top: 20px; }
        button:hover { background: #3b82f6; }
        #loading { display: none; text-align: center; margin-top: 15px; color: #3b82f6; font-weight: 700; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Redactor Académico</h1>
        <p class="status">● MOTOR GEMINI ACTIVADO (ESTABLE)</p>
        <form id="f" action="/generar" method="POST">
            <div class="grid">
                <div style="grid-column: span 2;">
                    <label>Tema del Trabajo:</label>
                    <input type="text" name="tema" required>
                </div>
                <div>
                    <label>Asignatura:</label>
                    <input type="text" name="asignatura" required>
                </div>
                <div>
                    <label>Docente:</label>
                    <input type="text" name="profesor" required>
                </div>
                <div style="grid-column: span 2;">
                    <label>Estudiantes y Matrículas:</label>
                    <textarea name="estudiantes" rows="3" required></textarea>
                </div>
            </div>
            <button type="submit" id="btn">GENERAR PDF PROFESIONAL</button>
            <div id="loading">Google Gemini está redactando... un momento.</div>
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
        prompt = f"Redacta un informe académico para la universidad sobre: {tema}. Asignatura: {asignatura}. Usa primera persona del plural. Incluye Bibliografía APA 7."
        response = model.generate_content(prompt)
        # Gemini entrega el texto directo, sin vueltas:
        return response.text
    except Exception as e:
        return f"Error con Gemini: {str(e)}"

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
    
    # Contenido
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
        return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Informe_UCATECI.pdf")
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
