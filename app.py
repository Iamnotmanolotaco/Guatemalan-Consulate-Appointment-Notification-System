import streamlit as st
import pandas as pd
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image

# ============================================================
# CONFIGURACIÓN
# ============================================================

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

URL_LOGO_GITHUB = "https://raw.githubusercontent.com/Iamnotmanolotaco/Inmigration-USCIS-Alerts-Automation/main/image.png"
URL_BANNER_GITHUB = "https://raw.githubusercontent.com/Iamnotmanolotaco/Inmigration-USCIS-Alerts-Automation/main/banner.png"

NOMBRE_EMPRESA = "Community Law Group, PLLC® "
DEPARTAMENTO = "Quality Control & Efficiency Department"
TELEFONO = "+1 (615) 913-5576"
EMAIL_CONTACTO = "executiveassistant2@communitylawgroup.com"
SITIO_WEB = "www.communitylawgroup.com"

DEFAULT_TO = ["consnashville@minex.gob.gt"]
DEFAULT_CC = ["lsillescas@minex.gob.gt", "dataprojects@communitylawgroup.com", 
              "executiveassistant2@communitylawgroup.com", "data.analyst7@communitylawgroup.com"]

LOGO_WIDTH = 180
TAMANO_LOGO = 190

MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

# ============================================================
# FUNCIONES PARA OBTENER Y REDIMENSIONAR LOGO
# ============================================================

def get_image_from_github(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        return None

def resize_logo(logo_bytes, target_width=LOGO_WIDTH):
    try:
        if logo_bytes is None:
            return None
        img = Image.open(BytesIO(logo_bytes))
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        target_height = int(target_width * aspect_ratio)
        img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        output = BytesIO()
        img_resized.save(output, format='PNG', quality=95, optimize=True)
        output.seek(0)
        print(f"   🖼️ Logo redimensionado: {target_width}x{target_height}px")
        return output.getvalue()
    except Exception as e:
        print(f"   ⚠️ Error al redimensionar logo: {e}")
        return logo_bytes

def get_logo_bytes():
    logo_bytes = get_image_from_github(URL_LOGO_GITHUB)
    if logo_bytes:
        return resize_logo(logo_bytes, LOGO_WIDTH)
    return None

def get_banner_base64():
    image_bytes = get_image_from_github(URL_BANNER_GITHUB)
    if image_bytes:
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_string}"
    return None

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def obtener_saludo():
    hora_actual = datetime.now().hour
    if 6 <= hora_actual < 12:
        return "Buenos días"
    elif 12 <= hora_actual < 18:
        return "Buenas tardes"
    else:
        return "Buenas noches"

def parsear_fechas(df):
    columna_fecha = None
    for col in df.columns:
        if 'date' in str(col).lower():
            columna_fecha = col
            break
    if columna_fecha is None:
        columna_fecha = df.columns[0]
    
    df[columna_fecha] = pd.to_datetime(df[columna_fecha], format='%m/%d/%Y', errors='coerce')
    df = df.dropna(subset=[columna_fecha])
    df['Date_only'] = df[columna_fecha].dt.date
    
    return df, columna_fecha

# ============================================================
# FUNCIÓN PARA GENERAR HTML DEL CORREO
# ============================================================

