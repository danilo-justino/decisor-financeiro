from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ==== CAMINHO ARQUIVOS ====
PASTA_CSV =  Path(r"Caminho Pasta\embraer\csv_tratados")
arquivo = PASTA_CSV / "base_demonstrativos_longo.csv"
aliquota_ir = 0.34
WACC = 0.14
# =====================

st.set_page_config(page_title="Decisor Financeiro ", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Carga e preparação
# ---------------------------------------------------------------------------

@st.cache_data
def carregar_base(arquivo: Path) -> pd.DataFrame:
    df = pd.read_csv(arquivo, sep=";", decimal=',', encoding="utf-8-sig",
                     dtype={"codigo": str})
    df["ano"] = df["ano"].astype(int)
    return df

def  serie(df: pd.DataFrame, codigo: str) -> pd.Series:
    """Valores de uma conta ao longo dos anos (index=ano). 0 se não existir."""
    s = (df[df["codigo"] == codigo]
         .set_index("ano")["valor"]
         .sort_index())
    if s.empty:
        anos = sorted(df["ano"].unique())
        return pd.Series(0.0, index=anos)
    return s

@st.cache_data
def montar_contas(_df: pd.DataFrame, wacc: float, aliq: float) -> dict:
    """Extrai as contas base e derivadas como Series (index=ano, crescente)."""
    bp = _df[_df["demonstrativo"] == "BP"]
    dre = _df[_df["demonstrativo"] == "DRE"]
    dfc = _df[_df["demonstrativo"] == "DFC"]

    c = {}
    # DRE
    c["receita"] = serie(dre, "3.01")
    c["cpv"] = -serie(dre, "3.02")
    c["lucro_bruto"] = serie(dre, "3.03")
    c["ebit"] = serie(dre, "3.05")
    c["desp_fin"] = -serie(dre, "3.06.02")
    c["lucro_liq"] = serie(dre, "3.11")
    c["sga"] = -(serie(dre, "3.04.01") + serie(dre, "3.04.02"))
    c["lair"] = serie(dre, "3.07")
    c["ir"] = serie(dre, "3.08")
    # DFC
    c["dep_amort"] = serie(dfc, "6.01.01.02")
    c["fco"] = serie(dfc, "6.01")
    c["fci"] = serie(dfc, "6.02")
    c["fcf_atividade"] = serie(dfc, "6.03")
    c["capex"] = - (serie(dfc, "6.02.01") + serie(dfc, "6.02.03"))
    # BP
    c["ativo_total"] = serie(bp, "1")
    c["ativo_circ"] = serie(bp, "1.01")
    c["caixa"] = serie(bp, "1.01.01")
    c["aplic_cp"] = serie(bp, "1.01.02")
    c["clientes"] = serie(bp, "1.01.03")
    c["estoques"] = serie(bp, "1.01.04")
    c["passivo_circ"] = serie(bp, "2.01")
    c["fornecedores"] = serie(bp, "2.01.02")
    c["emprest_cp"] = serie(bp, "2.01.04")
    c["passivo_nc"] = serie(bp, "2.02")
    c["emprest_lp"] = serie(bp, "2.02.01")
    c["pl"] = serie(bp, "2.03")
    c["passivo_tt"] = serie(bp, "2")
    # Derivadas
    c["aliquota"] = c["ir"]  / c["lair"]
    c["ebitda"] = c["ebit"] + c["dep_amort"]
    c["divida_bruta"] = c["emprest_cp"] + c["emprest_lp"]
    c["disponibilidades"] = c["caixa"] + c["aplic_cp"]
    c["divida_liquida"] = c["divida_bruta"] - c["disponibilidades"]
    c["nopat"] = c["ebit"] * (1 - aliq)
    c["capital_investido"] = c["pl"] + c["divida_liquida"]
    c["ccl"] = c["ativo_circ"] - c["passivo_circ"]
    c["fcl"] = c["fco"] - c["capex"]
    return c

def media(s: pd.Series) -> pd.Series:    
    """Saldo médio (ano atual + anterior)/2 — index crescente."""
    ant = s.shift(1)
    return (s + ant.fillna(s)) / 2

# formatação ---------------------------------------------------------------

def f_pct(v): return "n/d" if pd.isna(v) else f"{v*100:.1f}%".replace(".", ",")
def f_x(v):   return "n/d" if pd.isna(v) else f"{v:.2f}".replace(".", ",")
def f_d(v):   return "n/d" if pd.isna(v) else f"{v:.0f} dias"
def f_rs(v):  return "n/d" if pd.isna(v) else f"R$ {v:,.0f} mi".replace(",", ".")
def f_delta_rs(v):
    """Delta monetário SEM o prefixo 'R$': o sinal fica no início da string,
    permitindo que o st.metric pinte a seta na direção correta."""
    return None if pd.isna(v) else f"{v:+,.0f} mi".replace(",", ".")

def grafico_linha(s: pd.Series, titulo: str, formato_pct=False):
    d = s.reset_index(); d.columns = ["ano", "valor"]
    fig = px.line(d, x="ano", y="valor", markers=True, title=titulo)
    fig.update_xaxes(dtick=1)
    if formato_pct:
        fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig, use_container_width=True)

