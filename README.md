# decisor-financeiro
Motor de análise financeira: extração de DFPs (CVM) em PDF → tratamento em pandas → dashboard Streamlit

# 📊 Decisor Financeiro — Análise de Demonstrações Financeiras (DFP/CVM)

Pipeline completo de análise financeira: extrai demonstrativos de PDFs padronizados
da CVM (DFP), trata os dados com pandas e disponibiliza um dashboard interativo em
Streamlit com indicadores de liquidez, endividamento, rentabilidade, eficiência,
fluxo de caixa e criação de valor.

**Estudo de caso:** Embraer S.A. — DFP 31/12/2025 (consolidado, exercícios 2023–2025).

---

## 🎯 Contexto de Negócio

Analistas e gestores financeiros frequentemente recebem demonstrações financeiras
em PDF — formato ótimo para leitura, péssimo para análise. Transformar essas
informações em indicadores acionáveis costuma envolver digitação manual em
planilhas: processo lento, sujeito a erro e não reproduzível.

Este projeto resolve esse problema com um pipeline automatizado que responde
perguntas como:

- A empresa está **criando ou destruindo valor**? (ROIC vs WACC, EVA)
- A operação **gera caixa** compatível com o lucro reportado? (FCO/EBITDA, FCL)
- Qual a **saúde financeira de curto prazo**? (liquidez, capital de giro, ciclo de caixa)
- O **endividamento** é sustentável? (Dívida Líquida/EBITDA, cobertura de juros)
- De onde vem a rentabilidade? (decomposição DuPont: margem × giro × alavancagem)

## 🏗️ Arquitetura do Pipeline

  PDF (DFP/CVM) csv/ (brutos) csv_tratados/
┌──────────────┐ pdfplumber ┌──────────────┐ pandas ┌──────────────────┐
│ embj.pdf │ ─────────────► │ BP, DRE, DFC │ ─────────► │ base longa (tidy)│
└──────────────┘ etapa 1 └──────────────┘ etapa 2 └──────────────────┘
│ streamlit
▼ etapa 3
┌──────────────────┐
│ Dashboard │
└──────────────────┘

### Etapa 1 — Extração (`extrair_demonstrativos.py`)
- Lê o PDF com **pdfplumber** e identifica cada demonstrativo pelo título das páginas
- Captura código da conta, descrição e valores dos 3 exercícios via regex
- **Unifica o Balanço Patrimonial** (Ativo + Passivo/PL — afinal, Ativo = Passivo + PL)
- Gera um CSV bruto por demonstrativo

### Etapa 2 — Tratamento (`tratar_dados.py`)
- Renomeia colunas de período para o ano: `Último Exercício 31/12/2025` → `2025`
- Converte valores do padrão BR (`1.234.567`) para numérico
- Reduz a escala: R$ mil → **R$ milhões**
- Adiciona a coluna `nivel` (profundidade no plano de contas CVM)
- **Pivot para formato longo (tidy)**: `demonstrativo | codigo | descricao | nivel | ano | valor`
  — estrutura que permite filtros dinâmicos e escala para novas empresas/anos

### Etapa 3 — Dashboard (`desenvolvimento.py`)
Aplicação **Streamlit** com 8 páginas:

| Página | Conteúdo |
|---|---|
| 🏠 Home | Resumo executivo com cards (ano de referência selecionável) |
| 📋 Estrutura das DFs | Esqueleto das DFs com **Análise Vertical e Horizontal** (AV/AH), filtro de anos e nível de detalhe |
| 💧 Liquidez | Corrente, Seca, Imediata, Geral, CCL |
| 🏦 Endividamento | Dívida bruta/líquida, DL/EBITDA, cobertura de juros, debt-to-equity |
| 📈 Rentabilidade | ROE, ROA, ROI, ROIC, margens e decomposição **DuPont** |
| ⚙️ Eficiência | DSO, DIO, DPO, ciclo operacional e de conversão de caixa |
| 💵 Fluxo de Caixa | FCO/FCI/FCF, FCL, conversão de caixa, CAPEX |
| 🚀 Crescimento e Valor | Crescimento YoY, CAGR, NOPAT, **spread ROIC−WACC e EVA** |

Recursos: filtro de ano por página, WACC ajustável na sidebar (recalcula EVA em
tempo real), deltas com semântica de negócio (ex.: ciclo de caixa caindo = verde).

## 🚀 Como Executar

```bash
# 1. Clone e instale
git clone https://github.com/SEU_USUARIO/decisor-financeiro.git
cd decisor-financeiro
pip install -r requirements.txt

# 2. Ajuste os caminhos no topo de cada script (PDF_PATH, PASTA_CSV...)

# 3. Rode o pipeline na ordem
python extrair_demonstrativos.py   # PDF -> csv/
python tratar_dados.py             # csv/ -> csv_tratados/
streamlit run desenvolvimento.py   # dashboard
```

## 📐 Premissas e Decisões Técnicas

- **NOPAT** com alíquota estatutária de 34% (IR+CSLL) — em 2025 a alíquota efetiva
  é negativa (crédito fiscal), o que distorceria o indicador
- **WACC** é premissa ajustável (padrão 12%) — o dashboard permite sensibilidade
- Saldos de balanço em indicadores de retorno usam **média do período** (ano atual + anterior)/2
- Prazos (DSO/DIO/DPO) calculados com base 360 dias
- Contas mapeadas pelo **plano de contas padronizado da CVM** (ex.: `3.01` = Receita),
  o que torna o pipeline reutilizável para qualquer DFP de companhia aberta

## 🔍 Principais Insights do Caso Embraer (2023–2025)

- Receita +18% em 2025, mas **EBITDA −6%**: crescimento sem alavancagem operacional
- Resultado financeiro pressionado (cobertura de juros caiu de 2,1x para 0,9x)
  em ano de refinanciamento massivo da dívida
- Empresa virou **caixa líquido** (dívida líquida negativa) pela primeira vez na série
- Ciclo de conversão de caixa melhorou de 161 → 138 dias, mas estoques ainda
  imobilizam ~R$ 18 bi
- ROIC (~10%) próximo, porém abaixo do WACC: criação de valor ainda não sustentada

## 📁 Estrutura do Repositório
