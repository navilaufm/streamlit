import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import os
import urllib.request
import io
import rasterio
import rasterio.mask
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# PASO 1. CONFIGURACIÓN DE PÁGINA Y AUTENTICACIÓN GEE CON SERVICE ACCOUNT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Portal Climatológico & DEM de Cuenca",
    page_icon="🌊",
    layout="wide"
)

@st.cache_resource
def init_earth_engine():
    key_file = os.path.join(os.path.dirname(__file__), "ee-cydata-745adb8aa872.json")
    if not os.path.exists(key_file):
        key_file = "ee-cydata-745adb8aa872.json"

    try:
        credentials = ee.ServiceAccountCredentials(
            'service-ee-cydata@ee-cydata.iam.gserviceaccount.com',
            key_file
        )
        ee.Initialize(credentials, project='ee-cydata')
    except Exception:
        try:
            ee.Initialize(project='ee-cydata')
        except Exception:
            ee.Authenticate()
            ee.Initialize(project='ee-cydata')

init_earth_engine()

# -----------------------------------------------------------------------------
# PASO 2. ESTADO DE SESIÓN Y FUNCIONES AUXILIARES GEE
# -----------------------------------------------------------------------------
if "lat" not in st.session_state:
    st.session_state["lat"] = 18.18
if "lon" not in st.session_state:
    st.session_state["lon"] = -71.17
if "nivel_hybas" not in st.session_state:
    st.session_state["nivel_hybas"] = 7
if "frecuencia" not in st.session_state:
    st.session_state["frecuencia"] = "Diaria"


def get_cuenca_by_coords(lat, lon, level=7):
    punto_anzuelo = ee.Geometry.Point([lon, lat])
    dataset_name = f"WWF/HydroSHEDS/v1/Basins/hybas_{level}"
    cuenca_vector = ee.FeatureCollection(dataset_name) \
                      .filterBounds(punto_anzuelo) \
                      .first()
    return cuenca_vector

def get_cuenca_info(cuenca_vector):
    try:
        info = cuenca_vector.getInfo()
        if info and 'properties' in info:
            props = info['properties']
            return {
                'hybas_id': props.get('HYBAS_ID', 'N/A'),
                'sub_area': props.get('SUB_AREA', 0),
                'up_area': props.get('UP_AREA', 0),
                'pfaf_id': props.get('PFAF_ID', 'N/A'),
                'geometry': info.get('geometry', None)
            }
    except Exception:
        pass
    return None

def add_ee_layer(folium_map, ee_image_object, vis_params, name, opacity=1.0):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True,
        opacity=opacity
    ).add_to(folium_map)

# -----------------------------------------------------------------------------
# PASO 3. BARRA LATERAL (SIDEBAR): PARÁMETROS DE ANÁLISIS
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Parámetros de Análisis")

st.sidebar.subheader("🌊 Configuración de Cuenca")
current_level_idx = [5, 6, 7, 8, 10, 12].index(st.session_state["nivel_hybas"]) if st.session_state["nivel_hybas"] in [5, 6, 7, 8, 10, 12] else 2
input_nivel = st.sidebar.selectbox(
    "Nivel HydroSHEDS:",
    options=[5, 6, 7, 8, 10, 12],
    index=current_level_idx,
    help="Nivel de subdivisión hidrográfica de HydroSHEDS (L7 es por defecto)"
)

if input_nivel != st.session_state["nivel_hybas"]:
    st.session_state["nivel_hybas"] = input_nivel
    st.rerun()

nivel_hybas = st.session_state["nivel_hybas"]


st.sidebar.subheader("📍 Coordenadas de Referencia")
input_lat = st.sidebar.number_input("Latitud (°N)", value=float(st.session_state["lat"]), format="%.4f")
input_lon = st.sidebar.number_input("Longitud (°O)", value=float(st.session_state["lon"]), format="%.4f")

if (round(input_lat, 4) != round(st.session_state["lat"], 4)) or (round(input_lon, 4) != round(st.session_state["lon"], 4)):
    st.session_state["lat"] = input_lat
    st.session_state["lon"] = input_lon
    st.rerun()

st.sidebar.subheader("📅 Selección de Rango de Fechas")
default_start = datetime.date(2016, 1, 1)
default_end = datetime.date(2025, 12, 31)

fecha_inicio = st.sidebar.date_input(
    "Fecha de Inicio:",
    value=default_start,
    min_value=datetime.date(1981, 1, 1),
    max_value=datetime.date(2025, 12, 31)
)

fecha_fin = st.sidebar.date_input(
    "Fecha de Fin:",
    value=default_end,
    min_value=datetime.date(1981, 1, 1),
    max_value=datetime.date(2025, 12, 31)
)

if fecha_inicio > fecha_fin:
    st.sidebar.error("Error: La fecha de inicio debe ser anterior a la fecha final.")

st.sidebar.subheader("⏱️ Agregación Temporal")
frec_idx_side = ["Diaria", "Mensual", "Anual"].index(st.session_state["frecuencia"]) if st.session_state["frecuencia"] in ["Diaria", "Mensual", "Anual"] else 0
sel_frec_side = st.sidebar.selectbox(
    "Resolución del Gráfico:",
    options=["Diaria", "Mensual", "Anual"],
    index=frec_idx_side,
    help="Agregación temporal para la serie de tiempo (Diaria, Mensual, Anual)"
)
if sel_frec_side != st.session_state["frecuencia"]:
    st.session_state["frecuencia"] = sel_frec_side
    st.rerun()

