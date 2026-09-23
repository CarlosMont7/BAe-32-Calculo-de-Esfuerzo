import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Planificador BAe-32", layout="centered") # 'centered' se adapta mejor a móviles que 'wide'
st.title("✈️ Planificador BAe-32")
st.markdown("<p style='color: gray;'>Módulo de Logística y Recargues</p>", unsafe_allow_html=True)

# --- CONSTANTES ---
CONSUMO_HORA_L = 466
DENSIDAD_LBS_L = 1.76
CAPACIDAD_MAX_LBS = 3200

def parse_hhmm(tiempo_str):
    match = re.match(r"^(\d{1,2}):(\d{2})$", str(tiempo_str).strip())
    if match:
        return int(match.group(1)) + (int(match.group(2)) / 60.0)
    return 0.0

# ==========================================
# FASE 1: REQUERIMIENTOS TEÓRICOS
# ==========================================
st.subheader("1. Definición de Ruta")
st.write("Ingresa los tramos y presiona **Calcular Requerimientos**.")

if 'df_ruta_base' not in st.session_state:
    st.session_state.df_ruta_base = pd.DataFrame({
        "Origen": ["SLET", "SLSV", "SLET", "SLCB"],
        "Destino": ["SLSV", "SLET", "SLCB", "SLET"],
        "ETE (HH:MM)": ["00:50", "00:50", "00:55", "00:55"]
    })

df_ingreso = st.data_editor(
    st.session_state.df_ruta_base,
    num_rows="dynamic",
    use_container_width=True
)

if st.button("Calcular Requerimientos", type="primary", use_container_width=True):
    df_fase1 = df_ingreso[df_ingreso["Origen"].str.strip() != ""].copy()
    
    df_fase1["Horas_Dec"] = df_fase1["ETE (HH:MM)"].apply(parse_hhmm)
    df_fase1["Req_L"] = df_fase1["Horas_Dec"] * CONSUMO_HORA_L
    df_fase1["Req_lbs"] = df_fase1["Req_L"] * DENSIDAD_LBS_L
    
    st.session_state.df_fase1_calculado = df_fase1
    st.session_state.fase2_activa = True

