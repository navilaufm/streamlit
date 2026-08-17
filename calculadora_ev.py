import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración inicial de la página (layout centered optimizado para móvil)
st.set_page_config(
    page_title="AMEGUA | Calculadora EV", 
    page_icon="⚡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# URL oficial del logo de AMEGUA
LOGO_AMEGUA_URL = "https://images.squarespace-cdn.com/content/v1/5e83d5a6a631ec0bc312acae/356c4842-e22f-4676-af01-5bd222672807/logo+amegua+propuestas-01+copy.png"

# Estilos CSS optimizados: reducción de espacio superior y paleta oficial AMEGUA
st.markdown("""
<style>
    /* 1. ELIMINAR ESPACIO EN BLANCO SUPERIOR */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 760px !important;
    }
    header[data-testid="stHeader"] {
        height: 1.5rem !important;
        background: transparent !important;
    }

    /* 2. VARIABLES DE COLOR OFICIALES AMEGUA */
    :root {
        --amegua-blue: #0066CC;
        --amegua-blue-dark: #0047BA;
        --amegua-green: #78BE20;
        --amegua-cyan: #00C2CB;
    }

    /* 3. HERO CARD DE AHORRO (AMEGUA BRANDED) */
    .hero-card {
        background: linear-gradient(135deg, #0047BA 0%, #0066CC 55%, #00C2CB 100%);
        color: #ffffff !important;
        padding: 22px 18px;
        border-radius: 16px;
        text-align: center;
        margin: 12px 0 20px 0;
        box-shadow: 0 10px 25px -4px rgba(0, 102, 204, 0.45);
        border: 1px solid rgba(0, 194, 203, 0.4);
    }
    .hero-title {
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 700;
        color: #E0F2FE;
        margin-bottom: 4px;
    }
    .hero-amount {
        font-size: 2.6rem;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 6px;
        color: #ffffff;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
    }
    .hero-subtitle {
        font-size: 1.05rem;
        font-weight: 500;
        color: #F0F9FF;
    }
    .badge-amegua-green {
        background-color: #78BE20;
        color: #ffffff !important;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.88rem;
        font-weight: 800;
        display: inline-block;
        margin-top: 8px;
        box-shadow: 0 2px 8px rgba(120, 190, 32, 0.45);
        letter-spacing: 0.5px;
    }

    /* 4. SOBREESCRIBIR COLOR ROJO DE STREAMLIT POR AZUL Y VERDE AMEGUA */
    /* Pestañas */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: #94A3B8 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00D2FF !important;
        border-bottom: 3px solid #78BE20 !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #78BE20 !important;
    }

    /* Sliders (Elimina el rojo por completo) */
    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #0066CC !important;
        border: 2px solid #78BE20 !important;
        box-shadow: 0 0 10px rgba(120, 190, 32, 0.7) !important;
    }
    /* Relleno de la barra del slider */
    div[data-baseweb="slider"] > div > div:first-child {
        background: linear-gradient(90deg, #0047BA 0%, #0066CC 60%, #78BE20 100%) !important;
    }
    div[data-baseweb="slider"] div[style*="rgb(255, 75, 75)"],
    div[data-baseweb="slider"] div[style*="#ff4b4b"],
    div[data-baseweb="slider"] div[style*="#FF4B4B"] {
        background-color: #0066CC !important;
    }
    /* Texto con el valor numérico activo del slider */
    div[data-testid="stSlider"] div[data-baseweb="slider"] + div,
    div[data-testid="stSlider"] div[data-baseweb="slider"] span,
    div[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stSlider"] div[role="slider"] div {
        color: #00D2FF !important;
        font-weight: 700 !important;
    }

    /* Segmented Controls (Botones de selección) */
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button[data-checked="true"],
    div[data-testid="stSegmentedControl"] [aria-pressed="true"] {
        background-color: #0066CC !important;
        color: #ffffff !important;
        border: 1.5px solid #78BE20 !important;
        box-shadow: 0 0 10px rgba(120, 190, 32, 0.4) !important;
    }
    div[data-testid="stSegmentedControl"] button:hover {
        border-color: #00D2FF !important;
        color: #00D2FF !important;
    }

    /* Toggles e Interruptores activos en Verde AMEGUA */
    div[data-testid="stCheckbox"] input:checked + div,
    div[data-testid="stToggle"] input:checked + div {
        background-color: #78BE20 !important;
    }

    /* Input focus */
    input:focus, select:focus, textarea:focus {
        border-color: #0066CC !important;
        box-shadow: 0 0 8px rgba(0, 102, 204, 0.5) !important;
    }

    /* Ajuste en móvil */
    @media (max-width: 600px) {
        .hero-amount {
            font-size: 2.1rem;
        }
        .hero-card {
            padding: 18px 14px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Encabezado compacto con Logo AMEGUA
col_logo, col_title = st.columns([1, 2.3], vertical_alignment="center")

with col_logo:
    st.image(LOGO_AMEGUA_URL, use_container_width=True)

with col_title:
    st.markdown("<h2 style='margin-bottom: 2px;'>Calculadora de Ahorro EV</h2>", unsafe_allow_html=True)
    st.markdown("<span style='color: #78BE20; font-weight: 700;'>AMEGUA</span> • <span style='opacity: 0.85;'>Asociación de Movilidad Eléctrica de Guatemala</span>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

# Pestañas principales
tab_calc, tab_modelos = st.tabs(["🧮 Calculadora de Ahorro", "📋 Consumos por Modelo (kWh/100km)"])

# ==========================================
# TAB 1: CALCULADORA DE AHORRO
# ==========================================
with tab_calc:
    st.markdown("### 1. Datos de tu viaje")

    # Preset de tipo de vehículo
    tipo_vehiculo = st.segmented_control(
        "🚗 Tipo de vehículo:",
        options=["Sedán / Compacto", "SUV / Camioneta", "Pickup / SUV Grande"],
        default="SUV / Camioneta"
    )

    # Parámetros por defecto según tipo de auto
    if tipo_vehiculo == "Sedán / Compacto":
        rendimiento_default = 40.0       # km/gal
        consumo_ev_default = 15.0        # kWh / 100 km
        precio_gas_auto_default = 150000
        precio_ev_auto_default = 195000
    elif tipo_vehiculo == "Pickup / Grande":
        rendimiento_default = 25.0       # km/gal
        consumo_ev_default = 24.5        # kWh / 100 km
        precio_gas_auto_default = 240000
        precio_ev_auto_default = 310000
    else: # SUV / Camioneta
        rendimiento_default = 32.0       # km/gal
        consumo_ev_default = 19.0        # kWh / 100 km
        precio_gas_auto_default = 190000
        precio_ev_auto_default = 240000

    st.caption(f"💡 Referencia estimada: **{consumo_ev_default} kWh / 100 km** (EV) vs. **{rendimiento_default:.0f} km/gal** (Gasolina)")

    # Kilometraje diario
    km_dia = st.slider(
        "🛣️ Kilómetros recorridos al día:", 
        min_value=10, 
        max_value=200, 
        value=45, 
        step=5,
        help="Distancia total diaria que manejas entre ida, vuelta y diligencias."
    )

    dias_al_mes = st.slider("📅 Días de uso al mes:", min_value=10, max_value=31, value=26)
    km_mes = km_dia * dias_al_mes

    # Lugar de carga
    lugar_carga = st.segmented_control(
        "⚡ ¿Dónde recargarías?",
        options=["Casa (Tarifa Central)", "Casa (Departamentos)", "Paneles Solares"],
        default="Casa (Tarifa Central)",
        help="La tarifa residencial promedio en área central (EEGSA) es aprox Q1.51/kWh. Con paneles propios baja a ~Q0.40/kWh."
    )

    if lugar_carga == "Paneles Solares":
        precio_kwh_base = 0.40
    elif lugar_carga == "Casa (Departamentos)":
        precio_kwh_base = 2.10
    else:
        precio_kwh_base = 1.51

    # --- OPCIONES AVANZADAS ---
    with st.expander("⚙️ Personalizar precios y detalles avanzados (Opcional)"):
        st.markdown("**Precios de Combustible y Electricidad**")
        col_av1, col_av2 = st.columns(2)
        with col_av1:
            precio_galon = st.number_input("Precio Gasolina / Galón (Q)", value=38.50, step=0.5)
            rendimiento_gas = st.number_input("Rendimiento Gasolina (km/gal)", value=rendimiento_default, step=1.0)
        with col_av2:
            precio_kwh = st.number_input("Precio Electricidad / kWh (Q)", value=precio_kwh_base, step=0.05)
            consumo_kwh_100km = st.number_input(
                "Consumo EV (kWh / 100 km)", 
                value=consumo_ev_default, 
                step=0.5,
                help="Consumo estándar homologado del auto eléctrico (típico: 12 a 26 kWh cada 100 km)."
            )
        
        st.markdown("**Cálculo de Retorno de Inversión (Compra del Auto)**")
        col_av3, col_av4 = st.columns(2)
        with col_av3:
            precio_auto_gas = st.number_input("Precio Auto Combustión (Q)", value=precio_gas_auto_default, step=5000)
        with col_av4:
            precio_auto_ev = st.number_input("Precio Auto Eléctrico (Q)", value=precio_ev_auto_default, step=5000)
        
        incluir_mant = st.toggle(
            "Incluir ahorro en servicios de mantenimiento", 
            value=True, 
            help="Basado en estudios de Consumer Reports y el US Department of Energy (Argonne National Lab). En Guatemala: ~Q0.12/km en gasolina (aceite, filtros, bujías, fajas, frenos) vs ~Q0.05/km en EV (sin aceite ni fajas, frenos regenerativos de larga duración). Ahorro de ~58%."
        )

    # Si no abrió las opciones avanzadas, usamos los valores automáticos
    if 'precio_galon' not in locals():
        precio_galon = 38.50
        rendimiento_gas = rendimiento_default
        precio_kwh = precio_kwh_base
        consumo_kwh_100km = consumo_ev_default
        precio_auto_gas = precio_gas_auto_default
        precio_auto_ev = precio_ev_auto_default
        incluir_mant = True

    # --- CÁLCULOS PRINCIPALES ---
    # Combustible
    galones_mes = (km_mes / rendimiento_gas) if rendimiento_gas > 0 else 0
    gasto_gas_mes = galones_mes * precio_galon

    # Electricidad (Fórmula estándar: kWh / 100 km)
    kwh_mes = (km_mes / 100.0) * consumo_kwh_100km
    gasto_ev_mes = kwh_mes * precio_kwh

    # Mantenimiento estimado (Q0.12/km en gas vs Q0.05/km en EV en GT)
    mant_gas_mes = (km_mes * 0.12) if incluir_mant else 0
    mant_ev_mes = (km_mes * 0.05) if incluir_mant else 0

    total_gas_mes = gasto_gas_mes + mant_gas_mes
    total_ev_mes = gasto_ev_mes + mant_ev_mes

    ahorro_mes = total_gas_mes - total_ev_mes
    ahorro_ano = ahorro_mes * 12
    ahorro_5_anos = ahorro_ano * 5
    porcentaje_ahorro = (ahorro_mes / total_gas_mes * 100) if total_gas_mes > 0 else 0

    # --- RESULTADOS HERO CARD (PALETA AMEGUA) ---
    st.markdown("---")
    st.markdown("### 2. Tu Ahorro Estimado")

    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-title">⚡ Ahorro Mensual Proyectado</div>
        <div class="hero-amount">Q {ahorro_mes:,.2f}</div>
        <div class="hero-subtitle">Equivale a <b>Q {ahorro_ano:,.0f} al año</b></div>
        <div><span class="badge-amegua-green">🌱 {porcentaje_ahorro:.0f}% DE REDUCCIÓN EN GASTOS</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Métricas en columnas limpias
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric(
            label="Gasto Mensual Gasolina", 
            value=f"Q {total_gas_mes:,.2f}",
            delta=f"Q {gasto_gas_mes:,.0f} comb. + Q {mant_gas_mes:,.0f} mant.",
            delta_color="off"
        )
    with m_col2:
        st.metric(
            label="Gasto Mensual Eléctrico", 
            value=f"Q {total_ev_mes:,.2f}", 
            delta=f"-{porcentaje_ahorro:.0f}% menos",
            delta_color="normal"
        )

    # --- SECCIÓN DE GRÁFICAS (GRÁFICAS DE PIE / DONUT DE ALTO IMPACTO) ---
    st.markdown("#### 🍩 ¿A dónde va tu dinero cada mes?")

    # Vista de selector de gráfico
    modo_grafica = st.segmented_control(
        "Tipo de visualización:",
        options=["Distribución del Ahorro", "Comparativa Gasolina vs EV"],
        default="Distribución del Ahorro"
    )

    if modo_grafica == "Distribución del Ahorro":
        # Gráfico Donut de Presupuesto: Muestra el Ahorro en Verde AMEGUA, Electricidad en Azul y Mant en Cyan
        fig_donut = go.Figure(data=[go.Pie(
            labels=["¡Tu Ahorro en el Bolsillo! 💰", "Gasto en Electricidad ⚡", "Mantenimiento EV 🔧"],
            values=[max(0, ahorro_mes), gasto_ev_mes, mant_ev_mes],
            hole=0.60,
            marker=dict(
                colors=['#78BE20', '#0066CC', '#00C2CB'],
                line=dict(color='#0b192c', width=2)
            ),
            textinfo='label+percent',
            textposition='outside',
            hoverinfo='label+value+percent',
            hovertemplate='<b>%{label}</b><br>Monto: Q %{value:,.2f}<br>Porcentaje: %{percent}<extra></extra>'
        )])

        fig_donut.update_layout(
            showlegend=False,
            margin=dict(t=30, b=30, l=20, r=20),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(
                text=f"<b>{porcentaje_ahorro:.0f}%</b><br><span style='font-size: 12px;'>AHORRO</span>",
                x=0.5, y=0.5,
                font_size=24,
                font_color="#78BE20",
                showarrow=False
            )]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    else:
        # Comparativa lado a lado: 2 Donut charts (Gasolina vs EV)
        fig_duo = make_subplots(
            rows=1, cols=2, 
            specs=[[{'type': 'domain'}, {'type': 'domain'}]],
            subplot_titles=[f"⛽ Gasolina (Q{total_gas_mes:,.0f}/m)", f"⚡ Eléctrico (Q{total_ev_mes:,.0f}/m)"]
        )

        fig_duo.add_trace(go.Pie(
            labels=["Combustible", "Mantenimiento"],
            values=[gasto_gas_mes, mant_gas_mes],
            name="Gasolina",
            hole=0.55,
            marker=dict(colors=['#EF4444', '#F97316']),
            textinfo='percent',
            hovertemplate='<b>%{label}</b>: Q%{value:,.2f}<extra></extra>'
        ), 1, 1)

        fig_duo.add_trace(go.Pie(
            labels=["Electricidad", "Mantenimiento EV"],
            values=[gasto_ev_mes, mant_ev_mes],
            name="Eléctrico",
            hole=0.55,
            marker=dict(colors=['#0066CC', '#78BE20']),
            textinfo='percent',
            hovertemplate='<b>%{label}</b>: Q%{value:,.2f}<extra></extra>'
        ), 1, 2)

        fig_duo.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=40, b=40, l=10, r=10),
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_duo, use_container_width=True)

    # --- RETORNO DE INVERSIÓN Y MEDIO AMBIENTE ---
    c_roi, c_eco = st.columns(2)

    with c_roi:
        with st.container(border=True):
            st.markdown("⏱️ **Recuperación de Inversión**")
            diferencia_compra = precio_auto_ev - precio_auto_gas
            if diferencia_compra <= 0:
                st.success("¡Inmediato! El auto eléctrico cuesta igual o menos.")
            elif ahorro_mes > 0:
                meses_recuperacion = diferencia_compra / ahorro_mes
                anos = int(meses_recuperacion // 12)
                meses = int(round(meses_recuperacion % 12))
                
                # Formato natural de tiempo
                if anos == 1 and meses == 1:
                    tiempo_str = "1 año y 1 mes"
                elif anos == 1:
                    tiempo_str = f"1 año y {meses} meses" if meses > 0 else "1 año"
                elif anos > 1:
                    tiempo_str = f"{anos} años y {meses} meses" if meses > 0 else f"{anos} años"
                else:
                    tiempo_str = f"{meses} meses" if meses > 1 else "1 mes"

                st.info(f"Recuperas la diferencia de **Q{diferencia_compra:,.0f}** en aprox. **{tiempo_str}** solo con el ahorro de combustible.")
            else:
                st.warning("No hay ahorro mensual proyectado.")

    with c_eco:
        with st.container(border=True):
            st.markdown("🌱 **Impacto Ecológico**")
            co2_gas = (galones_mes * 12) * 8.74
            co2_ev = (kwh_mes * 12) * 0.25
            co2_evitado = max(0, co2_gas - co2_ev)
            arboles = int(co2_evitado / 22)
            st.success(f"Evitas **{co2_evitado:,.0f} kg de CO₂** al año. Equivale a sembrar **{arboles} árboles** 🌳.")

    # --- BENEFICIOS LEY GUATEMALA (AMEGUA / DECRETO 40-2022) ---
    with st.expander("📜 Beneficios de la Ley de Movilidad Eléctrica (Decreto 40-2022)"):
        st.markdown("""
        Promovida por el ecosistema de movilidad eléctrica en Guatemala e impulsada por **AMEGUA**:
        * **Exención de IPRIMA (100%):** Cero pago de impuesto de primera matrícula.
        * **Exoneración de Impuesto de Circulación (ISCV):** 100% de descuento en los primeros años de uso.
        * **Exención del IVA de importación:** Exoneración total o parcial según año de vigencia.
        * **Placas y distintivos verdes:** Identificación oficial de vehículo cero emisiones.
        """)

    # --- FUENTES Y DESGLOSE DE MANTENIMIENTO ---
    with st.expander("🔧 Fuentes y desglose del costo de mantenimiento (Combustión vs EV)"):
        st.markdown("""
        **¿Por qué un vehículo eléctrico gasta ~58% menos en taller?**
        
        * **Vehículo a Gasolina (~Q0.12 / km):**
          * Servicios menores periódicos cada 5,000–10,000 km (aceite de motor, filtro de aceite, filtro de aire).
          * Desgaste continuo de bujías, fajas de distribución, líquido de frenos, refrigerante de motor y embrague.
          * Freno mecánico por fricción constante (cambio de pastillas cada 25,000–35,000 km).
          * *Gasto acumulado:* ~Q12,000 a Q15,000 en servicios por cada 100,000 km.
        
        * **Vehículo Eléctrico (~Q0.05 / km):**
          * **Cero piezas de desgaste crítico:** No usa aceite, filtros de motor, fajas, bujías, tubos de escape ni cajas de cambios complejas.
          * **Freno regenerativo:** El motor desacelera el vehículo y recarga la batería, haciendo que las pastillas de freno duren **entre 80,000 y 120,000 km**.
          * Solo requiere cambio de filtro de cabina (A/C), rotación de llantas y revisión periódica de refrigerante de batería.
          * *Gasto acumulado:* ~Q5,000 a Q6,000 por cada 100,000 km.

        ---
        **Fuentes y Estudios de Referencia:**
        1. **Consumer Reports (Total Cost of Ownership Study):** Determina un **50% a 60% de menor costo de mantenimiento** a lo largo de la vida útil en vehículos eléctricos vs. gasolina.
        2. **US Department of Energy (Argonne National Laboratory):** Costo de $0.061/mi en gasolina vs. $0.031/mi en eléctricos (reducción directa del 49.2%).
        3. **Talleres y Agencias de Guatemala:** Tarifas promedio de mano de obra y repuestos en el mercado local.
        """)


# ==========================================
# TAB 2: CATÁLOGO DE CONSUMOS POR MODELO
# ==========================================
with tab_modelos:
    st.markdown("### 📋 Consumos de Referencia por Modelo")
    st.caption("Valores oficiales homologados (WLTP/CLTC) y consumo real promedio con aire acondicionado y tráfico habitual.")

    # Base de datos de modelos populares
    datos_ev = [
        # Compactos y Urbanos
        {"Modelo": "BYD Seagull (Dolphin Mini)", "Marca": "BYD", "Segmento": "Compacto / Urbano", "Batería": "30 - 38 kWh", "Oficial (WLTP/CLTC)": "9.6 - 10.5", "Consumo Real": 12.0, "Costo 100km (Q)*": 18.12},
        {"Modelo": "BYD Dolphin", "Marca": "BYD", "Segmento": "Compacto / Urbano", "Batería": "45 - 60 kWh", "Oficial (WLTP/CLTC)": "15.2 - 15.9", "Consumo Real": 15.5, "Costo 100km (Q)*": 23.41},
        {"Modelo": "Volkswagen ID.3", "Marca": "Volkswagen", "Segmento": "Compacto / Urbano", "Batería": "52 - 77 kWh", "Oficial (WLTP/CLTC)": "15.1 - 16.2", "Consumo Real": 17.0, "Costo 100km (Q)*": 25.67},
        {"Modelo": "MG4 Electric", "Marca": "MG", "Segmento": "Compacto / Urbano", "Batería": "51 - 64 kWh", "Oficial (WLTP/CLTC)": "16.0 - 17.0", "Consumo Real": 17.5, "Costo 100km (Q)*": 26.43},
        {"Modelo": "Renault Kwid E-Tech", "Marca": "Renault", "Segmento": "Compacto / Urbano", "Batería": "26.8 kWh", "Oficial (WLTP/CLTC)": "10.8 - 11.5", "Consumo Real": 13.0, "Costo 100km (Q)*": 19.63},
        
        # Sedanes
        {"Modelo": "Tesla Model 3 (Highland RWD)", "Marca": "Tesla", "Segmento": "Sedán", "Batería": "60 kWh", "Oficial (WLTP/CLTC)": "13.2", "Consumo Real": 15.0, "Costo 100km (Q)*": 22.65},
        {"Modelo": "Tesla Model 3 (Long Range)", "Marca": "Tesla", "Segmento": "Sedán", "Batería": "75 kWh", "Oficial (WLTP/CLTC)": "14.0", "Consumo Real": 16.2, "Costo 100km (Q)*": 24.46},
        {"Modelo": "BYD Seal", "Marca": "BYD", "Segmento": "Sedán", "Batería": "82.5 kWh", "Oficial (WLTP/CLTC)": "16.6 - 18.2", "Consumo Real": 18.5, "Costo 100km (Q)*": 27.94},
        {"Modelo": "BMW i4 (eDrive40)", "Marca": "BMW", "Segmento": "Sedán", "Batería": "70 - 84 kWh", "Oficial (WLTP/CLTC)": "16.1 - 18.5", "Consumo Real": 19.0, "Costo 100km (Q)*": 28.69},
        
        # SUVs y Crossovers
        {"Modelo": "BYD Atto 3 (Yuan Plus)", "Marca": "BYD", "Segmento": "SUV / Crossover", "Batería": "60.4 kWh", "Oficial (WLTP/CLTC)": "15.6 - 16.0", "Consumo Real": 18.0, "Costo 100km (Q)*": 27.18},
        {"Modelo": "Volvo EX30 (Single Motor)", "Marca": "Volvo", "Segmento": "SUV / Crossover", "Batería": "51 - 69 kWh", "Oficial (WLTP/CLTC)": "16.7 - 17.5", "Consumo Real": 18.5, "Costo 100km (Q)*": 27.94},
        {"Modelo": "Tesla Model Y (RWD)", "Marca": "Tesla", "Segmento": "SUV / Crossover", "Batería": "60 kWh", "Oficial (WLTP/CLTC)": "15.7", "Consumo Real": 17.5, "Costo 100km (Q)*": 26.43},
        {"Modelo": "Maxus Euniq 6 SUV", "Marca": "Maxus", "Segmento": "SUV / Crossover", "Batería": "70 kWh", "Oficial (WLTP/CLTC)": "21.5", "Consumo Real": 23.0, "Costo 100km (Q)*": 34.73},
        {"Modelo": "Hyundai Ioniq 5", "Marca": "Hyundai", "Segmento": "SUV / Crossover", "Batería": "58 - 77 kWh", "Oficial (WLTP/CLTC)": "16.7 - 18.0", "Consumo Real": 19.0, "Costo 100km (Q)*": 28.69},
        {"Modelo": "Geely EX5 / Geometry C", "Marca": "Geely", "Segmento": "SUV / Crossover", "Batería": "53 - 70 kWh", "Oficial (WLTP/CLTC)": "16.5 - 17.5", "Consumo Real": 18.5, "Costo 100km (Q)*": 27.94},

        # Pickups y Comerciales
        {"Modelo": "Maxus T90 EV (Pickup)", "Marca": "Maxus", "Segmento": "Pickup / Comercial", "Batería": "88.5 kWh", "Oficial (WLTP/CLTC)": "26.8", "Consumo Real": 29.0, "Costo 100km (Q)*": 43.79},
        {"Modelo": "Maxus Mifa 7 / Mifa 9", "Marca": "Maxus", "Segmento": "Pickup / Comercial", "Batería": "90 kWh", "Oficial (WLTP/CLTC)": "20.5 - 21.5", "Consumo Real": 24.5, "Costo 100km (Q)*": 37.00},
        {"Modelo": "Riddara RD6 (Geely Radar)", "Marca": "Riddara / Geely", "Segmento": "Pickup / Comercial", "Batería": "63 - 86 kWh", "Oficial (WLTP/CLTC)": "19.5 - 21.5", "Consumo Real": 24.0, "Costo 100km (Q)*": 36.24},
        {"Modelo": "Ford F-150 Lightning", "Marca": "Ford", "Segmento": "Pickup / Comercial", "Batería": "98 - 131 kWh", "Oficial (WLTP/CLTC)": "29.0 - 33.0", "Consumo Real": 34.0, "Costo 100km (Q)*": 51.34}
    ]

    df_ev = pd.DataFrame(datos_ev)

    # Filtros interactivos
    filtro_col1, filtro_col2 = st.columns([1, 1])
    with filtro_col1:
        categoria_sel = st.selectbox(
            "Filtrar por categoría:", 
            ["Todos", "Compacto / Urbano", "Sedán", "SUV / Crossover", "Pickup / Comercial"]
        )
    with filtro_col2:
        busqueda = st.text_input("🔍 Buscar por nombre o marca:", placeholder="ej. Seagull, Tesla, Maxus...")

    # Aplicar filtros
    df_filtrado = df_ev.copy()
    if categoria_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Segmento"] == categoria_sel]
    if busqueda:
        df_filtrado = df_filtrado[
            df_filtrado["Modelo"].str.contains(busqueda, case=False, na=False) |
            df_filtrado["Marca"].str.contains(busqueda, case=False, na=False)
        ]

    # Mostrar tabla estilizada con encabezados en 2 filas para optimizar el ancho de columnas
    html_table = """
    <div style="overflow-x: auto; width: 100%; border-radius: 10px; border: 1px solid rgba(120, 190, 32, 0.3); margin-bottom: 12px;">
    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; text-align: left;">
        <thead>
            <tr style="background: rgba(0, 102, 204, 0.22); border-bottom: 2px solid #78BE20;">
                <th style="padding: 10px 8px; font-weight: 700;">Modelo</th>
                <th style="padding: 10px 8px; font-weight: 700;">Segmento</th>
                <th style="padding: 10px 8px; font-weight: 700; text-align: center;">Batería<br><span style="font-size: 0.72rem; font-weight: normal; opacity: 0.85;">(kWh)</span></th>
                <th style="padding: 10px 8px; font-weight: 700; text-align: center;">Oficial<br><span style="font-size: 0.72rem; font-weight: normal; opacity: 0.85;">(WLTP/CLTC)</span></th>
                <th style="padding: 10px 8px; font-weight: 700; text-align: center; color: #78BE20;">Consumo Real<br><span style="font-size: 0.72rem; font-weight: normal; opacity: 0.85;">(kWh/100km)</span></th>
                <th style="padding: 10px 8px; font-weight: 700; text-align: right;">Costo 100km<br><span style="font-size: 0.72rem; font-weight: normal; opacity: 0.85;">(Q)*</span></th>
            </tr>
        </thead>
        <tbody>
    """
    for idx, (_, row) in enumerate(df_filtrado.iterrows()):
        bg = "rgba(255,255,255,0.03)" if idx % 2 == 0 else "transparent"
        html_table += f"""
            <tr style="background: {bg}; border-bottom: 1px solid rgba(125,125,125,0.12);">
                <td style="padding: 8px 8px; font-weight: 600;">{row['Modelo']}</td>
                <td style="padding: 8px 8px; opacity: 0.9;">{row['Segmento']}</td>
                <td style="padding: 8px 8px; text-align: center;">{row['Batería']}</td>
                <td style="padding: 8px 8px; text-align: center; opacity: 0.9;">{row['Oficial (WLTP/CLTC)']}</td>
                <td style="padding: 8px 8px; text-align: center; font-weight: 700; color: #78BE20;">{row['Consumo Real']:.1f}</td>
                <td style="padding: 8px 8px; text-align: right; font-weight: 600;">Q {row['Costo 100km (Q)*']:.2f}</td>
            </tr>
        """
    html_table += """
        </tbody>
    </table>
    </div>
    """
    st.html(html_table)

    st.caption("ℹ️ *Costo estimado por cada 100 km asumiendo tarifa residencial EEGSA promedio de **Q1.51 por kWh**.*")

    # Consejos de eficiencia para Guatemala
    with st.container(border=True):
        st.markdown("💡 **Factores que influyen en el consumo en Guatemala:**")
        st.markdown("""
        * **Topografía y Subidas:** Subir hacia Carretera a El Salvador o Mixco incrementa el consumo instantáneo, pero las bajadas recuperan hasta un 30% de energía gracias al **freno regenerativo**.
        * **Tráfico Urbano:** Al contrario de los autos de gasolina que gastan mucho en el tráfico, los EV gastan **muy poca energía detenidos** (solo el aire acondicionado).
        * **Aire Acondicionado:** En clima cálido (costa / oriente) añade aprox. **1.5 a 2.5 kWh / 100 km**.
        * **Velocidad en Carretera:** A más de 90 km/h la resistencia aerodinámica aumenta el consumo entre un 15% y 25%.
        """)