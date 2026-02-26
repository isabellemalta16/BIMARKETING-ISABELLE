import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="BI Marketing - Isabelle Malta", layout="wide")

# API KEY - Isabelle (Recomendação: Use st.secrets para produção)
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

# 2. CARREGAMENTO DE DADOS (Com TTL de 1 hora para atualizar 2026)
@st.cache_data(ttl=3600)
def carregar_dados():
    def limpar(df, nome_tier):
        # Padroniza colunas
        df.columns = df.columns.str.strip().str.lower()
        
        if 'tier' not in df.columns: 
            df['tier'] = nome_tier
        
        # Limpa espaços em branco nos nomes dos canais
        if 'mktchannel' in df.columns:
            df['mktchannel'] = df['mktchannel'].astype(str).str.strip()
            
        if 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['data'])
            
        # Converte métricas para números
        cols_numericas = ['investimento', 'leads', 'hotleads', 'vendas']
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df

    try:
        df2 = pd.read_csv(URL_T2)
        df3 = pd.read_csv(URL_T3)
        return pd.concat([limpar(df2, "T2"), limpar(df3, "T3")], ignore_index=True)
    except Exception as e:
        st.error(f"Erro ao ler as planilhas: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("📊 BI Marketing - Dashboard de Performance")
st.markdown("<p style='font-size: 14px; color: gray; margin-top: -15px;'>Elaborado por Isabelle Malta</p>", unsafe_allow_html=True)

try:
    df_total = carregar_dados()

    if df_total.empty:
        st.warning("Nenhum dado encontrado nas planilhas.")
    else:
        # --- SIDEBAR ---
        st.sidebar.header("🎯 Filtros")
        
        # Filtro de Ano
        df_total['ano'] = df_total['data'].dt.year
        anos_disponiveis = sorted(df_total['ano'].unique(), reverse=True)
        ano_selecionado = st.sidebar.selectbox("📅 Selecione o Ano:", anos_disponiveis)
        df_ano = df_total[df_total['ano'] == ano_selecionado]

        # Filtro de Mês
        meses_pt = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        meses_num = sorted(df_ano['data'].dt.month.unique())
        opcoes_mes = ["Todos"] + [meses_pt[m] for m in meses_num]
        mes_selecionado = st.sidebar.selectbox("📆 Selecione o Mês:", opcoes_mes)

        if mes_selecionado != "Todos":
            num_mes_sel = [k for k, v in meses_pt.items() if v == mes_selecionado][0]
            df_base_filtros = df_ano[df_ano['data'].dt.month == num_mes_sel]
        else:
            df_base_filtros = df_ano

        # Filtro de Orgânico
        considerar_organico = st.sidebar.checkbox("Considerar Orgânico?", value=True)

        # Refinar Período e Canais
        data_min, data_max = df_base_filtros['data'].min().date(), df_base_filtros['data'].max().date()
        periodo = st.sidebar.date_input("Refinar Período:", [data_min, data_max])
        tier_sel = st.sidebar.multiselect("Tier:", df_base_filtros['tier'].unique(), default=df_base_filtros['tier'].unique())
        canal_sel = st.sidebar.multiselect("Canais:", df_base_filtros['mktchannel'].unique(), default=df_base_filtros['mktchannel'].unique())

        st.sidebar.divider()
        st.sidebar.caption("Dados sincronizados com Google Sheets")

        # --- LÓGICA DE FILTRAGEM ---
        df_f = df_base_filtros.copy()
        
        # Regra do Orgânico (Busca por "organ" para pegar Orgânico ou Organico)
        if not considerar_organico:
            df_f = df_f[~df_f['mktchannel'].str.contains('organ', case=False, na=False)]

        # Filtro de Data (Segurança para range de datas)
        if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
            df_f = df_f[(df_f['data'].dt.date >= periodo[0]) & (df_f['data'].dt.date <= periodo[1])]
        
        # Filtros de Multiselect
        df_f = df_f[(df_f['tier'].isin(tier_sel)) & (df_f['mktchannel'].isin(canal_sel))]

        if not df_f.empty:
            # 1. KPIs TOTAIS
            inv, lds, hls, vds = df_f['investimento'].sum(), df_f['leads'].sum(), df_f['hotleads'].sum(), df_f['vendas'].sum()
            
            def f_moeda(v): return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            def f_qtd(v): return f"{int(v):,}".replace(',', '.')

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Investimento Total", f_moeda(inv))
            c2.metric("Total Leads", f_qtd(lds))
            c3.metric("Total Hotleads", f_qtd(hls))
            c4.metric("Total Vendas", f_qtd(vds))

            avg_cpl = inv / lds if lds > 0 else 0
            avg_cphl = inv / hls if hls > 0 else 0
            avg_cpv = inv / vds if vds > 0 else 0
            tx_conv = (vds / lds) * 100 if lds > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("CPL Médio", f_moeda(avg_cpl))
            m2.metric("CPHL Médio", f_moeda(avg_cphl))
            m3.metric("CPVenda Médio", f_moeda(avg_cpv))
            m4.metric("Taxa de Conversão", f"{tx_conv:.2f}%")

            # Funções de Gráficos
            def plot_g(df, x_col, y, title, cor):
                fig = px.bar(df, x=x_col, y=y, title=title, text_auto='.2f', height=500)
                fig.update_traces(marker_color=cor, textposition='outside', texttemplate='R$ %{y:,.2f}')
                return fig

            # 2. EVOLUÇÃO MENSAL
            st.divider()
            st.subheader("📉 Evolução Mensal de Performance")
            df_f['mes_ref'] = df_f['data'].dt.strftime('%Y-%m') # Ordenação cronológica correta
            df_m = df_f.groupby('mes_ref').agg({'investimento':'sum', 'leads':'sum', 'hotleads':'sum', 'vendas':'sum'}).reset_index().sort_values('mes_ref')
            
            # Recalcula as métricas por mês
            df_m['cpl'] = np.where(df_m['leads'] > 0, df_m['investimento'] / df_m['leads'], 0)
            df_m['cphl'] = np.where(df_m['hotleads'] > 0, df_m['investimento'] / df_m['hotleads'], 0)
            df_m['cpv'] = np.where(df_m['vendas'] > 0, df_m['investimento'] / df_m['vendas'], 0)

            st.plotly_chart(plot_g(df_m, 'mes_ref', 'cpl', "CPL por Mês", "#1E3A8A"), use_container_width=True)
            st.plotly_chart(plot_g(df_m, 'mes_ref', 'cphl', "CPHL por Mês", "#F59E0B"), use_container_width=True)
            st.plotly_chart(plot_g(df_m, 'mes_ref', 'cpv', "CPVenda por Mês", "#10B981"), use_container_width=True)

            # 3. PERFORMANCE POR CANAL
            st.divider()
            st.subheader("📊 Performance por Canal de Marketing")
            df_c = df_f.groupby('mktchannel').agg({'investimento':'sum', 'leads':'sum', 'hotleads':'sum', 'vendas':'sum'}).reset_index()
            df_c['cpl'] = np.where(df_c['leads'] > 0, df_c['investimento'] / df_c['leads'], 0)
            df_c['cphl'] = np.where(df_c['hotleads'] > 0, df_c['investimento'] / df_c['hotleads'], 0)
            df_c['cpv'] = np.where(df_c['vendas'] > 0, df_c['investimento'] / df_c['vendas'], 0)

            st.plotly_chart(plot_g(df_c.sort_values('cpl'), 'mktchannel', 'cpl', "CPL por Canal", "#1E3A8A"), use_container_width=True)

            # 4. FUNIL E IA
            st.divider()
            cf, ci = st.columns([1, 1])
            with cf:
                st.subheader("🏆 Funil de Conversão")
                st.plotly_chart(go.Figure(go.Funnel(y=["Leads", "Hotleads", "Vendas"], x=[lds, hls, vds], textinfo="value+percent initial")), use_container_width=True)
            with ci:
                st.subheader("🤖 Analista IA")
                pergunta = st.text_input("Sua dúvida estratégica sobre os dados:")
                if st.button("Gerar Análise IA"):
                    if pergunta:
                        with st.spinner('Consultando Gemini...'):
                            try:
                                model = genai.GenerativeModel('gemini-1.5-flash')
                                resumo = df_c[['mktchannel', 'investimento', 'cpl', 'cpv']].to_string()
                                response = model.generate_content(f"Dados atuais:\n{resumo}\n\nPergunta do usuário: {pergunta}")
                                st.info(response.text)
                            except:
                                st.error("Erro na análise da IA. Verifique sua chave API.")
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados.")

except Exception as e:
    st.error(f"Erro geral no Dashboard: {e}")