frecuencia = st.session_state["frecuencia"]


# Carga de Cuenca y DEM
cuenca_vector = get_cuenca_by_coords(st.session_state["lat"], st.session_state["lon"], level=nivel_hybas)
cuenca_geom = cuenca_vector.geometry()
dem_cuenca = ee.Image("USGS/SRTMGL1_003").clip(cuenca_geom)

str_start = fecha_inicio.strftime('%Y-%m-%d')
str_end = fecha_fin.strftime('%Y-%m-%d')
num_dias = max(1, (fecha_fin - fecha_inicio).days + 1)
num_anos = max(0.01, num_dias / 365.25)

# -----------------------------------------------------------------------------
# PASO 4. EXTRACCIÓN Y PROCESAMIENTO DE DATOS CHIRPS
# -----------------------------------------------------------------------------
def fetch_precipitation_single_chunk(start_str, end_str, lat, lon, level, freq):
    punto = ee.Geometry.Point([lon, lat])
    dataset_name = f"WWF/HydroSHEDS/v1/Basins/hybas_{level}"
    cuenca = ee.FeatureCollection(dataset_name).filterBounds(punto).first()
    geom = cuenca.geometry()

    if freq == "Diaria":
        chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                   .filterDate(start_str, end_str) \
                   .select('precipitation')
    elif freq == "Mensual":
        start_date = ee.Date(start_str)
        end_date = ee.Date(end_str)
        n_months = end_date.difference(start_date, 'month').round()
        def get_monthly_img(n):
            m_start = start_date.advance(n, 'month')
            m_end = m_start.advance(1, 'month')
            m_sum = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                      .filterDate(m_start, m_end) \
                      .select('precipitation') \
                      .sum()
            return m_sum.set({'system:time_start': m_start.millis()})
        months_list = ee.List.sequence(0, n_months.subtract(1))
        chirps = ee.ImageCollection(months_list.map(get_monthly_img))
    else:  # Anual
        start_year = int(start_str[:4])
        end_year = int(end_str[:4])
        years_list = ee.List.sequence(start_year, end_year)
        def get_annual_img(y):
            y_start = ee.Date.fromYMD(y, 1, 1)
            y_end = ee.Date.fromYMD(y, 12, 31)
            y_sum = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                      .filterDate(y_start, y_end) \
                      .select('precipitation') \
                      .sum()
            return y_sum.set({'system:time_start': y_start.millis()})
        chirps = ee.ImageCollection(years_list.map(get_annual_img))

    def calcular_promedio_cuenca(image):
        media = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom,
            scale=5566,
            maxPixels=1e9
        )
        return ee.Feature(None, {
            'timestamp_ms': image.get('system:time_start'),
            'lluvia_mm': media.get('precipitation')
        })

    feat_collection = ee.FeatureCollection(chirps.map(calcular_promedio_cuenca))
    features = feat_collection.getInfo()['features']
    if not features:
        return pd.DataFrame(columns=['fecha', 'lluvia_mm'])

    data = [{
        'timestamp_ms': f['properties']['timestamp_ms'],
        'lluvia_mm': f['properties']['lluvia_mm']
    } for f in features]

    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
    df['lluvia_mm'] = pd.to_numeric(df['lluvia_mm']).fillna(0)
    df = df.drop(columns=['timestamp_ms']).sort_values('fecha').reset_index(drop=True)
    return df

@st.cache_data(show_spinner=False)
def get_precipitation_df(start_str, end_str, lat, lon, level, freq):
    """
    Función robusta de extracción CHIRPS con fragmentación de fechas (Chunking).
    Google Earth Engine limita getInfo() a un máximo de 5000 elementos.
    Si el rango diario supera los 8 años (~2900 días), fragmenta automáticamente
    la consulta en sub-rangos de 8 años y concatena los DataFrames.
    """
    start_dt = pd.to_datetime(start_str)
    end_dt = pd.to_datetime(end_str)
    total_days = (end_dt - start_dt).days

    if freq == "Diaria" and total_days > 2900:
        dfs = []
        curr = start_dt
        while curr <= end_dt:
            chunk_end = min(curr + pd.DateOffset(years=8) - pd.Timedelta(days=1), end_dt)
            s_str = curr.strftime('%Y-%m-%d')
            e_str = chunk_end.strftime('%Y-%m-%d')
            df_sub = fetch_precipitation_single_chunk(s_str, e_str, lat, lon, level, freq)
            if not df_sub.empty:
                dfs.append(df_sub)
            curr = chunk_end + pd.Timedelta(days=1)
        if dfs:
            return pd.concat(dfs, ignore_index=True).drop_duplicates('fecha').sort_values('fecha').reset_index(drop=True)
        else:
            return pd.DataFrame(columns=['fecha', 'lluvia_mm'])
    else:
        return fetch_precipitation_single_chunk(start_str, end_str, lat, lon, level, freq)

