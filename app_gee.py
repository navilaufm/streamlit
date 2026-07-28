import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
# 2. ESTADO DE SESIÓN Y FUNCIONES AUXILIARES GEE
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
                'pfaf_id': props.get('PFAF_ID', 'N/A')
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
# 3. BARRA LATERAL (SIDEBAR): PARÁMETROS DE ANÁLISIS
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
# 4. EXTRACCIÓN Y PROCESAMIENTO DE DATOS CHIRPS
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_precipitation_df(start_str, end_str, lat, lon, level, freq):
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

# -----------------------------------------------------------------------------
# 5. ESTRUCTURA PRINCIPAL EN PESTAÑAS (TABS)
# -----------------------------------------------------------------------------
st.title("🌊 Portal Climatológico & Analizador de Cuencas")

cuenca_info = get_cuenca_info(cuenca_vector)
hybas_str = f"HYBAS_ID: {cuenca_info['hybas_id']}" if cuenca_info else f"Cuenca HydroSHEDS L{nivel_hybas}"
st.markdown(
    f"**Cuenca Activa:** `{hybas_str}` (Nivel {nivel_hybas}) | "
    f"**Coordenada:** ({st.session_state['lat']:.4f}° N, {st.session_state['lon']:.4f}° O) | "
    f"**Rango:** `{str_start}` a `{str_end}` ({num_anos:.1f} años)"
)

tab0, tab1, tab2 = st.tabs(["📍 Selector de Cuenca", "🗺️ Mapa, DEM & Satélite", "📈 Serie de Tiempo & Umbrales"])