def grafico_barras(dados: dict[str, pd.Series], titulo: str):
    d = pd.DataFrame(dados).reset_index().melt(id_vars="ano", var_name="métrica", value_name="valor")
    fig = px.bar(d, x="ano", y="valor", color="métrica", barmode="group", title=titulo)
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)

def cards(itens: list[tuple], n_col=4):
    """itens: [(rótulo, valor, delta) ou (rótulo, valor, delta, delta_color), ...]
    delta_color: "normal" (subir=verde) | "inverse" (subir=vermelho) | "off" (cinza)."""
    cols = st.columns(n_col)
    for i, item in enumerate(itens):
        rotulo, valor, delta = item[0], item[1], item[2]
        cor = item[3] if len(item) > 3 else "normal"
        cols[i % n_col].metric(rotulo, valor, delta, delta_color=cor)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

df = carregar_base(arquivo)

st.sidebar.title("📊 Decisor Financeiro")
pagina = st.sidebar.radio("Navegação", [
    "🏠 Home",
    "📋 Estrutura das DFs",
    "💧 Liquidez",
    "🏦 Endividamento e Capital",
    "📈 Rentabilidade",
    "⚙️ Eficiência Operacional",
    "💵 Fluxo de Caixa",
    "🚀 Crescimento e Valor",
])
st.sidebar.divider()
wacc = st.sidebar.slider("WACC (premissa)", 0.06, 0.20, WACC, 0.005)
st.sidebar.caption(f"WACC = {wacc:.1%} | IR/CSLL = {aliquota_ir:.0%} | Valores em R$ milhões")


# ---- Filtro global de anos (multisseleção) ----
todos_anos = sorted(df["ano"].unique())
#anos_sel = st.sidebar.multiselect("📅 Anos de análise", todos_anos, default=todos_anos)
#anos_sel = sorted(anos_sel)

def filtro_anos(chave: str):
    """Multiselect de anos no topo da página.
    Retorna: df filtrado, contas, anos, ult, ant."""
    anos_sel = st.multiselect("📅 Anos de análise", todos_anos,
                              default=todos_anos, key=f"anos_{chave}")
    anos_sel = sorted(anos_sel)
    if not anos_sel:
        st.warning("Selecione pelo menos um ano.")
        st.stop()
    df_f = df[df["ano"].isin(anos_sel)]
    contas = montar_contas(df_f, wacc, aliquota_ir)
    ult_ = anos_sel[-1]
    ant_ = anos_sel[-2] if len(anos_sel) > 1 else anos_sel[-1]
    return df_f, contas, anos_sel, ult_, ant_

def filtro_ano_unico(chave: str):
    """Selectbox de UM ano no topo da página.
    Cards mostram o ano escolhido vs o ano anterior da base;
    gráficos continuam com a série completa (contexto).
    Retorna: contas (série completa), ano selecionado (ult) e anterior (ant)."""
    ano_sel = st.selectbox("📅 Ano de análise", todos_anos[::-1],
                           key=f"ano_{chave}")
    contas = montar_contas(df, wacc, aliquota_ir)
    ant_ = max([a for a in todos_anos if a < ano_sel], default=ano_sel)
    return contas, ano_sel, ant_