# -----------------------------------------------------------------------------
# PASO 4.5. MÓDULO DIDÁCTICO RÁSTER (PROCESAMIENTO DE GEOTIFFS ICON Y MOTOR SAT)
# -----------------------------------------------------------------------------
ICON_FORECAST_URLS = {
    "Día 1 (24h)": "https://data.meteo.tech/icon/a_pcpn_24.tif",
    "Día 2 (48h)": "https://data.meteo.tech/icon/a_pcpn_48.tif",
    "Día 3 (72h)": "https://data.meteo.tech/icon/a_pcpn_72.tif",
    "Día 4 (96h)": "https://data.meteo.tech/icon/a_pcpn_96.tif",
    "Día 5 (120h)": "https://data.meteo.tech/icon/a_pcpn_120.tif",
    "Día 6 (144h)": "https://data.meteo.tech/icon/a_pcpn_144.tif",
}

def apply_radar_rgba(arr, max_val=200.0):
    """
    Convierte una matriz 2D de precipitación en una imagen RGBA estilo Radar Meteorológico usando NumPy puro.
    Paleta: Cyan (0.1mm) -> Azul -> Verde -> Amarillo -> Naranja -> Rojo -> Magenta (200+mm).
    """
    vals = np.clip(arr, 0.0, max_val)
    stops = np.array([0.0, 10.0, 30.0, 60.0, 100.0, 140.0, 180.0, 200.0])
    r_stops = np.array([0.0, 0.0,  0.0,  1.0,  1.0,  1.0,  0.8,  1.0])
    g_stops = np.array([0.9, 0.27, 0.9,  1.0,  0.6,  0.0,  0.0,  0.0])
    b_stops = np.array([1.0, 1.0,  0.0,  0.0,  0.0,  0.0,  0.8,  1.0])

    r = np.interp(vals, stops, r_stops)
    g = np.interp(vals, stops, g_stops)
    b = np.interp(vals, stops, b_stops)

    valid_mask = (arr > 0.5) & (arr < 1e30) & ~np.isnan(arr)
    a = np.where(valid_mask, 0.85, 0.0)

    return np.dstack([r, g, b, a])

@st.cache_data(show_spinner=False, ttl=3600)
def process_single_icon_raster(url, lat, lon, cuenca_geojson=None):
    """
    Función Didáctica de Ingesta y Recorte Ráster con Rasterio:
    1. urllib descarga los bytes del archivo GeoTIFF de la web.
    2. rasterio abre los datos directamente en la memoria RAM (MemoryFile).
    3. Extrae la precipitación en la coordenada puntual (lat, lon).
    4. Usa rasterio.mask.mask con la geometría GeoJSON de la cuenca para calcular
       la precipitación PROMEDIO sobre toda la cuenca.
    """
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        content = resp.read()

    with rasterio.MemoryFile(content) as memfile:
        with memfile.open() as src:
            # 1. Valor Puntual en Coordenada
            row, col = src.index(lon, lat)
            arr_full = src.read(1)
            if 0 <= row < arr_full.shape[0] and 0 <= col < arr_full.shape[1]:
                val_puntual = float(arr_full[row, col])
            else:
                val_puntual = 0.0

            # 2. Promedio Espacial en Polígono de la Cuenca
            if cuenca_geojson:
                try:
                    out_img, _ = rasterio.mask.mask(src, [cuenca_geojson], crop=True)
                    arr_cuenca = out_img[0]
                    valid_mask = (arr_cuenca != src.nodata) & (arr_cuenca < 1e30) & ~np.isnan(arr_cuenca) & (arr_cuenca >= 0)
                    valid_vals = arr_cuenca[valid_mask]
                    val_promedio = float(np.mean(valid_vals)) if len(valid_vals) > 0 else val_puntual
                except Exception:
                    val_promedio = val_puntual
            else:
                val_promedio = val_puntual

            bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]

    return {
        "val_promedio_cuenca": max(0.0, val_promedio),
        "val_puntual": max(0.0, val_puntual),
        "bytes": content,
        "bounds": bounds
    }

def get_sat_alert_level(val_mm, p90, p95, p99):
    """
    Motor de Alerta Temprana (SAT) basado en Percentiles Climatológicos Locales:
    - 🟢 Verde: Lluvia < P90 (Normal)
    - 🟡 Amarilla: P90 <= Lluvia < P95 (Precaución)
    - 🟠 Naranja: P95 <= Lluvia < P99 (Advertencia / Riesgo Alto)
    - 🔴 Roja: Lluvia >= P99 (Alerta Máxima / Peligro Extremo)
    """
    if p90 <= 0 or p95 <= 0 or p99 <= 0:
        if val_mm < 25: return "🟢 Verde", "#28a745", "Normal (<25 mm)"
        elif val_mm < 50: return "🟡 Amarilla", "#ffc107", "Precaución (25-50 mm)"
        elif val_mm < 100: return "🟠 Naranja", "#fd7e14", "Riesgo Alto (50-100 mm)"
        else: return "🔴 Roja", "#dc3545", "Peligro Extremo (>=100 mm)"

    if val_mm < p90:
        return "🟢 Verde", "#28a745", f"Normal (< P90: {p90:.1f} mm)"
    elif val_mm < p95:
        return "🟡 Amarilla", "#ffc107", f"Precaución (P90-P95: {p90:.1f}-{p95:.1f} mm)"
    elif val_mm < p99:
        return "🟠 Naranja", "#fd7e14", f"Riesgo Alto (P95-P99: {p95:.1f}-{p99:.1f} mm)"
    else:
        return "🔴 Roja", "#dc3545", f"Peligro Extremo (>= P99: {p99:.1f} mm)"