def generar_html_reporte(datos, tipo_reporte, logo_cid=None):
    saludo = obtener_saludo()
    
    if tipo_reporte == 'dia':
        dia = datos['dia']
        mes = datos['mes']
        año = datos['año']
        cantidad = datos['cantidad']
        filas_tabla = f"""
        <tr class="fila-normal">
            <td class="columna-fecha">{dia} de {MESES[mes]} de {año}</td>
            <td class="columna-cantidad"><strong>{cantidad}</strong> personas</td>
        </tr>
        """
    else:
        conteo = datos['conteo']
        total = datos['total']
        fecha_inicio = datos['fecha_inicio']
        fecha_fin = datos['fecha_fin']
        filas_tabla = ""
        for fecha, cantidad in sorted(conteo.items()):
            filas_tabla += f"""
            <tr class="fila-normal">
                <td class="columna-fecha">{fecha.day} de {MESES[fecha.month]} de {fecha.year}</td>
                <td class="columna-cantidad"><strong>{cantidad}</strong> personas</td>
            </tr>
            """
        filas_tabla += f"""
        <tr class="total-row">
            <td class="columna-fecha"><strong>TOTAL GENERAL</strong></td>
            <td class="columna-cantidad"><span class="total-cantidad">{total}</span> personas</td>
        </tr>
        """
    
    logo_html = ""
    if logo_cid:
        logo_html = f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <img src="cid:{logo_cid}" 
                 alt="{NOMBRE_EMPRESA}" 
                 width="{TAMANO_LOGO}" 
                 style="width: {TAMANO_LOGO}px; height: auto; border: none; display: block; margin: 0 auto;">
        </div>
        """
    
    firma_html = f"""
    <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #b8d1e8; font-family: 'Segoe UI', 'Calibri', Arial, sans-serif;">
        {logo_html}
        <div style="text-align: center;">
            <strong style="color: #1a3a5c; font-size: 14px;">{NOMBRE_EMPRESA}</strong><br>
            <span style="color: #4a7c9c; font-size: 12px;">{DEPARTAMENTO}</span><br>
            <span style="color: #666666; font-size: 11px;">
                📞 {TELEFONO} | ✉️ <a href="mailto:{EMAIL_CONTACTO}" style="color: #4a7c9c; text-decoration: none;">{EMAIL_CONTACTO}</a> | 🌐 <a href="https://{SITIO_WEB}" style="color: #4a7c9c; text-decoration: none;">{SITIO_WEB}</a>
            </span>
        </div>
    </div>
    """
    
    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', 'Calibri', Arial, sans-serif;
                line-height: 1.5;
                color: #000000;
                margin: 0;
                padding: 0;
                background-color: #f5f7fa;
            }}
            .container {{
                max-width: 650px;
                margin: 0 auto;
                padding: 25px;
                background-color: #ffffff;
                border: 1px solid #dce4ec;
            }}
            .header {{
                background-color: #e8f0f8;
                padding: 20px;
                border-bottom: 2px solid #b8d1e8;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 22px;
                font-weight: bold;
                color: #1a3a5c;
            }}
            .saludo {{
                background-color: #f0f6fc;
                border-left: 3px solid #4a7c9c;
                padding: 12px 18px;
                margin: 20px 0;
                font-size: 15px;
                color: #000000;
            }}
            .saludo strong {{
                color: #1a3a5c;
                font-weight: bold;
            }}
            .tabla-resumen {{
                margin: 25px 0;
                border: 1px solid #dce4ec;
                background-color: #ffffff;
                border-radius: 4px;
                overflow: hidden;
            }}
            .tabla-resumen table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .tabla-resumen th {{
                background-color: #e8f0f8;
                color: #1a3a5c;
                font-weight: bold;
                padding: 12px 15px;
                font-size: 14px;
                text-align: left;
                border-bottom: 2px solid #b8d1e8;
            }}
            .tabla-resumen td {{
                padding: 12px 15px;
                font-size: 14px;
                color: #000000;
                border-bottom: 1px solid #e8edf2;
                text-align: left;
            }}
            .tabla-resumen tr:last-child td {{
                border-bottom: none;
            }}
            .columna-fecha {{
                width: 60%;
                text-align: left;
            }}
            .columna-cantidad {{
                width: 40%;
                text-align: left;
            }}
            .fila-normal:hover {{
                background-color: #f8fafc;
            }}
            .total-row {{
                background-color: #f0f6fc;
                border-top: 1px solid #c8d8e8;
            }}
            .total-row td {{
                font-weight: bold;
                padding: 14px 15px;
            }}
            .total-cantidad {{
                font-size: 20px;
                font-weight: bold;
                color: #1a3a5c;
            }}
            .agradecimiento {{
                background-color: #f0f6fc;
                padding: 12px 18px;
                margin-top: 25px;
                text-align: center;
                font-size: 13px;
                color: #000000;
                border-top: 1px solid #dce4ec;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Reporte de Atenciones</h1>
            </div>
            <div class="saludo">
                <strong>{saludo},</strong><br>
                Esperamos que se encuentren muy bien.
            </div>
            <div class="tabla-resumen">
                <table>
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Personas Atendidas</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_tabla}
                    </tbody>
                </table>
            </div>
            <div class="agradecimiento">
                Muchas gracias por su atención y colaboración.<br>
                Quedamos atentos a cualquier consulta adicional.
            </div>
            {firma_html}
        </div>
    </body>
    </html>
    """
    
    return html