# ======================= 🏠 HOME =======================
if pagina == "🏠 Home":
    st.title("🏠 Resumo Executivo — Embraer S.A. (Consolidado)")

    anos = todos_anos
    c = montar_contas(df, wacc, aliquota_ir)

    ano_ref = st.selectbox("📅 Ano de referência dos cards", anos[::-1])
    ult = ano_ref
    ant = max([a for a in anos if a < ano_ref], default=ano_ref)

    st.caption(f"Cards: {ult} vs {ant} | Gráficos: {anos[0]}–{anos[-1]} | R$ milhões")

    cresc_rec = c["receita"][ult] / c["receita"][ant] - 1
    var_ll = c["lucro_liq"][ult] / c["lucro_liq"][ant] - 1
    cards([
        ("Receita", f_rs(c["receita"][ult]), f_pct(cresc_rec)),
        ("EBITDA", f_rs(c["ebitda"][ult]), f_pct(c["ebitda"][ult]/c["ebitda"][ant]-1)),
        ("Lucro Líquido", f_rs(c["lucro_liq"][ult]), f_pct(var_ll)),
        ("Dívida Líquida", f_rs(c["divida_liquida"][ult]),
         f_delta_rs(c["divida_liquida"][ult]-c["divida_liquida"][ant])),
    ])
    cards([
        ("Margem EBITDA", f_pct(c["ebitda"][ult]/c["receita"][ult]),
         f_pct(c["ebitda"][ult]/c["receita"][ult] - c["ebitda"][ant]/c["receita"][ant])),
        ("ROE", f_pct(c["lucro_liq"][ult]/media(c["pl"])[ult]), None),
        ("Liquidez Corrente", f_x(c["ativo_circ"][ult]/c["passivo_circ"][ult]), None),
        ("FCL (FCO − CAPEX)", f_rs(c["fcl"][ult]), f_delta_rs(c["fcl"][ult]-c["fcl"][ant])),
    ])

    col1, col2 = st.columns(2)
    with col1:
        grafico_barras({"Receita": c["receita"], "EBITDA": c["ebitda"],
                        "Lucro Líquido": c["lucro_liq"]}, "Resultado por ano")
    with col2:
        grafico_barras({"Dívida Bruta": c["divida_bruta"],
                        "Disponibilidades": c["disponibilidades"],
                        "Dívida Líquida": c["divida_liquida"]}, "Endividamento")

# ======================= 📋 ESTRUTURA =======================
elif pagina == "📋 Estrutura das DFs":
    st.title("📋 Estrutura das Demonstrações Financeiras")

    df_f, c, anos, ult, ant = filtro_anos("estrutura")

    col_a, col_b, col_c, col_d = st.columns([1.2, 1.2, 0.8, 0.8])
    with col_a:
        demonstrativo = st.selectbox("Demonstrativo", ["BP", "DRE", "DFC"])
    with col_b:
        nivel_max = st.slider("Nível de detalhe", 1, 5, 2)
    with col_c:
        incluir_av = st.toggle("Incluir AV", value=True)
    with col_d:
        incluir_ah = st.toggle("Incluir AH", value=len(anos) > 1,
                               disabled=len(anos) == 1)

    base = df_f[(df_f["demonstrativo"] == demonstrativo)
                & (df_f["nivel"] <= nivel_max)]
    largo = base.pivot_table(index=["codigo", "descricao"], columns="ano",
                             values="valor").reset_index()

    if incluir_av:
        base_av = {"BP": "1", "DRE": "3.01", "DFC": "6.01"}[demonstrativo]
        denominador = largo.loc[largo["codigo"] == base_av, anos].iloc[0]
        for a in anos:
            largo[f"AV {a}"] = largo[a] / denominador[a]

    if incluir_ah and len(anos) > 1:
        for a0, a1 in zip(anos[:-1], anos[1:]):
            largo[f"AH {a1}"] = largo[a1] / largo[a0].replace(0, pd.NA) - 1

    # Sequência: ano0, AV | ano1, AV, AH | ano2, AV, AH ...
    colunas = ["codigo", "descricao"]
    for i, a in enumerate(anos):
        colunas.append(a)
        if incluir_av:
            colunas.append(f"AV {a}")
        if incluir_ah and i > 0 and len(anos) > 1:
            colunas.append(f"AH {a}")
    largo = largo[colunas]

    nome_base = {"BP": "Ativo Total", "DRE": "Receita", "DFC": "FCO"}[demonstrativo]
    legenda = []
    if incluir_av:
        legenda.append(f"AV = % sobre {nome_base} do ano")
    if incluir_ah and len(anos) > 1:
        legenda.append("AH = variação sobre o ano anterior selecionado")
    if legenda:
        st.caption(" | ".join(legenda))

    st.dataframe(
        largo.style.format(
            {a: "{:,.0f}" for a in anos} |
            {col: "{:.1%}" for col in largo.columns
             if str(col).startswith(("AH", "AV"))},
            na_rep="—"),
        use_container_width=True, height=600)

    conta = st.selectbox("Evolução de uma conta", base["descricao"].unique())
    cod = base[base["descricao"] == conta]["codigo"].iloc[0]
    grafico_linha(serie(base, cod), conta)
              
