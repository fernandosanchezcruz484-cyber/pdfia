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

# --- CONFIGURACIÓN DIRECTA ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- DISEÑO WEB UCATECI ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generador UCATECI | Fernando Sánchez</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #f1f5f9; display: flex; justify-content: center; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 600px; }
        h1 { color: #1e293b; text-align: center; font-size: 24px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        label { display: block; margin: 10px 0 5px; font-weight: 600; font-size: 12px; color: #475569; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #2563eb; color: white; border: none; border-radius: 10px; font-weight: 800; margin-top: 20px; cursor: pointer; }
        #loading { display: none; text-align: center; color: #2563eb; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Generador de Trabajos UCATECI</h1>
        <p style="text-align:center; font-size:12px; color:green;">VERSIÓN MANUAL (CONEXIÓN DIRECTA)</p>
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
                    <label>Estudiantes (Nombre y Matrícula):</label>
                    <textarea name="estudiantes" required></textarea>
                </div>
            </div>
            <button type="submit" id="b">GENERAR PDF AHORA</button>
            <div id="loading">Redactando con Llama 3.1... espera un momento.</div>
        </form>
    </div>
    <script>
        document.getElementById('f').onsubmit = () => {
            document.getElementById('b').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
        };
    </script>
</body>
</html>
"""

def llamar_ia_manual(tema, asignatura):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": f"Redacta un informe académico formal sobre {tema} para la asignatura {asignatura}. Usa primera persona del plural. Al final pon Bibliografía APA 7."}
        ],
        "temperature": 0.5
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        datos = response.json()
        # Aquí no hay error de lista, vamos directo al grano:
        return datos['choices']['message']['content']
    except Exception as e:
        return f"Error en conexión manual: {str(e)}"

def crear_pdf(datos, contenido_ia):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    st_cent = ParagraphStyle('C', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
    st_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=11, leading=14, alignment=TA_JUSTIFY)
    
    elements = []
    # Portada básica pero funcional
    elements.append(Paragraph("<b>UNIVERSIDAD CATÓLICA DEL CIBAO (UCATECI)</b>", st_cent))
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(f"<b>TEMA: {datos['tema'].upper()}</b>", st_cent))
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(f"<b>Estudiantes:</b><br/>{datos['estudiantes'].replace('\\n', '<br/>')}", st_cent))
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<b>Docente:</b> {datos['profesor']}", st_cent))
    elements.append(PageBreak())
    
    # Contenido
    c_limpio = contenido_ia.replace('\n', '<br/>')
    c_limpio = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', c_limpio)
    elements.append(Paragraph(c_limpio, st_body))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index(): return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    try:
        d = request.form.to_dict()
        texto = llamar_ia_manual(d['tema'], d['asignatura'])
        pdf = crear_pdf(d, texto)
        return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Trabajo.pdf")
    except Exception as e:
        return f"Error crítico: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
