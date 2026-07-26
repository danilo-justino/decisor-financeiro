# -*- coding: utf-8 -*-
"""
Extrai dados de DFP (Demonstrações Financeiras Padronizadas) em PDF para CSV.

O PDF (Print to PDF) não tem camada de texto utilizável, então a extração
é feita por OCR (Tesseract) com renderização via PyMuPDF.

Saída: dados/dfp_extraido.csv
Colunas: demonstrativo, codigo, descricao, ultimo, penultimo, antepenultimo
(valores em R$ mil; ultimo=2025, penultimo=2024, antepenultimo=2023)
"""
import argparse
import io
import os
import re

import fitz  # pymupdf
import pandas as pd
import pytesseract
from PIL import Image

# Ajuste se necessário (instalação padrão no Windows):
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ---------------------------------------------------------------- OCR

def ocr_pagina(page, dpi=300, lang="por"):
    """Renderiza a página, corrige a rotação (conteúdo em paisagem) e faz OCR."""
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    img = img.rotate(-90, expand=True).convert("L")
    return pytesseract.image_to_string(img, lang=lang, config="--psm 6")


def detectar_demonstrativo(texto):
    t = texto.lower()
    if "patrimonial ativo" in t:
        return "BP_Ativo"
    if "passivo" in t[:600]:
        return "BP_Passivo"
    if "resultado" in t[:600] and "fluxo" not in t[:600]:
        return "DRE"
    if "fluxo de caixa" in t[:600]:
        return "DFC"
    return None

# ---------------------------------------------------------------- Parser

RE_CODIGO = re.compile(r"^\d(\.\d{2,})*$")
RE_VALOR = re.compile(r"^[~\-—–+]?\d{1,3}([.,]{1,2}\d{3})*[.,]?$")


def limpar_valor(tok):
    """'-34,.524.890' -> -34524890 ; '~1.022.541' -> -1022541 ; '64.395,' -> 64395"""
    neg = tok[0] in "~-—–"
    dig = re.sub(r"\D", "", tok)
    if not dig:
        return None
    return -int(dig) if neg else int(dig)


def parse_linha(linha):
    """Linha esperada: CODIGO DESCRICAO VALOR VALOR VALOR"""
    toks = linha.split()
    if len(toks) < 5:
        return None
    codigo = toks[0]
    if not RE_CODIGO.match(codigo):
        return None
    vals = toks[-3:]
    if not all(RE_VALOR.match(v) for v in vals):
        return None
    descricao = " ".join(toks[1:-3])
    if not descricao:
        return None
    valores = [limpar_valor(v) for v in vals]
    if any(v is None for v in valores):
        return None
    return codigo, descricao, *valores


def parse_texto(texto, demonstrativo):
    registros = []
    for linha in texto.splitlines():
        r = parse_linha(linha.strip())
        if r:
            registros.append((demonstrativo, *r))
    return registros

# ---------------------------------------------------------------- Main

def extrair(pdf_path, dpi=300, lang="por", saida="dados/dfp_extraido.csv"):
    doc = fitz.open(pdf_path)
    registros = []
    demonstrativo_atual = None
    for i, page in enumerate(doc, 1):
        print(f"OCR página {i}/{len(doc)}...")
        try:
            texto = ocr_pagina(page, dpi=dpi, lang=lang)
        except pytesseract.TesseractError:
            print(f"Idioma '{lang}' indisponível; usando 'eng'.")
            lang = "eng"
            texto = ocr_pagina(page, dpi=dpi, lang=lang)
        demonstrativo_atual = detectar_demonstrativo(texto) or demonstrativo_atual
        registros += parse_texto(texto, demonstrativo_atual or f"pagina_{i}")

    df = pd.DataFrame(
        registros,
        columns=["demonstrativo", "codigo", "descricao", "ultimo", "penultimo", "antepenultimo"],
    )
    df = df.drop_duplicates(subset=["demonstrativo", "codigo"], keep="first").reset_index(drop=True)

    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
    df.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n{len(df)} contas extraídas -> {saida}")
    print(df.groupby("demonstrativo").size())
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="Caminho do PDF da DFP")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--lang", default="por", help="Idioma do Tesseract (por/eng)")
    ap.add_argument("--saida", default="dados/dfp_extraido.csv")
    args = ap.parse_args()
    extrair(args.pdf, args.dpi, args.lang, args.saida)
