# -*- coding: utf-8 -*-
"""
Etapa 2 do projeto — Tratamento dos dados (pandas)

Lê os CSVs extraídos do PDF (brutos), trata, faz o pivot (formato longo)
e salva os CSVs tratados.

O que faz:
  - lê todos os CSVs da pasta de brutos (separador ";")
  - renomeia colunas de período: "Último Exercício 31/12/2025" -> "2025"
    (funciona também para "01/01/2025 à 31/12/2025")
  - converte valores do padrão BR ("1.234.567") para número
  - reduz a escala: divide por 1.000 (R$ mil -> R$ milhões)
  - padroniza nomes das colunas (codigo, descricao)
  - remove duplicados e espaços extras
  - unifica Balanço Patrimonial (Ativo + Passivo/PL), se estiverem separados
  - adiciona coluna "nivel" (profundidade do plano de contas)
  - PIVOT: converte as colunas de ano para o formato longo (ano | valor)
  - salva os CSVs tratados (largos, para conferência) e a base longa (dashboard)

"""

import re
from pathlib import Path

import pandas as pd

# ==== AJUSTE AQUI ====
PASTA_CSV = r"Caminho_Pasta\embraer\csv"
PASTA_TRATADOS = r"Caminho_Pasta\embraer\csv_tratados"
FORMATO_ANO = "%Y"   # "%Y" -> "2025"  |  "%m/%Y" -> "12/2025"
ESCALA = 1000        # divide por 1.000: R$ mil -> R$ milhões
# =====================

RE_DATA = re.compile(r"\d{2}/\d{2}/\d{4}")


# ---------------------------------------------------------------------------
# Funções de tratamento
# ---------------------------------------------------------------------------

def renomear_periodo(coluna: str) -> str:
    """'Último Exercício 31/12/2025' ou '... 01/01/2025 à 31/12/2025' -> '2025'."""
    datas = RE_DATA.findall(coluna)
    if datas:  # usa a data final do período
        return pd.to_datetime(datas[-1], format="%d/%m/%Y").strftime(FORMATO_ANO)
    return coluna


def br_para_numero(serie: pd.Series) -> pd.Series:
    """Remove separador de milhar BR ('1.234.567' -> 1234567) e converte para número."""
    return pd.to_numeric(
        serie.astype(str)
             .str.strip()
             .str.replace(".", "", regex=False)   # remove separador de milhar
             .str.replace(",", ".", regex=False), # segurança p/ eventuais decimais
        errors="coerce",
    )


def tratar_csv(arquivo: Path) -> pd.DataFrame:
    """Lê um CSV bruto e devolve o DataFrame tratado (valores em R$ milhões)."""
    df = pd.read_csv(arquivo, sep=";", encoding="utf-8-sig", dtype=str)

    # --- padroniza colunas de identificação ---
    df = df.rename(columns={
        "Codigo da Conta": "codigo",
        "Descricao da Conta": "descricao",
    })

    # --- renomeia colunas de período para o ano ---
    df = df.rename(columns={c: renomear_periodo(c) for c in df.columns})
    anos = [c for c in df.columns if c not in ("codigo", "descricao")]

    # --- valores BR -> número, reduzindo a escala (R$ mil -> R$ milhões) ---
    for c in anos:
        df[c] = (br_para_numero(df[c]) / ESCALA).round(1)

    # --- limpeza ---
    df["codigo"] = df["codigo"].str.strip()
    df["descricao"] = df["descricao"].str.strip()
    df = df.dropna(subset=["codigo"]).drop_duplicates(subset="codigo", keep="first")

    # --- enriquecimento: nível do plano de contas ---
    df["nivel"] = df["codigo"].str.count(r"\.") + 1

    return df[["codigo", "descricao", "nivel"] + anos].reset_index(drop=True)