# ======================= 💧 LIQUIDEZ =======================
elif pagina ==  "💧 Liquidez":
    st.title( "💧 Indicadores de Liquidez")     
    #df_f, c, anos, ult, ant = filtro_anos("liquidez")
    c, ult, ant = filtro_ano_unico("liquidez")
       
    corrente = c["ativo_circ"] / c["passivo_circ"]
    seca = (c["ativo_circ"] - c["estoques"]) / c["passivo_circ"]
    imediata = c["disponibilidades"] / c["passivo_circ"]
    geral = c["ativo_total"] / (c["passivo_circ"] + c["passivo_nc"])

    cards([
        ("Liquidez Corrente", f_x(corrente[ult]), f_x(corrente[ult]-corrente[ant]) if ult != ant else None),
        ("Liquidez Seca", f_x(seca[ult]), f_x(seca[ult]-seca[ant]) if  ult != ant else None),
        ("Liquidez Imediata", f_x(imediata[ult]), f_x(imediata[ult]-imediata[ant]) if ult != ant else None),
        ("Liquidez Geral", f_x(geral[ult]), f_x(geral[ult]-geral[ant]) if ult != ant else None),
        
    ])
    st.metric("Capital Circulante Líquido (CCL)", f_rs(c["ccl"][ult]), f_delta_rs(c["ccl"][ult]-c["ccl"][ant] if ult != ant else None))
    grafico_barras({"Corrente": corrente, "Seca": seca, "Imediata": imediata, "Geral": geral}, "Liquidez por ano")
    
    st.info("Seca << Corrente indica peso relevante de estoques no ativo circulante.")

# ======================= 🏦 ENDIVIDAMENTO =======================
elif pagina == "🏦 Endividamento e Capital":
    st.title("🏦 Endividamento e Estrutura de Capital")
    c, ult, ant = filtro_ano_unico("endividamento")

    dl_ebitda = c["divida_liquida"] / c["ebitda"]
    de = c["divida_liquida"] / c["pl"]
    debt_ratio = (c["passivo_circ"] + c["passivo_nc"]) / c["ativo_total"]
    cobertura = c["ebit"] / c["desp_fin"]

    cards([
        ("Dívida Bruta", f_rs(c["divida_bruta"][ult]), None),
        ("Dívida Líquida", f_rs(c["divida_liquida"][ult]),
         f_delta_rs(c["divida_liquida"][ult]-c["divida_liquida"][ant]) if ult != ant else None, "inverse"),
        ("Dív. Líq./EBITDA", f_x(dl_ebitda[ult]), f_x(dl_ebitda[ult]-dl_ebitda[ant]) if ult != ant else None, "inverse"),
        ("Cobertura de Juros", f_x(cobertura[ult]), f_x(cobertura[ult]-cobertura[ant]) if ult != ant else None),
    ])
    cards([
        ("Debt-to-Equity (DL/PL)", f_x(de[ult]), None),
        ("Debt Ratio (Passivo/Ativo)", f_pct(debt_ratio[ult]), None),
        ("Patrimônio Líquido", f_rs(c["pl"][ult]), None),
        ("Capital Investido", f_rs(c["capital_investido"][ult]), None),
    ])
    col1, col2 = st.columns(2)
    with col1:
        grafico_barras({"Dív. Líq./EBITDA": dl_ebitda}, "Alavancagem")
    with col2:
        grafico_linha(cobertura, "Cobertura de Juros (EBIT/Desp.Fin.)")

