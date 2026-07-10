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
import pytz
import traceback

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================

st.set_page_config(
    page_title="Reporte Consulado",
    page_icon="📋",
    layout="wide"
)

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

TAMANO_LOGO = 190
LOGO_WIDTH = 180
AÑO_FIJO = 2026

ZONA_HORARIA = pytz.timezone('America/Bogota')

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
        return output.getvalue()
    except Exception as e:
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
    hora_actual = datetime.now(ZONA_HORARIA).hour
    if 6 <= hora_actual < 12:
        return "Buenos días"
    elif 12 <= hora_actual < 18:
        return "Buenas tardes"
    else:
        return "Buenas noches"

def obtener_hora_local():
    return datetime.now(ZONA_HORARIA)

def parsear_fechas(df):
    """Detecta y parsea la columna de fechas"""
    columna_fecha = None
    for col in df.columns:
        if 'date' in str(col).lower():
            columna_fecha = col
            break
    if columna_fecha is None:
        columna_fecha = df.columns[0]
    
    # Intentar parsear fechas en formato MM/DD/YYYY
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
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO - CON MANEJO DE ERRORES
# ============================================================

def procesar_reporte(uploaded_file, tipo_reporte, fecha_params, 
                     smtp_username, smtp_password, 
                     to_emails, cc_emails, test_mode=False):
    
    try:
        # ============================================================
        # LECTURA SEGURA DEL EXCEL
        # ============================================================
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        except Exception as e:
            return False, f"❌ Error al leer el archivo Excel: {str(e)}"
        
        if len(df) == 0:
            return False, "❌ El archivo está vacío"
        
        # ============================================================
        # PROCESAR FECHAS
        # ============================================================
        try:
            df, columna_fecha = parsear_fechas(df)
            if len(df) == 0:
                return False, "❌ No se encontraron fechas válidas en el archivo"
        except Exception as e:
            return False, f"❌ Error al procesar fechas: {str(e)}"
        
        # ============================================================
        # OBTENER LOGO
        # ============================================================
        logo_bytes = get_logo_bytes()
        logo_cid = "company_logo_cid" if logo_bytes else None
        
        # ============================================================
        # PROCESAR SEGÚN TIPO
        # ============================================================
        if tipo_reporte == 'dia':
            dia = fecha_params['dia']
            mes = fecha_params['mes']
            año = AÑO_FIJO
            fecha_buscar = datetime(año, mes, dia).date()
            
            cantidad = len(df[df['Date_only'] == fecha_buscar])
            
            if cantidad == 0:
                return False, f"❌ No hay datos para el {dia} de {MESES[mes]} de {año}"
            
            datos = {'dia': dia, 'mes': mes, 'año': año, 'cantidad': cantidad}
            asunto = f"Reporte de atenciones - {dia} de {MESES[mes]} de {año}"
            
        else:  # Rango
            dia_ini = fecha_params['dia_ini']
            mes_ini = fecha_params['mes_ini']
            dia_fin = fecha_params['dia_fin']
            mes_fin = fecha_params['mes_fin']
            
            fecha_inicio = datetime(AÑO_FIJO, mes_ini, dia_ini).date()
            fecha_fin = datetime(AÑO_FIJO, mes_fin, dia_fin).date()
            
            mask = (df['Date_only'] >= fecha_inicio) & (df['Date_only'] <= fecha_fin)
            df_filtrado = df[mask]
            
            if len(df_filtrado) == 0:
                return False, f"❌ No hay datos en el rango solicitado"
            
            conteo = df_filtrado['Date_only'].value_counts().to_dict()
            total = sum(conteo.values())
            datos = {'conteo': conteo, 'total': total, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin}
            
            if dia_ini == dia_fin and mes_ini == mes_fin:
                asunto = f"Reporte de atenciones - {dia_ini} de {MESES[mes_ini]} de {AÑO_FIJO}"
            else:
                asunto = f"Reporte de atenciones - {dia_ini} de {MESES[mes_ini]} al {dia_fin} de {MESES[mes_fin]} de {AÑO_FIJO}"
        
        # ============================================================
        # GENERAR HTML
        # ============================================================
        html_body = generar_html_reporte(datos, tipo_reporte, logo_cid)
        
        # ============================================================
        # MODO PRUEBA
        # ============================================================
        if test_mode:
            to_emails = [smtp_username]
            cc_emails = []
            asunto = f"[PRUEBA] {asunto}"
        
        # ============================================================
        # ENVIAR CORREO
        # ============================================================
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

# Banner
banner_base64 = get_banner_base64()

if banner_base64:
    st.image(banner_base64, use_container_width=True)
else:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a3a5c, #4a7c9c);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <h1 style="color: white; margin: 0; font-size: 24px;">📋 Reporte de Atenciones - Consulado</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 4px 0 0 0;">Atenciones y servicios al Consulado de Guatemala</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 📧 Configuración SMTP")
    smtp_username = st.text_input("Correo de Outlook", value="", placeholder="tu@email.com")
    smtp_password = st.text_input("Contraseña", type="password", placeholder="••••••••")
    
    st.markdown("---")
    st.markdown("### 📁 Archivo de Datos")
    uploaded_file = st.file_uploader("Carga el archivo Excel", type=['xlsx', 'xls'])
    
    st.markdown("---")
    st.markdown("### 📨 Destinatarios")
    default_to = "consnashville@minex.gob.gt"
    default_cc = "lsillescas@minex.gob.gt, executiveassistant2@communitylawgroup.com, diana.lopez@communitylawgroup.com"
    
    to_input = st.text_area("Para (TO)", value=default_to, height=60)
    cc_input = st.text_area("CC", value=default_cc, height=60)
    
    st.markdown("---")
    st.markdown("### 🧪 Modo prueba")
    test_mode = st.checkbox("Activar modo prueba (envía solo a tu correo)")
    
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        enviar_reales = st.button("📨 Enviar", type="primary", use_container_width=True)
    with col_btn2:
        simular = st.button("📄 Simular", use_container_width=True)
    
    st.caption("🔒 TLS seguro · Sin almacenamiento")

# Área principal
if uploaded_file is not None:
    try:
        # ============================================================
        # LECTURA DEL EXCEL CON MANEJO DE ERRORES DETALLADO
        # ============================================================
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        except Exception as e:
            st.error(f"❌ Error al leer el archivo: {str(e)}")
            st.info("💡 Asegúrate de que el archivo sea un Excel válido (.xlsx o .xls)")
            st.stop()
        
        st.markdown("### 📊 Resumen de datos")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Registros", len(df))
        
        with col2:
            fecha_col = None
            for col in df.columns:
                if 'date' in str(col).lower():
                    fecha_col = col
                    break
            if fecha_col is None:
                fecha_col = df.columns[0]
            st.metric("Columnas", len(df.columns))
        
        with col3:
            st.metric("Hoy", obtener_hora_local().strftime('%d/%m/%Y'))
        
        with col4:
            st.metric("Año", AÑO_FIJO)
        
        with st.expander("👁️ Vista previa de datos"):
            st.dataframe(df.head(10), use_container_width=True)
        
        # ============================================================
        # SELECCIÓN DE PERÍODO
        # ============================================================
        st.markdown("### 📅 Seleccionar período")
        
        st.info(f"📌 Las fechas en el Excel están en formato **MM/DD/YYYY** (ejemplo: 01/05/2026 = 5 de enero) | 📅 **Año fijo: {AÑO_FIJO}** | 🕐 **Saludo actual:** {obtener_saludo()} ({obtener_hora_local().strftime('%H:%M')})")
        
        tipo_reporte = st.radio("Tipo de reporte:", ["Día específico", "Rango de fechas"], horizontal=True)
        
        fecha_params = {}
        
        if tipo_reporte == "Día específico":
            col_dia1, col_dia2 = st.columns(2)
            with col_dia1:
                dia = st.number_input("Día", min_value=1, max_value=31, value=1)
            with col_dia2:
                mes = st.number_input("Mes (1-12)", min_value=1, max_value=12, value=1)
            
            fecha_params = {'dia': dia, 'mes': mes}
            
        else:
            st.markdown("**Fecha de INICIO:**")
            col_ini1, col_ini2 = st.columns(2)
            with col_ini1:
                dia_ini = st.number_input("Día", min_value=1, max_value=31, value=1, key="dia_ini")
            with col_ini2:
                mes_ini = st.number_input("Mes (1-12)", min_value=1, max_value=12, value=1, key="mes_ini")
            
            st.markdown("**Fecha de FIN:**")
            col_fin1, col_fin2 = st.columns(2)
            with col_fin1:
                dia_fin = st.number_input("Día", min_value=1, max_value=31, value=1, key="dia_fin")
            with col_fin2:
                mes_fin = st.number_input("Mes (1-12)", min_value=1, max_value=12, value=1, key="mes_fin")
            
            fecha_params = {
                'dia_ini': dia_ini,
                'mes_ini': mes_ini,
                'dia_fin': dia_fin,
                'mes_fin': mes_fin
            }
        
        # ============================================================
        # PROCESAR ENVÍO
        # ============================================================
        if enviar_reales or simular:
            if enviar_reales and (not smtp_username or not smtp_password):
                st.error("⚠️ Ingresa tus credenciales de Outlook para enviar correos reales")
            else:
                to_emails = [email.strip() for email in to_input.split(',') if email.strip()]
                cc_emails = [email.strip() for email in cc_input.split(',') if email.strip()]
                
                if not to_emails:
                    st.error("❌ Debes especificar al menos un destinatario")
                else:
                    with st.spinner("⏳ Procesando reporte..."):
                        tipo = 'dia' if tipo_reporte == "Día específico" else 'rango'
                        
                        success, msg = procesar_reporte(
                            uploaded_file, tipo, fecha_params,
                            smtp_username, smtp_password,
                            to_emails, cc_emails,
                            test_mode
                        )
                    
                    st.markdown("---")
                    st.markdown("### 📋 Resultados")
                    
                    if success:
                        st.success(msg)
                        if test_mode:
                            st.info("🔬 Modo prueba activo: El correo se envió solo a tu cuenta")
                        else:
                            st.balloons()
                    else:
                        st.error(msg)
                        
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")
        st.code(traceback.format_exc())

else:
    st.info("📌 Carga un archivo Excel en la barra lateral para comenzar")
