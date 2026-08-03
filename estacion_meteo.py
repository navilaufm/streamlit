import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as gg
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Configuración del ícono oficial de Meteo Tech
APP_ICON = "https://meteo.tech/favicon.ico"

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Estación Meteorológica - Meteo Tech",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección del favicon oficial en el <head> del documento principal (soporte para Navegador & PWA)
components.html("""
<script>
    try {
        const topDoc = (window.top || window.parent || window).document;
        
        // Favicon estándar
        let link = topDoc.querySelector("link[rel*='icon']") || topDoc.createElement('link');
        link.type = 'image/x-icon';
        link.rel = 'shortcut icon';
        link.href = 'https://meteo.tech/favicon.ico';
        topDoc.getElementsByTagName('head')[0].appendChild(link);
        
        // Icono PWA para iOS / Android
        let appleLink = topDoc.querySelector("link[rel*='apple-touch-icon']") || topDoc.createElement('link');
        appleLink.rel = 'apple-touch-icon';
        appleLink.href = 'https://meteo.tech/favicon.ico';
        topDoc.getElementsByTagName('head')[0].appendChild(appleLink);
    } catch(e) {}
</script>
""", height=0, width=0)

# Estilos CSS personalizados para estética premium, eliminación del espacio superior y tema oscuro unificado
st.markdown("""
<style>
    /* 1. Eliminación del espacio superior muerto (Header Padding) */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 2rem !important;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 98% !important;
    }
    
    /* 2. Tema Oscuro Unificado (Contenedor Principal y Sidebar) */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] {
        background-color: #14171f !important;
        border-right: 1px solid #2e3440 !important;
    }
    
    /* 3. Tarjetas de Métricas KPI */
    .metric-card {
        background: linear-gradient(135deg, #1e222d 0%, #14171f 100%);
        border: 1px solid #2e3440;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 12px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #00e5ff;
    }
    .metric-title {
        color: #8f9ba8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-subtitle {
        color: #00e5ff;
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 4px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: rgba(0, 230, 118, 0.15);
        color: #00e676;
        border: 1px solid #00e676;
    }
    .status-badge-offline {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: rgba(255, 51, 102, 0.15);
        color: #ff3366;
        border: 1px solid #ff3366;
    }
    .forecast-card {
        background: linear-gradient(135deg, #1a1e29 0%, #11141c 100%);
        border: 1px solid #2e3440;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        margin-bottom: 10px;
    }
    .forecast-card:hover {
        border-color: #ffab00;
    }
    .forecast-day {
        color: #00e5ff;
        font-weight: 700;
        font-size: 0.95rem;
        text-transform: uppercase;
    }
    .forecast-temp {
        color: #ffffff;
        font-size: 1.2rem;
        font-weight: 700;
        margin: 6px 0;
    }
    .forecast-detail {
        color: #8f9ba8;
        font-size: 0.78rem;
    }
    .header-box {
        background: linear-gradient(90deg, #1a1e29 0%, #11141c 100%);
        padding: 20px 24px;
        border-radius: 14px;
        border-left: 5px solid #00e5ff;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE SESIÓN PERMANENTE VÍA COOKIES Y LOCALSTORAGE ---
phone_from_query = st.query_params.get("phone", "")
phone_from_cookie = st.context.cookies.get("meteo_user_phone", "") if hasattr(st, "context") and hasattr(st.context, "cookies") else ""

if phone_from_query:
    st.session_state["user_phone"] = phone_from_query
elif phone_from_cookie and not st.session_state.get("user_phone"):
    st.session_state["user_phone"] = phone_from_cookie

clean_phone = "".join(filter(str.isdigit, str(st.session_state.get("user_phone", ""))))

# PUENTE CLIENTE: Sincronizar Cookie + localStorage en el documento principal y auto-navegar si no hay URL param
js_sync_bridge = f"""
<a id="autoNav" href="#" target="_top" style="display:none;"></a>
<script>
    (function() {{
        try {{
            const topWin = window.top || window.parent || window;
            const topDoc = topWin.document;
            const topUrl = new URL(topWin.location.href);
            let urlPhone = topUrl.searchParams.get('phone');
            let urlStation = topUrl.searchParams.get('station_id') || topUrl.searchParams.get('station');
            let localPhone = topWin.localStorage.getItem('meteo_user_phone');
            let localStation = topWin.localStorage.getItem('meteo_station_id');
            let activePhone = '{clean_phone}';

            if (activePhone && activePhone.length > 0) {{
                topDoc.cookie = "meteo_user_phone=" + activePhone + "; path=/; max-age=31536000; SameSite=Lax";
                topWin.localStorage.setItem('meteo_user_phone', activePhone);
            }} else if (localPhone && localPhone.trim() !== '') {{
                topDoc.cookie = "meteo_user_phone=" + localPhone.trim() + "; path=/; max-age=31536000; SameSite=Lax";
                if (localStation && localStation.trim() !== '') {{
                    topDoc.cookie = "meteo_station_id=" + localStation.trim() + "; path=/; max-age=31536000; SameSite=Lax";
                }}
                if (!urlPhone || urlPhone.trim() === '') {{
                    topUrl.searchParams.set('phone', localPhone.trim());
                    if (localStation && localStation.trim() !== '' && !urlStation) {{
                        topUrl.searchParams.set('station_id', localStation.trim());
                    }}
                    const nav = document.getElementById('autoNav');
                    nav.href = topUrl.toString();
                    nav.click();
                }}
            }}
        }} catch(e) {{
            console.error("Session sync error:", e);
        }}
    }})();
</script>
"""
components.html(js_sync_bridge, height=0, width=0)

# Headers estándar para llamadas HTTP
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Función para convertir grados a dirección cardinal
def get_cardinal_direction(degree):
    if pd.isna(degree) or degree is None:
        return "N/A"
    try:
        deg = float(degree)
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = int((deg + 11.25) / 22.5) % 16
        return directions[idx]
    except (ValueError, TypeError):
        return "N/A"

# Función auxiliar para obtener la lectura más reciente válida de cualquier columna en el DataFrame
def get_latest_valid_val(df, col_name, fallback=np.nan):
    if df is not None and not df.empty and col_name in df.columns:
        valid_series = df[col_name].dropna()
        if not valid_series.empty:
            return valid_series.iloc[-1]
    return fallback

# --- FUNCIONES DE CONSULTA A APIS DE METEO.TECH ---

def fetch_stations_by_phone(phone):
    """Consulta las estaciones registradas a un número de teléfono (Sin cache para respuesta instantánea)"""
    if not phone:
        return []
    clean_p = "".join(filter(str.isdigit, str(phone)))
    if not clean_p:
        return []
    url = f"https://mm.meteo.tech/mt-core/v1/stations_by_phone?phone={clean_p}"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            if isinstance(res_json, list):
                return res_json
        return []
    except Exception:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def fetch_latest_station_readings(station_id):
    """Obtiene los valores actuales más recientes de las variables de la estación usando /v1/last"""
    url = f"https://mm.meteo.tech/mt-core/v1/last?station_id={station_id}&round=1"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if response.status_code == 200:
            geojson = response.json()
            features = geojson.get("features", [])
            latest_dict = {}
            latest_date_dt = None
            for feat in features:
                props = feat.get("properties", {})
                var_name = props.get("variable_name")
                val = props.get("data_value")
                dt_str = props.get("data_date")
                if var_name and val is not None:
                    try:
                        latest_dict[var_name] = float(val)
                    except (ValueError, TypeError):
                        latest_dict[var_name] = val
                if dt_str:
                    try:
                        dt = pd.to_datetime(dt_str)
                        if latest_date_dt is None or dt > latest_date_dt:
                            latest_date_dt = dt
                    except Exception:
                        pass
            return latest_dict, latest_date_dt
    except Exception:
        pass
    return {}, None

@st.cache_data(ttl=180, show_spinner=False)
def fetch_station_data(station_id, f1=None, f2=None):
    """Consulta la telemetría histórica de la estación"""
    base_url = "https://gc.meteo.tech/_api.php"
    params = {
        "op": "history",
        "station_id": station_id,
        "variable_id": "0"
    }
    
    if f1 and f2:
        params["f1"] = f1
        params["f2"] = f2

    try:
        response = requests.get(base_url, params=params, headers=DEFAULT_HEADERS, timeout=12)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        st.error(f"Error al conectar con el servidor meteorológico: {e}")
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_station_details(station_id):
    """Obtiene metadatos y coordenadas de la estación"""
    url = f"https://mm.meteo.tech/mt-core/v1/station?id={station_id}"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                meta = data[0]
                return meta.get("latitude"), meta.get("longitude"), meta
    except Exception:
        pass
    return None, None, {}

@st.cache_data(ttl=600, show_spinner=False)
def fetch_forecast_data(lat, lon):
    """Obtiene el pronóstico de 7 días para las coordenadas dadas"""
    if lat is None or lon is None:
        return {}
    url = f"https://mm.meteo.tech/mt-core/v1/forecast?lat={lat}&lon={lon}&d=7"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=12)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

# Función para procesar JSON a DataFrame estandarizado
def process_data(raw_data):
    if not raw_data or not isinstance(raw_data, list):
        return pd.DataFrame(), "Desconocida"

    df_raw = pd.DataFrame(raw_data)
    station_name = df_raw["station_name"].iloc[0] if "station_name" in df_raw.columns and not df_raw.empty else "Estación Meteo"

    df_raw["num_value"] = pd.to_numeric(df_raw["num_value"], errors="coerce")
    
    # Manejo de fechas
    if "data_date_local" in df_raw.columns:
        df_raw["fecha"] = pd.to_datetime(df_raw["data_date_local"])
    else:
        df_raw["fecha"] = pd.to_datetime(df_raw["data_date"])

    # Pivotear variables a columnas y rellenar hacia adelante (ffill)
    df = df_raw.pivot_table(
        index="fecha",
        columns="variable_name",
        values="num_value",
        aggfunc="first"
    ).sort_index().ffill()

    # Mapeo de nombres de variables
    var_map = {
        "TMP": "Temperatura (°C)",
        "HRP": "Humedad (%)",
        "PRS": "Presión (hPa)",
        "WNS": "Velocidad Viento (Km/h)",
        "WNG": "Ráfaga Viento (Km/h)",
        "WND": "Dirección Viento (°)",
        "PCP": "Lluvia (mm/h)",
        "PCA": "Lluvia Acumulada (mm)",
        "RSOL": "Radiación Solar (W/m²)",
        "UV": "Índice UV",
        "LPI": "Humedad Foliar (LPI)"
    }

    df = df.rename(columns=var_map)
    return df, station_name

# --- 1. SI NO HAY TELÉFONO -> PANTALLA DE INICIO DE SESIÓN ---
if not clean_phone:
    st.sidebar.image("https://meteo.tech/demos/saas-2/images/logo.png", use_container_width=True)
    st.sidebar.title("🔐 Autenticación")
    st.sidebar.info("Ingresa tu número de teléfono para cargar tus estaciones meteorológicas.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e222d 0%, #14171f 100%); padding: 32px; border-radius: 16px; border: 1px solid #2e3440; box-shadow: 0 8px 32px rgba(0,0,0,0.5); text-align: center;">
            <img src="https://meteo.tech/demos/saas-2/images/logo.png" style="max-width: 200px; margin-bottom: 20px;">
            <h2 style="color: #ffffff; margin-bottom: 8px;">Bienvenido a Meteo Tech</h2>
            <p style="color: #8f9ba8; font-size: 0.95rem; margin-bottom: 24px;">Ingresa tu número de teléfono registrado para acceder a tus estaciones en tiempo real y pronósticos.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            phone_input = st.text_input("📱 Número de Teléfono", placeholder="Ej: 50255261060")
            submit_btn = st.form_submit_button("🔑 Ingresar a mis Estaciones", use_container_width=True)
            
            if submit_btn:
                input_clean = "".join(filter(str.isdigit, str(phone_input)))
                if input_clean:
                    st.session_state["user_phone"] = input_clean
                    st.query_params["phone"] = input_clean
                    st.rerun()
                else:
                    st.error("Por favor ingresa un número de teléfono válido.")
    st.stop()

# --- 2. CONSULTAR ESTACIONES ASOCIADAS AL TELÉFONO ---
user_stations = fetch_stations_by_phone(clean_phone)

# --- 3. SI EL TELÉFONO NO TIENE ESTACIONES -> INVITACIÓN A REGISTRARSE EN METEO.TECH ---
if not user_stations:
    st.sidebar.image("https://meteo.tech/demos/saas-2/images/logo.png", use_container_width=True)
    st.sidebar.title("🎛️ Configuración")
    st.sidebar.warning(f"⚠️ Sin estaciones asociadas a +{clean_phone}")
    
    js_clear_snippet = """
    <a id="clearNav" href="/" target="_top" style="display:none;"></a>
    <script>
        try {
            const topWin = window.top || window.parent || window;
            const topDoc = topWin.document;
            topWin.localStorage.removeItem('meteo_user_phone');
            topWin.localStorage.removeItem('meteo_station_id');
            topDoc.cookie = "meteo_user_phone=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
            topDoc.cookie = "meteo_station_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        } catch(e){}
    </script>
    """
    
    if st.sidebar.button("🔄 Cambiar Número de Teléfono", use_container_width=True):
        st.session_state["user_phone"] = ""
        if "phone" in st.query_params:
            del st.query_params["phone"]
        if "station_id" in st.query_params:
            del st.query_params["station_id"]
        components.html(js_clear_snippet, height=0, width=0)
        st.rerun()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e222d 0%, #14171f 100%); padding: 32px; border-radius: 16px; border-left: 6px solid #00e5ff; border: 1px solid #2e3440; box-shadow: 0 8px 32px rgba(0,0,0,0.5); text-align: center;">
            <div style="font-size: 3.5rem; margin-bottom: 12px;">📡</div>
            <h3 style="color: #ffffff; margin-bottom: 10px;">No encontramos estaciones vinculadas</h3>
            <p style="color: #8f9ba8; font-size: 0.95rem; margin-bottom: 24px;">
                El número <b>+{clean_phone}</b> no tiene estaciones meteorológicas registradas actualmente en Meteo Tech.
            </p>
            <a href="https://meteo.tech" target="_blank" style="display: inline-block; background: #00e5ff; color: #0e1117; font-weight: bold; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-size: 1rem; margin-bottom: 16px;">👉 Registrarme en meteo.tech</a>
            <p style="color: #5b6575; font-size: 0.82rem;">Una vez registrado tu dispositivo, tus estaciones aparecerán automáticamente aquí.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Probar con otro número de teléfono", use_container_width=True):
            st.session_state["user_phone"] = ""
            if "phone" in st.query_params:
                del st.query_params["phone"]
            if "station_id" in st.query_params:
                del st.query_params["station_id"]
            components.html(js_clear_snippet, height=0, width=0)
            st.rerun()
    st.stop()

# --- 4. SI TIENE ESTACIONES -> MOSTRAR DASHBOARD CON SUS ESTACIONES REALES ---
st.sidebar.image("https://meteo.tech/demos/saas-2/images/logo.png", use_container_width=True)
st.sidebar.title("🎛️ Configuración")

st.sidebar.subheader("📱 Mi Cuenta")
st.sidebar.caption(f"Sesión activa: **+{clean_phone}**")

# Construcción de mapas y lista de estaciones disponibles
station_map = {f"{s.get('station_name', 'Estación')} (ID: {s.get('station_id')})": str(s.get('station_id')) for s in user_stations}
station_labels = list(station_map.keys())
station_ids = list(station_map.values())

# Obtener estación activa desde query_params, cookies o localStorage
url_station_id = str(st.query_params.get("station_id") or st.query_params.get("station") or "").strip()
cookie_station_id = st.context.cookies.get("meteo_station_id", "") if hasattr(st, "context") and hasattr(st.context, "cookies") else ""
target_station_id = url_station_id or cookie_station_id

default_idx = 0
if target_station_id and target_station_id in station_ids:
    default_idx = station_ids.index(target_station_id)

selected_label = st.sidebar.selectbox("📍 Selecciona tu Estación", station_labels, index=default_idx)
station_id = station_map[selected_label]

# Mantener sincronizado el parámetro station_id en URL, Cookies y LocalStorage
if st.query_params.get("station_id") != station_id:
    st.query_params["station_id"] = station_id

js_station_persist = f"""
<script>
    try {{
        const topWin = window.top || window.parent || window;
        const topDoc = topWin.document;
        topDoc.cookie = "meteo_station_id={station_id}; path=/; max-age=31536000; SameSite=Lax";
        topWin.localStorage.setItem("meteo_station_id", "{station_id}");
    }} catch(e){{}}
</script>
"""
components.html(js_station_persist, height=0, width=0)

js_logout_snippet = """
<script>
    try {
        const topWin = window.top || window.parent || window;
        const topDoc = topWin.document;
        topWin.localStorage.removeItem('meteo_user_phone');
        topWin.localStorage.removeItem('meteo_station_id');
        topDoc.cookie = "meteo_user_phone=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        topDoc.cookie = "meteo_station_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    } catch(e){}
</script>
"""

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state["user_phone"] = ""
    if "phone" in st.query_params:
        del st.query_params["phone"]
    if "station_id" in st.query_params:
        del st.query_params["station_id"]
    components.html(js_logout_snippet, height=0, width=0)
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📅 Rango de Fechas")
range_option = st.sidebar.selectbox(
    "Seleccionar Periodo",
    ["Últimos 5 Días", "Últimas 24 Horas", "Últimos 3 Días", "Últimos 7 Días", "Personalizado"]
)

now = datetime.now()
f1_str, f2_str = None, None

if range_option == "Últimas 24 Horas":
    f1_dt = now - timedelta(days=1)
    f1_str = f1_dt.strftime("%Y-%m-%d %H:%M:%S")
    f2_str = now.strftime("%Y-%m-%d %H:%M:%S")
elif range_option == "Últimos 3 Días":
    f1_dt = now - timedelta(days=3)
    f1_str = f1_dt.strftime("%Y-%m-%d %H:%M:%S")
    f2_str = now.strftime("%Y-%m-%d %H:%M:%S")
elif range_option == "Últimos 7 Días":
    f1_dt = now - timedelta(days=7)
    f1_str = f1_dt.strftime("%Y-%m-%d %H:%M:%S")
    f2_str = now.strftime("%Y-%m-%d %H:%M:%S")
elif range_option == "Personalizado":
    d_start = st.sidebar.date_input("Fecha Inicio", now - timedelta(days=5))
    d_end = st.sidebar.date_input("Fecha Fin", now)
    f1_str = f"{d_start} 00:00:00"
    f2_str = f"{d_end} 23:59:59"

st.sidebar.divider()
st.sidebar.subheader("🔄 Auto-Refresco")
enable_autorefresh = st.sidebar.checkbox("Activar Actualización Automática", value=True)
refresh_interval = st.sidebar.selectbox("Frecuencia de Actualización", ["15 Minutos", "5 Minutos", "30 Minutos"], index=0)

ref_mins = 15
if refresh_interval == "5 Minutos":
    ref_mins = 5
elif refresh_interval == "30 Minutos":
    ref_mins = 30

st.sidebar.caption(f"Refrescando automáticamente cada {ref_mins} min.")

if st.sidebar.button("🔄 Actualizar Datos Ahora", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- CARGA DE DATOS DE LA ESTACIÓN SELECCIONADA (LECTURA ACTUAL /LAST + HISTÓRICO + PRONÓSTICO) ---
latest_realtime, last_report_dt = fetch_latest_station_readings(station_id)
raw_data = fetch_station_data(station_id, f1=f1_str, f2=f2_str)
df, station_name = process_data(raw_data)

# Carga de coordenadas y pronóstico 7 días
lat, lon, station_meta = fetch_station_details(station_id)
forecast_data = fetch_forecast_data(lat, lon) if lat and lon else {}

# --- APLICACIÓN PRINCIPAL (FRAGMENTADA SI HAY AUTOREFRESH) ---
@st.fragment(run_every=f"{ref_mins}m" if enable_autorefresh else None)
def render_dashboard(data_df, name, station_lat, station_lon, forecast, realtime_last, last_dt):
    is_online = True
    latest_date = last_dt if last_dt is not None else (data_df.index[-1] if not data_df.empty else None)

    if latest_date is None:
        is_online = False
        st.warning("⚠️ No se encontraron registros de telemetría recientes para esta estación.")
    else:
        # Si la última lectura tiene más de 3 horas, consideramos la estación fuera de línea
        if (now - latest_date).total_seconds() > 10800:
            is_online = False

    # --- BANNER SUPERIOR DE LA ESTACIÓN ---
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(f"🌤️ {name}")
        coords_str = f" | 📍 Lat: `{station_lat}`, Lon: `{station_lon}`" if station_lat and station_lon else ""
        last_time_fmt = latest_date.strftime("%I:%M %p").lower() if latest_date is not None else "N/A"
        last_date_str = latest_date.strftime('%Y-%m-%d') if latest_date is not None else ""
        last_read_str = f"🕒 Último reporte: **{last_time_fmt}** ({last_date_str})" if latest_date is not None else "🕒 Telemetría fuera de línea"
        st.caption(f"📍 ID: `{station_id}`{coords_str} | {last_read_str}")
    with col_head2:
        st.markdown("<br>", unsafe_allow_html=True)
        if is_online and latest_date is not None:
            st.markdown(f'<div style="text-align: right;"><span class="status-badge">● SENSOR ONLINE ({latest_date.strftime("%H:%M")})</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align: right;"><span class="status-badge-offline">● SENSOR OFFLINE (Usando Respaldo)</span></div>', unsafe_allow_html=True)

    st.divider()

    # --- METRICAS KPIS PRINCIPALES (PRIORIZA /LAST -> HISTÓRICO -> BACKUP PRONÓSTICO) ---
    currently = forecast.get("currently", {}) if not is_online else {}

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    # 1. Temperatura (TMP)
    if is_online:
        temp_val = realtime_last.get("TMP", get_latest_valid_val(data_df, "Temperatura (°C)", np.nan))
        temp_max = data_df["Temperatura (°C)"].max() if "Temperatura (°C)" in data_df else np.nan
        temp_min = data_df["Temperatura (°C)"].min() if "Temperatura (°C)" in data_df else np.nan
        sub_temp = f"Mín: {temp_min:.1f}° | Máx: {temp_max:.1f}°" if not pd.isna(temp_min) else "Sin histórico"
    else:
        temp_val = currently.get("temperature", currently.get("air_temperature", np.nan))
        sub_temp = "Respaldo Pronóstico"

    temp_display_str = f"{float(temp_val):.1f} °C" if not pd.isna(temp_val) and temp_val is not None else "N/A"

    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌡️ Temperatura</div>
            <div class="metric-value">{temp_display_str}</div>
            <div class="metric-subtitle">{sub_temp}</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Humedad (HRP)
    if is_online:
        hr_val = realtime_last.get("HRP", get_latest_valid_val(data_df, "Humedad (%)", np.nan))
        hr_avg = data_df["Humedad (%)"].mean() if "Humedad (%)" in data_df else np.nan
        sub_hr = f"Promedio: {hr_avg:.0f}%" if not pd.isna(hr_avg) else "Sin histórico"
    else:
        hr_val = currently.get("humidity", currently.get("relative_humidity", np.nan))
        sub_hr = "Respaldo Pronóstico"

    hr_display_str = f"{float(hr_val):.0f} %" if not pd.isna(hr_val) and hr_val is not None else "N/A"

    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💦 Humedad</div>
            <div class="metric-value">{hr_display_str}</div>
            <div class="metric-subtitle">{sub_hr}</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Presión (PRS)
    if is_online:
        prs_val = realtime_last.get("PRS", get_latest_valid_val(data_df, "Presión (hPa)", np.nan))
        prs_min = data_df["Presión (hPa)"].min() if "Presión (hPa)" in data_df else np.nan
        prs_max = data_df["Presión (hPa)"].max() if "Presión (hPa)" in data_df else np.nan
        sub_prs = f"Rango: {prs_min:.0f} - {prs_max:.0f} hPa" if not pd.isna(prs_min) else "Sin histórico"
    else:
        prs_val = currently.get("pressure", currently.get("air_pressure_at_sea_level", np.nan))
        sub_prs = "Respaldo Pronóstico"

    prs_display_str = f"{float(prs_val):.1f} <span style='font-size: 1rem;'>hPa</span>" if not pd.isna(prs_val) and prs_val is not None else "N/A"

    with kpi3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🛩️ Presión</div>
            <div class="metric-value">{prs_display_str}</div>
            <div class="metric-subtitle">{sub_prs}</div>
        </div>
        """, unsafe_allow_html=True)

    # 4. Viento (WNS / WND)
    if is_online:
        wns_val = realtime_last.get("WNS", get_latest_valid_val(data_df, "Velocidad Viento (Km/h)", 0))
        wng_max = data_df["Ráfaga Viento (Km/h)"].max() if "Ráfaga Viento (Km/h)" in data_df else 0
        wnd_deg = realtime_last.get("WND", get_latest_valid_val(data_df, "Dirección Viento (°)", np.nan))
        cardinal = get_cardinal_direction(wnd_deg)
        sub_wind = f"Ráfaga Máx: {wng_max:.0f} Km/h"
    else:
        wns_val = currently.get("windSpeed", currently.get("wind_speed", 0))
        cardinal = currently.get("cy_bearing", "N/A")
        sub_wind = "Respaldo Pronóstico"

    with kpi4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🚩 Viento</div>
            <div class="metric-value">{float(wns_val):.0f} <span style="font-size: 1rem;">Km/h</span> ({cardinal})</div>
            <div class="metric-subtitle">{sub_wind}</div>
        </div>
        """, unsafe_allow_html=True)

    # 5. Radiación & UV (RSOL / UV)
    if is_online:
        rsol_val = realtime_last.get("RSOL", get_latest_valid_val(data_df, "Radiación Solar (W/m²)", 0))
        uv_val = realtime_last.get("UV", get_latest_valid_val(data_df, "Índice UV", 0))
        sub_uv = f"Índice UV: <b>{float(uv_val):.1f}</b>"
    else:
        rsol_val = 0
        uv_val = currently.get("uvIndex", 0)
        sub_uv = f"Índice UV: <b>{float(uv_val):.1f}</b> (Pronóstico)"

    with kpi5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">☀️ Rad. Solar / UV</div>
            <div class="metric-value">{float(rsol_val):.0f} <span style="font-size: 1rem;">W/m²</span></div>
            <div class="metric-subtitle">{sub_uv}</div>
        </div>
        """, unsafe_allow_html=True)

    # 6. Precipitación (PCP)
    if is_online:
        pcp_val = realtime_last.get("PCP", get_latest_valid_val(data_df, "Lluvia (mm/h)", 0))
        pca_max = data_df["Lluvia Acumulada (mm)"].max() if "Lluvia Acumulada (mm)" in data_df else 0
        sub_pcp = f"Acumulado: {pca_max:.1f} mm"
    else:
        pcp_val = 0
        sub_pcp = "Respaldo Pronóstico"

    with kpi6:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌧️ Precipitación</div>
            <div class="metric-value">{float(pcp_val):.1f} <span style="font-size: 1rem;">mm/h</span></div>
            <div class="metric-subtitle">{sub_pcp}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- PESTAÑAS DEL DASHBOARD ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔮 Pronóstico 7 Días",
        "🌡️ Temperatura y Humedad",
        "🚩 Dinámica del Viento",
        "🌧️ Precipitaciones",
        "☀️ Radiación Solar & UV",
        "🛩️ Barómetro (Presión)"
    ])

    # PALETA DE COLORES
    COLOR_TEMP = "#ff3366"     # Rosa Neón / Rojo Térmico
    COLOR_HUM = "#00e5ff"      # Cyan Neón
    COLOR_WIND = "#00e676"     # Verde Esmeralda
    COLOR_GUST = "#ffab00"     # Amber / Naranja
    COLOR_PRESS = "#ab47bc"    # Púrpura Orquídea
    COLOR_RAIN = "#29b6f6"     # Azul Lluvia
    COLOR_SOLAR = "#ffea00"    # Amarillo Solar

    # TAB 1: PRONÓSTICO 7 DÍAS (DEFAULT TAB)
    with tab1:
        st.subheader("🔮 Pronóstico Meteorológico a 7 Días")
        daily_list = forecast.get("daily", {}).get("data", [])

        if daily_list:
            st.markdown("<br>", unsafe_allow_html=True)

            # Tarjetas de Pronóstico Diario
            cols = st.columns(len(daily_list))
            for idx, day_data in enumerate(daily_list):
                day_name = day_data.get("cy_dia", "").upper()
                day_date = day_data.get("cy_simpletime", "")
                t_high = day_data.get("temperatureHigh", np.nan)
                t_low = day_data.get("temperatureLow", np.nan)
                rain_mm = day_data.get("daily_rain_mm", 0)
                rain_intensity = day_data.get("rain_intensity", "sin lluvia")
                wind_spd = day_data.get("windSpeed", 0)
                wind_dir = day_data.get("windBearing_name", "")
                uv_max = day_data.get("uvMax", "N/A")
                etp_val = day_data.get("etp", "N/A")

                with cols[idx]:
                    st.markdown(f"""
                    <div class="forecast-card">
                        <div class="forecast-day">{day_name} {day_date}</div>
                        <div class="forecast-temp">{t_high:.1f}° <span style="font-size:0.8rem; color:#8f9ba8;">/ {t_low:.1f}°C</span></div>
                        <div class="forecast-detail">🌧️ <b>{rain_mm} mm</b><br>({rain_intensity})</div>
                        <hr style="border-color:#2e3440; margin: 8px 0;">
                        <div class="forecast-detail">🚩 {wind_spd} Km/h {wind_dir}</div>
                        <div class="forecast-detail">☀️ UV Max: <b>{uv_max}</b></div>
                        <div class="forecast-detail">🌱 ETP: <b>{etp_val} mm</b></div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Gráficos del Pronóstico
            df_fcst = pd.DataFrame(daily_list)
            df_fcst["fecha_label"] = df_fcst["cy_dia"] + " " + df_fcst["cy_simpletime"]

            fig_fcst = make_subplots(specs=[[{"secondary_y": True}]])
            fig_fcst.add_trace(
                gg.Scatter(x=df_fcst["fecha_label"], y=df_fcst["temperatureHigh"], name="Temp. Máxima (°C)",
                           line=dict(color="#ff3366", width=3)),
                secondary_y=False
            )
            fig_fcst.add_trace(
                gg.Scatter(x=df_fcst["fecha_label"], y=df_fcst["temperatureLow"], name="Temp. Mínima (°C)",
                           line=dict(color="#00e5ff", width=3, dash="dash")),
                secondary_y=False
            )
            fig_fcst.add_trace(
                gg.Bar(x=df_fcst["fecha_label"], y=df_fcst["daily_rain_mm"], name="Lluvia Proyectada (mm)",
                       marker_color="#29b6f6", opacity=0.6),
                secondary_y=True
            )

            fig_fcst.update_layout(
                title="Evolución de Temperaturas y Lluvias Proyectadas (7 Días)",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,24,33,0.8)",
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_fcst.update_yaxes(title_text="Temperatura (°C)", secondary_y=False, gridcolor="#2a3142")
            fig_fcst.update_yaxes(title_text="Lluvia (mm)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_fcst, use_container_width=True)

        else:
            st.warning("⚠️ No hay información de pronóstico disponible para esta ubicación.")

    # TAB 2: TEMPERATURA Y HUMEDAD
    with tab2:
        if not data_df.empty:
            fig_temp = make_subplots(specs=[[{"secondary_y": True}]])
            if "Temperatura (°C)" in data_df:
                fig_temp.add_trace(
                    gg.Scatter(x=data_df.index, y=data_df["Temperatura (°C)"], name="Temperatura (°C)",
                               line=dict(color=COLOR_TEMP, width=3)),
                    secondary_y=False
                )
            if "Humedad (%)" in data_df:
                fig_temp.add_trace(
                    gg.Scatter(x=data_df.index, y=data_df["Humedad (%)"], name="Humedad (%)",
                               line=dict(color=COLOR_HUM, width=2.5, dash="dot")),
                    secondary_y=True
                )
            fig_temp.update_layout(
                title="Evolución de Temperatura y Humedad Relativa",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,24,33,0.8)",
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_temp.update_yaxes(title_text="Temperatura (°C)", secondary_y=False, gridcolor="#2a3142")
            fig_temp.update_yaxes(title_text="Humedad (%)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("Sin datos históricos de telemetría para mostrar en este gráfico.")

    # TAB 3: VIENTO & DIRECCIÓN
    with tab3:
        if not data_df.empty:
            col_w1, col_w2 = st.columns([2, 1])
            with col_w1:
                fig_wind = gg.Figure()
                if "Velocidad Viento (Km/h)" in data_df:
                    fig_wind.add_trace(gg.Scatter(
                        x=data_df.index, y=data_df["Velocidad Viento (Km/h)"], name="Velocidad (Km/h)",
                        line=dict(color=COLOR_WIND, width=2.5), fill="tozeroy", fillcolor="rgba(0,230,118,0.1)"
                    ))
                if "Ráfaga Viento (Km/h)" in data_df:
                    fig_wind.add_trace(gg.Scatter(
                        x=data_df.index, y=data_df["Ráfaga Viento (Km/h)"], name="Ráfaga Máx (Km/h)",
                        line=dict(color=COLOR_GUST, width=2, dash="dash")
                    ))
                fig_wind.update_layout(
                    title="Velocidad y Ráfagas de Viento",
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(20,24,33,0.8)",
                    hovermode="x unified",
                    margin=dict(l=20, r=20, t=50, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig_wind.update_yaxes(title_text="Velocidad (Km/h)", gridcolor="#2a3142")
                st.plotly_chart(fig_wind, use_container_width=True)

            with col_w2:
                if "Dirección Viento (°)" in data_df and "Velocidad Viento (Km/h)" in data_df:
                    clean_wind = data_df.dropna(subset=["Dirección Viento (°)", "Velocidad Viento (Km/h)"])
                    if not clean_wind.empty:
                        fig_polar = px.scatter_polar(
                            clean_wind,
                            r="Velocidad Viento (Km/h)",
                            theta="Dirección Viento (°)",
                            color="Velocidad Viento (Km/h)",
                            color_continuous_scale="Viridis",
                            title="Rosa de Vientos (Dirección e Intensidad)",
                            template="plotly_dark"
                        )
                        fig_polar.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            margin=dict(l=20, r=20, t=50, b=20)
                        )
                        st.plotly_chart(fig_polar, use_container_width=True)
        else:
            st.info("Sin datos históricos de telemetría para mostrar en este gráfico.")

    # TAB 4: PRECIPITACIONES
    with tab4:
        if not data_df.empty:
            fig_rain = make_subplots(specs=[[{"secondary_y": True}]])
            if "Lluvia (mm/h)" in data_df:
                fig_rain.add_trace(
                    gg.Bar(x=data_df.index, y=data_df["Lluvia (mm/h)"], name="Lluvia Instantánea (mm/h)",
                           marker_color=COLOR_RAIN, opacity=0.8),
                    secondary_y=False
                )
            if "Lluvia Acumulada (mm)" in data_df:
                fig_rain.add_trace(
                    gg.Scatter(x=data_df.index, y=data_df["Lluvia Acumulada (mm)"], name="Acumulado (mm)",
                               line=dict(color="#00e5ff", width=3)),
                    secondary_y=True
                )
            fig_rain.update_layout(
                title="Precipitación Instantánea y Acumulada",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,24,33,0.8)",
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_rain.update_yaxes(title_text="Lluvia (mm/h)", secondary_y=False, gridcolor="#2a3142")
            fig_rain.update_yaxes(title_text="Acumulado (mm)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_rain, use_container_width=True)
        else:
            st.info("Sin datos históricos de telemetría para mostrar en este gráfico.")

    # TAB 5: RADIACIÓN & UV
    with tab5:
        if not data_df.empty:
            fig_rad = make_subplots(specs=[[{"secondary_y": True}]])
            if "Radiación Solar (W/m²)" in data_df:
                fig_rad.add_trace(
                    gg.Scatter(x=data_df.index, y=data_df["Radiación Solar (W/m²)"], name="Radiación Solar (W/m²)",
                               line=dict(color=COLOR_SOLAR, width=2), fill="tozeroy", fillcolor="rgba(255,234,0,0.15)"),
                    secondary_y=False
                )
            if "Índice UV" in data_df:
                fig_rad.add_trace(
                    gg.Scatter(x=data_df.index, y=data_df["Índice UV"], name="Índice UV",
                               line=dict(color="#ff9100", width=2.5, dash="dot")),
                    secondary_y=True
                )
            fig_rad.update_layout(
                title="Radiación Solar Global e Índice UV",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,24,33,0.8)",
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_rad.update_yaxes(title_text="Radiación (W/m²)", secondary_y=False, gridcolor="#2a3142")
            fig_rad.update_yaxes(title_text="Índice UV", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_rad, use_container_width=True)
        else:
            st.info("Sin datos históricos de telemetría para mostrar en este gráfico.")

    # TAB 6: PRESIÓN BAROMÉTRICA (ÚLTIMA PESTAÑA)
    with tab6:
        if not data_df.empty and "Presión (hPa)" in data_df:
            fig_prs = gg.Figure()
            fig_prs.add_trace(gg.Scatter(
                x=data_df.index, y=data_df["Presión (hPa)"], name="Presión Atmosférica (hPa)",
                line=dict(color=COLOR_PRESS, width=3),
                fill="tozeroy", fillcolor="rgba(171,71,188,0.12)"
            ))
            prs_min_val = data_df["Presión (hPa)"].min() - 2
            prs_max_val = data_df["Presión (hPa)"].max() + 2
            fig_prs.update_layout(
                title="Tendencia de Presión Atmosférica (Barómetro)",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,24,33,0.8)",
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20)
            )
            fig_prs.update_yaxes(title_text="Presión (hPa)", range=[prs_min_val, prs_max_val], gridcolor="#2a3142")
            st.plotly_chart(fig_prs, use_container_width=True)
        else:
            st.info("Esta estación no cuenta con sensor de Presión Barométrica registrado.")

    st.divider()

    # --- TABLA DE RESUMEN DIARIO & EXPORTAR EN EXPANDER DISCRETO AL FINAL ---
    if not data_df.empty:
        with st.expander("📊 Resumen Estadístico Diario & Exportación de Datos (CSV)", expanded=False):
            col_tb1, col_tb2 = st.columns([3, 1])
            with col_tb1:
                st.write("##### Resumen Estadístico Diario (Telemetría Disponible)")
            with col_tb2:
                csv_data = data_df.to_csv().encode("utf-8")
                st.download_button(
                    label="📥 Descargar Serie Histórica (CSV)",
                    data=csv_data,
                    file_name=f"estacion_meteo_{station_id}_{latest_date.strftime('%Y%m%d')}.csv" if latest_date else f"estacion_meteo_{station_id}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            # Agregar dinámicamente solo columnas existentes en data_df
            agg_dict = {}
            if "Temperatura (°C)" in data_df.columns:
                agg_dict["Temperatura (°C)"] = ["mean", "min", "max"]
            if "Humedad (%)" in data_df.columns:
                agg_dict["Humedad (%)"] = ["mean", "min", "max"]
            if "Presión (hPa)" in data_df.columns:
                agg_dict["Presión (hPa)"] = ["mean", "min", "max"]
            if "Velocidad Viento (Km/h)" in data_df.columns:
                agg_dict["Velocidad Viento (Km/h)"] = ["mean", "max"]
            if "Lluvia (mm/h)" in data_df.columns:
                agg_dict["Lluvia (mm/h)"] = ["sum"]

            if agg_dict:
                df_daily = data_df.resample("D").agg(agg_dict).round(1)
                df_daily.columns = [f"{col[0]} ({col[1].upper()})" for col in df_daily.columns]
                st.dataframe(df_daily, use_container_width=True)

# Renderizar Dashboard con Ground Truth (/last) y Pronóstico
render_dashboard(df, station_name, lat, lon, forecast_data, latest_realtime, last_report_dt)
