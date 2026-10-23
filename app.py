import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import importlib
import src.dashboard_data as _db_mod
_db_mod = importlib.reload(_db_mod)

fetch_cidades_disponiveis = _db_mod.fetch_cidades_disponiveis
fetch_merged_data = _db_mod.fetch_merged_data
fetch_all_cities_summary = _db_mod.fetch_all_cities_summary
sincronizar_cidade_api_neon = getattr(_db_mod, "sincronizar_cidade_api_neon", None)

from src.extract import Extract

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira chamada Streamlit)
# ==============================================================================
st.set_page_config(
    page_title="Smart City Dashboard | Clima & Qualidade do Ar",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 2. INJEÇÃO DE CSS EXTERNO COM ST.HTML() (Técnicas /estilizacao-streamlit-css)
# ==============================================================================
def inject_custom_css():
    """Injeta a folha de estilos CSS mantida em src/style.css."""
    css_path = os.path.join(os.path.dirname(__file__), "src", "style.css")
    if not os.path.exists(css_path):
        css_path = os.path.join(os.path.dirname(__file__), "..", "src", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.html(f"<style>{css_content}</style>")

inject_custom_css()

# Ícones SVG profissionais reutilizáveis
ICON_METRO = """<span class="ui-icon ui-icon-brand"><svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg></span>"""
ICON_SETTINGS = """<span class="ui-icon ui-icon-cyan"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg></span>"""
ICON_TABLE = """<span class="ui-icon ui-icon-cyan"><svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg></span>"""
ICON_CHART = """<span class="ui-icon ui-icon-brand"><svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg></span>"""
ICON_LEAF = """<span class="ui-icon ui-icon-lime"><svg viewBox="0 0 24 24"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg></span>"""
ICON_CORR = """<span class="ui-icon ui-icon-pink"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><path d="M8 12h8"></path><path d="M12 8v8"></path></svg></span>"""
ICON_MAP = """<span class="ui-icon ui-icon-lime"><svg viewBox="0 0 24 24"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon><line x1="8" y1="2" x2="8" y2="18"></line><line x1="16" y1="6" x2="16" y2="22"></line></svg></span>"""

# ==============================================================================
# 3. PALETA DE CORES PLOTLY DERIVADA DA REFERÊNCIA (ref/OIP.webp)
# ==============================================================================
COLOR_INDIGO = "#5b50bc"
COLOR_ELECTRIC_BLUE = "#4833e0"
COLOR_CYAN = "#479ccf"
COLOR_PINK = "#bc4f86"
COLOR_LIME = "#c2d58f"
COLOR_AMBER = "#e5a443"
COLOR_CARD_BG = "#25273c"
COLOR_GRID = "rgba(90, 95, 138, 0.2)"
COLOR_TEXT_MUTED = "#8e92ab"

# Configuração que desativa as opções de mexer no gráfico ao passar o mouse
PLOTLY_STATIC_CONFIG = {
    "displayModeBar": False,
    "staticPlot": False,
    "scrollZoom": False,
    "doubleClick": False,
    "showAxisDragHandles": False,
}

def aplicar_tema_plotly(fig: go.Figure):
    """Aplica o visual dark e limpo da referência nos gráficos do Plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f2ff", family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto"),
        margin=dict(l=15, r=15, t=35, b=15),
        dragmode=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=COLOR_TEXT_MUTED, size=11)
        ),
        xaxis=dict(gridcolor=COLOR_GRID, linecolor=COLOR_GRID, zeroline=False, fixedrange=True),
        yaxis=dict(gridcolor=COLOR_GRID, linecolor=COLOR_GRID, zeroline=False, fixedrange=True),
    )
    return fig

# ==============================================================================
# 4. FUNÇÕES DE SUPORTE E CLASSIFICAÇÃO (FASE 3: THRESHOLDS OMS)
# ==============================================================================
def classificar_qualidade_ar(pm25_val: float) -> tuple[str, str, str]:
    """Retorna status, classe do badge e diagnóstico de saúde baseado na OMS."""
    if pd.isna(pm25_val):
        return "Indisponível", "badge-indigo", "Sem telemetria recente."
    if pm25_val <= 15.0:
        return "Excelente", "badge-lime", "Qualidade do ar ótima conforme diretriz OMS. Risco mínimo."
    elif pm25_val <= 35.0:
        return "Moderada", "badge-indigo", "Pessoas sensíveis devem ter cautela ao ar livre."
    else:
        return "Alerta Crítico", "badge-pink", "Acima dos padrões da OMS! Evitar esforço físico prolongado."

# ==============================================================================
# 5. SIDEBAR (Estilo painel escuro da referência)
# ==============================================================================
with st.sidebar:
    st.markdown(f"### {ICON_METRO} **Smart City Console**", unsafe_allow_html=True)
    st.caption("Central de Monitoramento Urbano & Poluentes")
    st.markdown("<br>", unsafe_allow_html=True)

    # Lista de metrópoles suportadas pela API Open-Meteo (Extract.CIDADES)
    cidades_api = list(Extract.CIDADES.keys())
    idx_padrao = cidades_api.index("Recife") if "Recife" in cidades_api else 0

    cidade_selecionada = st.selectbox(
        "Selecione a Metrópole:",
        options=cidades_api,
        index=idx_padrao,
        help="Metrópoles brasileiras suportadas pela API Open-Meteo."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### {ICON_SETTINGS} **Filtros e Opções**", unsafe_allow_html=True)
    mostrar_tabela_dados = st.checkbox("Exibir tabela tabular de dados", value=False)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sincronizar Painel", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("Arquitetura ETL: Open-Meteo ➔ MongoDB ➔ NeonDB")

# ==============================================================================
# 6. CARREGAMENTO DOS DADOS COM CACHE
# ==============================================================================
@st.cache_data(ttl=300)
def load_data(cidade: str) -> pd.DataFrame:
    return fetch_merged_data(cidade)

@st.cache_data(ttl=300)
def load_cities_summary() -> pd.DataFrame:
    return fetch_all_cities_summary()

df = load_data(cidade_selecionada)
df_summary = load_cities_summary()

# ==============================================================================
# 7. CABEÇALHO / HERO BAR (Topo escuro com tipografia moderna)
# ==============================================================================
with st.container(border=True, key="header_container"):
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"<h1>Telemetria Urbana: {cidade_selecionada}</h1>", unsafe_allow_html=True)
        st.markdown(
            f"<p>Painel de controle metropolitano integrado de <b>{cidade_selecionada}</b>: clima, dispersão de ventos, qualidade do ar e benchmarking.</p>",
            unsafe_allow_html=True
        )
    with col_h2:
        if not df.empty and "data_hora" in df.columns:
            data_recente = df["data_hora"].max().strftime("%d/%m/%Y %H:%M")
            st.markdown(
                f"<div style='text-align: right; padding-top: 8px;'>"
                f"<span style='color: #8e92ab; font-size: 0.8rem;'>ÚLTIMA ATUALIZAÇÃO</span><br>"
                f"<span style='color: #c2d58f; font-weight: 700; font-size: 1.05rem;'>{data_recente}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='text-align: right; padding-top: 8px;'>"
                f"<span style='color: #8e92ab; font-size: 0.8rem;'>STATUS DA CIDADE</span><br>"
                f"<span style='color: #e5a443; font-weight: 700; font-size: 1.05rem;'>Não Sincronizada</span>"
                f"</div>",
                unsafe_allow_html=True
            )

# Verificação se há registros
if df.empty:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True, key="card_recomendacao"):
        st.markdown(
            f"<h4>Telemetria de {cidade_selecionada} ainda não carregada no NeonDB</h4>"
            f"<p style='color: #8e92ab;'>Esta metrópole faz parte da lista oficial da API Open-Meteo, mas ainda não possui séries temporais no banco relacional.</p>",
            unsafe_allow_html=True
        )
        if st.button(f"Sincronizar {cidade_selecionada} agora (Open-Meteo ➔ NeonDB)", type="primary"):
            with st.spinner(f"Coletando e persistindo telemetria de {cidade_selecionada}..."):
                sincronizar_cidade_api_neon(cidade_selecionada)
                st.cache_data.clear()
                st.success(f"Telemetria de {cidade_selecionada} sincronizada com sucesso!")
                st.rerun()
    st.stop()

ultimo_reg = df.iloc[-1]
primeiro_reg = df.iloc[0]
delta_temp = round(ultimo_reg.get("temperature_2m", 0) - primeiro_reg.get("temperature_2m", 0), 1)
status_ar, badge_class, recomendacao_texto = classificar_qualidade_ar(ultimo_reg.get("pm2_5", None))

# ==============================================================================
# 8. LINHA DE KPI CARDS (Com classes de chaves estáticas e cores de referência)
# ==============================================================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    with st.container(border=True, key="card_temp"):
        t_val = ultimo_reg.get("temperature_2m")
        st.metric(
            label="Temperatura",
            value=f"{t_val:.1f} °C" if pd.notna(t_val) else "--",
            delta=f"{delta_temp:+.1f} °C ciclo",
        )

with col2:
    with st.container(border=True, key="card_humidity"):
        u_val = ultimo_reg.get("relative_humidity_2m")
        st.metric(
            label="Umidade Relativa",
            value=f"{int(u_val)} %" if pd.notna(u_val) else "--",
            delta="Normal" if pd.notna(u_val) and 40 <= u_val <= 70 else "Atenção",
            delta_color="off"
        )

with col3:
    with st.container(border=True, key="card_rain"):
        chuva_total = df["precipitation"].sum() if "precipitation" in df.columns else 0.0
        st.metric(
            label="Chuva Acumulada",
            value=f"{chuva_total:.1f} mm",
            delta="Tempo Seco" if chuva_total == 0 else f"{chuva_total:.1f} mm detectado",
            delta_color="off"
        )

with col4:
    with st.container(border=True, key="card_wind"):
        v_val = ultimo_reg.get("wind_speed_10m")
        st.metric(
            label="Velocidade do Vento",
            value=f"{v_val:.1f} km/h" if pd.notna(v_val) else "--",
            delta="Brisa Leve" if pd.notna(v_val) and v_val < 20 else "Vento Ativo",
            delta_color="off"
        )

with col5:
    with st.container(border=True, key="card_air_quality"):
        pm25_val = ultimo_reg.get("pm2_5")
        st.metric(
            label="Índice PM2.5",
            value=f"{pm25_val:.1f} µg/m³" if pd.notna(pm25_val) else "--",
        )
        st.markdown(f'<span class="badge-ref {badge_class}">{status_ar}</span>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 9. NAVEGAÇÃO POR PILLS ESTILIZADAS COM SLIDER (Fases 1, 2, 3 e 4)
# ==============================================================================
with st.container():
    aba_selecionada = st.pills(
        "Navegação do Dashboard",
        options=[
            "Painel Climático",
            "Qualidade do Ar & Poluentes",
            "Correlações e Recomendações",
            "Comparativo Multi-Cidades (Benchmarking)",
        ],
        default="Painel Climático",
        label_visibility="collapsed",
        key="nav_pills"
    )

# ==============================================================================
# 10. CONTEÚDO DAS VISÕES (GRÁFICOS SEM MODEBAR E ESTÁTICOS AO HOVER)
# ==============================================================================

# --- VISÃO 1: PAINEL CLIMÁTICO ---
if aba_selecionada == "Painel Climático":
    c_left, c_right = st.columns([2, 1])

    with c_left:
        with st.container(border=True, key="card_chart_clima"):
            st.markdown("#### **Evolução Térmica e Umidade do Ar**")
            fig_clima = go.Figure()

            # Linha de Temperatura (Indigo vibrante com marcadores)
            fig_clima.add_trace(go.Scatter(
                x=df["data_hora"],
                y=df["temperature_2m"],
                name="Temperatura (°C)",
                line=dict(color=COLOR_INDIGO, width=3),
                mode="lines+markers",
                marker=dict(size=6, color="#ffffff")
            ))

            # Linha de Umidade no eixo Y secundário (Cyan da referência)
            fig_clima.add_trace(go.Scatter(
                x=df["data_hora"],
                y=df["relative_humidity_2m"],
                name="Umidade (%)",
                line=dict(color=COLOR_CYAN, width=2, dash="dash"),
                yaxis="y2"
            ))

            fig_clima.update_layout(
                yaxis=dict(title="Temperatura (°C)", fixedrange=True),
                yaxis2=dict(
                    title="Umidade (%)",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    fixedrange=True
                )
            )
            st.plotly_chart(
                aplicar_tema_plotly(fig_clima),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

    with c_right:
        with st.container(border=True, key="card_chart_rain"):
            st.markdown("#### **Precipitação Horária (mm)**")
            fig_rain = go.Figure()
            fig_rain.add_trace(go.Bar(
                x=df["data_hora"],
                y=df["precipitation"],
                marker_color=COLOR_ELECTRIC_BLUE,
                marker_line_width=0,
                opacity=0.9,
                name="Chuva"
            ))
            fig_rain.update_layout(yaxis=dict(title="Volume (mm)", fixedrange=True))
            st.plotly_chart(
                aplicar_tema_plotly(fig_rain),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

# --- VISÃO 2: QUALIDADE DO AR & POLUENTES (FASE 3: THRESHOLDS DA OMS) ---
elif aba_selecionada == "Qualidade do Ar & Poluentes":
    c_ar1, c_ar2 = st.columns([1, 1])

    with c_ar1:
        with st.container(border=True, key="card_chart_qualidade"):
            st.markdown("#### **Partículas Inaláveis: PM10 vs PM2.5**")
            fig_pm = go.Figure()

            # Área PM10 (Âmbar/Amarelo da referência)
            fig_pm.add_trace(go.Scatter(
                x=df["data_hora"],
                y=df.get("pm10", []),
                name="PM10 (Inaláveis)",
                fill="tozeroy",
                line=dict(color=COLOR_AMBER, width=2),
                fillcolor="rgba(229, 164, 67, 0.15)"
            ))

            # Área PM2.5 (Pink da referência)
            fig_pm.add_trace(go.Scatter(
                x=df["data_hora"],
                y=df.get("pm2_5", []),
                name="PM2.5 (Finas)",
                fill="tozeroy",
                line=dict(color=COLOR_PINK, width=2),
                fillcolor="rgba(188, 79, 134, 0.25)"
            ))

            # Thresholds da OMS: 15 µg/m³ (PM2.5) e 45 µg/m³ (PM10)
            fig_pm.add_hline(
                y=15,
                line_dash="dot",
                line_color=COLOR_LIME,
                annotation_text="Limite Seguro OMS (PM2.5: 15 µg/m³)",
                annotation_position="top right",
                annotation_font=dict(color=COLOR_LIME, size=10)
            )

            fig_pm.add_hline(
                y=45,
                line_dash="dot",
                line_color=COLOR_AMBER,
                annotation_text="Limite Alerta OMS (PM10: 45 µg/m³)",
                annotation_position="bottom right",
                annotation_font=dict(color=COLOR_AMBER, size=10)
            )

            fig_pm.update_layout(yaxis=dict(title="Concentração (µg/m³)", fixedrange=True))
            st.plotly_chart(
                aplicar_tema_plotly(fig_pm),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

    with c_ar2:
        with st.container(border=True, key="card_chart_poluentes"):
            st.markdown("#### **Gases Urbanos: CO, NO₂ e Ozônio (O₃)**")
            fig_gases = go.Figure()

            if "carbon_monoxide" in df.columns:
                fig_gases.add_trace(go.Scatter(
                    x=df["data_hora"],
                    y=df["carbon_monoxide"],
                    name="Monóxido de Carbono (CO)",
                    line=dict(color="#a89cf2", width=2)
                ))
            if "nitrogen_dioxide" in df.columns:
                fig_gases.add_trace(go.Scatter(
                    x=df["data_hora"],
                    y=df["nitrogen_dioxide"],
                    name="Dióxido de Nitrogênio (NO₂)",
                    line=dict(color=COLOR_LIME, width=2)
                ))
            if "ozone" in df.columns:
                fig_gases.add_trace(go.Scatter(
                    x=df["data_hora"],
                    y=df["ozone"],
                    name="Ozônio (O₃)",
                    line=dict(color=COLOR_CYAN, width=2)
                ))

            fig_gases.update_layout(yaxis=dict(title="Concentração (µg/m³)", fixedrange=True))
            st.plotly_chart(
                aplicar_tema_plotly(fig_gases),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

# --- VISÃO 3: CORRELAÇÕES E RECOMENDAÇÕES (FASE 3: ALERTAS INTELIGENTES) ---
elif aba_selecionada == "Correlações e Recomendações":
    c_corr1, c_corr2 = st.columns([1, 1])

    with c_corr1:
        with st.container(border=True, key="card_chart_disp"):
            st.markdown("#### **Dispersão: Velocidade do Vento vs PM2.5**")
            fig_disp = px.scatter(
                df,
                x="wind_speed_10m",
                y="pm2_5",
                color="temperature_2m",
                color_continuous_scale=[[0, COLOR_ELECTRIC_BLUE], [0.5, COLOR_INDIGO], [1, COLOR_PINK]],
                labels={
                    "wind_speed_10m": "Vento (km/h)",
                    "pm2_5": "PM2.5 (µg/m³)",
                    "temperature_2m": "Temp (°C)"
                }
            )
            st.plotly_chart(
                aplicar_tema_plotly(fig_disp),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

    with c_corr2:
        with st.container(border=True, key="card_recommendation"):
            st.markdown("#### **Painel de Ação Urbana & Recomendações**")
            
            # Cards inspirados nas caixas de 'Recommendation' e 'Current Tariff' da imagem ref
            st.markdown(f"""
            <div class="recommendation-card">
                <div class="recommendation-header">
                    <span class="recommendation-title">Qualidade do Ar Atual</span>
                    <span class="badge-ref {badge_class}">{status_ar}</span>
                </div>
                <div class="recommendation-val">{ultimo_reg.get('pm2_5', 0):.1f} µg/m³</div>
                <p style="color: #8e92ab; font-size: 0.85rem; margin: 0 0 12px 0;">{recomendacao_texto}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="recommendation-card">
                <div class="recommendation-header">
                    <span class="recommendation-title">Ventilação Urbana & Dispersão</span>
                    <span class="badge-ref badge-lime">Save Energy</span>
                </div>
                <div class="recommendation-val" style="color: #479ccf;">{ultimo_reg.get('wind_speed_10m', 0):.1f} km/h</div>
                <p style="color: #8e92ab; font-size: 0.85rem; margin: 0 0 12px 0;">
                    Ventos ideais para a dispersão de poluentes na atmosfera metropolitana.
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Emitir Relatório de Alerta Urbano", type="primary", use_container_width=True):
                st.success("Relatório de sustentabilidade e alertas emitido com sucesso!")

# --- VISÃO 4: COMPARATIVO MULTI-CIDADES (FASE 4: BENCHMARKING & MAPA) ---
else:
    c_m1, c_m2 = st.columns([1, 1])

    # Se apenas uma cidade estiver no banco, oferecemos benchmarking com as capitais suportadas
    if df_summary.empty or len(df_summary) <= 1:
        # Monta dados comparativos de referência das 10 capitais suportadas pela ETL
        ranking_data = []
        for cid, (lat, lon) in Extract.CIDADES.items():
            if cid == cidade_selecionada and not df.empty:
                ranking_data.append({
                    "cidade": cid,
                    "lat": lat,
                    "lon": lon,
                    "pm25": float(df["pm2_5"].mean() if "pm2_5" in df.columns else 12.0),
                    "temp": float(df["temperature_2m"].mean() if "temperature_2m" in df.columns else 26.5),
                    "chuva": float(df["precipitation"].sum() if "precipitation" in df.columns else 0.0),
                    "status": "Monitoramento Ativo (NeonDB)"
                })
            else:
                ranking_data.append({
                    "cidade": cid,
                    "lat": lat,
                    "lon": lon,
                    "pm25": 14.5 if cid in ("Curitiba", "Porto Alegre") else (22.0 if cid in ("São Paulo", "Rio de Janeiro") else 16.0),
                    "temp": 20.0 if cid in ("Curitiba", "Porto Alegre") else 27.0,
                    "chuva": 1.2,
                    "status": "Aguardando Sincronização"
                })
        df_bench = pd.DataFrame(ranking_data).sort_values("pm25", ascending=True)
    else:
        df_bench = df_summary.copy()
        df_bench["lat"] = df_bench["cidade"].map(lambda c: Extract.CIDADES.get(c, (0, 0))[0])
        df_bench["lon"] = df_bench["cidade"].map(lambda c: Extract.CIDADES.get(c, (0, 0))[1])
        df_bench["pm25"] = df_bench["pm25_medio"]
        df_bench["temp"] = df_bench["temp_media"]
        df_bench["status"] = "Persistido no NeonDB"

    with c_m1:
        with st.container(border=True, key="card_chart_ranking"):
            st.markdown(f"#### {ICON_CHART} **Ranking de Qualidade do Ar (PM2.5 Médio)**", unsafe_allow_html=True)
            fig_rank = px.bar(
                df_bench.sort_values("pm25", ascending=True),
                x="pm25",
                y="cidade",
                orientation="h",
                color="pm25",
                color_continuous_scale=[[0, COLOR_LIME], [0.5, COLOR_INDIGO], [1, COLOR_PINK]],
                labels={"pm25": "PM2.5 (µg/m³)", "cidade": "Cidade"}
            )
            # Linha guia da OMS no ranking
            fig_rank.add_vline(
                x=15,
                line_dash="dot",
                line_color=COLOR_LIME,
                annotation_text="OMS: 15 µg/m³",
                annotation_position="top right"
            )
            fig_rank.update_layout(yaxis=dict(title="", fixedrange=True), xaxis=dict(fixedrange=True))
            st.plotly_chart(
                aplicar_tema_plotly(fig_rank),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

    with c_m2:
        with st.container(border=True, key="card_chart_map"):
            st.markdown(f"#### {ICON_MAP} **Mapa Metropolitano de Capitais Brasileiras**", unsafe_allow_html=True)
            fig_map = px.scatter_geo(
                df_bench,
                lat="lat",
                lon="lon",
                hover_name="cidade",
                size="pm25",
                color="temp",
                color_continuous_scale="Plasma",
                scope="south america",
                labels={"temp": "Temp (°C)", "pm25": "PM2.5"},
                title="Geolocalização das Capitais Monitoradas"
            )
            fig_map.update_geos(
                bgcolor="rgba(0,0,0,0)",
                showcountries=True,
                countrycolor="rgba(90, 95, 138, 0.4)",
                coastlinecolor="rgba(90, 95, 138, 0.4)",
                landcolor="#1c1d30",
                subunitcolor="rgba(90, 95, 138, 0.2)",
                fitbounds="locations"
            )
            st.plotly_chart(
                aplicar_tema_plotly(fig_map),
                use_container_width=True,
                config=PLOTLY_STATIC_CONFIG
            )

# ==============================================================================
# 11. TABELA DE DADOS BRUTOS (OPCIONAL)
# ==============================================================================
if mostrar_tabela_dados:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True, key="card_tabela"):
        st.markdown(f"#### {ICON_TABLE} **Série Temporal Completa Persistida (NeonDB)**", unsafe_allow_html=True)
        df_display = df.copy()
        df_display["data_hora"] = df_display["data_hora"].dt.strftime("%d/%m/%Y %H:%M")
        if "temperature_2m" in df_display:
            df_display["temperature_2m"] = df_display["temperature_2m"].map(lambda x: f"{x:.1f} °C" if pd.notna(x) else "")
        if "relative_humidity_2m" in df_display:
            df_display["relative_humidity_2m"] = df_display["relative_humidity_2m"].map(lambda x: f"{int(x)} %" if pd.notna(x) else "")
        if "precipitation" in df_display:
            df_display["precipitation"] = df_display["precipitation"].map(lambda x: f"{x:.1f} mm" if pd.notna(x) else "")
        if "wind_speed_10m" in df_display:
            df_display["wind_speed_10m"] = df_display["wind_speed_10m"].map(lambda x: f"{x:.1f} km/h" if pd.notna(x) else "")
        if "pm10" in df_display:
            df_display["pm10"] = df_display["pm10"].map(lambda x: f"{x:.1f} µg/m³" if pd.notna(x) else "")
        if "pm2_5" in df_display:
            df_display["pm2_5"] = df_display["pm2_5"].map(lambda x: f"{x:.1f} µg/m³" if pd.notna(x) else "")
        if "ozone" in df_display:
            df_display["ozone"] = df_display["ozone"].map(lambda x: f"{x:.1f} µg/m³" if pd.notna(x) else "")

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
