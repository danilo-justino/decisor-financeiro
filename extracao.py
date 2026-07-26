# -*- coding: utf-8 -*-
"""
Etapa 1 do projeto — Extração + Tratamento (pandas)

Extrai cada demonstrativo do PDF da DFP (padrão CVM), trata os dados com pandas
e salva um CSV por demonstrativo com:
  - colunas de período renomeadas para o ANO (ex.: "2025", "2024", "2023")
  - valores convertidos de texto BR ("1.234.567") para numérico (float)
  - Balanço Patrimonial unificado (Ativo + Passivo/PL)
  - coluna "nivel" (profundidade do plano de contas) para facilitar filtros

Uso:
    pip install pdfplumber pandas
    python extrair_demonstrativos.py
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd
import pdfplumber

# ==== AJUSTE AQUI ====
PDF_PATH = r"Caminho_Pasta\embraer\embj.pdf"
PASTA_SAIDA = r"Caminho_Pasta\embraer\csv"
FORMATO_ANO = "%Y"   # "%Y" -> "2025"  |  "%m/%Y" -> "12/2025"
# =====================

RE_LINHA = re.compile(
    r"^(\d+(?:\.\d+)*)\s+(.+?)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s*$"
)
RE_TITULO = re.compile(r"^DFs? (Individuais|Consolidadas)\s*/\s*(.+)$")
# Datas na linha abaixo dos rótulos: "Conta 31/12/2025 31/12/2024 31/12/2023"
# ou "Conta 01/01/2025 à 31/12/2025 ..."
_DATA = r"(\d{2}/\d{2}/\d{4}(?:\s*à\s*\d{2}/\d{2}/\d{4})?)"
RE_PERIODOS = re.compile(rf"Antepenúltimo Exercício\s+Conta\s+{_DATA}\s+{_DATA}\s+{_DATA}", re.S)


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^\w\s-]", "", t).strip().lower()
    return re.sub(r"[\s/]+", "_", t)


def periodo_para_ano(periodo: str) -> str:
    """'31/12/2025' ou '01/01/2025 à 31/12/2025' -> '2025' (ou '12/2025')."""
    data_final = re.findall(r"\d{2}/\d{2}/\d{4}", periodo)[-1]
    return pd.to_datetime(data_final, format="%d/%m/%Y").strftime(FORMATO_ANO)


def br_para_float(serie: pd.Series) -> pd.Series:
    """Converte texto no padrão BR ('1.234.567' / '-1.234,56') para float."""
    return pd.to_numeric(
        serie.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def extrair(pdf_path: Path) -> dict:
    """Lê o PDF e retorna {titulo: DataFrame tratado}."""
    brutos = {}       # titulo -> {"periodos": [...], "linhas": [...]}
    titulo_atual = None

    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            for ln in texto.splitlines():
                m = RE_TITULO.match(ln.strip())
                if m:
                    titulo_atual = f"{m.group(1)} - {m.group(2).strip()}"
                    brutos.setdefault(titulo_atual, {"periodos": None, "linhas": []})
                    break
            if not titulo_atual:
                continue

            bloco = brutos[titulo_atual]
            if bloco["periodos"] is None:
                m = RE_PERIODOS.search(texto)
                if m:
                    bloco["periodos"] = list(m.groups())

            for ln in texto.splitlines():
                m = RE_LINHA.match(ln.strip())
                if m:
                    bloco["linhas"].append(m.groups())

    # ---- Unifica Balanço Patrimonial (Ativo = Passivo + PL) ----
    unificados = {}
    for titulo, bloco in brutos.items():
        chave = re.sub(r"Balanço Patrimonial\s+(Ativo|Passivo)", "Balanço Patrimonial", titulo).strip()
        alvo = unificados.setdefault(chave, {"periodos": bloco["periodos"], "linhas": []})
        alvo["linhas"].extend(bloco["linhas"])
        alvo["periodos"] = alvo["periodos"] or bloco["periodos"]

    # ---- Tratamento em pandas ----
    demonstrativos = {}
    for titulo, bloco in unificados.items():
        if not bloco["linhas"]:
            continue
        anos = [periodo_para_ano(p) for p in bloco["periodos"]] if bloco["periodos"] else ["ultimo", "penultimo", "antepenultimo"]

        df = pd.DataFrame(bloco["linhas"], columns=["codigo", "descricao"] + anos)

        # valores BR -> float
        for c in anos:
            df[c] = br_para_float(df[c])

        # limpeza e enriquecimento
        df["descricao"] = df["descricao"].str.strip()
        df = df.drop_duplicates(subset="codigo", keep="first")
        df["nivel"] = df["codigo"].str.count(r"\.") + 1
        df = df[["codigo", "descricao", "nivel"] + anos].reset_index(drop=True)

        demonstrativos[titulo] = df

    return demonstrativos


def main():
    saida = Path(PASTA_SAIDA)
    saida.mkdir(parents=True, exist_ok=True)

    demonstrativos = extrair(Path(PDF_PATH))

    for titulo, df in demonstrativos.items():
        arq = saida / f"{slug(titulo)}.csv"
        df.to_csv(arq, sep=";", index=False, encoding="utf-8-sig", decimal=",")
        print(f"OK  {arq.name}  ({len(df)} contas | colunas: {list(df.columns)})")

    print(f"\nConcluído. Arquivos salvos em: {saida}")


if __name__ == "__main__":
    main()