if st.session_state.get("fase2_activa", False):
    df_fase1 = st.session_state.df_fase1_calculado
    req_total_mision_L = df_fase1["Req_L"].sum()
    
    st.success(f"**Total Misión:** {req_total_mision_L:.0f} L ({req_total_mision_L * DENSIDAD_LBS_L:.0f} lbs)")
    st.markdown("---")

    # ==========================================
    # FASE 2: LOGÍSTICA EN FORMATO DE TARJETAS (MOBILE FRIENDLY)
    # ==========================================
    st.subheader("2. Logística de Recargues")
    
    remanente_inicial_mision = st.number_input(
        "Combustible Inicial en Alas (lbs):", 
        min_value=0.0, value=1200.0, step=100.0
    )
    
    rem_actual_lbs = remanente_inicial_mision
    total_recargado_L = 0.0

    # Iteración de los tramos de vuelo usando Tarjetas Contenedoras
    for i, row in df_fase1.iterrows():
        with st.container(border=True):
            st.markdown(f"### 🛫 Tramo: **{row['Origen']} ➔ {row['Destino']}**")
            
            # Fila de opciones superiores en la tarjeta
            col_a, col_b = st.columns([1, 2])
            has_jet = col_a.checkbox("¿Hay Jet-A1?", key=f"jet_{i}", value=True)
            
            rem_actual_L = rem_actual_lbs / DENSIDAD_LBS_L
            col_b.markdown(f"**Inicial:** {rem_actual_lbs:.0f} lbs / {rem_actual_L:.0f} L")
            
            req_L = row['Req_L']
            req_lbs = req_L * DENSIDAD_LBS_L
            espacio_disp_lbs = CAPACIDAD_MAX_LBS - rem_actual_lbs
            espacio_disp_L = max(0.0, espacio_disp_lbs / DENSIDAD_LBS_L)
            
            # Métricas rápidas dentro de la tarjeta
            m1, m2 = st.columns(2)
            m1.metric("Requerido para Tramo", f"{req_L:.0f} L")
            m2.metric("Espacio Máx. Disp.", f"{espacio_disp_L:.0f} L")
            
            # Input de recargue
            sugerencia_inicial = req_L if has_jet else 0.0
            if f"recargue_{i}" not in st.session_state:
                st.session_state[f"recargue_{i}"] = sugerencia_inicial
                
            if not has_jet:
                st.session_state[f"recargue_{i}"] = 0.0
                
            recargue_L = st.number_input(
                "Cantidad a Recargar (L):", 
                key=f"recargue_{i}", 
                min_value=0.0, 
                step=50.0,
                disabled=not has_jet
            )
            
            total_recargado_L += recargue_L
            recargue_lbs = recargue_L * DENSIDAD_LBS_L
            total_bordo = rem_actual_lbs + recargue_lbs
            
            # Validación y Estado dentro de la tarjeta
            if total_bordo > (CAPACIDAD_MAX_LBS + 5):
                exceso_lbs = total_bordo - CAPACIDAD_MAX_LBS
                exceso_litros = exceso_lbs / DENSIDAD_LBS_L
                st.error(f"🔴 EXCEDE. Reduce {exceso_litros:.0f} L")
                rem_actual_lbs = total_bordo - req_lbs
            elif total_bordo < req_lbs:
                faltante_lbs = req_lbs - total_bordo
                faltante_L = faltante_lbs / DENSIDAD_LBS_L
                st.error(f"🔴 FALTANTE. Carga {faltante_L:.0f} L más")
                rem_actual_lbs = 0
            else:
                rem_final_lbs = total_bordo - req_lbs
                rem_final_L = rem_final_lbs / DENSIDAD_LBS_L
                st.success(f"✅ Saldo al Aterrizar: {rem_final_lbs:.0f} lbs / {rem_final_L:.0f} L")
                rem_actual_lbs = rem_final_lbs 

    # ------------------------------------------
    # Tarjeta Final: Destino Final (Reposición)
    # ------------------------------------------
    destino_final = df_fase1.iloc[-1]['Destino']
    
    with st.container(border=True):
        st.markdown(f"### 🛬 Destino Final / Base: **{destino_final}**")
        
        col_fa, col_fb = st.columns([1, 2])
        has_jet_final = col_fa.checkbox("¿Hay Jet-A1 en Base?", key="jet_final", value=True)
        
        rem_actual_L_final = rem_actual_lbs / DENSIDAD_LBS_L
        col_fb.markdown(f"**Llegas con:** {rem_actual_lbs:.0f} lbs / {rem_actual_L_final:.0f} L")
        
        espacio_disp_lbs_final = CAPACIDAD_MAX_LBS - rem_actual_lbs
        espacio_disp_L_final = max(0.0, espacio_disp_lbs_final / DENSIDAD_LBS_L)
        st.markdown(f"**Espacio Disponible en Tanques:** {espacio_disp_L_final:.0f} L")
        
        if not has_jet_final:
            st.session_state["recargue_final"] = 0.0
            
        recargue_final_L = st.number_input(
            "Recargue Final en Base (Reposición) (L):", 
            key="recargue_final", 
            min_value=0.0,
            value=0.0, 
            step=50.0,
            disabled=not has_jet_final
        )
        
        total_recargado_L += recargue_final_L
        saldo_absoluto_lbs = rem_actual_lbs + (recargue_final_L * DENSIDAD_LBS_L)
        saldo_absoluto_L = saldo_absoluto_lbs / DENSIDAD_LBS_L
        
        combustible_pendiente_L = req_total_mision_L - total_recargado_L
        
        if saldo_absoluto_lbs > (CAPACIDAD_MAX_LBS + 5):
            exceso_lbs = saldo_absoluto_lbs - CAPACIDAD_MAX_LBS
            exceso_litros = exceso_lbs / DENSIDAD_LBS_L
            st.error(f"🔴 EXCEDE EN BASE. Reduce {exceso_litros:.0f} L")
        else:
            texto_final = f"Tanques Finales: {saldo_absoluto_lbs:.0f} lbs / {saldo_absoluto_L:.0f} L"
            if combustible_pendiente_L > 5:
                st.warning(f"⚠️ Faltan reponer {combustible_pendiente_L:.0f} L en total | {texto_final}")
            elif combustible_pendiente_L < -5:
                st.info(f"ℹ️ Excedente de {abs(combustible_pendiente_L):.0f} L | {texto_final}")
            else:
                st.success(f"🎯 ¡Combustible Cuadrado! | {texto_final}")