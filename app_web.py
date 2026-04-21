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

from groq import Groq

# --- EL CÓDIGO BUSCA LA LLAVE EN LA CAJA FUERTE DE RENDER ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

app = Flask(__name__)

# --- DISEÑO WEB PREMIUM ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generador Académico Pro | Fernando Sánchez</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        :root { --primary: #0f172a; --accent: #3b82f6; --bg: #e2e8f0; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); display: flex; justify-content: center; padding: 40px 15px; color: #0f172a; min-height: 100vh; }
        .card { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 40px; border-radius: 20px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.15); width: 100%; max-width: 700px; border: 1px solid rgba(255,255,255,0.5); }
        header { text-align: center; margin-bottom: 30px; }
        h1 { font-size: 30px; font-weight: 800; color: var(--primary); margin-bottom: 5px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .form-group { margin-bottom: 15px; }
        .full { grid-column: span 2; }
        label { display: block; margin-bottom: 6px; font-weight: 700; font-size: 13px; color: #334155; text-transform: uppercase; }
        input, textarea, select { width: 100%; padding: 12px 15px; border: 2px solid #cbd5e1; border-radius: 12px; font-size: 14px; transition: all 0.3s ease; background: #f8fafc; font-family: inherit; box-sizing: border-box; }
        button { width: 100%; padding: 18px; background: var(--primary); color: white; border: none; border-radius: 14px; font-weight: 800; font-size: 16px; cursor: pointer; transition: 0.3s; margin-top: 10px; }
        .loader { display: none; text-align: center; color: var(--accent); margin-top: 20px; }
        .spinner { width: 30px; height: 30px; border: 4px solid #e2e8f0; border-top: 4px solid var(--accent); border-radius: 50%; display: inline-block; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <header><h1>Redactor Académico Pro</h1><p>Motor: Groq (Llama 3.1)</p></header>
        <form id="pdfForm" action="/generar" method="POST">
            <div class="grid">
                <div class="form-group"><label>Logo:</label><select name="logo_filename"><option value="ucateci.png">UCATECI</option><option value="pucmm.png">PUCMM</option><option value="uasd.png">UASD</option></select></div>
                <div class="form-group"><label>Facultad:</label><select name="facultad" id="facultad" onchange="actualizarEscuelas()" required><option value="">-- Seleccione --</option><option value="Facultad de las Ingenierías">Ingenierías</option><option value="Facultad de Ciencias de la Salud">Salud</option><option value="Facultad de Ciencias Sociales">Ciencias Sociales</option></select></div>
                <div class="form-group full"><label>Escuela:</label><select name="escuela" id="escuela" required><option value="">Primero elija una facultad</option></select></div>
                <div class="form-group full"><label>Tema:</label><input type="text" name="tema" required></div>
                <div class="form-group"><label>Asignatura:</label><input type="text" name="asignatura" required></div>
                <div class="form-group"><label>Docente:</label><input type="text" name="profesor" required></div>
                <div class="form-group full"><label>Instrucciones:</label><textarea name="instrucciones"></textarea></div>
                <div class="form-group full"><label>Estudiantes:</label><textarea name="estudiantes" required></textarea></div>
            </div>
            <button type="submit" id="submitBtn">Generar Documento PDF</button>
            <div id="loading" class="loader"><div class="spinner"></div><p>Redactando...</p></div>
        </form>
    </div>
    <script>
        const escuelas = { "Facultad de las Ingenierías": ["Escuela de Ingeniería Industrial", "Escuela de Ingeniería de Sistemas"], "Facultad de Ciencias de la Salud": ["Escuela de Medicina"], "Facultad de Ciencias Sociales": ["Escuela de Administración"] };
        function actualizarEscuelas() { const fac = document.getElementById("facultad").value; const esc = document.getElementById("escuela"); esc.innerHTML = ""; if (fac) { escuelas[fac].forEach(e => { let op = document.createElement("option"); op.value = e; op.text = e; esc.add(op); }); } }
        document.getElementById('pdfForm').onsubmit = () => { document.getElementById('submitBtn').style.display = 'none'; document.getElementById('loading').style.display = 'block'; };
    </script>
</body>
</html>
"""

def generar_contenido_ia(tema, asignatura, instrucciones):
    if not client: return "Error: Falta la API KEY en Render."
    prompt = f"Redacta un trabajo académico formal en primera persona del plural sobre: {tema}. Asignatura: {asignatura}. Instrucciones: {instrucciones}. Incluye Bibliografía APA 7."
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.5
        )
        # ESTA LÍNEA ES LA ÚNICA QUE IMPORTA: tiene el
        return response.choices.message.content
    except Exception as e:
        return f"ERROR REAL DE LA IA: {str(e)}"

def crear_pdf(datos, contenido_ia):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    st_cent = ParagraphStyle('Cent', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
    st_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, leading=14)
    elements = []
    
    # Portada simplificada para evitar errores
    elements.append(Paragraph(f"<b>{datos.get('facultad', '')}</b>", st_cent))
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(f"<b>TEMA: {datos.get('tema', '')}</b>", st_cent))
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph(f"Estudiantes: {datos.get('estudiantes', '')}", st_cent))
    elements.append(PageBreak())
    
    # Cuerpo
    texto_limpio = contenido_ia.replace('\n', '<br/>')
    elements.append(Paragraph(texto_limpio, st_body))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index(): return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    try:
        datos = request.form.to_dict()
        contenido = generar_contenido_ia(datos.get('tema', ''), datos.get('asignatura', ''), datos.get('instrucciones', ''))
        pdf = crear_pdf(datos, contenido)
        return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Trabajo.pdf")
    except Exception as e:
        return f"Error crítico en el servidor: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
