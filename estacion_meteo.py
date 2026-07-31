import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as gg
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Estación Meteorológica - Tiempo Real & Tendencias",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para estética premium y colores vivos
st.markdown("""
<style>
    /* Estilos globales y tarjeta de métrica */
    .stApp {
        background-color: #0e1117;  
    }
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
    .header-box {
        background: linear-gradient(90deg, #1a1e29 0%, #11141c 100%);
        padding: 20px 24px;
        border-radius: 14px;
        border-left: 5px solid #00e5ff;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)

# Función para convertir grados a dirección cardinal
def get_cardinal_direction(degree):
    if pd.isna(degree):
        return "N/A"
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((degree + 11.25) / 22.5) % 16
    return directions[idx]

# Función para consultar la API de meteo.tech
@st.cache_data(ttl=180, show_spinner=False)
def fetch_station_data(station_id="234424088", f1=None, f2=None):
    base_url = "https://gc.meteo.tech/_api.php"
    params = {
        "op": "history",
        "station_id": station_id,
        "variable_id": "0"
    }
    
    if f1 and f2:
        params["f1"] = f1
        params["f2"] = f2

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=12)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        st.error(f"Error al conectar con el servidor meteorológico: {e}")
        return []

# Función para procesar JSON a DataFrame estandarizado
def process_data(raw_data):
    if not raw_data or not isinstance(raw_data, list):
        return pd.DataFrame(), "Desconocida"

    df_raw = pd.DataFrame(raw_data)
    station_name = df_raw["station_name"].iloc[0] if "station_name" in df_raw.columns and not df_raw.empty else "Estación Encinal"

    df_raw["num_value"] = pd.to_numeric(df_raw["num_value"], errors="coerce")
    
    # Manejo de fechas
    if "data_date_local" in df_raw.columns:
        df_raw["fecha"] = pd.to_datetime(df_raw["data_date_local"])
    else:
        df_raw["fecha"] = pd.to_datetime(df_raw["data_date"])

    # Pivotear variables a columnas
    df = df_raw.pivot_table(
        index="fecha",
        columns="variable_name",
        values="num_value",
        aggfunc="first"
    ).sort_index()

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

# --- SIDEBAR & REGLAS DE TIEMPO ---
st.sidebar.image("https://meteo.tech/demos/saas-2/images/logo.png", use_container_width=True)
st.sidebar.title("🎛️ Configuración")

station_id = st.sidebar.text_input("ID de la Estación", value="234424088")

st.sidebar.subheader("📅 Rango de Fechas")
range_option = st.sidebar.selectbox(
    "Seleccionar Periodo",
    ["Por Defecto (Últimos 5 Días API)", "Últimas 24 Horas", "Últimos 3 Días", "Últimos 7 Días", "Personalizado"]
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
refresh_interval = st.sidebar.selectbox("Frecuencia de Actualización", ["10 Minutos", "5 Minutos", "1 Minuto"], index=0)

ref_mins = 10
if refresh_interval == "5 Minutos":
    ref_mins = 5
elif refresh_interval == "1 Minuto":
    ref_mins = 1

st.sidebar.caption(f"Refrescando automáticamente cada {ref_mins} min.")

if st.sidebar.button("🔄 Actualizar Datos Ahora", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- CARGA Y PROCESAMIENTO DE DATOS ---
raw_data = fetch_station_data(station_id, f1=f1_str, f2=f2_str)
df, station_name = process_data(raw_data)

# --- APLICACIÓN PRINCIPAL (FRAGMENTADA SI HAY AUTOREFRESH) ---
@st.fragment(run_every=f"{ref_mins}m" if enable_autorefresh else None)
def render_dashboard(data_df, name):
    if data_df.empty:
        st.warning("⚠️ No se encontraron registros meteorológicos para la estación y rango seleccionados.")
        return

    latest_date = data_df.index[-1] ##ultimo del dataframe
    latest = data_df.iloc[-1] #ultimo de la ultima fila del dataframe

    # --- BANNER SUPERIOR ---
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(f"🌤️ Estación Meteorológica: {name}")
        st.caption(f"📍 ID Estación: `{station_id}` | 🕒 Última Lectura: **{latest_date.strftime('%Y-%m-%d %H:%M:%S')}**")
    with col_head2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div style="text-align: right;"><span class="status-badge">● SENSOR ONLINE ({latest_date.strftime("%H:%M")})</span></div>', unsafe_allow_html=True)

    st.divider()

    # --- METRICAS KPIS PRINCIPALES (TIEMPO REAL) ---
    st.subheader("⚡ Lecturas en Tiempo Real & Resumen del Periodo")

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    # 1. Temperatura
    temp_val = latest.get("Temperatura (°C)", np.nan)
    temp_max = data_df["Temperatura (°C)"].max() if "Temperatura (°C)" in data_df else np.nan
    temp_min = data_df["Temperatura (°C)"].min() if "Temperatura (°C)" in data_df else np.nan
    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌡️ Temperatura</div>
            <div class="metric-value">{temp_val:.1f} °C</div>
            <div class="metric-subtitle">Mín: {temp_min:.1f}° | Máx: {temp_max:.1f}°</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Humedad
    hr_val = latest.get("Humedad (%)", np.nan)
    hr_avg = data_df["Humedad (%)"].mean() if "Humedad (%)" in data_df else np.nan
    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💦 Humedad</div>
            <div class="metric-value">{hr_val:.0f} %</div>
            <div class="metric-subtitle">Promedio: {hr_avg:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Presión
    prs_val = latest.get("Presión (hPa)", np.nan)
    prs_min = data_df["Presión (hPa)"].min() if "Presión (hPa)" in data_df else np.nan
    prs_max = data_df["Presión (hPa)"].max() if "Presión (hPa)" in data_df else np.nan
    with kpi3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🛩️ Presión</div>
            <div class="metric-value">{prs_val:.1f} <span style="font-size: 1rem;">hPa</span></div>
            <div class="metric-subtitle">Rango: {prs_min:.0f} - {prs_max:.0f} hPa</div>
        </div>
        """, unsafe_allow_html=True)

    # 4. Viento
    wns_val = latest.get("Velocidad Viento (Km/h)", 0)
    wng_max = data_df["Ráfaga Viento (Km/h)"].max() if "Ráfaga Viento (Km/h)" in data_df else 0
    wnd_deg = latest.get("Dirección Viento (°)", np.nan)
    cardinal = get_cardinal_direction(wnd_deg)
    with kpi4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🚩 Viento</div>
            <div class="metric-value">{wns_val:.0f} <span style="font-size: 1rem;">Km/h</span> ({cardinal})</div>
            <div class="metric-subtitle">Ráfaga Máx: {wng_max:.0f} Km/h</div>
        </div>
        """, unsafe_allow_html=True)

    # 5. Radiación & UV
    rsol_val = latest.get("Radiación Solar (W/m²)", 0)
    uv_val = latest.get("Índice UV", 0)
    with kpi5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">☀️ Rad. Solar / UV</div>
            <div class="metric-value">{rsol_val:.0f} <span style="font-size: 1rem;">W/m²</span></div>
            <div class="metric-subtitle">Índice UV: <b>{uv_val:.1f}</b></div>
        </div>
        """, unsafe_allow_html=True)

    # 6. Precipitación
    pcp_val = latest.get("Lluvia (mm/h)", 0)
    pca_max = data_df["Lluvia Acumulada (mm)"].max() if "Lluvia Acumulada (mm)" in data_df else 0
    with kpi6:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌧️ Precipitación</div>
            <div class="metric-value">{pcp_val:.1f} <span style="font-size: 1rem;">mm/h</span></div>
            <div class="metric-subtitle">Acumulado: {pca_max:.1f} mm</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TENDENCIAS TEMPORALES (GRÁFICOS PLOTLY) ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🌡️ Perfil Térmico & Humedad",
        "🚩 Dinámica del Viento",
        "🌧️ Precipitaciones",
        "🛩️ Barómetro (Presión)",
        "☀️ Radiación Solar & UV"
    ])

    # COLOR PALETTE MODERNA VIVA
    COLOR_TEMP = "#ff3366"     # Rosa Neón / Rojo Térmico
    COLOR_HUM = "#00e5ff"      # Cyan Neón
    COLOR_WIND = "#00e676"     # Verde Esmeralda
    COLOR_GUST = "#ffab00"     # Amber / Naranja
    COLOR_PRESS = "#ab47bc"    # Púrpura Orquídea
    COLOR_RAIN = "#29b6f6"     # Azul Lluvia
    COLOR_SOLAR = "#ffea00"    # Amarillo Solar

    # TAB 1: TEMPERATURA Y HUMEDAD
    with tab1:
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

    # TAB 2: VIENTO & DIRECCIÓN
    with tab2:
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
            # Rosa de Vientos (Polar Plot)
            if "Dirección Viento (°)" in data_df and "Velocidad Viento (Km/h)" in data_df:
                clean_wind = data_df.dropna(subset=["Dirección Viento (°)", "Velocidad Viento (Km/h)"])
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

    # TAB 3: PRECIPITACIONES
    with tab3:
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

    # TAB 4: PRESIÓN BAROMÉTRICA
    with tab4:
        fig_prs = gg.Figure()
        if "Presión (hPa)" in data_df:
            fig_prs.add_trace(gg.Scatter(
                x=data_df.index, y=data_df["Presión (hPa)"], name="Presión Atmosférica (hPa)",
                line=dict(color=COLOR_PRESS, width=3),
                fill="tozeroy", fillcolor="rgba(171,71,188,0.12)"
            ))

        prs_min_val = data_df["Presión (hPa)"].min() - 2 if "Presión (hPa)" in data_df else 950
        prs_max_val = data_df["Presión (hPa)"].max() + 2 if "Presión (hPa)" in data_df else 1050

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

    # TAB 5: RADIACIÓN & UV
    with tab5:
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

    st.divider()

    # --- TABLA DE RESUMEN DIARIO & EXPORTAR ---
    col_tb1, col_tb2 = st.columns([3, 1])
    with col_tb1:
        st.subheader("📊 Resumen Estadístico Diario")
    with col_tb2:
        csv_data = data_df.to_csv().encode("utf-8")
        st.download_button(
            label="📥 Descargar Serie Histórica (CSV)",
            data=csv_data,
            file_name=f"estacion_meteo_{station_id}_{latest_date.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Agrupar por día para resumen
    df_daily = data_df.resample("D").agg({
        "Temperatura (°C)": ["mean", "min", "max"],
        "Humedad (%)": ["mean", "min", "max"],
        "Presión (hPa)": ["mean", "min", "max"],
        "Velocidad Viento (Km/h)": ["mean", "max"],
        "Lluvia (mm/h)": ["sum"]
    }).round(1)

    df_daily.columns = [f"{col[0]} ({col[1].upper()})" for col in df_daily.columns]
    st.dataframe(df_daily, use_container_width=True)

# Renderizar Dashboard
render_dashboard(df, station_name)
