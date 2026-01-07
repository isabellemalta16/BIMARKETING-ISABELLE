import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="BI Marketing - Isabelle Malta", layout="wide")

# API KEY - Isabelle
GOOGLE_API_KEY = "AIzaSyCWN90RJQox7ZQ4vj-n6lBxaT067fh4Jgc"
genai.configure(api_key=GOOGLE_API_KEY)

URL_BASE = "https://docs.google.com/spreadsheets/d/1oR-dRsIhAcB27SXftA3WsOqesGamCr4eTLVjZSZDu9I/gviz/tq?tqx=out:csv&sheet="
URL_T2 = URL_BASE + "T2"
URL_T3 = URL_BASE + "T3"

# Estilos Visuais
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #f0f2f6; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def carregar_dados():
    def limpar(df, nome_tier):
        df.columns = df.columns.str.strip().str.lower()
        if 'tier' not in df.columns: df['tier'] = nome_tier
        if 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['data'])
        for col in ['investimento', 'leads', 'hotleads', 'vendas']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    df2 = pd.read_csv(URL_T2)
    df3 = pd.read_csv(URL_T3)
    return pd.concat([limpar(df2, "T2"), limpar(df3, "T3")], ignore_index=True)

st.title("📊 BI Marketing - Dashboard de Performance")
st.markdown("##### *Elaborado por Isabelle Malta*")

try:
    df_total = carregar_dados()

    # --- SIDEBAR ---
    st.sidebar.header("🎯 Filtros")
    periodo = st.sidebar.date_input("Período:", [df_total['data'].min().date(), df_total['data'].max().date()])
    tier_sel = st.sidebar.multiselect("Tier:", df_total['tier'].unique(), default=df_total['tier'].unique())
    canal_sel = st.sidebar.multiselect("Canais:", df_total['mktchannel'].unique(), default=df_total['mktchannel'].unique())
    # NOTA DE ATUALIZAÇÃO
    st.sidebar.divider()
    st.sidebar.markdown("📅 **Status dos Dados:**")
    st.sidebar.caption("Atualizado com base em **infoleads** e **investimento agências** em 02/01/2026")
    df_f = df_total.copy()
    if isinstance(periodo, list) and len(periodo) == 2:
        df_f = df_f[(df_f['data'].dt.date >= periodo[0]) & (df_f['data'].dt.date <= periodo[1])]
    df_f = df_f[(df_f['tier'].isin(tier_sel)) & (df_f['mktchannel'].isin(canal_sel))]

    if not df_f.empty:
        # 1. KPIs TOTAIS (Bullets)
        inv, lds, hls, vds = df_f['investimento'].sum(), df_f['leads'].sum(), df_f['hotleads'].sum(), df_f['vendas'].sum()
        def f_moeda(v): return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        def f_qtd(v): return f"{int(v):,}".replace(',', '.')

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Investimento Total", f_moeda(inv))
        c2.metric("Total Leads", f_qtd(lds))
        c3.metric("Total Hotleads", f_qtd(hls))
        c4.metric("Total Vendas", f_qtd(vds))

        # Funções para os gráficos gigantes
        def plot_g(df, x_col, y, title, cor):
            fig = px.bar(df, x=x_col, y=y, title=title, text_auto='.2f', height=550)
            fig.update_traces(marker_color=cor, textposition='outside', texttemplate='R$ %{y:,.2f}')
            return fig

        # 2. EVOLUÇÃO MENSAL
        st.divider()
        st.subheader("📉 Evolução Mensal de Performance")
        df_f['mes_ref'] = df_f['data'].dt.strftime('%m-%b/%y')
        df_m = df_f.groupby('mes_ref').agg({'investimento':'sum', 'leads':'sum', 'hotleads':'sum', 'vendas':'sum'}).reset_index().sort_values('mes_ref')
        df_m['cpl'] = np.where(df_m['leads'] > 0, df_m['investimento'] / df_m['leads'], 0)
        df_m['cphl'] = np.where(df_m['hotleads'] > 0, df_m['investimento'] / df_m['hotleads'], 0)
        df_m['cpv'] = np.where(df_m['vendas'] > 0, df_m['investimento'] / df_m['vendas'], 0)

        st.plotly_chart(plot_g(df_m, 'mes_ref', 'cpl', "CPL Total por Mês", "#1E3A8A"), use_container_width=True)
        st.plotly_chart(plot_g(df_m, 'mes_ref', 'cphl', "CPHL Total por Mês", "#F59E0B"), use_container_width=True)
        st.plotly_chart(plot_g(df_m, 'mes_ref', 'cpv', "CPVenda Total por Mês", "#10B981"), use_container_width=True)

        # 3. PERFORMANCE POR CANAL
        st.divider()
        st.subheader("📊 Performance por Canal de Marketing")
        df_c = df_f.groupby('mktchannel').agg({'investimento':'sum', 'leads':'sum', 'hotleads':'sum', 'vendas':'sum'}).reset_index()
        df_c['cpl'] = np.where(df_c['leads'] > 0, df_c['investimento'] / df_c['leads'], 0)
        df_c['cphl'] = np.where(df_c['hotleads'] > 0, df_c['investimento'] / df_c['hotleads'], 0)
        df_c['cpv'] = np.where(df_c['vendas'] > 0, df_c['investimento'] / df_c['vendas'], 0)

        st.plotly_chart(plot_g(df_c.sort_values('cpl'), 'mktchannel', 'cpl', "CPL por Canal", "#1E3A8A"), use_container_width=True)
        st.plotly_chart(plot_g(df_c.sort_values('cphl'), 'mktchannel', 'cphl', "CPHL por Canal", "#F59E0B"), use_container_width=True)
        st.plotly_chart(plot_g(df_c.sort_values('cpv'), 'mktchannel', 'cpv', "CPVenda por Canal", "#10B981"), use_container_width=True)

        # 4. FUNIL E IA
        st.divider()
        cf, ci = st.columns([1, 1])
        with cf:
            st.subheader("🏆 Funil de Conversão")
            st.plotly_chart(go.Figure(go.Funnel(y=["Leads", "Hotleads", "Vendas"], x=[lds, hls, vds], textinfo="value+percent initial")), use_container_width=True)
        
        with ci:
            st.subheader("🤖 Analista IA")
            pergunta = st.text_input("Sua dúvida estratégica:")
            if st.button("Gerar Análise IA"):
                if pergunta:
                    with st.spinner('Consultando Gemini...'):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            # Enviamos o resumo por canal para ela analisar melhor
                            resumo = df_c[['mktchannel', 'investimento', 'cphl', 'cpv']].to_string()
                            response = model.generate_content(f"Dados:\n{resumo}\n\nPergunta: {pergunta}")
                            st.info(response.text)
                        except:
                            st.error("Limite de uso atingido. Tente novamente em 60 segundos.")

except Exception as e:
    st.error(f"Erro no Dash: {e}")