# ============================================================
# FUNCIÓN PARA ENVIAR CORREO
# ============================================================

def enviar_correo(smtp_username, smtp_password, to_emails, cc_emails, 
                  subject, html_body, logo_bytes=None, test_mode=False):
    try:
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = ", ".join(to_emails)
        if cc_emails:
            msg['CC'] = ", ".join(cc_emails)
        msg['X-Priority'] = '1'
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        if logo_bytes:
            try:
                logo_cid = "company_logo_cid"
                image_part = MIMEImage(logo_bytes)
                image_part.add_header('Content-ID', f'<{logo_cid}>')
                image_part.add_header('Content-Disposition', 'inline', filename='logo.png')
                image_part.add_header('X-Attachment-Id', logo_cid)
                msg.attach(image_part)
                print("   🖼️ Logo adjuntado correctamente")
            except Exception as e:
                print(f"   ⚠️ Error al adjuntar logo: {e}")
        
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            all_recipients = to_emails + (cc_emails if cc_emails else [])
            server.sendmail(smtp_username, all_recipients, msg.as_string())
        
        if test_mode:
            return True, "✅ Correo enviado en MODO PRUEBA"
        else:
            return True, "✅ Correo enviado exitosamente"
            
    except Exception as e:
        return False, f"❌ Error al enviar: {str(e)}"

# ============================================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ============================================================

def procesar_reporte(uploaded_file, tipo_reporte, fecha_params, 
                     smtp_username, smtp_password, 
                     to_emails, cc_emails, test_mode=False):
    
    try:
        df = pd.read_excel(uploaded_file)
        df, columna_fecha = parsear_fechas(df)
        
        if len(df) == 0:
            return False, "❌ No se encontraron fechas válidas en el archivo"
        
        logo_bytes = get_logo_bytes()
        logo_cid = "company_logo_cid" if logo_bytes else None
        
        if tipo_reporte == 'dia':
            dia = fecha_params['dia']
            mes = fecha_params['mes']
            año = fecha_params['año']
            fecha_buscar = datetime(año, mes, dia).date()
            
            cantidad = len(df[df['Date_only'] == fecha_buscar])
            
            if cantidad == 0:
                return False, f"❌ No hay datos para el {dia} de {MESES[mes]} de {año}"
            
            datos = {'dia': dia, 'mes': mes, 'año': año, 'cantidad': cantidad}
            asunto = f"Reporte de atenciones - {dia} de {MESES[mes]} de {año}"
            
        else:
            dia_ini = fecha_params['dia_ini']
            mes_ini = fecha_params['mes_ini']
            año_ini = fecha_params['año_ini']
            dia_fin = fecha_params['dia_fin']
            mes_fin = fecha_params['mes_fin']
            año_fin = fecha_params['año_fin']
            
            fecha_inicio = datetime(año_ini, mes_ini, dia_ini).date()
            fecha_fin = datetime(año_fin, mes_fin, dia_fin).date()
            
            mask = (df['Date_only'] >= fecha_inicio) & (df['Date_only'] <= fecha_fin)
            df_filtrado = df[mask]
            
            if len(df_filtrado) == 0:
                return False, f"❌ No hay datos en el rango solicitado"
            
            conteo = df_filtrado['Date_only'].value_counts().to_dict()
            total = sum(conteo.values())
            datos = {'conteo': conteo, 'total': total, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin}
            
            if año_inicio == año_fin:
                asunto = f"Reporte de atenciones - {dia_ini} de {MESES[mes_ini]} al {dia_fin} de {MESES[mes_fin]} de {año_inicio}"
            else:
                asunto = f"Reporte de atenciones - {dia_ini} de {MESES[mes_ini]} de {año_ini} al {dia_fin} de {MESES[mes_fin]} de {año_fin}"
        
        html_body = generar_html_reporte(datos, tipo_reporte, logo_cid)
        
        if test_mode:
            to_emails = [smtp_username]
            cc_emails = []
            asunto = f"[PRUEBA] {asunto}"
        
        success, msg = enviar_correo(
            smtp_username, smtp_password,
            to_emails, cc_emails,
            asunto, html_body,
            logo_bytes, test_mode
        )
        
        return success, msg
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================