def tratar_pasta(pasta: str | Path) -> dict[str, pd.DataFrame]:
    """Trata todos os CSVs da pasta e unifica o Balanço Patrimonial."""
    tratados = {}
    for arquivo in sorted(Path(pasta).glob("*.csv")):
        if "indicadores" in arquivo.stem or "tratado" in arquivo.stem:
            continue  # ignora saídas de outras etapas

        # Ativo e Passivo formam UM único demonstrativo (Ativo = Passivo + PL)
        chave = re.sub(r"balanco_patrimonial_(ativo|passivo)",
                       "balanco_patrimonial", arquivo.stem)

        df = tratar_csv(arquivo)

        if chave in tratados:
            tratados[chave] = (
                pd.concat([tratados[chave], df], ignore_index=True)
                  .drop_duplicates(subset="codigo", keep="first")
                  .sort_values("codigo", key=lambda s: s.map(
                      lambda x: [int(n) for n in x.split(".")]))
                  .reset_index(drop=True)
            )
        else:
            tratados[chave] = df

    return tratados


# ---------------------------------------------------------------------------
# Pivot — formato longo (tidy), ideal para Streamlit / dashboards
# ---------------------------------------------------------------------------

def para_formato_longo(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Converte os demonstrativos (formato largo: uma coluna por ano)
    para uma única base no formato longo:

        demonstrativo | codigo | descricao | nivel | ano  | valor
        ------------- | ------ | --------- | ----- | ---- | -------
        DRE           | 3.01   | Receita...| 2     | 2025 | 41883.2
        DRE           | 3.01   | Receita...| 2     | 2024 | 35424.2
    """
    bases = []
    for nome, df in dfs.items():
        anos = [c for c in df.columns if c not in ("codigo", "descricao", "nivel")]

        longo = df.melt(
            id_vars=["codigo", "descricao", "nivel"],
            value_vars=anos,
            var_name="ano",
            value_name="valor",
        )

        # nome curto do demonstrativo (bom p/ filtros no dashboard)
        if "balanco" in nome:
            longo["demonstrativo"] = "BP"
        elif "resultado" in nome:
            longo["demonstrativo"] = "DRE"
        elif "fluxo" in nome:
            longo["demonstrativo"] = "DFC"
        else:
            longo["demonstrativo"] = nome

        bases.append(longo)

    base = pd.concat(bases, ignore_index=True)
    base["ano"] = base["ano"].astype(int)   # ordenação correta em eixos/sliders
    base = base[["demonstrativo", "codigo", "descricao", "nivel", "ano", "valor"]]
    return base.sort_values(["demonstrativo", "codigo", "ano"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Salvamento
# ---------------------------------------------------------------------------

def salvar_tratados(dfs: dict[str, pd.DataFrame], pasta: str | Path) -> None:
    """Salva cada demonstrativo tratado (formato largo) em um novo CSV."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    for nome, df in dfs.items():
        arq = pasta / f"{nome}_tratado.csv"
        df.to_csv(arq, sep=";", index=False, encoding="utf-8-sig", decimal=",")
        print(f"OK  {arq.name}  ({len(df)} contas | colunas: {list(df.columns)})")


def salvar_base_longa(base: pd.DataFrame, pasta: str | Path) -> None:
    """Salva a base única no formato longo (consumo do dashboard)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    arq = pasta / "base_demonstrativos_longo.csv"
    base.to_csv(arq, sep=";", index=False, encoding="utf-8-sig", decimal=",")
    print(f"OK  {arq.name}  ({len(base)} linhas | "
          f"{base['demonstrativo'].nunique()} demonstrativos | "
          f"anos: {sorted(base['ano'].unique())})")


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Tratamento
    dfs = tratar_pasta(PASTA_CSV)

    # 2. Pivot para o formato longo
    base = para_formato_longo(dfs)

    # 3. Salvamento
    salvar_tratados(dfs, PASTA_TRATADOS)      # largos: 1 coluna por ano (conferência)
    salvar_base_longa(base, PASTA_TRATADOS)   # longo: ano/valor em linhas (dashboard)

    print(f"\nArquivos salvos em: {PASTA_TRATADOS}")
    print("\nAmostra da base longa:")
    print(base.head(9).to_string(index=False))
