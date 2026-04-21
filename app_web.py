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

# --- INTERFAZ MEJORADA CON MENÚS DINÁMICOS ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Asesor Académico UCATECI Pro</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
        
        :root {
            --primary: #1e3a8a; /* Azul UCATECI */
            --accent: #d97706; /* Dorado UCATECI */
            --bg: #f8fafc;
        }

        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: var(--bg); 
            display: flex; justify-content: center; padding: 40px 20px; 
            color: #1e293b;
        }

        .card { 
            background: white; padding: 40px; border-radius: 24px; 
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);
            width: 100%; max-width: 650px; border: 1px solid #e2e8f0;
        }

        h1 { text-align: center; font-size: 30px; font-weight: 800; margin-bottom: 8px; color: var(--primary); }
        .subtitle { text-align: center; color: #64748b; margin-bottom: 30px; font-size: 15px; }

        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 700; font-size: 14px; color: #475569; }
        
        input, textarea, select { 
            width: 100%; padding: 12px 16px; border: 2px solid #f1f5f9; 
            border-radius: 12px; font-size: 15px; transition: all 0.3s;
            background: #f8fafc; font-family: inherit;
        }

        input:focus, select:focus, textarea:focus { 
            outline: none; border-color: var(--primary); background: white;
            box-shadow: 0 0 0 4px rgba(30, 58, 138, 0.1);
        }

        button { 
            width: 100%; padding: 18px; background: var(--primary); color: white; 
            border: none; border-radius: 16px; font-weight: 700; font-size: 16px;
            cursor: pointer; transition: all 0.3s; margin-top: 10px;
            box-shadow: 0 10px 15px -3px rgba(30, 58, 138, 0.3);
        }

        button:hover { background: #172554; transform: translateY(-2px); }
        button:active { transform: translateY(0); }

        .loader { display: none; text-align: center; color: var(--primary); margin-top: 20px; font-weight: 600; }
        
        textarea { height: 100px; resize: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Redactor Académico</h1>
        <p class="subtitle">Generador de Informes Técnicos - UCATECI</p>
        
        <form id="pdfForm" action="/generar" method="POST">
            <div class="form-group">
                <label>Universidad (Logo):</label>
                <select name="logo_filename">
                    <option value="ucateci.png">UCATECI (La Vega)</option>
                    <option value="uasd.png">UASD</option>
                    <option value="pucmm.png">PUCMM</option>
                </select>
            </div>

            <div class="form-group">
                <label>Facultad:</label>
                <select name="facultad" id="facultad" onchange="actualizarEscuelas()">
                    <option value="">Seleccione una facultad</option>
                    <option value="Facultad de las Ingenierías">Facultad de las Ingenierías</option>
                    <option value="Facultad de Ciencias de la Salud">Facultad de Ciencias de la Salud</option>
                    <option value="Facultad de Humanidades">Facultad de Humanidades</option>
                    <option value="Facultad de Ciencias Sociales y Administrativas">Facultad de Ciencias Sociales</option>
                </select>
            </div>

            <div class="form-group">
                <label>Escuela:</label>
                <select name="escuela" id="escuela">
                    <option value="">Primero elija una facultad</option>
                </select>
            </div>

            <div class="form-group">
                <label>Tema del Informe:</label>
                <input type="text" name="tema" placeholder="Ej. Optimización de procesos industriales" required>
            </div>

            <div class="form-group">
                <label>Asignatura:</label>
                <input type="text" name="asignatura" placeholder="Ej. Tecnología Mecánica" required>
            </div>

            <div class="form-group">
                <label>Presentado por (Nombre y Matrícula):</label>
                <textarea name="estudiantes" placeholder="Fernando Sánchez, 2024-0777" required></textarea>
            </div>

            <div class="form-group">
                <label>Profesor(a):</label>
                <input type="text" name="profesor" placeholder="Ej. Hipólita Cepeda (MES)" required>
            </div>

            <button type="submit" id="submitBtn">Generar Trabajo Final</button>
            <div id="loading" class="loader">⚙️ Redactando en primera persona...</div>
        </form>
    </div>

    <script>
        const escuelasPorFacultad = {
            "Facultad de las Ingenierías": ["Escuela de Ingeniería Industrial", "Escuela de Ingeniería de Sistemas", "Escuela de Ingeniería Civil", "Escuela de Arquitectura"],
            "Facultad de Ciencias de la Salud": ["Escuela de Medicina", "Escuela de Enfermería", "Escuela de Bioanálisis", "Escuela de Odontología"],
            "Facultad de Humanidades": ["Escuela de Psicología", "Escuela de Educación", "Escuela de Comunicación"],
            "Facultad de Ciencias Sociales y Administrativas": ["Escuela de Administración", "Escuela de Contabilidad", "Escuela de Derecho", "Escuela de Mercadeo"]
        };

        function actualizarEscuelas() {
            const facultadSel = document.getElementById("facultad").value;
            const escuelaSelect = document.getElementById("escuela");
            escuelaSelect.innerHTML = "";

            if (facultadSel && escuelasPorFacultad[facultadSel]) {
                escuelasPorFacultad[facultadSel].forEach(esc => {
                    let option = document.createElement("option");
                    option.value = esc;
                    option.text = esc;
                    escuelaSelect.add(option);
                });
            } else {
                let option = document.createElement("option");
                option.text = "Primero elija una facultad";
                escuelaSelect.add(option);
            }
        }

        document.getElementById('pdfForm').onsubmit = function() {
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('loading').style.display = 'block';
        };
    </script>
</body>
</html>
"""

def generar_contenido_ia(tema, asignatura):
    # Prompt ajustado a PRIMERA PERSONA (yo o nosotros)
    prompt = (
        f"Actúa como un estudiante de ingeniería experto de UCATECI. Redacta un informe técnico sobre: {tema}. "
        f"Asignatura: {asignatura}. "
        f"REGLAS CRÍTICAS: "
        f"1. Redacta estrictamente en PRIMERA PERSONA (yo o nosotros). Ej: 'Realizamos un análisis', 'Pude observar', 'Concluyo que'. "
        f"2. Estructura: Introducción, Desarrollo profundo, Conclusiones. "
        f"3. NADA de saludos de IA. "
        f"4. Al final añade una 'Bibliografía' con 3 fuentes reales en APA 7."
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
    style_portada = ParagraphStyle('Portada', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, leading=18)
    style_tema = ParagraphStyle('Tema', parent=style_portada, fontSize=14, fontName='Helvetica-Bold', leading=20)
    style_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, leading=16)

    elements = []

    # --- PORTADA UCATECI ESTILO FERNANDO ---
    elements.append(Paragraph("<b>Universidad Católica del Cibao</b>", style_portada))
    elements.append(Paragraph("<b>(UCATECI)</b>", style_portada))
    elements.append(Spacer(1, 0.5*cm))

    logo_path = os.path.join('static', 'logos', datos['logo_filename'])
    if os.path.exists(logo_path):
        img = Image(logo_path, width=4.5*cm, height=4.5*cm)
        elements.append(img)
    
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<b>{datos['facultad']}</b>", style_portada))
    elements.append(Paragraph(f"<b>{datos['escuela']}</b>", style_portada))
    
    elements.append(Spacer(1, 2.5*cm))
    elements.append(Paragraph("<b>Tema</b>", style_tema))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(datos['tema'], style_portada))
    
    elements.append(Spacer(1, 1.5*cm))
    elements.append(Paragraph("<b>Trabajo Final de la asignatura</b>", style_tema))
    elements.append(Paragraph(datos['asignatura'], style_portada))
    
    elements.append(Spacer(1, 1.5*cm))
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

    elements.append(PageBreak()) 

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
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name="Informe_Final_UCATECI.pdf")

if __name__ == '__main__':
    app.run(debug=True)
