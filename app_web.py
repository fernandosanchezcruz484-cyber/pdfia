# --- IMPORTACIONES ---
# Ya no necesitamos 'asyncio'
import io
import html
import re
import traceback
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER

try:
    import g4f
except ImportError:
    print("="*50)
    print("ERROR: Faltan bibliotecas.")
    print("Ejecuta este comando en tu terminal:")
    print("pip install g4f flask reportlab curl_cffi")
    print("="*50)
    exit()

# --- CONTENIDO HTML (Front-End) ---
HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Redactor Académico IA</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            max-width: 600px; 
            margin: 20px auto; 
            padding: 20px; 
            background-color: #f9fafb;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        h2 { 
            color: #1F2937;
            text-align: center;
        }
        form { 
            display: grid; 
            gap: 12px; 
        }
        label {
            font-weight: 600;
            color: #4B5563;
        }
        input[type="text"], textarea { 
            width: 100%; 
            padding: 10px; 
            box-sizing: border-box;
            border: 1px solid #E5E7EB;
            border-radius: 6px;
            font-size: 14px;
        }
        textarea {
            height: 100px;
        }
        button { 
            padding: 12px; 
            background-color: #1F2937; 
            color: white; 
            border: none; 
            cursor: pointer; 
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
        }
        button:hover {
            background-color: #374151;
        }
        .loading {
            display: none; /* Oculto por defecto */
            text-align: center;
            font-weight: bold;
            color: #2563EB;
        }
    </style>
</head>
<body>
    <h2>Redactor Académico IA</h2>
    
    <form id="informeForm" action="/generar" method="POST">
        
        <label for="nombre">Nombre del Estudiante:</label>
        <input type="text" id="nombre" name="nombre" required>

        <label for="matricula">Matrícula:</label>
        <input type="text" id="matricula" name="matricula" required>

        <label for="fecha">Fecha:</label>
        <input type="text" id="fecha" name="fecha" required>

        <label for="tema">Tema General:</label>
        <input type="text" id="tema" name="tema" required>

        <label for="contexto">Instrucciones / Texto (Opcional):</label>
        <textarea id="contexto" name="contexto"></textarea>

        <button type="submit" id="btnGenerar">Generar Informe PDF</button>
        <div id="loadingMessage" class="loading">
            Procesando... Esto puede tardar hasta un minuto.
        </div>
    </form>
    
    <script>
        document.getElementById('informeForm').addEventListener('submit', function() {
            document.getElementById('btnGenerar').disabled = true;
            document.getElementById('btnGenerar').style.backgroundColor = '#555';
            document.getElementById('loadingMessage').style.display = 'block';
        });
    </script>