# =============================================================================
# PESTAÑA 0: SELECTOR INTERACTIVO DE CUENCA
# =============================================================================
with tab0:
    st.subheader(f"📍 Selección Interactiva de Cuenca por Clic en Mapa (HydroSHEDS Nivel {nivel_hybas})")
    st.info(f"Haz clic en cualquier punto del mapa para interceptar la cuenca HydroSHEDS (Nivel {nivel_hybas}) correspondiente.")

    m_select = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=9, tiles="OpenStreetMap")

    # Dibujar la cuenca actual
    cuenca_fc = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m_select, ee.Image().paint(cuenca_fc, 0, 2), {'palette': 'blue'}, f'Cuenca HydroSHEDS L{nivel_hybas}')

    # Marcador en el punto actual
    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto seleccionado: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}",
        tooltip="Punto actual de análisis",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m_select)

    folium.LayerControl().add_to(m_select)

    # Renderizar mapa interactivo escuchando clics
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

    # Capa de Satélite alternativa
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Esri Satélite',
        overlay=False
    ).add_to(m)

    # 1. Visualización DEM SRTM
    dem_vis = {'min': 0, 'max': 2500, 'palette': ['006600', '002200', 'fff700', 'ab0000', 'b8b8b8', 'ffffff']}
    add_ee_layer(m, dem_cuenca, dem_vis, 'DEM de la Cuenca (SRTM 30m)', opacity=opacity_dem)

    # 2. Capa de Precipitación Promedio Anual (Total / Años)
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

    # 3. Límite Vectorial de la Cuenca
    cuenca_fc = ee.FeatureCollection([cuenca_vector])
    add_ee_layer(m, ee.Image().paint(cuenca_fc, 0, 3), {'palette': 'black'}, f'Límite Cuenca HydroSHEDS L{nivel_hybas}')

    # Marcador del punto
    folium.Marker(
        [st.session_state["lat"], st.session_state["lon"]],
        popup=f"Punto: {st.session_state['lat']:.4f}, {st.session_state['lon']:.4f}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)

    # Leyenda flotante superpuesta directamente en el mapa Folium
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

    col_freq, _ = st.columns([2, 1])
    with col_freq:
        frec_idx_tab = ["Diaria", "Mensual", "Anual"].index(st.session_state["frecuencia"]) if st.session_state["frecuencia"] in ["Diaria", "Mensual", "Anual"] else 0
        sel_frec_tab = st.radio(
            "⏱️ Selecciona la Agregación Temporal del Gráfico:",
            options=["Diaria", "Mensual", "Anual"],
            horizontal=True,
            index=frec_idx_tab,
            key="tab_frecuencia_radio",
            help="Los umbrales de lluvia extrema (P90, P95, P99) se calculan siempre sobre la serie diaria (>2mm). Cambiar la frecuencia ajusta la resolución del gráfico y la tabla."
        )
        if sel_frec_tab != st.session_state["frecuencia"]:
            st.session_state["frecuencia"] = sel_frec_tab
            st.rerun()

    frecuencia = st.session_state["frecuencia"]



    with st.spinner("Procesando serie temporal desde Google Earth Engine..."):
        # 1. Obtenemos la serie diaria para el cálculo estricto de umbrales diarios
        df_daily = get_precipitation_df(
            str_start, str_end, st.session_state["lat"], st.session_state["lon"], nivel_hybas, "Diaria"
        )

        # 2. Si la frecuencia elegida es distinta de Diaria, obtenemos la serie agregada
        if frecuencia == "Diaria":
            df_precip = df_daily
        else:
            df_precip = get_precipitation_df(
                str_start, str_end, st.session_state["lat"], st.session_state["lon"], nivel_hybas, frecuencia
            )

    if df_daily.empty or df_precip.empty:
        st.warning("No se encontraron registros de precipitación para el rango de fechas seleccionado.")
    else:
        # --- CÁLCULO DE UMBRALES DIARIOS (Días de lluvia > 2mm) ---
        precip_dias_lluvia = df_daily[df_daily['lluvia_mm'] > 2]['lluvia_mm']

        if not precip_dias_lluvia.empty:
            p90 = precip_dias_lluvia.quantile(0.90)
            p95 = precip_dias_lluvia.quantile(0.95)
            p99 = precip_dias_lluvia.quantile(0.99)
        else:
            p90, p95, p99 = 0.0, 0.0, 0.0

        total_precip = df_daily['lluvia_mm'].sum()
        promedio_anual = total_precip / num_anos

        # --- TARJETAS DE MÉTRICAS (KPIs) ---
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Precipitación Total", f"{total_precip:.1f} mm")
        col2.metric("Promedio Anual", f"{promedio_anual:.1f} mm/año")
        col3.metric("P90 Diario (>2mm)", f"{p90:.1f} mm/día")
        col4.metric("P95 Diario (>2mm)", f"{p95:.1f} mm/día")
        col5.metric("P99 Diario Crítico", f"{p99:.1f} mm/día")

        st.divider()

        # Botón de Descarga CSV
        st.download_button(
            label=f"📥 Descargar Serie Temporal {frecuencia} (CSV)",
            data=df_precip.to_csv(index=False).encode('utf-8'),
            file_name=f"precipitacion_{frecuencia.lower()}_hybas_{cuenca_info['hybas_id'] if cuenca_info else 'cuenca'}.csv",
            mime="text/csv"
        )

        # --- GRÁFICA INTERACTIVA CON PLOTLY (Serie + Acumulada) ---
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

        # Mostrar líneas horizontales de umbral si la vista es diaria
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

        # --- TOP 10 EVENTOS EXTREMOS ---
        st.markdown(f"### 🔥 Top 10 Períodos ({frecuencia}) con Mayor Precipitación")
        top10 = df_precip.sort_values('lluvia_mm', ascending=False).head(10).reset_index(drop=True)
        top10['fecha'] = top10['fecha'].dt.strftime('%Y-%m-%d')
        st.dataframe(top10, use_container_width=True)

        # --- CONTEO DE DÍAS EXTREMOS DIARIOS ---
        st.markdown("### ⚠️ Conteo de Días que Superan los Umbrales Diarios Críticos")
        n_p90 = (df_daily['lluvia_mm'] > p90).sum() if p90 > 0 else 0
        n_p95 = (df_daily['lluvia_mm'] > p95).sum() if p95 > 0 else 0
        n_p99 = (df_daily['lluvia_mm'] > p99).sum() if p99 > 0 else 0

        col_a, col_b, col_c = st.columns(3)
        col_a.info(f"**Días > P90 ({p90:.1f} mm/día):** {n_p90} días")
        col_b.warning(f"**Días > P95 ({p95:.1f} mm/día):** {n_p95} días")
        col_c.error(f"**Días > P99 ({p99:.1f} mm/día):** {n_p99} días")

        # Pie de página y margen de scroll inferior
        st.markdown("---")
        st.caption("🌊 *Portal Climatológico & Analizador de Cuencas con Google Earth Engine, Folium & Streamlit*")
        st.markdown("<div style='height: 160px;'></div>", unsafe_allow_html=True)