st.set_page_config(
    page_title="Reporte Consulado",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS - MODO CLARO FORZADO
# ============================================================

st.markdown("""
<style>
    /* Ocultar elementos */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Fondo general */
    .stApp, .stApp > div, .main, .main > div, .block-container {
        background-color: #e8edf2 !important;
    }
    
    /* BARRA LATERAL - AZUL CLARO */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0f4f8, #d5dde6) !important;
        border-right: 2px solid #1a4a7a !important;
    }
    
    section[data-testid="stSidebar"] > div {
        background-color: transparent !important;
    }
    
    /* TEXTOS EN LA BARRA LATERAL - OSCUROS */
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stText,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #1a2a3a !important;
    }
    
    /* INPUTS EN BARRA LATERAL */
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #1a2a3a !important;
        border-color: #c8d0d8 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder {
        color: #8a9bb0 !important;
        opacity: 0.7 !important;
    }
    
    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {
        border-color: #1a4a7a !important;
        box-shadow: 0 0 20px rgba(26, 74, 122, 0.15) !important;
    }
    
    section[data-testid="stSidebar"] .stTextArea > div > div > textarea {
        background-color: #ffffff !important;
        color: #1a2a3a !important;
        border-color: #c8d0d8 !important;
        border-radius: 8px !important;
        font-size: 14px !important;
    }
    
    section[data-testid="stSidebar"] .stFileUploader > div > button {
        background-color: #1a4a7a !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    
    section[data-testid="stSidebar"] .stFileUploader > div > button:hover {
        background-color: #0d2a4a !important;
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .stCheckbox label {
        color: #1a2a3a !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        padding: 10px 16px !important;
        transition: all 0.3s ease !important;
        border: none !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:first-child {
        background: linear-gradient(135deg, #1a4a7a, #6c3483) !important;
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:first-child:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 25px rgba(26, 74, 122, 0.3) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:last-child {
        background: rgba(26, 74, 122, 0.08) !important;
        color: #1a2a3a !important;
        border: 1px solid rgba(26, 74, 122, 0.15) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:last-child:hover {
        background: rgba(26, 74, 122, 0.15) !important;
        transform: translateY(-3px) !important;
    }
    
    section[data-testid="stSidebar"] .stCaption {
        color: #4a5a6a !important;
        font-size: 11px !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] hr {
        border-color: #d5dde6 !important;
        margin: 12px 0 !important;
        opacity: 0.5 !important;
    }
    
    /* TÍTULO DE LA BARRA LATERAL */
    .sidebar-title {
        text-align: center;
        padding: 16px 0 12px 0;
        border-bottom: 2px solid #1a4a7a;
        margin-bottom: 16px;
    }
    
    .sidebar-title .main {
        font-weight: 800;
        color: #1a3a5c;
        font-size: 24px;
        letter-spacing: -0.3px;
    }
    
    .sidebar-title .sub {
        font-size: 12px;
        color: #4a5a6a;
        letter-spacing: 1.5px;
        font-weight: 600;
    }
    
    /* SECCIONES DE LA BARRA LATERAL */
    .sidebar-section {
        background: rgba(26, 74, 122, 0.05);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(26, 74, 122, 0.08);
        transition: all 0.3s ease;
    }
    
    .sidebar-section:hover {
        background: rgba(26, 74, 122, 0.10);
        border-color: #1a4a7a;
        transform: translateX(4px);
    }
    
    .sidebar-section .icon {
        font-size: 18px;
        margin-right: 8px;
    }
    
    .sidebar-section .label {
        font-weight: 700;
        color: #1a2a3a !important;
        font-size: 14px;
    }
    
    .sidebar-section .desc {
        font-size: 12px;
        color: #4a5a6a !important;
        margin-top: 2px;
    }
    
    /* ANIMACIONES */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate { animation: fadeInUp 0.6s ease-out; }
    .animate-delay-1 { animation-delay: 0.1s; }
    .animate-delay-2 { animation-delay: 0.2s; }
    .animate-delay-3 { animation-delay: 0.3s; }
    .animate-delay-4 { animation-delay: 0.4s; }
    
    /* TARJETAS */
    .card {
        background-color: #ffffff !important;
        border-radius: 14px;
        padding: 22px 26px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
        border: 1px solid #e8edf2 !important;
        margin-bottom: 16px;
        animation: fadeInUp 0.5s ease-out;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.08) !important;
    }
    
    /* MÉTRICAS */
    .metric-container {
        background-color: #ffffff !important;
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
        border: 2px solid #e8edf2 !important;
        transition: all 0.3s ease;
        animation: fadeInUp 0.5s ease-out;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }
    
    .metric-container:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.08) !important;
    }
    
    .metric-value {
        font-size: 38px;
        font-weight: 800;
        line-height: 1.2;
        color: #1a4a7a !important;
    }
    
    .metric-label {
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 4px;
        color: #4a5a6a !important;
    }
    
    .metric-red .metric-value { color: #c0392b !important; }
    .metric-red .metric-label { color: #922b21 !important; }
    .metric-red { border-color: #c0392b !important; }
    
    .metric-yellow .metric-value { color: #d4ac0d !important; }
    .metric-yellow .metric-label { color: #9a7d0a !important; }
    .metric-yellow { border-color: #d4ac0d !important; }
    
    .metric-green .metric-value { color: #1e8449 !important; }
    .metric-green .metric-label { color: #145a32 !important; }
    .metric-green { border-color: #1e8449 !important; }
    
    .metric-blue .metric-value { color: #1a4a7a !important; }
    .metric-blue .metric-label { color: #0d2a4a !important; }
    .metric-blue { border-color: #1a4a7a !important; }
    
    .metric-purple .metric-value { color: #6c3483 !important; }
    .metric-purple .metric-label { color: #6c3483 !important; }
    .metric-purple { border-color: #6c3483 !important; }
    
    /* EXPANDER */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #1a2a3a !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        border: 1px solid #e8edf2 !important;
    }
    
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        border: 1px solid #e8edf2 !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }
    
    /* DATA FRAME */
    .stDataFrame, .stDataFrame > div, .stDataFrame table {
        background-color: #ffffff !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        border: 1px solid #e8edf2 !important;
    }
    
    .stDataFrame th {
        background-color: #f0f4f8 !important;
        color: #1a2a3a !important;
    }
    
    .stDataFrame td {
        background-color: #ffffff !important;
        color: #1a2a3a !important;
    }
    
    /* RESULTADOS */
    .result-success {
        background-color: #eafaf1 !important;
        border-left: 6px solid #27ae60 !important;
        padding: 14px 18px;
        border-radius: 6px;
        margin: 6px 0;
        color: #1a2a3a !important;
        font-size: 15px;
        font-weight: 500;
        animation: fadeInUp 0.4s ease-out;
    }
    
    .result-error {
        background-color: #fdedec !important;
        border-left: 6px solid #c0392b !important;
        padding: 14px 18px;
        border-radius: 6px;
        margin: 6px 0;
        color: #1a2a3a !important;
        font-size: 15px;
        font-weight: 500;
        animation: fadeInUp 0.4s ease-out;
    }
    
    .result-info {
        background-color: #eaf2fa !important;
        border-left: 6px solid #1e40af !important;
        padding: 14px 18px;
        border-radius: 6px;
        margin: 6px 0;
        color: #1a2a3a !important;
        font-size: 15px;
        font-weight: 500;
        animation: fadeInUp 0.4s ease-out;
    }
    
    /* BOTONES */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease !important;
        border: none !important;
        background: linear-gradient(135deg, #1a4a7a, #6c3483) !important;
        color: white !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 25px rgba(26, 74, 122, 0.3) !important;
    }
    
    /* RADIO BUTTONS */
    .stRadio > div {
        background-color: #ffffff !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        border: 1px solid #e8edf2 !important;
    }
    
    .stRadio label {
        color: #1a2a3a !important;
        font-weight: 500 !important;
    }
    
    /* NUMBER INPUT */
    .stNumberInput > div > div > input {
        background-color: #ffffff !important;
        color: #1a2a3a !important;
        border-color: #c8d0d8 !important;
        border-radius: 8px !important;
    }
    
    /* FOOTER */
    .footer {
        text-align: center;
        padding: 20px;
        color: #4a5a6a !important;
        font-size: 13px;
        border-top: 2px solid #e8edf2;
        margin-top: 30px;
    }
    
    /* TEXTOS GENERALES */
    h1, h2, h3, h4, h5, h6 {
        color: #1a2a3a !important;
        font-weight: 700 !important;
    }
    
    .stMarkdown, .stText, .stCaption, label {
        color: #4a5a6a !important;
    }
    
    .stAlert {
        background-color: #ffffff !important;
        border: 1px solid #e8edf2 !important;
        border-radius: 8px !important;
    }
    
    .stAlert > div {
        color: #1a2a3a !important;
    }
    
    .stSpinner > div {
        border-color: #1a4a7a !important;
    }
    
    .banner-container {
        border-radius: 14px;
        overflow: hidden;
        margin-bottom: 25px;
        animation: fadeInUp 0.5s ease-out;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    
    .text-large {
        font-size: 18px;
        line-height: 1.6;
    }
    
    .text-dark { color: #0d1a2a !important; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# BANNER
# ============================================================

banner_base64 = get_banner_base64()

if banner_base64:
    st.markdown(f"""
    <div class="banner-container">
        <img src="{banner_base64}" alt="Reporte Consulado" style="width: 100%; height: auto; display: block;">
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a3a5c, #4a7c9c);
        padding: 30px 40px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(26, 58, 92, 0.25);
        animation: fadeInUp 0.5s ease-out;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
            <div>
                <h1 style="color: white; font-size: 28px; font-weight: 700; margin: 0; letter-spacing: -0.5px;">
                    📋 Reporte Consulado
                </h1>
                <p style="color: rgba(255,255,255,0.9); font-size: 15px; margin: 4px 0 0 0;">
                    Atenciones y servicios al Consulado de Guatemala
                </p>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <span style="background: rgba(255,255,255,0.2); color: white; padding: 6px 16px; border-radius: 30px; font-size: 13px; font-weight: 600;">v1.0</span>
                <span style="background: rgba(46, 204, 113, 0.3); color: #2ecc71; padding: 6px 16px; border-radius: 30px; font-size: 13px; font-weight: 600; border: 1px solid rgba(46, 204, 113, 0.3);">● Active</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# BARRA LATERAL
# ============================================================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-title">
        <div class="main">📋 Reporte</div>
        <div class="sub">CONSULADO</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="sidebar-section">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="icon">📧</span>
            <span class="label">Correo</span>
        </div>
        <div class="desc">Configuración SMTP de Outlook</div>
    </div>
    """, unsafe_allow_html=True)
    
    smtp_username = st.text_input("Usuario", value="", placeholder="tu@email.com", label_visibility="collapsed")
    smtp_password = st.text_input("Contraseña", type="password", placeholder="••••••••", label_visibility="collapsed")
    
    st.markdown("""
    <div class="sidebar-section">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="icon">📁</span>
            <span class="label">Datos</span>
        </div>
        <div class="desc">Carga tu archivo Excel</div>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Archivo Excel", type=['xlsx', 'xls'], label_visibility="collapsed")
    
    st.markdown("""
    <div class="sidebar-section">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="icon">📨</span>
            <span class="label">Destinatarios</span>
        </div>
        <div class="desc">Separados por comas</div>
    </div>
    """, unsafe_allow_html=True)
    
    to_input = st.text_area("Para (TO)", value=", ".join(DEFAULT_TO), label_visibility="collapsed", height=60)
    cc_input = st.text_area("CC", value=", ".join(DEFAULT_CC), label_visibility="collapsed", height=60)
    
    st.markdown("""
    <div class="sidebar-section">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="icon">🧪</span>
            <span class="label">Modo prueba</span>
        </div>
        <div class="desc">Envía solo a tu cuenta</div>
    </div>
    """, unsafe_allow_html=True)
    
    test_mode = st.checkbox("", label_visibility="collapsed")
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        enviar_reales = st.button("📨 Enviar", type="primary", use_container_width=True)
    with col_btn2:
        simular = st.button("📄 Simular", use_container_width=True)
    
    st.markdown("---")
    st.caption("🔒 TLS seguro · Sin almacenamiento")

# ============================================================
# ÁREA PRINCIPAL
# ============================================================

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    st.markdown(f"<div class='text-large text-dark' style='font-weight: 700; font-size: 20px; margin-bottom: 16px;'>📊 Resumen de datos</div>", unsafe_allow_html=True)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.markdown(f"""
        <div class="metric-container metric-blue animate animate-delay-1">
            <div class="metric-value">{len(df)}</div>
            <div class="metric-label">Registros</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m2:
        fecha_col = None
        for col in df.columns:
            if 'date' in str(col).lower():
                fecha_col = col
                break
        if fecha_col is None:
            fecha_col = df.columns[0]
        fechas_unicas = df[fecha_col].nunique()
        st.markdown(f"""
        <div class="metric-container metric-purple animate animate-delay-2">
            <div class="metric-value">{fechas_unicas}</div>
            <div class="metric-label">Fechas</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m3:
        st.markdown(f"""
        <div class="metric-container metric-yellow animate animate-delay-3">
            <div class="metric-value">{datetime.now().strftime('%d/%m')}</div>
            <div class="metric-label">Hoy</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m4:
        st.markdown(f"""
        <div class="metric-container metric-green animate animate-delay-4">
            <div class="metric-value">{datetime.now().year}</div>
            <div class="metric-label">Año</div>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("👁️ Vista previa de datos"):
        st.dataframe(df.head(10), use_container_width=True)
    
    st.subheader("📅 Seleccionar período")
    
    tipo_reporte = st.radio("Tipo de reporte:", ["Día específico", "Rango de fechas"], horizontal=True)
    
    if tipo_reporte == "Día específico":
        col_dia1, col_dia2, col_dia3 = st.columns(3)
        with col_dia1:
            dia = st.number_input("Día", min_value=1, max_value=31, value=1)
        with col_dia2:
            mes = st.number_input("Mes", min_value=1, max_value=12, value=1)
        with col_dia3:
            año = st.number_input("Año", min_value=2000, max_value=2100, value=datetime.now().year)
        
        fecha_params = {'dia': dia, 'mes': mes, 'año': año}
        
    else:
        st.markdown("**Fecha de inicio:**")
        col_ini1, col_ini2, col_ini3 = st.columns(3)
        with col_ini1:
            dia_ini = st.number_input("Día inicio", min_value=1, max_value=31, value=1)
        with col_ini2:
            mes_ini = st.number_input("Mes inicio", min_value=1, max_value=12, value=1)
        with col_ini3:
            año_ini = st.number_input("Año inicio", min_value=2000, max_value=2100, value=datetime.now().year)
        
        st.markdown("**Fecha de fin:**")
        col_fin1, col_fin2, col_fin3 = st.columns(3)
        with col_fin1:
            dia_fin = st.number_input("Día fin", min_value=1, max_value=31, value=1)
        with col_fin2:
            mes_fin = st.number_input("Mes fin", min_value=1, max_value=12, value=1)
        with col_fin3:
            año_fin = st.number_input("Año fin", min_value=2000, max_value=2100, value=datetime.now().year)
        
        fecha_params = {
            'dia_ini': dia_ini, 'mes_ini': mes_ini, 'año_ini': año_ini,
            'dia_fin': dia_fin, 'mes_fin': mes_fin, 'año_fin': año_fin
        }
    
    if enviar_reales or simular:
        if enviar_reales and (not smtp_username or not smtp_password):
            st.error("⚠️ Ingresa tus credenciales de Outlook para enviar correos reales")
        else:
            with st.spinner("⏳ Procesando reporte..."):
                tipo = 'dia' if tipo_reporte == "Día específico" else 'rango'
                
                # ============================================================
                # LLAMADA CORRECTA A LA FUNCIÓN
                # ============================================================
                success, msg = procesar_reporte(
                    uploaded_file, tipo, fecha_params,
                    smtp_username, smtp_password,
                    to_emails, cc_emails,
                    test_mode
                )
                # ============================================================
            
            st.markdown("---")
            st.markdown(f"<div style='font-weight: 700; color: #1a2a3a; font-size: 20px;'>📋 Resultados</div>", unsafe_allow_html=True)
            
            if success:
                st.success(msg)
                if test_mode:
                    st.info("🔬 Modo prueba activo: El correo se envió solo a tu cuenta")
                else:
                    st.balloons()
            else:
                st.error(msg)

else:
    st.markdown("""
    <div style="
        text-align: center;
        padding: 100px 30px;
        background-color: #ffffff;
        border-radius: 14px;
        border: 2px dashed #d5dde6;
        animation: fadeInUp 0.6s ease-out;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    ">
        <div style="font-size: 72px; margin-bottom: 24px;">📂</div>
        <h2 style="color: #1a2a3a; font-weight: 800; margin: 0; font-size: 28px;">Carga tu archivo Excel</h2>
        <p style="color: #4a5a6a; margin: 12px 0 0 0; font-size: 17px;">
            Sube el archivo con los registros de atención del consulado
        </p>
        <div style="margin-top: 20px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
            <span style="background: #f5f8fc; padding: 6px 20px; border-radius: 30px; font-size: 14px; font-weight: 600; color: #4a5a6a;">MM/DD/YYYY</span>
            <span style="background: #f5f8fc; padding: 6px 20px; border-radius: 30px; font-size: 14px; font-weight: 600; color: #4a5a6a;">Fecha</span>
            <span style="background: #f5f8fc; padding: 6px 20px; border-radius: 30px; font-size: 14px; font-weight: 600; color: #4a5a6a;">Atenciones</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================

st.markdown("""
<div class="footer">
    <strong style="color: #1a2a3a;">Reporte Consulado</strong> · Community Law Group
    <br>
    © 2026 · Data &amp; Efficiency Team
</div>
""", unsafe_allow_html=True)