# -----------------------------------------------------------------------------
# PASO 5. ESTRUCTURA PRINCIPAL EN PESTAÑAS (TABS)
# -----------------------------------------------------------------------------
st.title("🌊 Portal Climatológico & Analizador de Cuencas")

cuenca_info = get_cuenca_info(cuenca_vector)
hybas_str = f"HYBAS_ID: {cuenca_info['hybas_id']}" if cuenca_info else f"Cuenca HydroSHEDS L{nivel_hybas}"
st.markdown(
    f"**Cuenca Activa:** `{hybas_str}` (Nivel {nivel_hybas}) | "
    f"**Coordenada:** ({st.session_state['lat']:.4f}° N, {st.session_state['lon']:.4f}° O) | "
    f"**Rango Histórico:** `{str_start}` a `{str_end}` ({num_anos:.1f} años)"
)

tab0, tab1, tab2, tab3 = st.tabs([
    "📍 Selector de Cuenca",
    "🗺️ Mapa, DEM & Satélite",
    "📈 Serie de Tiempo & Umbrales",
    "🚨 Alerta Temprana (SAT ICON)"
])

# =============================================================================
# PESTAÑA 0: SELECTOR INTERACTIVO DE CUENCA
# =============================================================================
with tab0:
    st.subheader(f"📍 Selección Interactiva de Cuenca por Clic en Mapa (HydroSHEDS Nivel {nivel_hybas})")
    st.info(f"Haz clic en cualquier punto del mapa para interceptar la cuenca HydroSHEDS (Nivel {nivel_hybas}) correspondiente.")

    m_select = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=9, tiles="OpenStreetMap")

    cuenca_fc = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m_select, ee.Image().paint(cuenca_fc, 0, 2), {'palette': 'blue'}, f'Cuenca HydroSHEDS L{nivel_hybas}')

    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto seleccionado: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}",
        tooltip="Punto actual de análisis",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m_select)

    folium.LayerControl().add_to(m_select)

    map_data = st_folium(
        m_select,
        width=950,
        height=500,
        key=f"select_basin_map_{nivel_hybas}_{st.session_state['lat']:.4f}_{st.session_state['lon']:.4f}",
        returned_objects=["last_clicked"]
    )

    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]

        if (round(clicked_lat, 4) != round(st.session_state["lat"], 4)) or (round(clicked_lon, 4) != round(st.session_state["lon"], 4)):
            st.session_state["lat"] = clicked_lat
            st.session_state["lon"] = clicked_lon
            st.rerun()

    if cuenca_info:
        st.success(f"✅ **Cuenca Seleccionada Activa (`HYBAS_ID: {cuenca_info['hybas_id']}`)**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Latitud", f"{st.session_state['lat']:.4f}° N")
        c2.metric("Longitud", f"{st.session_state['lon']:.4f}° O")
        c3.metric("Sub-área Cuenca", f"{cuenca_info['sub_area']:.1f} km²")
        c4.metric("Área Cuenca Aguas Arriba", f"{cuenca_info['up_area']:.1f} km²")