# ======================= 📈 RENTABILIDADE =======================
elif pagina == "📈 Rentabilidade":
    st.title("📈 Indicadores de Rentabilidade")
    c, ult, ant = filtro_ano_unico("rentabilidade")

    roe = c["lucro_liq"] / media(c["pl"])
    roa = c["lucro_liq"] / media(c["ativo_total"])
    roi = c["lucro_liq"] / media(c["capital_investido"])
    roic = c["nopat"] / media(c["capital_investido"])

    cards([
        ("ROE", f_pct(roe[ult]), f_pct(roe[ult]-roe[ant]) if ult != ant else None),
        ("ROA", f_pct(roa[ult]), f_pct(roa[ult]-roa[ant]) if ult != ant else None),
        ("ROI", f_pct(roi[ult]), f_pct(roi[ult]-roi[ant]) if ult != ant else None),
        ("ROIC", f_pct(roic[ult]), f_pct(roic[ult]-roic[ant]) if ult != ant else None),
    ])
    
    st.divider()

    st.subheader("Margens")
    mb = c["lucro_bruto"] / c["receita"] ; me = c["ebitda"] / c["receita"]
    mo = c["ebit"] / c["receita"] ; ml = c["lucro_liq"] / c["receita"]
    cards([
        ("Margem Bruta", f_pct(mb[ult]), f_pct(mb[ult]-mb[ant]) if ult != ant else None),
        ("Margem EBITDA", f_pct(me[ult]), f_pct(me[ult]-me[ant]) if ult != ant else None),
        ("Margem EBIT", f_pct(mo[ult]), f_pct(mo[ult]-mo[ant]) if ult != ant else None),
        ("Margem Líquida", f_pct(ml[ult]), f_pct(ml[ult]-ml[ant]) if ult != ant else None),
    ])

    st.divider()

    st.subheader("DuPont: ROE = Margem x Giro x Alavancagem")
    giro = c["receita"] / media(c["ativo_total"])
    alav = media(c["ativo_total"]) / media(c["pl"])
    cards([
        ("Margem Líquida", f_pct(ml[ult]), None),
        ("Giro dos Ativos", f_x(giro[ult]), None),
        ("Alavancagem", f_x(alav[ult]), None),
        ("ROE", f_pct((ml*giro*alav)[ult]), None),
    ])

    st.divider()

    grafico_barras({"ROE": roe, "ROA": roa, "ROIC": roic}, "Rentabilidade por ano")

# ======================= ⚙️ EFICIÊNCIA =======================
elif pagina == "⚙️ Eficiência Operacional":
    st.title("⚙️ Eficiência Operacional")
    c, ult, ant = filtro_ano_unico("eficiencia")

    dso = media(c["clientes"]) * 360 / c["receita"] 
    dio = media(c["estoques"]) * 360 / c["cpv"]
    dpo = media(c["fornecedores"]) *360 / c["cpv"]
    co = dso + dio
    ccc = dso + dio - dpo

    cards([
        ("DSO - Prazo Médio de Recebimento", f_d(dso[ult]), f_d(dso[ult]-dso[ant]) if ult != ant else None, "inverse"),
        ("DIO - Prazo Médio de Estocagem", f_d(dio[ult]), f_d(dio[ult]-dio[ant]) if ult != ant else None, "inverse" ),
        ("DPO - Prazo Médio de Pagamento", f_d(dpo[ult]), f_d(dpo[ult]-dpo[ant]) if ult != ant else None),
        ("CO - Ciclo Operacional", f_d(co[ult]), f_d(co[ult]-co[ant]) if ult != ant else None, "inverse"),
        ("CCC - Ciclo de Conversão de Caixa", f_d(ccc[ult]), f_d(ccc[ult]-ccc[ant]) if ult != ant else None, "inverse"),
    ])

    grafico_barras({"DSO": dso, "DIO": dio, "DPO": dpo, "CO": co, "CCC": ccc}, "Ciclo Financeiro (dias)")
    
    st.divider()

    st.subheader("Estrutura de Custos")
    cards([
        ("CPV (% Receita)", f_pct( (c["cpv"]/c["receita"])[ult]), None),
        ("SG&A (% Receita)", f_pct( (c["sga"]/c["receita"])[ult]), None),
        ("Giro dos Ativos", f_x( (c["receita"]/media(c["ativo_total"]))[ult]), None),
        ("Estoques", f_rs(c["estoques"][ult]), f_delta_rs(c["estoques"][ult]-c["estoques"][ant]) if ult != ant else None),
    ])

    grafico_barras({"CPV": c["cpv"]/c["receita"], "SG&A": c["sga"]/c["receita"]}, "Estrutura de Custos (% Receita)")

