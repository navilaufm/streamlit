import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DEM Cuenca 7070870860",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo para maximizar la visualización en pantalla
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. AUTENTICACIÓN CON SERVICE ACCOUNT GEE
# -----------------------------------------------------------------------------
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
# 3. CARGA DE LA CUENCA 7070870860 Y DEM (HydroSHEDS L7)
# -----------------------------------------------------------------------------
HYBAS_ID = 7070870860

@st.cache_data
def get_basin_and_dem(hybas_id):
    # Filtrar cuenca en HydroSHEDS Nivel 7
    basins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_7")
    cuenca = basins.filter(ee.Filter.eq('HYBAS_ID', hybas_id)).first()

    geom = cuenca.geometry()

    # DEM SRTM 30m recortado a la cuenca
    dem = ee.Image("USGS/SRTMGL1_003").clip(geom)

    # Centroide y metadatos
    centroid = geom.centroid().coordinates().getInfo()  # [lon, lat]
    props = cuenca.getInfo()['properties']

    # Rango de elevación
    stats = dem.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=geom,
        scale=90,
        maxPixels=1e9
    ).getInfo()

    return cuenca, dem, centroid, props, stats

try:
    cuenca_feat, dem_cuenca, centroid, props, stats = get_basin_and_dem(HYBAS_ID)
    lat_center, lon_center = centroid[1], centroid[0]
    min_elev = stats.get('elevation_min', 0)
    max_elev = stats.get('elevation_max', 3000)
except Exception as err:
    st.error(f"Error al cargar la cuenca {HYBAS_ID}: {err}")
    st.stop()

# -----------------------------------------------------------------------------
# 4. ENCABEZADO, MÉTRICAS Y SLIDER DE TRANSPARENCIA
# -----------------------------------------------------------------------------
st.title("🏔️ Modelo Digital de Elevación (DEM) - Cuenca HydroSHEDS L7")

c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
c1.metric("HYBAS_ID", f"{HYBAS_ID}")
c2.metric("Sub-Área", f"{props.get('SUB_AREA', 0):.1f} km²")
c3.metric("Rango Elevación", f"{min_elev:.0f} a {max_elev:.0f} m")

with c4:
    dem_opacity = st.slider(
        "🎛️ Transparencia Capa DEM",
        min_value=0.0,
        max_value=1.0,
        value=0.75,
        step=0.05,
        help="Mueve el slider para ajustar la opacidad del DEM"
    )

# -----------------------------------------------------------------------------
# 5. MAPA INTERACTIVO PANTALLA COMPLETA CON FOLIUM
# -----------------------------------------------------------------------------
m = folium.Map(location=[lat_center, lon_center], zoom_start=9, tiles="OpenStreetMap")

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

# 1. Capa DEM con paleta hipsométrica y transparencia dinámica
dem_vis = {
    'min': min_elev,
    'max': max_elev,
    'palette': ['006600', '002200', 'fff700', 'ab0000', 'b8b8b8', 'ffffff']
}
add_ee_layer(m, dem_cuenca, dem_vis, f'DEM SRTM (Cuenca {HYBAS_ID})', opacity=dem_opacity)

# 2. Límite Vectorial de la Cuenca
cuenca_fc = ee.FeatureCollection([cuenca_feat])
add_ee_layer(m, ee.Image().paint(cuenca_fc, 0, 3), {'palette': 'black'}, f'Límite Cuenca {HYBAS_ID}')

# Marcador en el centroide
folium.Marker(
    [lat_center, lon_center],
    popup=f"Centroide Cuenca {HYBAS_ID}",
    tooltip="Centroide de la Cuenca",
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)

folium.LayerControl().add_to(m)

# Renderizar en pantalla ancha y alta
st_folium(m, width="100%", height=720, key="dem_full_map")



