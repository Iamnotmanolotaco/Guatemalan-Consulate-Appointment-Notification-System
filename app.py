# consulate_report_app.py
# Reporte de Atenciones - Consulado (versión Streamlit)

import streamlit as st
import pandas as pd
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
from datetime import datetime, timedelta
import os
import requests
from io import BytesIO

# ============================================================
# CONFIGURACIÓN
# ============================================================

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

# URL del logo en GitHub (CAMBIA POR TU URL)
URL_LOGO_GITHUB = "https://raw.githubusercontent.com/Iamnotmanolotaco/Inmigration-USCIS-Alerts-Automation/main/logo.png"

# Datos de contacto para la firma
NOMBRE_EMPRESA = "Community Law Group, PLLC® "
DEPARTAMENTO = "Quality Control & Efficiency Department"
TELEFONO = "+1 (615) 913-5576"
EMAIL_CONTACTO = "executiveassistant2@communitylawgroup.com"
SITIO_WEB = "www.communitylawgroup.com"

# Destinatarios (por defecto, se pueden editar en la interfaz)
DEFAULT_TO = ["consnashville@minex.gob.gt"]
DEFAULT_CC = ["lsillescas@minex.gob.gt", "dataprojects@communitylawgroup.com", 
              "executiveassistant2@communitylawgroup.com", "data.analyst7@communitylawgroup.com"]

# Tamaño del logo
TAMANO_LOGO = 190

MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

# ============================================================
# FUNCIONES PARA OBTENER RECURSOS
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

def get_logo_bytes():
    return get_image_from_github(URL_LOGO_GITHUB)

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

def formatear_mes(numero_mes):
    return MESES[numero_mes]

def parsear_fechas(df):
    """Detecta y parsea la columna de fechas en el DataFrame"""
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
    
    # Logo HTML con CID
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
        
        # Parte HTML
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Adjuntar logo con CID
        if logo_bytes:
            try:
                logo_cid = "company_logo_cid"
                image_part = MIMEImage(logo_bytes)
                image_part.add_header('Content-ID', f'<{logo_cid}>')
                image_part.add_header('Content-Disposition', 'inline', filename='logo.png')
                image_part.add_header('X-Attachment-Id', logo_cid)
                msg.attach(image_part)
                print("🖼️ Logo adjuntado correctamente")
            except Exception as e:
                print(f"⚠️ Error al adjuntar logo: {e}")
        
        # Enviar
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
    """Procesa el archivo y envía el reporte"""
    
    try:
        # Leer archivo
        df = pd.read_excel(uploaded_file)
        
        # Parsear fechas
        df, columna_fecha = parsear_fechas(df)
        
        if len(df) == 0:
            return False, "❌ No se encontraron fechas válidas en el archivo"
        
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
            
        else:  # rango
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
        
        # Generar HTML
        logo_cid = "company_logo_cid"
        html_body = generar_html_reporte(datos, tipo_reporte, logo_cid)
        
        # Obtener logo
        logo_bytes = get_logo_bytes()
        
        # Enviar correo
        if test_mode:
            # En modo prueba, enviar solo al correo del usuario
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
# INTERFAZ STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Reporte Consulado",
    page_icon="📋",
    layout="wide"
)

# Título
st.title("📋 Reporte de Atenciones - Consulado")
st.markdown("---")

# Sidebar - Configuración
with st.sidebar:
    st.header("📧 Configuración SMTP")
    smtp_username = st.text_input("Correo de Outlook", value="", placeholder="tu@email.com")
    smtp_password = st.text_input("Contraseña", type="password", placeholder="••••••••")
    
    st.markdown("---")
    st.header("📁 Archivo de Datos")
    uploaded_file = st.file_uploader("Carga el archivo Excel", type=['xlsx', 'xls'])
    
    st.markdown("---")
    st.header("📨 Destinatarios")
    to_input = st.text_area("Para (TO)", value=", ".join(DEFAULT_TO), 
                           help="Separa los correos con comas")
    cc_input = st.text_area("CC", value=", ".join(DEFAULT_CC),
                           help="Separa los correos con comas")
    
    st.markdown("---")
    st.header("🧪 Modo Prueba")
    test_mode = st.checkbox("Activar modo prueba", 
                            help="En modo prueba, los correos se envían solo a tu cuenta")

# Área principal
col1, col2 = st.columns([2, 1])

with col1:
    if uploaded_file is not None:
        st.success(f"✅ Archivo cargado: {uploaded_file.name}")
        
        # Mostrar vista previa
        df_preview = pd.read_excel(uploaded_file)
        st.info(f"📊 Registros cargados: {len(df_preview)}")
        
        with st.expander("👁️ Vista previa de datos"):
            st.dataframe(df_preview.head(10))
        
        # Opciones de reporte
        st.subheader("📅 Seleccionar período")
        
        tipo_reporte = st.radio("Tipo de reporte:", ["Día específico", "Rango de fechas"])
        
        if tipo_reporte == "Día específico":
            col_dia1, col_dia2, col_dia3 = st.columns(3)
            with col_dia1:
                dia = st.number_input("Día", min_value=1, max_value=31, value=1)
            with col_dia2:
                mes = st.number_input("Mes", min_value=1, max_value=12, value=1)
            with col_dia3:
                año = st.number_input("Año", min_value=2000, max_value=2100, value=datetime.now().year)
            
            fecha_params = {'dia': dia, 'mes': mes, 'año': año}
            
        else:  # Rango
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
        
        # Botón enviar
        st.markdown("---")
        enviar_btn = st.button("📨 Enviar Reporte", type="primary")
        
        if enviar_btn:
            # Validar credenciales
            if not smtp_username or not smtp_password:
                st.error("❌ Por favor ingresa tus credenciales de Outlook")
            else:
                # Procesar destinatarios
                to_emails = [email.strip() for email in to_input.split(',') if email.strip()]
                cc_emails = [email.strip() for email in cc_input.split(',') if email.strip()]
                
                if not to_emails:
                    st.error("❌ Debes especificar al menos un destinatario")
                else:
                    with st.spinner("⏳ Procesando y enviando reporte..."):
                        # Determinar tipo
                        tipo = 'dia' if tipo_reporte == "Día específico" else 'rango'
                        
                        # Procesar
                        success, msg = procesar_reporte(
                            uploaded_file, tipo, fecha_params,
                            smtp_username, smtp_password,
                            to_emails, cc_emails,
                            test_mode
                        )
                        
                        if success:
                            st.success(msg)
                            if test_mode:
                                st.info("🔬 Modo prueba activo: El correo se envió solo a tu cuenta")
                            else:
                                st.balloons()
                        else:
                            st.error(msg)
        
    else:
        st.info("📌 Carga un archivo Excel en la barra lateral para comenzar")

with col2:
    st.markdown("""
    ### 📋 Instrucciones
    
    1. **Configura tu correo** en la barra lateral
    2. **Carga el archivo Excel** con los datos
    3. **Selecciona el período** del reporte
    4. **Activa modo prueba** para verificar (recomendado)
    5. **Envía el reporte**
    
    ### 📌 Formato del Excel
    - El archivo debe tener una columna de fechas
    - Formato de fecha: `MM/DD/YYYY`
    - Ejemplo: `01/05/2026` = 5 de enero
    
    ### 🔒 Seguridad
    - Las credenciales no se guardan
    - Conexión SMTP con TLS
    - Modo prueba disponible
    """)

st.markdown("---")
st.caption("Reporte Consulado - Versión Cloud | Community Law Group")