# ======================= 💵 FLUXO DE CAIXA =======================
elif pagina == "💵 Fluxo de Caixa":
    st.title("💵 Fluxo de Caixa")
    c, ult, ant = filtro_ano_unico("fluxo")

    conv = c["fco"] / c["ebitda"]
    cards([
        ("FCO - Operacional", f_rs(c["fco"][ult]), f_delta_rs(c["fco"][ult]-c["fco"][ant]) if ult != ant else None),
        ("FCI - Investimento", f_rs(c["fci"][ult]), f_rs(c["fci"][ult]-c["fci"][ant]) if ult != ant else None),
        ("FCF - Financiamento", f_rs(c["fcf_atividade"][ult]), f_rs(c["fcf_atividade"][ult]-c["fcf_atividade"][ant]) if ult != ant else None),
        ("FCL - (FCO - CAPEX)", f_rs(c["fcl"][ult]), f_delta_rs(c["fcl"][ult]-c["fcl"][ant]) if ult != ant else None),
    ])
    cards([
        ("Conversão de Caixa (FCO/EBITDA)", f_pct(conv[ult]), f_pct(conv[ult]-conv[ant]) if ult != ant else None),
        ("CAPEX", f_rs(c["capex"][ult]), None),
        ("CAPEX (% Receita)", f_pct((c["capex"]/c["receita"])[ult]), None),
        ("D&A", f_rs(c["dep_amort"][ult]), None),
    ])

    st.divider()

    grafico_barras({"FCO": c["fco"], "FCI": c["fci"], "FCF": c["fcf_atividade"], "FCL": c["fcl"]}, "Fluxo de Caixa por ano")
    
# ======================= 🚀 CRESCIMENTO E VALOR =======================
elif pagina == "🚀 Crescimento e Valor":
    st.title("🚀 Crescimento e Criação Valor")
    c, ult, ant = filtro_ano_unico("crescimento")

    cresc_rec =  c["receita"].pct_change()
    cresc_ebitda = c["ebitda"].pct_change()
    cresc_ll = c["lucro_liq"].pct_change()
    roic = c["nopat"] / media(c["capital_investido"])
    spread = roic - wacc
    eva = c["nopat"] - media(c["capital_investido"]) * wacc

    cagr = ((c["receita"][todos_anos[-1]] / c["receita"][todos_anos[0]]) ** (1 / (len(todos_anos) - 1)) - 1)

    cards([
        ("Crescimento Receita", f_pct(cresc_rec[ult]), None),
        ("Crescimento EBITDA", f_pct(cresc_ebitda[ult]), None),
        ("Crescimento Lucro Líquido", f_pct(cresc_ll[ult]), None),
        ("CAGR Receita", f_pct(cagr) if cagr is not None else "n/d", None),
    ])

    st.divider()

    cards([
        ("ROIC", f_pct(roic[ult]), None),
        ("NOPAT", f_rs(c["nopat"][ult]), None),
        (f"Spread (ROIC − WACC {wacc:.1%})", f_pct(spread[ult]), None),
        ("EVA", f_rs(eva[ult]), f_delta_rs(eva[ult]-eva[ant]) if ult != ant else None),
    ])
    
    col1, col2 = st.columns(2)
    with col1:
        grafico_barras({"Receita": cresc_rec, "EBITDA": cresc_ebitda, "Lucro Líquido": cresc_ll}, "Crescimento YoY")

    with col2:
        grafico_barras({"EVA": eva}, "EVA por ano")
    if spread[ult] < 0:
        st.warning(f"ROIC ({roic[ult]:.1%}) abaixo do WACC ({wacc:.1%}): "
                   "Destruição de valor no período.")
    else:
        st.success(f"ROIC ({roic[ult]:.1%}) acima do WACC ({wacc:.1%}): Criação de Valor." )


