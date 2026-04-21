import io
import os
import re
import traceback
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

import g4f

app = Flask(__name__)

# --- INTERFAZ PREMIUM DINÁMICA ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asesor Académico Pro | Fernando Sánchez</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #1e3a8a;
            --accent: #b45309;
            --bg: #f1f5f9;
        }

        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: var(--bg); 
            display: flex; justify-content: center; padding: 40px 20px; 
            color: #0f172a;
        }

        .card { 
            background: white; padding: 45px; border-radius: 30px; 
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.1);
            width: 100%; max-width: 680px; border: 1px solid #e2e8f0;
        }

        header { text-align: center; margin-bottom: 35px; }
        h1 { font-size: 32px; font-weight: 800; color: var(--primary); margin-bottom: 5px; letter-spacing: -1px; }
        .badge { background: #dbeafe; color: var(--primary); padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .form-group { margin-bottom: 20px; }
        .full { grid-column: span 2; }

        label { display: block; margin-bottom: 8px; font-weight: 700; font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
        
        input, textarea, select { 
            width: 100%; padding: 14px; border: 2px solid #f1f5f9; 
            border-radius: 14px; font-size: 15px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: #f8fafc; font-family: inherit;
        }

        input:focus, select:focus, textarea:focus { 
            outline: none; border-color: var(--primary); background: white;
            box-shadow: 0 0 0 4px rgba(30, 58, 138, 0.08);
        }

        button { 
            width: 100%; padding: 20px; background: var(--primary); color: white; 
            border: none; border-radius: 18px; font-weight: 800; font-size: 16px;
            cursor: pointer; transition: 0.3s; margin-top: 15px;
            box-shadow: 0 10px 20px -5px rgba(30, 58, 138, 0.3);
        }

        button:hover { background: #172554; transform: translateY(-3px); box-shadow: 0 20px 25px -5px rgba(30, 58, 138, 0.4); }
        
        .loader { display: none; text-align: center; color: var(--primary); margin-top: 25px; }
        .spinner { width: 30px; height: 30px; border: 4px solid #e2e8f0; border-top: 4px solid var(--primary); border-radius: 50%; display: inline-block; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        textarea { height: 110px; resize: none; }
    </style>
</head>
<body>
    <div class="card">
        <header>
            <span class="badge">V3.0 Ultra Final</span>
            <h1>Redactor Académico</h1>
            <p style="color: #64748b;">Especializado en Ingenierías y Ciencias Sociales</p>
        </header>
        
        <form id="pdfForm" action="/generar" method="POST">
            <div class="grid">
                <div class="form-group">
                    <label>Logo Universidad:</label>
                    <select name="logo_filename">
                        <option value="ucateci.png">UCATECI (La Vega)</option>
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
                    <label>Tema del Informe:</label>
                    <input type="text" name="tema" placeholder="Ej. Implementación de Lean Manufacturing" required>
                </div>
                <div class="form-group">
                    <label>Asignatura:</label>
                    <input type="text" name="asignatura" placeholder="Ej. Metodología II" required>
                </div>
                <div class="form-group">
                    <label>Profesor(a):</label>
                    <input type="text" name="profesor" placeholder="Hipólita Cepeda (MES)" required>
                </div>
                <div class="form-group full">
                    <label>Presentado por (Nombres y Matrículas):</label>
                    <textarea name="estudiantes" placeholder="Fernando Sánchez, 2024-0777&#10;Juan Pérez, 2024-0123" required></textarea>
                </div>
            </div>

            <button type="submit" id="submitBtn">Generar Trabajo Final (1ra Persona)</button>
            <div id="loading" class="loader">
                <div class="spinner"></div>
                <p style="margin-top: 10px;"><b>Redactando informe profesional...</b><br>Esto tomará unos 40 segundos.</p>
            </div>
        </form>
    </div>

    <script>
        const escuelas = {
            "Facultad de las Ingenierías": ["Escuela de Ingeniería Industrial", "Escuela de Ingeniería de Sistemas", "Escuela de Ingeniería Civil", "Escuela de Arquitectura"],
            "Facultad de Ciencias de la Salud": ["Escuela de Medicina", "Escuela de Enfermería", "Escuela de Bioanálisis"],
            "Facultad de Ciencias Sociales": ["Escuela de Administración", "Escuela de Contabilidad", "Escuela de Derecho", "Escuela de Psicología"]
        };

        function actualizarEscuelas() {
            const fac = document.getElementById("facultad").value;
            const esc = document.getElementById("escuela");
            esc.innerHTML = "";
            if (fac) {
                escuelas[fac].forEach(e => {
                    let op = document.createElement("option");
                    op.value = e; op.text = e; esc.add(op);
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

def generar_contenido_ia(tema, asignatura):
    prompt = (
        f"Eres un estudiante destacado de la Universidad UCATECI. Redacta un informe de investigación sobre: {tema}. "
        f"Asignatura: {asignatura}. "
        f"INSTRUCCIONES: 1. Redacta en PRIMERA PERSONA DEL PLURAL (Nosotros). "
        f"2. Usa un tono académico, denso y profesional. 3. Sin preámbulos. "
        f"4. Estructura: Introducción, Desarrollo por puntos y Conclusión. "
        f"5. Al final incluye Bibliografía con 3 fuentes reales en APA 7."
    )
    try:
        response = g4f.ChatCompletion.create(model=g4f.models.gpt_4, messages=[{"role": "user", "content": prompt}])
        return response if response else "Error: La IA no devolvió contenido."
    except Exception:
        return "Fallo en la conexión con la IA. Por favor, intente de nuevo."

def crear_pdf(datos, contenido_ia):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=2.54*cm, leftMargin=2.54*cm, 
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    
    styles = getSampleStyleSheet()
    st_centrado = ParagraphStyle('Cent', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, leading=18)
    st_bold_cent = ParagraphStyle('BoldCent', parent=st_centrado, fontName='Helvetica-Bold', fontSize=13)
    st_tema = ParagraphStyle('Tema', parent=st_centrado, fontSize=15, fontName='Helvetica-Bold', leading=22)
    st_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=17, alignment=TA_JUSTIFY)

    elements = []

    # --- PORTADA ACADÉMICA ---
    elements.append(Paragraph("<b>Universidad Católica del Cibao</b>", st_centrado))
    elements.append(Paragraph("<b>(UCATECI)</b>", st_centrado))
    elements.append(Spacer(1, 0.4*cm))

    logo_path = os.path.join('static', 'logos', datos['logo_filename'])
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=4.2*cm, height=4.2*cm))
    
    elements.append(Spacer(1, 0.8*cm))
    elements.append(Paragraph(f"<b>{datos['facultad'].upper()}</b>", st_bold_cent))
    elements.append(Paragraph(f"<b>{datos['escuela'].upper()}</b>", st_bold_cent))
    
    elements.append(Spacer(1, 3.2*cm))
    elements.append(Paragraph("<b>Tema</b>", st_bold_cent))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(datos['tema'], st_tema))
    
    elements.append(Spacer(1, 2.2*cm))
    elements.append(Paragraph("<b>Trabajo Final de la asignatura</b>", st_bold_cent))
    elements.append(Paragraph(datos['asignatura'], st_centrado))
    
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("<b>Presentado por:</b>", st_bold_cent))
    for est in datos['estudiantes'].split('\n'):
        elements.append(Paragraph(est.strip(), st_centrado))
    
    elements.append(Spacer(1, 1.8*cm))
    elements.append(Paragraph("<b>Docente</b>", st_bold_cent))
    elements.append(Paragraph(datos['profesor'], st_centrado))
    
    elements.append(Spacer(1, 1.2*cm))
    elements.append(Paragraph(f"La Vega, R.D. / {datetime.now().strftime('%B %Y')}", st_centrado))

    elements.append(PageBreak())

    # --- CUERPO DEL INFORME ---
    txt_procesado = contenido_ia.replace("**", "<b>").replace("\n", "<br/>")
    # Limpiador de códigos de cita si llegaran a aparecer
    txt_procesado = re.sub(r'\', '', txt_procesado)
    
    elements.append(Paragraph(txt_procesado, st_body))

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
        contenido = generar_contenido_ia(datos['tema'], datos['asignatura'])
        pdf = crear_pdf(datos, contenido)
        return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=f"Informe_{datetime.now().strftime('%Y%m%d')}.pdf")
    except Exception as e:
        return f"Error crítico: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
