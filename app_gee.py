import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.graph_objects as go
import datetime
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y AUTENTICACIÓN GEE CON SERVICE ACCOUNT
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
# 2. ESTADO DE SESIÓN (SESSION STATE) Y BÚSQUEDA DE CUENCA POR COORDENADAS
# -----------------------------------------------------------------------------
if "lat" not in st.session_state:
    st.session_state["lat"] = 18.18
if "lon" not in st.session_state:
    st.session_state["lon"] = -71.17

@st.cache_data
def get_cuenca_by_coords(lat, lon):
    punto_anzuelo = ee.Geometry.Point([lon, lat])
    cuenca_vector = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_12") \
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
                'pfaf_id': props.get('PFAF_ID', 'N/A')
            }
    except Exception:
        pass
    return None

def add_ee_layer(folium_map, ee_image_object, vis_params, name):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True
    ).add_to(folium_map)

cuenca_vector = get_cuenca_by_coords(st.session_state["lat"], st.session_state["lon"])
cuenca_geom = cuenca_vector.geometry()
dem_cuenca = ee.Image("USGS/SRTMGL1_003").clip(cuenca_geom)

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL (SIDEBAR): SELECTOR DE COORDENADAS Y FECHAS
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Parámetros de Análisis")

st.sidebar.subheader("📍 Coordenadas de Referencia")
input_lat = st.sidebar.number_input("Latitud (°N)", value=float(st.session_state["lat"]), format="%.4f")
input_lon = st.sidebar.number_input("Longitud (°O)", value=float(st.session_state["lon"]), format="%.4f")

if (round(input_lat, 4) != round(st.session_state["lat"], 4)) or (round(input_lon, 4) != round(st.session_state["lon"], 4)):
    st.session_state["lat"] = input_lat
    st.session_state["lon"] = input_lon
    st.rerun()

st.sidebar.subheader("📅 Selección de Rango de Fechas")
default_start = datetime.date(2023, 1, 1)
default_end = datetime.date(2023, 12, 31)

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

# -----------------------------------------------------------------------------
# 4. EXTRACCIÓN Y PROCESAMIENTO DE DATOS CHIRPS
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_precipitation_df(start_str, end_str, lat, lon):
    punto = ee.Geometry.Point([lon, lat])
    cuenca = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_12").filterBounds(punto).first()
    geom = cuenca.geometry()

    chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
               .filterDate(start_str, end_str) \
               .select('precipitation')

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

str_start = fecha_inicio.strftime('%Y-%m-%d')
str_end = fecha_fin.strftime('%Y-%m-%d')

# -----------------------------------------------------------------------------
# 5. ESTRUCTURA PRINCIPAL EN PESTAÑAS (TABS)
# -----------------------------------------------------------------------------
st.title("🌊 Dashboards de Análisis Climatológico e Indicadores de Cuenca")

cuenca_info = get_cuenca_info(cuenca_vector)
hybas_str = f"HYBAS_ID: {cuenca_info['hybas_id']}" if cuenca_info else "Cuenca HydroSHEDS L12"
st.markdown(f"**Cuenca Activa:** `{hybas_str}` | **Coordenada:** ({st.session_state['lat']:.4f}° N, {st.session_state['lon']:.4f}° O) | **Rango:** `{str_start}` a `{str_end}`")

tab0, tab1, tab2 = st.tabs(["📍 Selector de Cuenca", "🗺️ Mapa & DEM", "📈 Serie de Tiempo & Umbrales"])

