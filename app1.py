import streamlit as st
st.title("Visor de Cuencas - CATIE 2026")
cuenca = st.selectbox("Seleccione Cuenca",["Suchiate","Maria Linda","Coyolate","Paz","Motagua"])
umbral = st.slider("Indique el umbral", 0,500,10)
st.success(f" Seleccionó {cuenca} : y umbral de {umbral} mm") 
