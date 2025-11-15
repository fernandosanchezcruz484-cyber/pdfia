# --- IMPORTACIONES ---
import io
import html
import re  # Importante para la corrección de '###'
import traceback
from datetime import datetime
from flask import Flask, request, send_file, render_template_string

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER

# Importamos las librerías directamente.
import g4f
import flask
import reportlab
import curl_cffi

# --- CONTENIDO HTML (Front-End) ---
# --- ¡NUEVA INTERFAZ "HERMOSA" Y PROFESIONAL! ---

HTML_INTERFAZ = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redactor Académico IA</title>
    <style>
        /* --- Fuentes y Reset Básico --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #F9FAFB; /* Gris muy claro de fondo */
            color: #1F2937;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 40px 20px;
            min-height: 100vh;
        }

        /* --- Contenedor Principal --- */
        .container {
            max-width: 650px;
            width: 100%;
        }

        /* --- Cabecera --- */
        header {
            text-align: center;
            margin-bottom: 32px;
        }
        header h1 {
            font-size: 32px;
            font-weight: 700;
            color: #111827;
        }
        header p {
            font-size: 16px;
            color: #4B5563;
            margin-top: 8px;
        }

        /* --- Tarjeta del Formulario --- */
        .form-card {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.07), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid #E5E7EB;
        }

        /* --- Estilos del Formulario --- */
        form { 
            display: grid; 
            gap: 20px; /* Espacio entre elementos */
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
        }

        label {
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input[type="text"], textarea { 
            width: 100%; 
            padding: 12px 16px;
            border: 1px solid #D1D5DB; /* Borde gris */
            border-radius: 8px;
            font-size: 16px;
            font-family: 'Inter', sans-serif;
            color: #111827;
            background-color: #F9FAFB;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #2563EB; /* Color de acento azul */
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        textarea {
            height: 120px;
            resize: vertical;
        }

        /* --- Botón de Envío --- */
        button { 
            padding: 14px 20px;
            background-color: #1F2937; /* Color oscuro principal */
            color: white; 
            border: none; 
            cursor: pointer; 
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            width: 100%;
            transition: background-color 0.2s, transform 0.1s;
        }
        
        button:hover {
            background-color: #374151;
        }
        
        button:active {
            transform: scale(0.98);
        }
        
        button:disabled {
            background-color: #9CA3AF; /* Gris para deshabilitado */
            cursor: not-allowed;
        }

        /* --- Mensaje de Carga --- */
        .loading {
            display: none; 
            text-align: center;
            font-weight: 500;
            color: #2563EB;
            font-size: 16px;
            margin-top: 10px;
        }
    </style>
</head>
<body>

    <div class="container">
        <header>
            <h1>Redactor Académico IA</h1>
            <p>Genera informes profesionales con bibliografía en segundos.</p>
        </header>

        <main class="form-card">
            <form id="informeForm" action="/generar" method="POST">
                
                <div class="form-group">
                    <label for="nombre">Nombre del Estudiante:</label>
                    <input type="text" id="nombre" name="nombre" placeholder="Ej. Juan Pérez" required>
                </div>

                <div class="form-group">
                    <label for="matricula">Matrícula:</label>
                    <input type="text" id="matricula" name="matricula" placeholder="Ej. 2024-0123" required>
                </div>

                <div class="form-group">
                    <label for="fecha">Fecha:</label>
                    <input type="text" id="fecha" name="fecha" placeholder="Ej. 15 de noviembre de 2025" required>
                </div>

                <div class="form-group">
                    <label for="tema">Tema General:</label>
                    <input type="text" id="tema" name="tema" placeholder="Ej. La Revolución Industrial y su impacto" required>
                </div>

                <div class="form-group">
                    <label for="contexto">Instrucciones / Texto (Opcional):</label>
                    <textarea id="contexto" name="contexto" placeholder="Pega aquí el texto base del profesor, puntos clave a incluir, etc."></textarea>
                </div>

                <button type="submit" id="btnGenerar">Generar Informe PDF</button>
                
                <div id="loadingMessage" class="loading">
                    Procesando... Esto puede tardar hasta un minuto.
                </div>
            </form>
        </main>
    </div>
    
    <script>
        document.getElementById('informeForm').addEventListener('submit', function() {
            var btn = document.getElementById('btnGenerar');
            btn.disabled = true;
            btn.textContent = 'Generando...';
            document.getElementById('loadingMessage').style.display = 'block';
        });
    </script>
</body>
</html>
"""


# --- LÓGICA DE IA (Back-End) ---
# --- ¡PROMPT MEJORADO CON BIBLIOGRAFÍA! ---
def obtener_respuesta_ia(tema, contexto_extra):
    try:
        if contexto_extra and len(contexto_extra) > 5:
            prompt_sistema = (
                "Eres un asistente académico experto. Responde basándote en las instrucciones proporcionadas. "
                "Usa un tono formal. Usa negritas (**) para resaltar títulos. "
                "Al final del informe, incluye una sección de **Bibliografía** con 3 fuentes *reales y verificables* (en formato APA) que respalden el contenido."
            )
            mensaje_usuario = f"TEMA: {tema}\n\nINSTRUCCIONES/TEXTO BASE:\n{contexto_extra}"
        else:
            prompt_sistema = (
                "Eres un investigador académico. Redacta un informe técnico. No puedes incluir preguntas "
                "como '¿Desea que profundice en algún aspecto específico?'. Debes entregar un informe completo."
                "Estructura: **Introducción**, **Desarrollo**, **Conclusión**."
                "Al final del informe, incluye una sección separada llamada **'Bibliografía'** con 3-5 fuentes *reales y verificables* (en formato APA) que respalden el contenido."
                "Usa un tono formal y denso."
            )
            mensaje_usuario = f"Informe sobre: {tema}"

        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4, # Usar el modelo más capaz
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": mensaje_usuario}
            ],
            timeout=120 # Damos más tiempo para respuestas complejas
        )
        if not response: 
            return "Error: Respuesta vacía de la IA. Intenta de nuevo."
        return response

    except Exception as e:
        return f"Error generando respuesta: {str(e)}"


# --- LÓGICA DE PDF (Back-End) ---
# --- ¡VERSIÓN CORREGIDA PARA '###' Y '**'! ---
def generar_pdf_profesional(nombre, matricula, fecha, tema, contenido):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2.5*cm, leftMargin=2.5*cm,
                                topMargin=2.5*cm, bottomMargin=2.5*cm)
        
        estilos = getSampleStyleSheet()
        elementos = []

        # Paleta de colores profesional
        color_titulo = colors.HexColor("#1F2937") 
        color_acento = colors.HexColor("#2563EB") 
        color_texto = colors.HexColor("#374151")  
        
        # Estilos de Párrafo
        estilo_titulo = ParagraphStyle('TituloDoc', parent=estilos['Title'], fontSize=24, textColor=color_titulo, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold')
        estilo_cuerpo = ParagraphStyle('Cuerpo', parent=estilos['Normal'], fontSize=11, leading=16, alignment=TA_JUSTIFY, textColor=color_texto, fontName='Helvetica')
        estilo_tabla_lbl = ParagraphStyle('TB', parent=estilos['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=color_titulo)
        estilo_tabla_txt = ParagraphStyle('TT', parent=estilos['Normal'], fontSize=11, textColor=colors.black)

        # --- Construcción del PDF ---
        
        # 1. Título y Portada
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
        
        # 2. Contenido de la IA (¡CON CORRECCIÓN!)
        txt = html.escape(contenido)
        
        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
        # Reemplaza '### Título' por '<b>Título</b>'
        txt = re.sub(r'(?m)^#+\s*(.*?)$', r'<b>\1</b>', txt)
        
        # Reemplaza saltos de línea por <br/>
        txt = txt.replace("\n", "<br/>")
        
        # Reemplaza **negrita** por <b>negrita</b>
        while "**" in txt:
            txt = txt.replace("**", "<b>", 1)
            txt = txt.replace("**", "</b>", 1)
        # --- Fin de la corrección ---
        
        elementos.append(Paragraph(txt, estilo_cuerpo))
        
        # Construir el documento
        doc.build(elementos)
        
        buffer.seek(0)
        return buffer.read()

    except Exception as e:
        traceback.print_exc()
        return None

# --- SERVIDOR WEB (Flask) ---
# (Esta parte no necesita cambios)
app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string(HTML_INTERFAZ)

@app.route('/generar', methods=['POST'])
def generar_informe():
    try:
        nombre = request.form['nombre']
        matricula = request.form['matricula']
        fecha = request.form['fecha']
        tema = request.form['tema']
        contexto = request.form['contexto']

        respuesta = obtener_respuesta_ia(tema, contexto)

        if not respuesta or "Error" in respuesta:
            return f"Error de la IA: {respuesta}", 500 

        pdf_bytes = generar_pdf_profesional(nombre, matricula, fecha, tema, respuesta)
        
        if pdf_bytes is None:
            return "Error creando el PDF", 500

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
    app.run(debug=True, port=5000)