# =============================================================================
# PESTAÑA 0: SELECTOR INTERACTIVO DE CUENCA
# =============================================================================
with tab0:
    st.subheader("📍 Selección Interactiva de Cuenca por Clic en Mapa")
    st.info("Haz clic en cualquier punto del mapa para interceptar la cuenca HydroSHEDS (Nivel 12) correspondiente. La cuenca seleccionada se usará automáticamente en las demás pestañas de análisis.")

    m_select = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=9, tiles="OpenStreetMap")

    # Dibujar la cuenca actual
    cuenca_fc = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m_select, ee.Image().paint(cuenca_fc, 0, 2), {'palette': 'blue'}, 'Cuenca Seleccionada')

    # Marcador en el punto actual
    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto seleccionado: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}",
        tooltip="Punto actual de análisis",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m_select)

    folium.LayerControl().add_to(m_select)

    # Renderizar mapa interactivo escuchando clics
    map_data = st_folium(m_select, width=950, height=500, key="select_basin_map", returned_objects=["last_clicked"])

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
    st.subheader("Modelo Digital de Elevación (DEM) y Precipitación Acumulada")

    m = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=11, tiles="OpenStreetMap")

    # 1. Visualización DEM
    dem_vis = {'min': 0, 'max': 2500, 'palette': ['006600', '002200', 'fff700', 'ab0000', 'b8b8b8', 'ffffff']}
    add_ee_layer(m, dem_cuenca, dem_vis, 'DEM de la Cuenca (SRTM)')

    # 2. Visualización Vectorial de la Cuenca
    cuenca_fc = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m, ee.Image().paint(cuenca_fc, 0, 2), {'palette': 'black'}, 'Límite Cuenca HydroSHEDS L12')

    # 3. Capa de Precipitación Acumulada en el Rango
    chirps_sum = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
                   .filterDate(str_start, str_end) \
                   .select('precipitation') \
                   .sum() \
                   .clip(cuenca_geom)

    precip_vis = {'min': 0, 'max': 1000, 'palette': ['blue', 'purple', 'cyan', 'green', 'yellow', 'red']}
    add_ee_layer(m, chirps_sum, precip_vis, f'Precipitación Acumulada ({str_start} - {str_end})')

    # Agregar marcador del punto
    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)

    folium.LayerControl().add_to(m)

    st_folium(m, width=950, height=550, key="analysis_map", returned_objects=[])

# =============================================================================
# PESTAÑA 2: SERIE DE TIEMPO Y CÁLCULO DE UMBRALES
# =============================================================================
with tab2:
    st.subheader("Análisis Estadístico de Precipitación y Umbrales Críticos")

    with st.spinner("Procesando la serie de tiempo diaria desde Google Earth Engine..."):
        df_precip = get_precipitation_df(str_start, str_end, st.session_state["lat"], st.session_state["lon"])

    if df_precip.empty:
        st.warning("No se encontraron registros de precipitación para el rango de fechas seleccionado.")
    else:
        # --- CÁLCULO DE UMBRALES (> 2mm) ---
        precip_dias_lluvia = df_precip[df_precip['lluvia_mm'] > 2]['lluvia_mm']

        if not precip_dias_lluvia.empty:
            p90 = precip_dias_lluvia.quantile(0.90)
            p95 = precip_dias_lluvia.quantile(0.95)
            p99 = precip_dias_lluvia.quantile(0.99)
        else:
            p90, p95, p99 = 0.0, 0.0, 0.0

        # --- TARJETAS DE MÉTRICAS (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precipitación Total", f"{df_precip['lluvia_mm'].sum():.1f} mm")
        col2.metric("Umbral P90 (>2mm)", f"{p90:.2f} mm")
        col3.metric("Umbral P95 (>2mm)", f"{p95:.2f} mm")
        col4.metric("Umbral P99 Crítico", f"{p99:.2f} mm")

        st.divider()

        # --- GRÁFICA INTERACTIVA CON PLOTLY ---
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_precip['fecha'],
            y=df_precip['lluvia_mm'],
            mode='lines',
            name='Precipitación Diaria (mm)',
            line=dict(color='#1f77b4', width=1.5)
        ))

        if p90 > 0:
            fig.add_hline(y=p90, line_dash="dash", line_color="orange", annotation_text=f"P90: {p90:.1f} mm")
            fig.add_hline(y=p95, line_dash="dash", line_color="red", annotation_text=f"P95: {p95:.1f} mm")
            fig.add_hline(y=p99, line_dash="dash", line_color="darkred", annotation_text=f"P99: {p99:.1f} mm")

        fig.update_layout(
            title=f"Serie Temporal Diaria y Umbrales ({str_start} a {str_end}) - HYBAS_ID: {cuenca_info['hybas_id'] if cuenca_info else 'N/A'}",
            xaxis_title="Fecha",
            yaxis_title="Precipitación Promedio en Cuenca (mm/día)",
            template="plotly_white",
            height=450,
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        # --- CONTEO DE EVENTOS CRÍTICOS ---
        st.markdown("### ⚠️ Conteo de Eventos que superan Umbrales Críticos")

        n_p90 = (df_precip['lluvia_mm'] > p90).sum() if p90 > 0 else 0
        n_p95 = (df_precip['lluvia_mm'] > p95).sum() if p95 > 0 else 0
        n_p99 = (df_precip['lluvia_mm'] > p99).sum() if p99 > 0 else 0

        col_a, col_b, col_c = st.columns(3)
        col_a.info(f"**Días > P90 ({p90:.1f} mm):** {n_p90} días")
        col_b.warning(f"**Días > P95 ({p95:.1f} mm):** {n_p95} días")
        col_c.error(f"**Días > P99 ({p99:.1f} mm):** {n_p99} días")