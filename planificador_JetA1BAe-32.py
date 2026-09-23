import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Planificador BAe-32", layout="wide")
st.title("✈️ Planificador de Vuelo - Jetstream BAe-32")

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
st.header("1. Definición de Ruta y Requerimientos")
st.write("Agrega los tramos y tiempos. Al presionar **Calcular**, se bloqueará esta tabla y se generará la logística.")

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

if st.button("Calcular Requerimientos y Pasar a Logística", type="primary"):
    df_fase1 = df_ingreso[df_ingreso["Origen"].str.strip() != ""].copy()
    
    df_fase1["Horas_Dec"] = df_fase1["ETE (HH:MM)"].apply(parse_hhmm)
    df_fase1["Req_L"] = df_fase1["Horas_Dec"] * CONSUMO_HORA_L
    df_fase1["Req_lbs"] = df_fase1["Req_L"] * DENSIDAD_LBS_L
    
    st.session_state.df_fase1_calculado = df_fase1
    st.session_state.fase2_activa = True

if st.session_state.get("fase2_activa", False):
    df_fase1 = st.session_state.df_fase1_calculado
    req_total_mision_L = df_fase1["Req_L"].sum()
    
    st.success(f"**Total Requerido para la Misión:** {req_total_mision_L:.0f} Litros ({req_total_mision_L * DENSIDAD_LBS_L:.0f} lbs)")
    st.markdown("---")

    # ==========================================
    # FASE 2: CUADRO LOGÍSTICO Y RECARGUES
    # ==========================================
    st.header("2. Logística de Recargues por Tramo")
    
    remanente_inicial_mision = st.number_input(
        "Combustible Inicial en Alas antes de iniciar la misión (lbs):", 
        min_value=0.0, value=1200.0, step=100.0
    )
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns([0.7, 1.1, 1.6, 1.1, 1.4, 1.3, 3.2])
    c1.markdown("**Jet-A1?**")
    c2.markdown("**Aeródromo**")
    c3.markdown("**Inicial (lbs / L)**")
    c4.markdown("**Req (L)**")
    c5.markdown("**Espacio Disp (L)**")
    c6.markdown("**Recargue (L)**")
    c7.markdown("**Estado / Saldo (lbs / L)**")
    
    rem_actual_lbs = remanente_inicial_mision
    total_recargado_L = 0.0

    for i, row in df_fase1.iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([0.7, 1.1, 1.6, 1.1, 1.4, 1.3, 3.2])
        
        has_jet = c1.checkbox("", key=f"jet_{i}", value=True)
        c2.markdown(f"<div style='padding-top:10px;'>{row['Origen']}</div>", unsafe_allow_html=True)
        
        rem_actual_L = rem_actual_lbs / DENSIDAD_LBS_L
        c3.markdown(f"<div style='padding-top:10px; color:gray;'>{rem_actual_lbs:.0f} lbs / {rem_actual_L:.0f} L</div>", unsafe_allow_html=True)
        
        req_L = row['Req_L']
        req_lbs = req_L * DENSIDAD_LBS_L
        c4.markdown(f"<div style='padding-top:10px; color:gray;'>{req_L:.0f} L</div>", unsafe_allow_html=True)
        
        espacio_disp_lbs = CAPACIDAD_MAX_LBS - rem_actual_lbs
        espacio_disp_L = max(0.0, espacio_disp_lbs / DENSIDAD_LBS_L)
        c5.markdown(f"<div style='padding-top:10px; color:#1f77b4; font-weight:bold;'>Max: {espacio_disp_L:.0f} L</div>", unsafe_allow_html=True)
        
        sugerencia_inicial = req_L if has_jet else 0.0
        if f"recargue_{i}" not in st.session_state:
            st.session_state[f"recargue_{i}"] = sugerencia_inicial
            
        if not has_jet:
            st.session_state[f"recargue_{i}"] = 0.0
            
        recargue_L = c6.number_input(
            "Recargue", 
            key=f"recargue_{i}", 
            min_value=0.0, 
            step=50.0, 
            label_visibility="collapsed",
            disabled=not has_jet
        )
        
        total_recargado_L += recargue_L
        recargue_lbs = recargue_L * DENSIDAD_LBS_L
        total_bordo = rem_actual_lbs + recargue_lbs
        
        if total_bordo > (CAPACIDAD_MAX_LBS + 5):
            exceso_lbs = total_bordo - CAPACIDAD_MAX_LBS
            exceso_litros = exceso_lbs / DENSIDAD_LBS_L
            c7.error(f"🔴 EXCEDE. Reduce {exceso_litros:.0f} L")
            rem_actual_lbs = total_bordo - req_lbs
        elif total_bordo < req_lbs:
            # Nuevo cálculo para indicar la cantidad exacta que falta
            faltante_lbs = req_lbs - total_bordo
            faltante_L = faltante_lbs / DENSIDAD_LBS_L
            c7.error(f"🔴 FALTANTE. Carga {faltante_L:.0f} L más")
            rem_actual_lbs = 0
        else:
            rem_final_lbs = total_bordo - req_lbs
            rem_final_L = rem_final_lbs / DENSIDAD_LBS_L
            c7.success(f"✅ Final: {rem_final_lbs:.0f} lbs / {rem_final_L:.0f} L")
            rem_actual_lbs = rem_final_lbs 

    # ------------------------------------------
    # Fila extra: Destino Final (Reposición)
    # ------------------------------------------
    st.markdown("---")
    destino_final = df_fase1.iloc[-1]['Destino']
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns([0.7, 1.1, 1.6, 1.1, 1.4, 1.3, 3.2])
    
    has_jet_final = c1.checkbox("", key="jet_final", value=True)
    c2.markdown(f"<div style='padding-top:10px;'><b>{destino_final} (Base)</b></div>", unsafe_allow_html=True)
    
    rem_actual_L_final = rem_actual_lbs / DENSIDAD_LBS_L
    c3.markdown(f"<div style='padding-top:10px; color:gray;'>{rem_actual_lbs:.0f} lbs / {rem_actual_L_final:.0f} L</div>", unsafe_allow_html=True)
    c4.markdown(f"<div style='padding-top:10px; color:gray;'>0 L</div>", unsafe_allow_html=True)
    
    espacio_disp_lbs_final = CAPACIDAD_MAX_LBS - rem_actual_lbs
    espacio_disp_L_final = max(0.0, espacio_disp_lbs_final / DENSIDAD_LBS_L)
    c5.markdown(f"<div style='padding-top:10px; color:#1f77b4; font-weight:bold;'>Max: {espacio_disp_L_final:.0f} L</div>", unsafe_allow_html=True)
    
    if not has_jet_final:
        st.session_state["recargue_final"] = 0.0
        
    recargue_final_L = c6.number_input(
        "Recargue Final", 
        key="recargue_final", 
        min_value=0.0,
        value=0.0, 
        step=50.0, 
        label_visibility="collapsed",
        disabled=not has_jet_final
    )
    
    total_recargado_L += recargue_final_L
    saldo_absoluto_lbs = rem_actual_lbs + (recargue_final_L * DENSIDAD_LBS_L)
    saldo_absoluto_L = saldo_absoluto_lbs / DENSIDAD_LBS_L
    
    combustible_pendiente_L = req_total_mision_L - total_recargado_L
    
    if saldo_absoluto_lbs > (CAPACIDAD_MAX_LBS + 5):
        exceso_lbs = saldo_absoluto_lbs - CAPACIDAD_MAX_LBS
        exceso_litros = exceso_lbs / DENSIDAD_LBS_L
        c7.error(f"🔴 EXCEDE. Reduce {exceso_litros:.0f} L")
    else:
        texto_final = f"Final: {saldo_absoluto_lbs:.0f} lbs / {saldo_absoluto_L:.0f} L"
        if combustible_pendiente_L > 5:
            c7.warning(f"⚠️ Faltan {combustible_pendiente_L:.0f} L | {texto_final}")
        elif combustible_pendiente_L < -5:
            c7.info(f"ℹ️ Sobran {abs(combustible_pendiente_L):.0f} L | {texto_final}")
        else:
            c7.success(f"🎯 Cuadrado | {texto_final}")