# =============================================================================
# PESTAÑA 1: MAPA Y DEM
# =============================================================================
with tab1:
    st.subheader("🗺️ Modelo Digital de Elevación (DEM) y Precipitación Promedio Anual")

    ctrl_col1, ctrl_col2 = st.columns(2)
    with ctrl_col1:
        opacity_dem = st.slider("🎛️ Opacidad Capa DEM (SRTM)", 0.0, 1.0, 0.70, 0.05, key="op_dem")
    with ctrl_col2:
        opacity_precip = st.slider("🎛️ Opacidad Precipitación Promedio Anual", 0.0, 1.0, 0.65, 0.05, key="op_precip")

    m = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=10, tiles="OpenStreetMap")

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Esri Satélite',
        overlay=False
    ).add_to(m)

    dem_vis = {'min': 0, 'max': 2500, 'palette': ['006600', '002200', 'fff700', 'ab0000', 'b8b8b8', 'ffffff']}
    add_ee_layer(m, dem_cuenca, dem_vis, 'DEM de la Cuenca (SRTM 30m)', opacity=opacity_dem)

    chirps_sum = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                   .filterDate(str_start, str_end) \
                   .select('precipitation') \
                   .sum() \
                   .clip(cuenca_geom)

    chirps_promedio_anual = chirps_sum.divide(num_anos)

    precip_vis = {
        'min': 300,
        'max': 3000,
        'palette': ['#ffffcc', '#a1dab4', '#41b6c4', '#2c7fb8', '#253494', '#081d58']
    }
    add_ee_layer(
        m,
        chirps_promedio_anual,
        precip_vis,
        f'Precipitación Promedio Anual (mm/año: {str_start[:4]}-{str_end[:4]})',
        opacity=opacity_precip
    )

    cuenca_fc = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m, ee.Image().paint(cuenca_fc, 0, 3), {'palette': 'black'}, f'Límite Cuenca HydroSHEDS L{nivel_hybas}')

    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)

    legend_map_html = """
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 230px;
        background-color: rgba(255, 255, 255, 0.92);
        border: 1px solid #ccc; z-index:9999; font-size:11px;
        padding: 10px; border-radius: 8px; font-family: sans-serif;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        <div style="margin-bottom: 8px;">
            <span style="font-weight:bold; color: #212529;">🌧️ Precipitación (mm/año)</span>
            <div style="background: linear-gradient(to right, #ffffcc, #a1dab4, #41b6c4, #2c7fb8, #253494, #081d58); height: 10px; border-radius: 3px; margin-top: 3px;"></div>
            <div style="display: flex; justify-content: space-between; font-size: 9px; color: #555; margin-top: 2px;">
                <span>300 mm</span>
                <span>1650 mm</span>
                <span>3000+ mm</span>
            </div>
        </div>
        <div style="border-top: 1px solid #ddd; padding-top: 6px;">
            <span style="font-weight:bold; color: #212529;">🏔️ Elevación DEM (m)</span>
            <div style="background: linear-gradient(to right, #006600, #002200, #fff700, #ab0000, #b8b8b8, #ffffff); height: 10px; border-radius: 3px; margin-top: 3px;"></div>
            <div style="display: flex; justify-content: space-between; font-size: 9px; color: #555; margin-top: 2px;">
                <span>0 m</span>
                <span>1250 m</span>
                <span>2500+ m</span>
            </div>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_map_html))
    folium.LayerControl().add_to(m)

    st_folium(
        m,
        width=950,
        height=580,
        key=f"analysis_map_{nivel_hybas}_{st.session_state['lat']:.4f}_{st.session_state['lon']:.4f}",
        returned_objects=[]
    )

# =============================================================================
# PESTAÑA 2: SERIE DE TIEMPO Y CÁLCULO DE UMBRALES
# =============================================================================
with tab2:
    st.subheader("📈 Análisis Estadístico de Precipitación y Umbrales")

    frecuencia = st.session_state["frecuencia"]

    with st.spinner("Procesando serie temporal desde Google Earth Engine..."):
        df_daily = get_precipitation_df(
            str_start, str_end, st.session_state["lat"], st.session_state["lon"], nivel_hybas, "Diaria"
        )
        if frecuencia == "Diaria":
            df_precip = df_daily
        else:
            df_precip = get_precipitation_df(
                str_start, str_end, st.session_state["lat"], st.session_state["lon"], nivel_hybas, frecuencia
            )

    if df_daily.empty or df_precip.empty:
        st.warning("No se encontraron registros de precipitación para el rango de fechas seleccionado.")
    else:
        precip_dias_lluvia = df_daily[df_daily['lluvia_mm'] > 0.1]['lluvia_mm']
        if precip_dias_lluvia.empty or len(precip_dias_lluvia) < 3:
            precip_dias_lluvia = df_daily[df_daily['lluvia_mm'] > 0]['lluvia_mm']

        if not precip_dias_lluvia.empty:
            p90 = float(precip_dias_lluvia.quantile(0.90))
            p95 = float(precip_dias_lluvia.quantile(0.95))
            p99 = float(precip_dias_lluvia.quantile(0.99))
        else:
            p90, p95, p99 = 0.0, 0.0, 0.0

        total_precip = df_daily['lluvia_mm'].sum()
        promedio_anual = total_precip / num_anos

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Precipitación Total", f"{total_precip:.1f} mm")
        col2.metric("Promedio Anual", f"{promedio_anual:.1f} mm/año")
        col3.metric("P90 Diario (>2mm)", f"{p90:.1f} mm/día")
        col4.metric("P95 Diario (>2mm)", f"{p95:.1f} mm/día")
        col5.metric("P99 Diario Crítico", f"{p99:.1f} mm/día")

        st.divider()

        st.download_button(
            label=f"📥 Descargar Serie Temporal {frecuencia} (CSV)",
            data=df_precip.to_csv(index=False).encode('utf-8'),
            file_name=f"precipitacion_{frecuencia.lower()}_hybas_{cuenca_info['hybas_id'] if cuenca_info else 'cuenca'}.csv",
            mime="text/csv"
        )

        df_precip['acumulada_mm'] = df_precip['lluvia_mm'].cumsum()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=df_precip['fecha'],
                y=df_precip['lluvia_mm'],
                mode='lines',
                name=f'Precipitación {frecuencia} (mm)',
                line=dict(color='#1f77b4', width=1.5)
            ),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=df_precip['fecha'],
                y=df_precip['acumulada_mm'],
                mode='lines',
                name='Precipitación Acumulada (mm)',
                line=dict(color='#2ca02c', width=1.5, dash='dot')
            ),
            secondary_y=True
        )

        if frecuencia == "Diaria" and p90 > 0:
            fig.add_hline(y=p90, line_dash="dash", line_color="orange", annotation_text=f"P90 Diario: {p90:.1f} mm")
            fig.add_hline(y=p95, line_dash="dash", line_color="red", annotation_text=f"P95 Diario: {p95:.1f} mm")
            fig.add_hline(y=p99, line_dash="dash", line_color="darkred", annotation_text=f"P99 Diario: {p99:.1f} mm")

        fig.update_layout(
            title=f"Serie Temporal ({frecuencia}) y Lluvia Acumulada ({str_start} a {str_end}) - HYBAS_ID: {cuenca_info['hybas_id'] if cuenca_info else 'N/A'}",
            xaxis_title="Fecha",
            template="plotly_white",
            height=480,
            hovermode="x unified"
        )
        fig.update_yaxes(title_text=f"Precipitación {frecuencia} (mm)", secondary_y=False)
        fig.update_yaxes(title_text="Acumulada Total (mm)", secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"### 🔥 Top 10 Períodos ({frecuencia}) con Mayor Precipitación")
        top10 = df_precip.sort_values('lluvia_mm', ascending=False).head(10).reset_index(drop=True)
        top10['fecha'] = top10['fecha'].dt.strftime('%Y-%m-%d')
        st.dataframe(top10, use_container_width=True)

        st.markdown("### ⚠️ Conteo de Días que Superan los Umbrales Diarios Críticos")
        n_p90 = (df_daily['lluvia_mm'] > p90).sum() if p90 > 0 else 0
        n_p95 = (df_daily['lluvia_mm'] > p95).sum() if p95 > 0 else 0
        n_p99 = (df_daily['lluvia_mm'] > p99).sum() if p99 > 0 else 0

        col_a, col_b, col_c = st.columns(3)
        col_a.info(f"**Días > P90 ({p90:.1f} mm/día):** {n_p90} días")
        col_b.warning(f"**Días > P95 ({p95:.1f} mm/día):** {n_p95} días")
        col_c.error(f"**Días > P99 ({p99:.1f} mm/día):** {n_p99} días")

# =============================================================================
# PESTAÑA 3: SISTEMA DE ALERTA TEMPRANA (SAT OPERATIVO ICON)
# =============================================================================
with tab3:
    st.subheader("🚨 Sistema de Alerta Temprana (SAT) - Pronóstico 1 a 6 Días (Modelo ICON)")

    with st.expander("📚 Explicación Didáctica para Estudiantes: ¿Cómo funciona este SAT?", expanded=False):
        st.markdown(r"""
        **Metodología Integrada del SAT Operativo**:
        1. **Climatología Base de la Cuenca (CHIRPS)**: Se obtienen los percentiles históricos de lluvia diaria ($P_{90}$, $P_{95}$, $P_{99}$) promediados en la cuenca activa desde Google Earth Engine.
        2. **Ingesta de Pronóstico Ráster (Modelo ICON)**: Se cargan dinámicamente los GeoTIFFs de pronóstico de precipitación de 24h para los próximos 6 días (`a_pcpn_24.tif` a `a_pcpn_144.tif`).
        3. **Recorte Espacial con `rasterio`**: Cada GeoTIFF se recorta usando la geometría GeoJSON de la cuenca HydroSHEDS para calcular la **lluvia promedio pronosticada en la cuenca**.
        4. **Lectura Puntual**: En paralelo, se lee el valor del píxel en la coordenada exacta ($lat, lon$) seleccionada por el usuario.
        5. **Evaluación de Alerta SAT**:
           - 🟢 **Verde (Normal)**: Lluvia promedio de cuenca $< P_{90}$
           - 🟡 **Amarilla (Precaución)**: $P_{90} \le \text{Lluvia} < P_{95}$
           - 🟠 **Naranja (Advertencia / Riesgo Alto)**: $P_{95} \le \text{Lluvia} < P_{99}$
           - 🔴 **Roja (Peligro Extremo)**: $\text{Lluvia} \ge P_{99}$
        """)

    # 1. Obtener percentiles históricos de la cuenca activa con base climatológica dinámica
    st.markdown("### 📊 Umbrales Climatológicos Dinámicos de la Cuenca")
    
    col_ctx1, _ = st.columns([3, 1])
    with col_ctx1:
        modo_umbrales = st.radio(
            "🎯 Selecciona la Base Climatológica para los Percentiles del SAT:",
            options=[
                "📅 Fechas Seleccionadas en Sidebar (Filtro Estacional Activo)",
                "🗓️ Mismo Mes Histórico (Climatología del Mes del Pronóstico)",
                "📊 Serie Histórica Completa (1981–2025)"
            ],
            horizontal=True,
            key="modo_percentiles_sat",
            help="Prueba cambiando entre opciones para mostrar a tus alumnos cómo varía el semáforo de alerta (Verde, Amarilla, Naranja, Roja) según la temporada de lluvias o el mes del año."
        )

    with st.spinner("Calculando percentiles climatológicos adaptativos de la cuenca..."):
        if "Mismo Mes Histórico" in modo_umbrales:
            df_full = get_precipitation_df("1981-01-01", "2025-12-31", st.session_state["lat"], st.session_state["lon"], nivel_hybas, "Diaria")
            mes_actual = datetime.datetime.now().month
            df_hist_sat = df_full[df_full['fecha'].dt.month == mes_actual] if not df_full.empty else df_full
        elif "Serie Histórica Completa" in modo_umbrales:
            df_hist_sat = get_precipitation_df("1981-01-01", "2025-12-31", st.session_state["lat"], st.session_state["lon"], nivel_hybas, "Diaria")
        else:
            df_hist_sat = get_precipitation_df(str_start, str_end, st.session_state["lat"], st.session_state["lon"], nivel_hybas, "Diaria")

        if not df_hist_sat.empty:
            # Filtrar días con precipitación apreciable (> 0.1 mm) para no distorsionar en épocas secas
            rain_days = df_hist_sat[df_hist_sat['lluvia_mm'] > 0.1]['lluvia_mm']
            if rain_days.empty or len(rain_days) < 3:
                rain_days = df_hist_sat[df_hist_sat['lluvia_mm'] > 0]['lluvia_mm']

            if not rain_days.empty:
                p90_sat = float(rain_days.quantile(0.90))
                p95_sat = float(rain_days.quantile(0.95))
                p99_sat = float(rain_days.quantile(0.99))
            else:
                p90_sat, p95_sat, p99_sat = 2.0, 5.0, 10.0
        else:
            p90_sat, p95_sat, p99_sat = 25.0, 50.0, 100.0

    m1, m2, m3 = st.columns(3)
    m1.metric("P90 Cuenca (Umbral Amarilla)", f"{p90_sat:.1f} mm/día")
    m2.metric("P95 Cuenca (Umbral Naranja)", f"{p95_sat:.1f} mm/día")
    m3.metric("P99 Cuenca (Umbral Roja)", f"{p99_sat:.1f} mm/día")

    st.divider()

    # 2. Descarga y procesamiento de los 6 rásteres de pronóstico ICON
    cuenca_geojson_sat = cuenca_info['geometry'] if cuenca_info else None
    
    sat_results = []
    with st.spinner("Descargando y procesando los GeoTIFFs de pronóstico de lluvia del modelo ICON (24h a 144h)..."):
        for nombre_dia, url_tif in ICON_FORECAST_URLS.items():
            res_raster = process_single_icon_raster(url_tif, st.session_state["lat"], st.session_state["lon"], cuenca_geojson_sat)
            prom_cuenca = res_raster["val_promedio_cuenca"]
            val_puntual = res_raster["val_puntual"]
            
            tag_alerta, color_hex, desc_alerta = get_sat_alert_level(prom_cuenca, p90_sat, p95_sat, p99_sat)
            
            sat_results.append({
                "Nombre": nombre_dia,
                "Lluvia_Cuenca_mm": prom_cuenca,
                "Lluvia_Puntual_mm": val_puntual,
                "Alerta": tag_alerta,
                "Color": color_hex,
                "Descripcion": desc_alerta,
                "Bytes": res_raster["bytes"],
                "Bounds": res_raster["bounds"]
            })

    df_sat = pd.DataFrame(sat_results)

    # 3. Mostrar Tarjetas KPI por Día (Día 1 a Día 6)
    st.markdown("### 🚨 Estado de Alerta por Día de Pronóstico (24h a 144h)")
    cols_sat = st.columns(6)
    for idx, row_sat in enumerate(sat_results):
        with cols_sat[idx]:
            st.markdown(f"**{row_sat['Nombre']}**")
            st.markdown(
                f"""
                <div style="
                    background-color: {row_sat['Color']}; 
                    color: white; 
                    padding: 8px; 
                    border-radius: 6px; 
                    text-align: center;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 8px;
                ">
                    {row_sat['Alerta']}
                </div>
                """, 
                unsafe_allow_html=True
            )
            st.caption(f"🌧️ Cuenca: **{row_sat['Lluvia_Cuenca_mm']:.1f} mm**")
            st.caption(f"📍 Punto: **{row_sat['Lluvia_Puntual_mm']:.1f} mm**")

    st.divider()

    # 4. Hietograma Interactivo de Pronóstico SAT
    st.markdown("### 📈 Hietograma de Pronóstico SAT vs. Umbrales de Cuenca")
    
    df_sat['Acumulada_Cuenca'] = df_sat['Lluvia_Cuenca_mm'].cumsum()
    
    fig_sat = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Lluvia promedio en cuenca
    fig_sat.add_trace(
        go.Bar(
            x=df_sat['Nombre'],
            y=df_sat['Lluvia_Cuenca_mm'],
            name='Lluvia Promedio Cuenca (mm/24h)',
            marker_color='#1f77b4',
            opacity=0.85
        ),
        secondary_y=False
    )
    
    # Lluvia puntual de referencia
    fig_sat.add_trace(
        go.Scatter(
            x=df_sat['Nombre'],
            y=df_sat['Lluvia_Puntual_mm'],
            mode='lines+markers',
            name='Lluvia Puntual Coordenada (mm/24h)',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ),
        secondary_y=False
    )
    
    # Acumulada
    fig_sat.add_trace(
        go.Scatter(
            x=df_sat['Nombre'],
            y=df_sat['Acumulada_Cuenca'],
            mode='lines+markers',
            name='Acumulada Cuenca (mm)',
            line=dict(color='#2ca02c', width=2)
        ),
        secondary_y=True
    )
    
    # Umbrales
    if p90_sat > 0:
        fig_sat.add_hline(y=p90_sat, line_dash="dash", line_color="#ffc107", annotation_text=f"P90 Amarilla: {p90_sat:.1f} mm")
        fig_sat.add_hline(y=p95_sat, line_dash="dash", line_color="#fd7e14", annotation_text=f"P95 Naranja: {p95_sat:.1f} mm")
        fig_sat.add_hline(y=p99_sat, line_dash="dash", line_color="#dc3545", annotation_text=f"P99 Roja: {p99_sat:.1f} mm")

    fig_sat.update_layout(
        title=f"Hietograma de Pronóstico a 6 Días (ICON) - HYBAS_ID: {cuenca_info['hybas_id'] if cuenca_info else 'N/A'}",
        xaxis_title="Horizonte de Pronóstico",
        template="plotly_white",
        height=450,
        hovermode="x unified"
    )
    fig_sat.update_yaxes(title_text="Lluvia Diaria 24h (mm)", secondary_y=False)
    fig_sat.update_yaxes(title_text="Lluvia Acumulada (mm)", secondary_y=True)

    st.plotly_chart(fig_sat, use_container_width=True)

    st.divider()

    # 5. Visualizador de Mapa de Lluvia Pronosticada ICON (Folium Overlay)
    st.markdown("### 🗺️ Visualizador Ráster del Pronóstico ICON en el Mapa")
    
    col_sel_map, col_op = st.columns([2, 1])
    with col_sel_map:
        dia_mapa_sel = st.selectbox(
            "🌧️ Selecciona el Día de Pronóstico a Visualizar en el Mapa:",
            options=[row["Nombre"] for row in sat_results],
            index=0
        )
    with col_op:
        opacidad_raster = st.slider("🎛️ Opacidad Capa Ráster ICON", 0.0, 1.0, 0.70, 0.05, key="op_icon_sat")

    idx_mapa = [row["Nombre"] for row in sat_results].index(dia_mapa_sel)
    data_mapa_sel = sat_results[idx_mapa]

    m_sat = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=9, tiles="OpenStreetMap")
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Esri Satélite',
        overlay=False
    ).add_to(m_sat)

    try:
        with rasterio.MemoryFile(data_mapa_sel["Bytes"]) as memfile_sat:
            with memfile_sat.open() as src_sat:
                arr_sat = src_sat.read(1)
                
                # Mapeo directo RGBA con paleta de Radar Meteorológico en NumPy puro
                rgba_sat = apply_radar_rgba(arr_sat, max_val=200.0)
                
                folium.raster_layers.ImageOverlay(
                    image=rgba_sat,
                    bounds=data_mapa_sel["Bounds"],
                    name=f"Pronóstico ICON {dia_mapa_sel}",
                    opacity=opacidad_raster,
                    overlay=True,
                    control=True
                ).add_to(m_sat)
    except Exception as e_sat:
        st.warning(f"No se pudo renderizar la capa ráster visual: {e_sat}")

    cuenca_fc_sat = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m_sat, ee.Image().paint(cuenca_fc_sat, 0, 3), {'palette': 'black'}, f'Límite Cuenca HydroSHEDS L{nivel_hybas}')

    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}<br>Lluvia: {data_mapa_sel['Lluvia_Puntual_mm']:.1f} mm",
        tooltip="Punto Seleccionado",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m_sat)

    # Leyenda visual de Radar Meteorológico (0 a 200+ mm)
    legend_sat_html = """
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 250px;
        background-color: rgba(255, 255, 255, 0.95);
        border: 1px solid #888; z-index:9999; font-size:11px;
        padding: 10px; border-radius: 8px; font-family: sans-serif;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    ">
        <div style="margin-bottom: 4px;">
            <span style="font-weight:bold; color: #111;">📡 Radar Meteorológico (mm/24h)</span>
            <div style="background: linear-gradient(to right, #00e5ff, #0044ff, #00e600, #ffff00, #ff9900, #ff0000, #cc00cc); height: 12px; border-radius: 4px; margin-top: 4px;"></div>
            <div style="display: flex; justify-content: space-between; font-size: 9px; color: #222; margin-top: 3px; font-weight: bold;">
                <span>0</span>
                <span>50</span>
                <span>100</span>
                <span>150</span>
                <span>200+ mm</span>
            </div>
        </div>
    </div>
    """
    m_sat.get_root().html.add_child(folium.Element(legend_sat_html))

    folium.LayerControl().add_to(m_sat)

    st_folium(
        m_sat,
        width=950,
        height=520,
        key=f"sat_forecast_map_{nivel_hybas}_{st.session_state['lat']:.4f}_{st.session_state['lon']:.4f}_{idx_mapa}",
        returned_objects=[]
    )

    # 6. Tabla de datos exportables
    st.markdown("### 📋 Tabla Resumen de Pronóstico SAT")
    df_export_sat = df_sat[["Nombre", "Lluvia_Cuenca_mm", "Lluvia_Puntual_mm", "Alerta", "Descripcion"]].copy()
    df_export_sat.columns = ["Horizonte", "Lluvia Promedio Cuenca (mm)", "Lluvia Puntual Coordenada (mm)", "Nivel Alerta", "Detalle Climatológico"]
    st.dataframe(df_export_sat, use_container_width=True)

    st.download_button(
        label="📥 Descargar Tabla Pronóstico SAT (CSV)",
        data=df_export_sat.to_csv(index=False).encode('utf-8'),
        file_name=f"pronostico_sat_hybas_{cuenca_info['hybas_id'] if cuenca_info else 'cuenca'}.csv",
        mime="text/csv"
    )

# Pie de página y margen de scroll inferior
st.markdown("---")
st.caption("🌊 *Portal Climatológico & Analizador de Cuencas con Google Earth Engine, Folium, Rasterio & Streamlit*")
st.markdown("<div style='height: 160px;'></div>", unsafe_allow_html=True)