</body>
</html>
"""

# --- LÓGICA DE IA (Back-End) ---
# ¡CAMBIO! Esta función ahora es SÍNCRONA (no 'async')
def obtener_respuesta_ia(tema, contexto_extra):
    try:
        if contexto_extra and len(contexto_extra) > 5:
            prompt_sistema = (
                "Eres un asistente académico experto. Responde basándote en las instrucciones proporcionadas. "
                "Usa un tono formal. Usa negritas (**) para resaltar títulos."
            )
            mensaje_usuario = f"TEMA: {tema}\n\nINSTRUCCIONES/TEXTO BASE:\n{contexto_extra}"
        else:
            prompt_sistema = (
                "Eres un investigador académico. Redacta un informe técnico. No puedes incluir preguntas "
                "como '¿Desea que profundice en algún aspecto específico?'. Debes entregar un informe completo."
                "Estructura: **Introducción**, **Desarrollo**, **Conclusión**."
                "Usa un tono formal y denso."
            )
            mensaje_usuario = f"Informe sobre: {tema}"

        # ¡CAMBIO! Usamos .create (síncrono) en lugar de .create_async (asíncrono)
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": mensaje_usuario}
            ],
        )
        if not response: 
            return "Error: Respuesta vacía de la IA."
        return response

    except Exception as e:
        return f"Error generando respuesta: {str(e)}"

# --- LÓGICA DE PDF (Back-End) ---
# (Esta función ya estaba bien, pero la dejamos igual)
def generar_pdf_profesional(nombre, matricula, fecha, tema, contenido):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2.5*cm, leftMargin=2.5*cm,
                                topMargin=2.5*cm, bottomMargin=2.5*cm)
        
        estilos = getSampleStyleSheet()
        elementos = []

        color_titulo = colors.HexColor("#1F2937") 
        color_acento = colors.HexColor("#2563EB") 
        color_texto = colors.HexColor("#374151")  
        estilo_titulo = ParagraphStyle('TituloDoc', parent=estilos['Title'], fontSize=24, textColor=color_titulo, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold')
        estilo_cuerpo = ParagraphStyle('Cuerpo', parent=estilos['Normal'], fontSize=11, leading=16, alignment=TA_JUSTIFY, textColor=color_texto, fontName='Helvetica')
        estilo_tabla_lbl = ParagraphStyle('TB', parent=estilos['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=color_titulo)
        estilo_tabla_txt = ParagraphStyle('TT', parent=estilos['Normal'], fontSize=11, textColor=colors.black)

        elementos.append(Paragraph("INFORME ACADÉMICO", estilo_titulo))
        elementos.append(HRFlowable(width="100%", thickness=2, color=color_acento, spaceAfter=20))
        datos = [
            [Paragraph("Estudiante:", estilo_tabla_lbl), Paragraph(html.escape(nombre), estilo_tabla_txt)],
            [Paragraph("Matrícula:", estilo_tabla_lbl), Paragraph(html.escape(matricula), estilo_tabla_txt)],
            [Paragraph("Fecha:", estilo_tabla_lbl), Paragraph(html.escape(fecha), estilo_tabla_txt)],
            [Paragraph("Tema:", estilo_tabla_lbl), Paragraph(html.escape(tema), estilo_tabla_txt)]
        ]
        t = Table(datos, colWidths=[4*cm, 11*cm])
        t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
        elementos.append(t)
        elementos.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=20))
        
        # Limpieza de HTML y formato
        txt = html.escape(contenido)
        txt = txt.replace("\n", "<br/>")
        while "**" in txt:
            txt = txt.replace("**", "<b>", 1)
            txt = txt.replace("**", "</b>", 1)
        
        elementos.append(Paragraph(txt, estilo_cuerpo))
        doc.build(elementos)
        
        buffer.seek(0)
        return buffer.read()

    except Exception as e:
        traceback.print_exc()
        return None

# --- SERVIDOR WEB (Flask) ---

app = Flask(__name__)

# Ruta 1: Muestra la página web (el HTML de arriba)
@app.route('/')
def index():
    return render_template_string(HTML_INTERFAZ)

# Ruta 2: Recibe los datos, genera el PDF y lo envía
@app.route('/generar', methods=['POST'])
def generar_informe():
    try:
        # 1. Obtener datos
        nombre = request.form['nombre']
        matricula = request.form['matricula']
        fecha = request.form['fecha']
        tema = request.form['tema']
        contexto = request.form['contexto']

        # 2. Llamar a la lógica de IA (¡ahora es síncrona!)
        # Ya no necesitamos 'consultar_ia_sync'
        respuesta = obtener_respuesta_ia(tema, contexto)

        if not respuesta or "Error" in respuesta:
            return f"Error de la IA: {respuesta}", 500 

        # 3. Llamar a la lógica de PDF
        pdf_bytes = generar_pdf_profesional(nombre, matricula, fecha, tema, respuesta)
        
        if pdf_bytes is None:
            return "Error creando el PDF", 500

        # 4. Enviar el PDF al navegador
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"Informe_{nombre.replace(' ', '_')}.pdf"
        )
            
    except Exception as e:
        return f"Error interno del servidor: {str(e)}", 500

# --- INICIAR EL SERVIDOR ---
if __name__ == '__main__':
    print("Iniciando servidor web...")
    print("Abre tu navegador y ve a: http://127.0.0.1:5000")
    # app.run() mantiene el programa corriendo para aceptar peticiones
    app.run(debug=True, port=5000)