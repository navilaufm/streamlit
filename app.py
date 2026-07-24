import streamlit as st

# ---------------------------------------------------------
# 1. Configuración de la página y Menú Superior
# ---------------------------------------------------------
st.set_page_config(
    page_title="Streamlit Showcase",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Menú superior (Header básico & Descripción)
st.title("🚀 Hello World con Streamlit componentes")
st.caption("Una vista rápida por los principales componentes de la interfaz de usuario.")

st.divider()

# ---------------------------------------------------------
# 2. Menú Lateral (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración Lateral")
    st.write("Usa la barra lateral para filtros o controles globales.")
    
    # Inputs en la barra lateral
    user_name = st.text_input("Tu nombre:", value="Desarrollador")
    environment = st.selectbox("Entorno:", ["Desarrollo", "Staging", "Producción"])
    show_advanced = st.checkbox("Mostrar opciones avanzadas", value=True)

# Mensaje de bienvenida personalizado desde la sidebar
st.success(f"¡Bienvenido/a, **{user_name}**! Estás explorando en el entorno de **{environment}**.")

# ---------------------------------------------------------
# 3. Pestañas (Tabs)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🎛️ Controles e Inputs", "📊 Métricas y Datos", "🎨 Diseño y Mensajes"])

# --- TAB 1: CONTROLES E INPUTS ---
with tab1:
    st.subheader("Selección e Interacción")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sliders y Botones
        slider_val = st.slider("Selecciona un valor (Slider):", min_value=0, max_value=100, value=50)
        
        if st.button("🔴 Presióname (Botón)", use_container_width=True):
            st.toast(f"¡Hiciste clic! El valor del slider es {slider_val}.")
            
    with col2:
        # Checkboxes y Radio buttons
        framework = st.radio("¿Tu lenguaje principal?", ["Python", "JavaScript", "Julia", "R"])
        multi_select = st.multiselect("Librerías favoritas:", ["Pandas", "NumPy", "Geemap", "Xarray"], default=["Pandas"])

# --- TAB 2: MÉTRICAS Y DATOS ---
with tab2:
    st.subheader("Visualización de Indicadores")
    
    # Grid de métricas
    m1, m2, m3 = st.columns(3)
    m1.metric(label="Usuarios Activos", value="1,250", delta="12%")
    m2.metric(label="Tiempo de Respuesta", value="45 ms", delta="-5 ms")
    m3.metric(label="Uso de Memoria", value="68%", delta="2%", delta_color="inverse")
    
    st.divider()
    
    # Expander para ocultar detalles/tablas
    with st.expander("🔍 Ver JSON de estado actual"):
        st.json({
            "usuario": user_name,
            "entorno": environment,
            "slider_valor": slider_val,
            "opciones_avanzadas": show_advanced,
            "librerias": multi_select
        })

# --- TAB 3: DISEÑO Y MENSAJES ---
with tab3:
    st.subheader("Notificaciones y Estilos")
    
    # Mensajes de estado
    st.info("💡 Este es un mensaje informativo (`st.info`).")
    st.warning("⚠️ Este es un mensaje de advertencia (`st.warning`).")
    st.error("🚨 Ocurrió un error ficticio (`st.error`).")
    
    if show_advanced:
        st.write("---")
        st.subheader("Carga de archivos")
        uploaded_file = st.file_uploader("Subir un archivo CSV o JSON:", type=["csv", "json"])