import streamlit as st

# Configuración de la página (opcional)
st.set_page_config(page_title="Mockup de Dashboard", layout="wide")

# 1. Título y Encabezado principal con Popover en la esquina superior derecha
col_title, col_popover = st.columns([5, 1])

with col_title:
    st.title("Mi Dashboard de Datos")
    st.header("Vista General del Proyecto")

with col_popover:
    st.markdown("<br>", unsafe_allow_html=True)  # Alineación vertical leve
    with st.popover("⚙️ Ajustes", use_container_width=True):
        st.markdown("### Configuración Global")
        st.checkbox("Mostrar valores acumulados", value=True)
        st.slider("Sensibilidad del Modelo", 0.0, 1.0, 0.5)
        st.button("Aplicar Cambios")

# 2. Menú Lateral (Sidebar) con opciones
with st.sidebar:
    st.title("Navegación")
    st.header("Filtros")
    
    # Menú desplegable (Selectbox)
    opcion = st.selectbox(
        "Selecciona el modelo:",
        ("Modelo Predictivo A", "Modelo Estadístico B", "Análisis de Red C")
    )
    
    st.write(f"Has seleccionado: **{opcion}**")
    
    # Un menú simple adicional
    st.radio("Nivel de detalle:", ["Básico", "Intermedio", "Avanzado"])

# 3. Tres secciones en el cuerpo usando Tabs (Pestañas)
# st.tabs permite organizar el contenido de forma eficiente
tab1, tab2, tab3 = st.tabs(["📈 Análisis", "📊 Gráficos", "📋 Datos Crudos"])

with tab1:
    st.header("Sección de Análisis")
    st.write("En esta pestaña puedes incluir métricas clave.")
    # Ejemplo de métrica mencionada en la documentación
    st.metric(label="Crecimiento Mensual", value="75%", delta="12%")

    st.divider()

    # Ejemplo de st.expander (Contenido colapsable / desplegable)
    with st.expander("ℹ️ Ver metodología e información detallada"):
        st.write("Esta sección utiliza un `st.expander` para ocultar información secundaria que el usuario puede desplegar cuando la necesite.")
        st.caption("Fórmula utilizada: Crecimiento = ((Mes Actual - Mes Anterior) / Mes Anterior) * 100")


with tab2:
    st.header("Visualización de Gráficos")
    st.write("Aquí puedes insertar gráficos interactivos de librerías como Plotly o Altair.")
    st.info("Espacio reservado para el gráfico del modelo seleccionado.")

with tab3:
    st.header("Exploración de Datos")
    st.write("Muestra tablas o dataframes en esta sección.")
    # st.dataframe(tu_dataframe) # Comenta esto cuando tengas datos

    with st.popover("📥 Opciones de Descargar Datos"):
        st.write("Selecciona el formato de exportación:")
        st.download_button("Descargar CSV", data="id,valor\n1,100\n2,200", file_name="datos.csv", mime="text/csv")


### Explicación de los componentes:
# *   **`st.title` y `st.header`:** Se utilizan para dar estructura jerárquica al contenido.
# *   **`st.sidebar`:** Crea un panel lateral persistente donde puedes colocar widgets de control sin obstruir el área principal.
# *   **`st.selectbox`:** Funciona como el menú desplegable para que el usuario elija opciones.
# *   **`st.tabs`:** Es una de las herramientas de diseño más útiles para mockups rápidos, ya que permite separar diferentes vistas dentro de una misma página.
# *   **`st.metric`:** Ideal para dashboards, muestra valores numéricos destacados con indicadores de cambio (delta).
# *   **`st.expander`:** Crea un contenedor desplegable/colapsable ideal para ocultar información complementaria o notas metodológicas.
# *   **`st.popover`:** Crea un botón emergente que al ser presionado despliega una ventana flotante con controles o filtros contextuales.

# Este código permite tener una estructura funcional lista para ser desplegada en la **Streamlit Community Cloud** o localmente.