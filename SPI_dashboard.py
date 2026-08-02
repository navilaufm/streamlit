import streamlit as st
import json
import urllib.request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as gg
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard SPI - Monitoreo de Sequía",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Styling (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
    .block-container {
        padding-top: 3.8rem !important;
        padding-bottom: 2rem !important;
    }
    .main-header {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-color, inherit);
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.9rem;
        color: var(--text-color, inherit);
        opacity: 0.8;
        margin-bottom: 1rem;
    }
    .alert-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        font-size: 0.85rem;
        font-weight: 600;
        border-radius: 20px;
        color: white;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

BASE_URL = "https://cvtas.snet.gob.sv/SPI/"
VALID_SPI_URL = "https://cvtas.snet.gob.sv/SPI/valid_spi.json"

# Helper for alert level badge styling
def get_alert_badge(alert_level, color):
    text_color = "#000000" if str(color).upper() in ["#FFFF00", "#FFEB3B", "#FFF"] else "#FFFFFF"
    return f'<span class="alert-badge" style="background-color: {color}; color: {text_color};">{alert_level}</span>'

# ---------------------------------------------------------
# Data Ingestion & Caching
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def load_valid_periods():
    try:
        req = urllib.request.Request(VALID_SPI_URL, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        st.sidebar.error(f"Error al cargar lista de períodos: {e}")
        return {"periods": [{"period": "2026-07", "month_name": "Julio", "file": "spi_2026_07.geojson"}]}

@st.cache_data(ttl=1800)
def load_geojson_data(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req) as response:
        raw = json.loads(response.read().decode('utf-8'))
    return raw

# Fetch list of available months
valid_manifest = load_valid_periods()
periods_list = valid_manifest.get("periods", [])

# Build period selection mapping
period_options = {
    f"{p.get('month_name', p.get('period'))} ({p.get('period')})": p.get("file")
    for p in periods_list
}

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Filtros y Control")
    st.markdown("---")
    
    # Station Selector Container (Rendered first at top of sidebar)
    station_container = st.container()
    st.markdown("---")
    
    # Period Selector Container (Rendered second)
    period_container = st.container()

with period_container:
    selected_period_label = st.selectbox(
        "📅 Seleccionar Mes / Período:",
        options=list(period_options.keys()),
        index=max(0, len(period_options) - 2) if len(period_options) > 1 else 0  # Default to recent period
    )

selected_file = period_options[selected_period_label]
target_geojson_url = BASE_URL + selected_file

# Load selected period data
try:
    geojson_raw = load_geojson_data(target_geojson_url)
except Exception as e:
    st.error(f"Error al cargar GeoJSON para {selected_period_label}: {e}")
    st.stop()
    
collection_props = geojson_raw.get("properties", {})
features = geojson_raw.get("features", [])

with period_container:
    st.markdown(f"**Período Seleccionado:** {collection_props.get('month_name', '')} {collection_props.get('period', '')}")
    st.markdown(f"**Estaciones Monitoreadas:** {len(features)}")
    
    if collection_props.get("generated_at"):
        try:
            gen_time = datetime.fromisoformat(collection_props.get("generated_at").replace("Z", "+00:00"))
            st.caption(f"Actualizado: {gen_time.strftime('%Y-%m-%d %H:%M UTC')}")
        except Exception:
            st.caption(f"Generado: {collection_props.get('generated_at')}")

# Parse GeoJSON into structured DataFrames
stations_data = []
daily_records = []

for f in features:
    coords = f.get("geometry", {}).get("coordinates", [0, 0])
    lon, lat = coords[0], coords[1]
    p = f.get("properties", {})
    m = p.get("metadata", {})
    
    station_id = p.get("station_id", "")
    station_name = p.get("station_name", "Sin Nombre")
    spi = p.get("spi", 0.0)
    alert_level = p.get("alert_level", "Normal")
    marker_color = p.get("marker_color", "#808080")
    
    rainfall_mm = m.get("rainfall_mm", 0.0)
    ref_mean = m.get("ref_mean_pn", 0.0)
    ref_std = m.get("ref_std_sigma", 0.0)
    total_days = m.get("total_days", 0)
    valid_days = m.get("valid_days", 0)
    missing_days = m.get("missing_days", 0)
    rainy_days = m.get("rainy_days", 0)
    dry_days = m.get("dry_days", 0)
    
    pct_deficit = ((ref_mean - rainfall_mm) / ref_mean * 100) if ref_mean > 0 else 0
    
    stations_data.append({
        "station_id": station_id,
        "station_name": station_name,
        "source_id": p.get("source_id", ""),
        "source_station_id": p.get("source_station_id", ""),
        "lat": lat,
        "lon": lon,
        "spi": spi,
        "alert_level": alert_level,
        "marker_color": marker_color,
        "rainfall_mm": rainfall_mm,
        "ref_mean_pn": ref_mean,
        "ref_std_sigma": ref_std,
        "total_days": total_days,
        "valid_days": valid_days,
        "missing_days": missing_days,
        "missing_percentage": m.get("missing_percentage", 0),
        "rainy_days": rainy_days,
        "dry_days": dry_days,
        "pct_deficit": pct_deficit
    })
    
    for d in m.get("daily_data", []):
        daily_records.append({
            "station_id": station_id,
            "station_name": station_name,
            "date": d.get("date"),
            "total_mm": d.get("total_mm", 0.0),
            "has_data": d.get("has_data", True)
        })

df_stations = pd.DataFrame(stations_data)
df_daily = pd.DataFrame(daily_records)

# Show all stations directly without filtering
df_filtered = df_stations

# Render Station Dropdown FIRST in station_container at top of sidebar
with station_container:
    selected_station_name = st.selectbox(
        "📍 Seleccionar Estación:",
        options=df_stations["station_name"].tolist() if not df_stations.empty else []
    )

with st.sidebar:
    st.markdown("---")
    if st.button("🔄 Recargar Todos los Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# Main Header
# ---------------------------------------------------------
col_head1, col_head2 = st.columns([1.2, 4])
with col_head1:
    st.image("https://img1.wsimg.com/isteam/ip/7df7d502-f608-4f42-96e5-594268ea23ec/CRRH-SICA%20.png", width=250)
with col_head2:
    st.markdown('<div class="main-header">🌧️ Monitor de Índice Estandarizado de Precipitación (SPI)</div>', unsafe_allow_html=True)
    station_str = f" &bull; Estación Seleccionada: <b style='color: #2563EB;'>{selected_station_name}</b>" if selected_station_name else ""
    st.markdown(f'<div class="sub-header">Análisis geoespacial y meteorológico de sequía para <b>{collection_props.get("month_name", "")} {collection_props.get("period", "")}</b>{station_str}</div>', unsafe_allow_html=True)

# Dynamic tab title for selected station
detail_tab_title = f"📍 Detalle Estación {selected_station_name}" if selected_station_name else "📍 Detalle por Estación"

tab_map, tab_compare, tab_multi_month, tab_table, tab_detail, tab_info = st.tabs([
    "🗺️ Mapa & Resumen General",
    "📊 Comparativa del Mes",
    "📈 Evolución Multi-Mes",
    "📋 Tabla Global de Datos",
    detail_tab_title,
    "ℹ️ Metodología & SAT Sequía"
])

# =========================================================
# TAB 1: MAPA Y RESUMEN GENERAL
# =========================================================
with tab_map:
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Estaciones", len(df_stations))
    with col2:
        avg_spi = df_stations["spi"].mean() if not df_stations.empty else 0
        st.metric("SPI Promedio", f"{avg_spi:.2f}", delta="Categoría Sequía" if avg_spi < 0 else "Húmedo")
    with col3:
        severe_count = len(df_stations[df_stations["alert_level"].str.contains("Severa|Extrema", case=False, na=False)]) if not df_stations.empty else 0
        st.metric("Sequía Severa / Extrema", severe_count, delta_color="inverse")
    with col4:
        avg_rain = df_stations["rainfall_mm"].mean() if not df_stations.empty else 0
        st.metric("Lluvia Promedio", f"{avg_rain:.1f} mm")
    with col5:
        avg_ref = df_stations["ref_mean_pn"].mean() if not df_stations.empty else 0
        st.metric("Ref. Histórica Prom.", f"{avg_ref:.1f} mm")

    st.markdown("---")
    
    col_map, col_info = st.columns([2, 1])
    
    with col_map:
        st.subheader(f"Mapa Temático de Estaciones ({collection_props.get('month_name', '')} {collection_props.get('period', '')})")
        
        avg_lat = df_stations["lat"].mean() if not df_stations.empty else 17.0
        avg_lon = df_stations["lon"].mean() if not df_stations.empty else -88.5
        
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=8, tiles="CartoDB positron")
        
        for _, row in df_filtered.iterrows():
            popup_html = f"""
            <div style="font-family: sans-serif; width: 220px; font-size: 13px;">
                <h4 style="margin: 0 0 6px 0; color: #1E293B;">{row['station_name']}</h4>
                <hr style="margin: 4px 0;">
                <b>Período:</b> {collection_props.get('month_name', '')} {collection_props.get('period', '')}<br>
                <b>SPI Index:</b> <span style="font-size: 15px; font-weight: bold;">{row['spi']}</span><br>
                <b>Alerta:</b> <span style="color: {row['marker_color']}; font-weight: bold;">{row['alert_level']}</span><br>
                <b>Lluvia del Mes:</b> {row['rainfall_mm']} mm<br>
                <b>Prom. Histórico:</b> {row['ref_mean_pn']} mm<br>
                <b>Días Lluvia / Secos:</b> {row['rainy_days']} / {row['dry_days']}
            </div>
            """
            
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=10,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"{row['station_name']} (SPI: {row['spi']})",
                color="#333333",
                weight=1.5,
                fill=True,
                fill_color=row["marker_color"],
                fill_opacity=0.95
            ).add_to(m)
            
        st_folium(m, width="100%", height=460)

    with col_info:
        st.subheader("Distribución de Niveles de Alerta")
        
        if not df_stations.empty:
            alert_counts = df_stations["alert_level"].value_counts().reset_index()
            alert_counts.columns = ["Nivel de Alerta", "Cantidad"]
            color_map = dict(zip(df_stations["alert_level"], df_stations["marker_color"]))
            
            fig_donut = px.pie(
                alert_counts,
                names="Nivel de Alerta",
                values="Cantidad",
                hole=0.4,
                color="Nivel de Alerta",
                color_discrete_map=color_map
            )
            fig_donut.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        
        st.markdown("#### Leyenda del Semáforo SPI")
        legend_html = """
        <div style="font-size: 0.9rem; line-height: 2.0;">
            <span style="font-size: 1.1rem;">🔴</span> <b style="color: #8B0000;">Sequía Extrema</b> (SPI &le; -2.0)<br>
            <span style="font-size: 1.1rem;">🔴</span> <b style="color: #DC2626;">Sequía Severa</b> (-1.99 a -1.50)<br>
            <span style="font-size: 1.1rem;">🟠</span> <b style="color: #D97706;">Sequía Moderada</b> (-1.49 a -1.00)<br>
            <span style="font-size: 1.1rem;">🟡</span> <b style="color: #CA8A04;">Sequía Débil</b> (-0.99 a -0.50)<br>
            <span style="font-size: 1.1rem;">🟢</span> <b style="color: #16A34A;">Normal / Húmedo</b> (SPI &gt; -0.50)
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

# =========================================================
# TAB 2: DETALLE POR ESTACIÓN
# =========================================================
with tab_detail:
    st.info("💡 **Vista Individual de Estación:** Esta pestaña muestra de forma exclusiva los datos meteorológicos y la serie diaria de la estación seleccionada en la barra lateral. Las pestañas anteriores muestran comparativas globales de toda la red.")
    if selected_station_name and not df_stations.empty:
        st_row = df_stations[df_stations["station_name"] == selected_station_name].iloc[0]
        
        badge_html = get_alert_badge(st_row['alert_level'], st_row['marker_color'])
        st.markdown(f"### Estación: **{st_row['station_name']}** {badge_html}", unsafe_allow_html=True)
        st.caption(f"ID Estación: {st_row['station_id']} | Coordenadas: [{st_row['lat']}, {st_row['lon']}] | Período: {collection_props.get('month_name', '')} {collection_props.get('period', '')}")
        
        st.markdown("---")
        
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("SPI Índice", f"{st_row['spi']:.2f}")
        with m2:
            st.metric("Lluvia Registrada", f"{st_row['rainfall_mm']} mm")
        with m3:
            st.metric("Promedio Histórico", f"{st_row['ref_mean_pn']} mm")
        with m4:
            st.metric("Déficit de Lluvia", f"{st_row['pct_deficit']:.1f}%")
        with m5:
            st.metric("Días Lluvia vs Secos", f"{st_row['rainy_days']} / {st_row['dry_days']}")

        st.markdown("---")
        
        st.subheader(f"📊 Precipitaciones Diarias ({collection_props.get('month_name', '')} {collection_props.get('period', '')})")
        
        st_daily = df_daily[df_daily["station_name"] == selected_station_name].copy()
        
        if not st_daily.empty:
            st_daily["date"] = pd.to_datetime(st_daily["date"])
            st_daily = st_daily.sort_values("date")
            st_daily["cumulative_mm"] = st_daily["total_mm"].cumsum()
            
            fig_daily = gg.Figure()
            
            fig_daily.add_trace(gg.Bar(
                x=st_daily["date"],
                y=st_daily["total_mm"],
                name="Lluvia Diaria (mm)",
                marker_color="#2563EB",
                hovertemplate="<b>Fecha:</b> %{x|%Y-%m-%d}<br><b>Precipitación:</b> %{y:.1f} mm<extra></extra>"
            ))
            
            fig_daily.add_trace(gg.Scatter(
                x=st_daily["date"],
                y=st_daily["cumulative_mm"],
                name="Lluvia Acumulada (mm)",
                mode="lines+markers",
                line=dict(color="#059669", width=3),
                hovertemplate="<b>Acumulado al %{x|%m-%d}:</b> %{y:.1f} mm<extra></extra>"
            ))
            
            fig_daily.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Precipitación (mm)",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.1, x=0),
                margin=dict(t=30, b=40, l=40, r=40),
                template="plotly_white"
            )
            
            st.plotly_chart(fig_daily, use_container_width=True)
            
            with st.expander("📄 Ver Tabla de Registro Diario Completo"):
                st_daily_display = st_daily[["date", "total_mm", "cumulative_mm", "has_data"]].copy()
                st_daily_display["date"] = st_daily_display["date"].dt.strftime("%Y-%m-%d")
                st_daily_display.columns = ["Fecha", "Lluvia (mm)", "Acumulado (mm)", "Dato Válido"]
                st.dataframe(st_daily_display, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron registros diarios para esta estación.")

# =========================================================
# TAB 3: COMPARATIVA DEL MES
# =========================================================
with tab_compare:
    st.subheader(f"Ranking SPI por Severidad ({collection_props.get('month_name', '')} {collection_props.get('period', '')})")
    
    if not df_stations.empty:
        df_sorted = df_stations.sort_values("spi", ascending=True)
        
        fig_rank = px.bar(
            df_sorted,
            x="spi",
            y="station_name",
            orientation="h",
            color="alert_level",
            color_discrete_map=dict(zip(df_stations["alert_level"], df_stations["marker_color"])),
            text="spi",
            labels={"station_name": "Estación", "spi": "Índice SPI", "alert_level": "Alerta"}
        )
        fig_rank.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_rank.update_layout(
            template="plotly_white",
            xaxis_title="Índice SPI (Valores más negativos indican mayor sequía)",
            yaxis_title="",
            height=400,
            margin=dict(l=20, r=40, t=20, b=40)
        )
        st.plotly_chart(fig_rank, use_container_width=True)
        
        st.markdown("---")
        
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            st.subheader("Lluvia Registrada vs. Promedio Histórico")
            df_melted = pd.melt(
                df_stations,
                id_vars=["station_name"],
                value_vars=["rainfall_mm", "ref_mean_pn"],
                var_name="Tipo",
                value_name="Precipitación_mm"
            )
            df_melted["Tipo"] = df_melted["Tipo"].replace({
                "rainfall_mm": f"Lluvia Observada ({collection_props.get('period', '')})",
                "ref_mean_pn": "Referencia Histórica"
            })
            
            fig_comp_bar = px.bar(
                df_melted,
                x="station_name",
                y="Precipitación_mm",
                color="Tipo",
                barmode="group",
                color_discrete_map={f"Lluvia Observada ({collection_props.get('period', '')})": "#0284C7", "Referencia Histórica": "#94A3B8"},
                labels={"station_name": "Estación", "Precipitación_mm": "Precipitación (mm)"}
            )
            fig_comp_bar.update_layout(
                template="plotly_white",
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=20, b=80),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_comp_bar, use_container_width=True)

        with col_comp2:
            st.subheader("Relación Días Lluviosos vs. Secos")
            fig_days = px.bar(
                df_stations,
                x="station_name",
                y=["rainy_days", "dry_days"],
                labels={"value": "Días", "variable": "Condición", "station_name": "Estación"},
                color_discrete_map={"rainy_days": "#3B82F6", "dry_days": "#F59E0B"}
            )
            fig_days.data[0].name = "Días Lluviosos"
            fig_days.data[1].name = "Días Secos"
            fig_days.update_layout(
                template="plotly_white",
                barmode="stack",
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=20, b=80),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_days, use_container_width=True)

# =========================================================
# TAB 4: EVOLUCIÓN MULTI-MES
# =========================================================
with tab_multi_month:
    st.subheader("📈 Tendencia Histórica e Inter-mensual del SPI")
    st.markdown("Comparativa de evolución del SPI a lo largo de todos los meses disponibles en el sistema.")
    
    # Load all available period GeoJSONs for multi-month trend analysis
    all_months_data = []
    for p in periods_list:
        file_name = p.get("file")
        period_code = p.get("period")
        month_label = p.get("month_name", period_code)
        try:
            raw_g = load_geojson_data(BASE_URL + file_name)
            for feat in raw_g.get("features", []):
                prop = feat.get("properties", {})
                met = prop.get("metadata", {})
                all_months_data.append({
                    "period": period_code,
                    "month_name": month_label,
                    "station_name": prop.get("station_name"),
                    "spi": prop.get("spi"),
                    "alert_level": prop.get("alert_level"),
                    "rainfall_mm": met.get("rainfall_mm"),
                    "ref_mean_pn": met.get("ref_mean_pn")
                })
        except Exception:
            pass
            
    df_multi = pd.DataFrame(all_months_data)
    
    if not df_multi.empty:
        # Multi-line plot of SPI per station across months
        fig_multi_spi = px.line(
            df_multi,
            x="month_name",
            y="spi",
            color="station_name",
            markers=True,
            title="Evolución del SPI por Estación",
            labels={"month_name": "Mes", "spi": "Índice SPI", "station_name": "Estación"}
        )
        fig_multi_spi.add_hline(y=-1.0, line_dash="dash", line_color="#FFA500", annotation_text="Sequía Moderada (-1.0)")
        fig_multi_spi.add_hline(y=-1.5, line_dash="dash", line_color="#FF0000", annotation_text="Sequía Severa (-1.5)")
        fig_multi_spi.add_hline(y=-2.0, line_dash="dash", line_color="#8B0000", annotation_text="Sequía Extrema (-2.0)")
        
        fig_multi_spi.update_layout(
            template="plotly_white",
            hovermode="x unified",
            height=450
        )
        st.plotly_chart(fig_multi_spi, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("Precipitación Mensual Observada (mm) por Estación")
        fig_multi_rain = px.bar(
            df_multi,
            x="station_name",
            y="rainfall_mm",
            color="month_name",
            barmode="group",
            labels={"station_name": "Estación", "rainfall_mm": "Lluvia (mm)", "month_name": "Mes"}
        )
        fig_multi_rain.update_layout(
            template="plotly_white",
            xaxis_tickangle=-45,
            height=400
        )
        st.plotly_chart(fig_multi_rain, use_container_width=True)

# =========================================================
# TAB 5: TABLA DE DATOS & EXPORTACIÓN
# =========================================================
with tab_table:
    st.subheader(f"Tabla Global de Metadata ({collection_props.get('month_name', '')} {collection_props.get('period', '')})")
    
    display_cols = [
        "station_id", "station_name", "spi", "alert_level",
        "rainfall_mm", "ref_mean_pn", "pct_deficit",
        "rainy_days", "dry_days", "missing_days", "lat", "lon"
    ]
    
    if not df_filtered.empty:
        df_export = df_filtered[display_cols].copy()
        df_export.columns = [
            "ID Estación", "Nombre Estación", "SPI", "Alerta",
            "Lluvia (mm)", "Ref. Histórica (mm)", "Déficit (%)",
            "Días Lluvia", "Días Secos", "Días Faltantes", "Latitud", "Longitud"
        ]
        
        st.dataframe(
            df_export.style.background_gradient(subset=["SPI"], cmap="Reds_r"),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Descargar CSV ({collection_props.get('period', '')})",
                data=csv_data,
                file_name=f"spi_estaciones_{collection_props.get('period', '')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            geojson_str = json.dumps(geojson_raw, indent=2).encode('utf-8')
            st.download_button(
                label=f"🌐 Descargar GeoJSON ({collection_props.get('period', '')})",
                data=geojson_str,
                file_name=f"spi_{collection_props.get('period', '')}.geojson",
                mime="application/geo+json",
                use_container_width=True
            )

# =========================================================
# TAB 6: METODOLOGÍA & SAT SEQUÍA
# =========================================================
with tab_info:
    st.subheader("ℹ️ Metodología y Sistema de Alerta Temprana (SAT) por Sequía")
    st.markdown("Información metodológica simplificada sobre el **Índice de Precipitación Estandarizada (SPI)** adaptado para la región por el CRRH.")
    
    st.markdown("---")
    
    col_info1, col_info2 = st.columns([1.1, 1])
    
    with col_info1:
        st.markdown("### 📌 ¿Qué es el SPI?")
        st.info(
            "El **Índice de Precipitación Estandarizada (SPI)** es el indicador climático utilizado para detectar y caracterizar deficiencias de lluvia. "
            "Su función principal es comparar la lluvia registrada en un periodo específico con el promedio histórico de ese mismo lugar, "
            "permitiendo identificar estadísticamente qué tan anormal es la falta de agua."
        )
        
        st.markdown("### 🧮 ¿Cómo se calcula? (La Fórmula)")
        st.latex(r"SPI = \frac{P - PN}{\sigma}")
        st.markdown(r"""
        - **$P$ (Precipitación):** Lluvia total acumulada en el mes o periodo actual.
        - **$PN$ (Precipitación Normal):** Promedio histórico de lluvia para esa ubicación y mes específico.
        - **$\sigma$ (Desviación Estándar):** Medida de variabilidad histórica habitual de la lluvia en la zona.
        """)
        
        st.markdown("### 🎯 ¿Para qué sirve esta información?")
        st.success(
            "Este índice funciona como un **indicador de verificación** que confirma la ocurrencia de una sequía. "
            "Es una herramienta esencial para que autoridades y productores agrícolas puedan tomar acciones preventivas "
            "(como entrega de semillas, gestión de seguros paramétricos o auxilio) antes de que los impactos en las cosechas sean irreversibles."
        )

    with col_info2:
        st.markdown("### 🚦 Niveles de Alerta y Categorías de Sequía")
        
        table_html = """
        <table style="width:100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;">
            <thead>
                <tr style="border-bottom: 2px solid #CBD5E1;">
                    <th style="padding: 8px;">Valor SPI</th>
                    <th style="padding: 8px;">Categoría Sequía</th>
                    <th style="padding: 8px;">Alerta SAT</th>
                    <th style="padding: 8px; text-align: center;">Nivel</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 8px;"><b>&gt; -0.5</b></td>
                    <td>Condiciones Normales</td>
                    <td><b>Vigilancia</b></td>
                    <td style="text-align: center;"><span style="background-color:#16A34A; color:white; padding:3px 10px; border-radius:12px; font-weight:bold;">Verde</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 8px;"><b>-0.5 a -1.0</b></td>
                    <td>Sequía Débil</td>
                    <td><b>Preaviso</b></td>
                    <td style="text-align: center;"><span style="background-color:#CA8A04; color:white; padding:3px 10px; border-radius:12px; font-weight:bold;">Amarillo</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 8px;"><b>-1.1 a -1.5</b></td>
                    <td>Sequía Moderada</td>
                    <td><b>Aviso</b></td>
                    <td style="text-align: center;"><span style="background-color:#D97706; color:white; padding:3px 10px; border-radius:12px; font-weight:bold;">Naranja</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 8px;"><b>-1.6 a -2.0</b></td>
                    <td>Sequía Severa</td>
                    <td><b>Alerta</b></td>
                    <td style="text-align: center;"><span style="background-color:#DC2626; color:white; padding:3px 10px; border-radius:12px; font-weight:bold;">Rojo</span></td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><b>&lt; -2.0</b></td>
                    <td>Sequía Extrema</td>
                    <td><b>Emergencia</b></td>
                    <td style="text-align: center;"><span style="background-color:#7E22CE; color:white; padding:3px 10px; border-radius:12px; font-weight:bold;">Púrpura</span></td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🛡️ Metodología del SAT por Sequía")
        st.markdown("""
        1. **Uso de Datos Reales:** A diferencia de estimaciones satelitales (que suelen sobreestimar lluvia y retrasar alertas), este sistema prioriza datos de **estaciones meteorológicas reales** en terreno para obtener precisión científica.
        2. **Vigilancia de Meses Críticos:** Se presta especial atención a los meses de **junio, julio y agosto** (período de la Canícula), vitales para la agricultura de subsistencia regional.
        3. **Automatización de Avisos:** Al caer la lluvia registrada por debajo de umbrales definidos, el sistema genera automáticamente notificaciones. Si la lluvia se normaliza, la alerta se desactiva.
        """)

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #94A3B8; font-size: 0.85rem;">'
    'Fuente: CRRH - CVTAS. Más información en <a href="https://recursoshidricos.org/" target="_blank" style="color: #3B82F6; text-decoration: underline;">https://recursoshidricos.org/</a>'
    '</div>',
    unsafe_allow_html=True
)
