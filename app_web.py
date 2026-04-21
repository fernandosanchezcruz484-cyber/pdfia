import io
import os
import re
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

import g4f

app = Flask(__name__)

# --- INTERFAZ CON MENÚ DESPLEGABLE ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Generador Académico Pro</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background: #f4f7f6; display: flex; justify-content: center; padding: 40px; }
        .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 600px; }
        h1 { text-align: center; color: #1a202c; margin-bottom: 25px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #cbd5e0; border-radius: 8px; font-size: 15px; }
        button { width: 100%; padding: 15px; background: #2d3748; color: white; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; margin-top: 10px; }
        button:hover { background: #1a202c; }
        .loader { display: none; text-align: center; color: #2b6cb0; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Redactor Académico UCATECI</h1>
        <form id="pdfForm" action="/generar" method="POST">
            <div class="form-group">
                <label>Seleccionar Universidad (Logo):</label>
                <select name="logo_filename">
                    <option value="ucateci.png">UCATECI (La Vega)</option>
                    <option value="uasd.png">UASD</option>
                    <option value="unphu.png">UNPHU</option>
                    <option value="pucmm.png">PUCMM</option>
                </select>
            </div>
            <div class="form-group">
                <label>Facultad:</label>
                <input type="text" name="facultad" value="Facultad de las ingenierías" required>
            </div>
            <div class="form-group">
                <label>Escuela:</label>
                <input type="text" name="escuela" value="Escuela de Ingeniería Industrial" required>
            </div>
            <div class="form-group">
                <label>Tema del Informe:</label>
                <input type="text" name="tema" placeholder="Ej. Presencialidad y estrés académico" required>
            </div>
            <div class="form-group">
                <label>Asignatura:</label>
                <input type="text" name="asignatura" placeholder="Metodología de la investigación" required>
            </div>
            <div class="form-group">
                <label>Presentado por (Nombres y Matrículas):</label>
                <textarea name="estudiantes" placeholder="Fernando Sánchez, 2024-0777" required></textarea>
            </div>
            <div class="form-group">
                <label>Profesor(a):</label>
                <input type="text" name="profesor" placeholder="Hipólita Cepeda (MES)" required>
            </div>
            <button type="submit" id="submitBtn">Generar Trabajo Final</button>
            <div id="loading" class="loader">⚙️ Redactando en tercera persona y dando formato APA...</div>
        </form>
    </div>
    <script>
        document.getElementById('pdfForm').onsubmit = function() {
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('loading').style.display = 'block';
        };
    </script>
</body>
</html>
"""

def generar_contenido_ia(tema, asignatura):
    prompt = (
        f"Actúa como un académico experto. Redacta un informe profundo sobre el tema: {tema}. "
        f"Asignatura: {asignatura}. "
        f"REGLAS: 1. Usa estrictamente la TERCERA PERSONA. 2. Estructura: Introducción, Desarrollo, Conclusión. "
        f"3. Al final añade una 'Bibliografía' con 3 fuentes reales en APA 7. "
        f"4. Prohibido saludar o decir 'aquí tienes el informe'."
    )
    try:
        response = g4f.ChatCompletion.create(model=g4f.models.gpt_4, messages=[{"role": "user", "content": prompt}])
        return response
    except:
        return "Error al generar contenido. Por favor reintenta."

def crear_pdf(datos, contenido_ia):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)
    
    styles = getSampleStyleSheet()
    
    # --- ESTILOS PERSONALIZADOS ---
    style_portada = ParagraphStyle('Portada', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, leading=18)
    style_tema = ParagraphStyle('Tema', parent=style_portada, fontSize=14, fontName='Helvetica-Bold', leading=20)
    style_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, leading=16)

    elements = []

    # --- PORTADA (Idéntica a tu imagen) ---
    elements.append(Paragraph("<b>Universidad Católica del Cibao</b>", style_portada))
    elements.append(Paragraph("<b>(UCATECI)</b>", style_portada))
    elements.append(Spacer(1, 0.5*cm))

    # Logo dinámico
    logo_path = os.path.join('static', 'logos', datos['logo_filename'])
    if os.path.exists(logo_path):
        img = Image(logo_path, width=4*cm, height=4*cm)
        elements.append(img)
    
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<b>{datos['facultad']}</b>", style_portada))
    elements.append(Paragraph(f"<b>{datos['escuela']}</b>", style_portada))
    
    elements.append(Spacer(1, 3*cm))
    elements.append(Paragraph("<b>Tema</b>", style_tema))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(datos['tema'], style_portada))
    
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("<b>Trabajo Final de la asignatura</b>", style_tema))
    elements.append(Paragraph(datos['asignatura'], style_portada))
    
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("<b>Presentado por:</b>", style_tema))
    for est in datos['estudiantes'].split('\n'):
        elements.append(Paragraph(est.strip(), style_portada))
    
    elements.append(Spacer(1, 1.5*cm))
    elements.append(Paragraph("<b>Profesora</b>", style_tema))
    elements.append(Paragraph(datos['profesor'], style_portada))
    
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("La Vega, República Dominicana", style_portada))
    elements.append(Paragraph("<b>Fecha</b>", style_tema))
    elements.append(Paragraph(datetime.now().strftime("%B del %Y"), style_portada))

    elements.append(PageBreak()) # Saltar al contenido

    # --- CUERPO DEL INFORME ---
    clean_text = contenido_ia.replace("**", "<b>").replace("\n", "<br/>")
    elements.append(Paragraph(clean_text, style_body))

    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    datos = request.form.to_dict()
    contenido = generar_contenido_ia(datos['tema'], datos['asignatura'])
    pdf_buffer = crear_pdf(datos, contenido)
    
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name="Trabajo_Final.pdf")

if __name__ == '__main__':
    app.run(debug=True)
