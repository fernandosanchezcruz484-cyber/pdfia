import io
import os
import re
import time
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

import g4f

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
        
        :root {
            --primary: #0f172a;
            --accent: #3b82f6;
            --bg: #e2e8f0;
        }

        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            display: flex; justify-content: center; padding: 40px 15px; 
            color: #0f172a; min-height: 100vh;
        }

        .card { 
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 40px; border-radius: 20px; 
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.15);
            width: 100%; max-width: 700px; border: 1px solid rgba(255,255,255,0.5);
        }

        header { text-align: center; margin-bottom: 30px; }
        h1 { font-size: 30px; font-weight: 800; color: var(--primary); margin-bottom: 5px; }
        .subtitle { color: #475569; font-size: 15px; font-weight: 500; }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .form-group { margin-bottom: 15px; }
        .full { grid-column: span 2; }

        label { display: block; margin-bottom: 6px; font-weight: 700; font-size: 13px; color: #334155; text-transform: uppercase; }
        
        input, textarea, select { 
            width: 100%; padding: 12px 15px; border: 2px solid #cbd5e1; 
            border-radius: 12px; font-size: 14px; transition: all 0.3s ease;
            background: #f8fafc; font-family: inherit; box-sizing: border-box;
        }

        input:focus, select:focus, textarea:focus { 
            outline: none; border-color: var(--accent); background: white;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
        }

        button { 
            width: 100%; padding: 18px; background: var(--primary); color: white; 
            border: none; border-radius: 14px; font-weight: 800; font-size: 16px;
            cursor: pointer; transition: 0.3s; margin-top: 10px;
        }

        button:hover { background: var(--accent); transform: translateY(-2px); box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.4); }
        
        .loader { display: none; text-align: center; color: var(--accent); margin-top: 20px; }
        .spinner { width: 30px; height: 30px; border: 4px solid #e2e8f0; border-top: 4px solid var(--accent); border-radius: 50%; display: inline-block; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <header>
            <h1>Redactor Académico Pro</h1>
            <p class="subtitle">Generador Inteligente con Formato APA 7</p>
        </header>
        
        <form id="pdfForm" action="/generar" method="POST">
            <div class="grid">
                <div class="form-group">
                    <label>Universidad (Logo):</label>
                    <select name="logo_filename">
                        <option value="ucateci.png">UCATECI</option>
                        <option value="pucmm.png">PUCMM</option>
                        <option value="uasd.png">UASD</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Facultad:</label>
                    <select name="facultad" id="facultad" onchange="actualizarEscuelas()" required>
                        <option value="">-- Seleccione --</option>
                        <option value="Facultad de las Ingenierías">Ingenierías</option>
                        <option value="Facultad de Ciencias de la Salud">Salud</option>
                        <option value="Facultad de Ciencias Sociales">Ciencias Sociales</option>
                    </select>
                </div>
                <div class="form-group full">
                    <label>Escuela:</label>
                    <select name="escuela" id="escuela" required>
                        <option value="">Primero elija una facultad</option>
                    </select>
                </div>
                <div class="form-group full">
                    <label>Tema de Investigación:</label>
                    <input type="text" name="tema" placeholder="Ej. Presencialidad y estrés académico" required>
                </div>
                <div class="form-group">
                    <label>Asignatura:</label>
                    <input type="text" name="asignatura" placeholder="Ej. Metodología de la investigación" required>
                </div>
                <div class="form-group">
                    <label>Docente:</label>
                    <input type="text" name="profesor" placeholder="Hipólita Cepeda (MES)" required>
                </div>
                <div class="form-group full">
                    <label>Instrucciones / Preguntas a desarrollar:</label>
                    <textarea name="instrucciones" placeholder="Pega aquí si el profesor pide responder preguntas específicas, un formato de puntos clave, etc."></textarea>
                </div>
                <div class="form-group full">
                    <label>Presentado por (Nombres y Matrículas):</label>
                    <textarea name="estudiantes" style="height: 70px;" placeholder="Ashley Rashel Vargas, 2024-0811&#10;Fernando Sánchez, 2024-0777" required></textarea>
                </div>
            </div>

            <button type="submit" id="submitBtn">Generar Documento PDF</button>
            <div id="loading" class="loader">
                <div class="spinner"></div>
                <p><b>Investigando y redactando...</b><br>Esto tomará entre 30 y 60 segundos.</p>
            </div>
        </form>
    </div>

    <script>
        const escuelas = {
            "Facultad de las Ingenierías": ["Escuela de Ingeniería Industrial", "Escuela de Ingeniería de Sistemas", "Escuela de Ingeniería Civil", "Escuela de Arquitectura"],
            "Facultad de Ciencias de la Salud": ["Escuela de Medicina", "Escuela de Enfermería", "Escuela de Odontología"],
            "Facultad de Ciencias Sociales": ["Escuela de Administración", "Escuela de Contabilidad", "Escuela de Psicología"]
        };

        function actualizarEscuelas() {
            const fac = document.getElementById("facultad").value;
            const esc = document.getElementById("escuela");
            esc.innerHTML = "";
            if (fac) {
                escuelas[fac].forEach(e => {
                    let op = document.createElement("option"); op.value = e; op.text = e; esc.add(op);
                });
            } else {
                esc.add(new Option("Elija primero la facultad", ""));
            }
        }

        document.getElementById('pdfForm').onsubmit = () => {
            document.getElementById('submitBtn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
        };
    </script>
</body>
</html>
"""

def limpiar_formato_ia(texto):
    texto = re.sub(r'(?m)^### (.*?)$', r'<br/><font size="12"><b>\1</b></font>', texto)
    texto = re.sub(r'(?m)^## (.*?)$', r'<br/><font size="14"><b>\1</b></font>', texto)
    texto = re.sub(r'(?m)^# (.*?)$', r'<br/><font size="16"><b>\1</b></font>', texto)
    texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    texto = re.sub(r'(?m)^[-*]\s+(.*?)$', r'• \1', texto)
    texto = texto.replace('\n', '<br/>')
    texto = texto.replace('<br/><br/><br/>', '<br/><br/>')
    return texto

def generar_contenido_ia(tema, asignatura, instrucciones):
    prompt = (
        f"Eres un estudiante universitario realizando un trabajo final sobre: '{tema}'. "
        f"Asignatura: {asignatura}. "
        f"Instrucciones a responder: {instrucciones if instrucciones else 'Desarrolla el tema de forma profunda y académica.'}. "
        f"REGLAS: "
        f"1. Redacta en PRIMERA PERSONA DEL PLURAL ('Investigamos', 'Concluimos'). "
        f"2. NADA de saludos, inicia directo con el texto. "
        f"3. NO uses el símbolo ## para los títulos, simplemente usa **TÍTULO** en mayúsculas. "
        f"4. Al final añade 'Bibliografía' con 3 fuentes reales en APA 7."
    )
    
    # Intento 1: Modelo Principal Automático
    try:
        response = g4f.ChatCompletion.create(
            model="gpt-4", 
            messages=[{"role": "user", "content": prompt}],
            timeout=120
        )
        if response and len(response) > 50:
            return response
    except Exception:
        pass

    # Intento 2: Modelo de Respaldo Rápido
    try:
        response_b = g4f.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            timeout=120
        )
        if response_b and len(response_b) > 50:
            return response_b
    except Exception:
        pass
            
    return "Error temporal. Los servidores de IA están saturados en este momento. Por favor, espera un minuto y dale al botón de generar nuevamente."

def obtener_fecha_espanol():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes = meses[datetime.now().month - 1]
    anio = datetime.now().year
    return f"{mes} del {anio}"

def crear_pdf(datos, contenido_ia):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2.54*cm, leftMargin=2.54*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    st_cent = ParagraphStyle('Cent', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, leading=16)
    st_bold = ParagraphStyle('BoldC', parent=st_cent, fontName='Helvetica-Bold', fontSize=12)
    st_tema = ParagraphStyle('Tema', parent=st_cent, fontSize=14, fontName='Helvetica-Bold', leading=18)
    st_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=16, alignment=TA_JUSTIFY)

    elements = []

    # --- NOMBRE DE UNIVERSIDAD EN UNA SOLA LÍNEA LIMPIA ---
    nombres_universidades = {
        "ucateci.png": "Universidad Católica del Cibao (UCATECI)",
        "pucmm.png": "Pontificia Universidad Católica Madre y Maestra (PUCMM)",
        "uasd.png": "Universidad Autónoma de Santo Domingo (UASD)"
    }
    nombre_uni = nombres_universidades.get(datos.get('logo_filename', ''), "Universidad")

    # PORTADA
    elements.append(Paragraph(f"<b>{nombre_uni}</b>", st_cent))
    elements.append(Spacer(1, 0.2*cm))

    logo_path = os.path.join('static', 'logos', datos['logo_filename'])
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=3.5*cm, height=3.5*cm))
    
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"<b>{datos.get('facultad', '')}</b>", st_bold))
    elements.append(Paragraph(f"<b>{datos.get('escuela', '')}</b>", st_bold))
    
    elements.append(Spacer(1, 1.5*cm))
    elements.append(Paragraph("<b>Tema</b>", st_bold))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(datos.get('tema', ''), st_tema))
    
    elements.append(Spacer(1, 1.2*cm))
    elements.append(Paragraph("<b>Trabajo Final de la asignatura</b>", st_bold))
    elements.append(Paragraph(datos.get('asignatura', ''), st_cent))
    
    elements.append(Spacer(1, 1.2*cm))
    elements.append(Paragraph("<b>Presentado por:</b>", st_bold))
    for est in datos.get('estudiantes', '').split('\n'):
        if est.strip():
            elements.append(Paragraph(est.strip(), st_cent))
    
    elements.append(Spacer(1, 1.2*cm))
    elements.append(Paragraph("<b>Docente</b>", st_bold))  
    elements.append(Paragraph(datos.get('profesor', ''), st_cent))
    
    elements.append(Spacer(1, 0.8*cm))
    elements.append(Paragraph("La Vega, República Dominicana", st_cent))
    elements.append(Paragraph(f"<b>Fecha</b>", st_bold))
    elements.append(Paragraph(obtener_fecha_espanol(), st_cent)) 

    elements.append(PageBreak())

    # CUERPO DEL INFORME
    texto_formateado = limpiar_formato_ia(contenido_ia)
    elements.append(Paragraph(texto_formateado, st_body))

    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar():
    try:
        datos = request.form.to_dict()
        contenido = generar_contenido_ia(datos.get('tema', ''), datos.get('asignatura', ''), datos.get('instrucciones', ''))
        pdf = crear_pdf(datos, contenido)
        return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name="Trabajo_Final.pdf")
    except Exception as e:
        return f"Error crítico: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
