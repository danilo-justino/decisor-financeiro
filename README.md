# decisor-financeiro
Motor de análise financeira: extração de DFPs (CVM) em PDF → tratamento em pandas → dashboard Streamlit

# 📊 Decisor Financeiro

Pipeline de análise financeira que automatiza a extração de Demonstrações Financeiras Padronizadas (DFPs) da CVM em PDF, realiza o tratamento dos dados com Pandas e disponibiliza um dashboard interativo em Streamlit para análise de liquidez, rentabilidade, endividamento, eficiência operacional, fluxo de caixa e criação de valor.

> **Estudo de caso:** Embraer S.A. — DFP Consolidada (31/12/2025), utilizando os exercícios de 2023, 2024 e 2025.

---

## 📷 Dashboard

### Home

> <img width="1891" height="905" alt="image" src="https://github.com/user-attachments/assets/5e0ce9d3-1f12-4833-9dd5-bd71555214ed" />

### Estrutura das DFs

> <img width="1528" height="835" alt="image" src="https://github.com/user-attachments/assets/7b0a925c-04d1-4dd6-ae10-8f8ba0717c52" />

### Crescimento e Valor

> <img width="1597" height="882" alt="image" src="https://github.com/user-attachments/assets/3fdc277e-27e9-418a-bc1a-4863eafe8e0b" />





## 🚀 Tecnologias

- Python
- Pandas
- Streamlit
- Plotly
- pdfplumber
- Regex
- NumPy

---

## 🎯 Contexto de Negócio

Analistas financeiros frequentemente recebem demonstrações financeiras em PDF — formato excelente para leitura, mas inadequado para análises quantitativas.

Transformar essas informações em indicadores normalmente exige copiar dados manualmente para planilhas, tornando o processo lento, sujeito a erros e pouco reproduzível.

Este projeto automatiza todo esse fluxo, permitindo responder perguntas como:

- A empresa está criando ou destruindo valor? *(ROIC × WACC, EVA)*
- O lucro é convertido em caixa? *(FCO, FCL e Conversão de Caixa)*
- Como está a liquidez de curto prazo?
- O nível de endividamento é sustentável?
- A rentabilidade decorre de margem, eficiência ou alavancagem? *(DuPont)*

---

# 🏗 Arquitetura do Pipeline

```text
PDF (DFP/CVM)                     CSV Bruto                   CSV Tratado

┌──────────────┐
│ embj.pdf     │
└──────┬───────┘
       │
       │ pdfplumber
       ▼
┌─────────────────────┐
│ BP • DRE • DFC      │
└──────┬──────────────┘
       │
       │ pandas
       ▼
┌─────────────────────┐
│ Base Longa (Tidy)   │
└──────┬──────────────┘
       │
       │ Streamlit
       ▼
┌─────────────────────┐
│ Dashboard           │
└─────────────────────┘
```

---

# ⚙ Pipeline

## Etapa 1 — Extração (`extrair_demonstrativos.py`)

- Leitura dos PDFs utilizando **pdfplumber**
- Identificação automática dos demonstrativos
- Extração de:
  - Código da conta
  - Descrição
  - Valores dos três exercícios
- Unificação do Ativo e Passivo/Patrimônio Líquido em um único Balanço Patrimonial
- Geração dos CSVs brutos

---

## Etapa 2 — Tratamento (`tratar_dados.py`)

- Padronização dos nomes dos períodos
- Conversão do padrão brasileiro de números para formato numérico
- Conversão de R$ mil para R$ milhões
- Inclusão do nível hierárquico das contas
- Transformação para formato **Long (Tidy Data)**

Estrutura final:

| Demonstrativo | Código | Descrição | Nível | Ano | Valor |
|--------------|---------|-----------|-------|-----|-------|

Esse formato facilita filtros, agregações e visualizações dinâmicas.

---

## Etapa 3 — Dashboard (`desenvolvimento.py`)

Aplicação desenvolvida em **Streamlit** contendo oito módulos analíticos.

| Página | Conteúdo |
|---------|----------|
| 🏠 Home | Resumo executivo |
| 📋 Estrutura das DFs | AV/AH e detalhamento das contas |
| 💧 Liquidez | Liquidez Corrente, Seca, Geral, Imediata e Capital de Giro |
| 🏦 Endividamento | Dívida Bruta, Dívida Líquida, Cobertura de Juros, DL/EBITDA |
| 📈 Rentabilidade | ROE, ROA, ROIC, ROI, Margens e DuPont |
| ⚙ Eficiência | DSO, DIO, DPO e Ciclo de Caixa |
| 💵 Fluxo de Caixa | FCO, FCI, FCF, FCL e Conversão de Caixa |
| 🚀 Crescimento e Valor | CAGR, NOPAT, EVA e Spread ROIC − WACC |

### Recursos do Dashboard

- Seleção dinâmica do ano
- WACC ajustável
- Recalculo automático do EVA
- Indicadores com semântica financeira
- Gráficos interativos
- Navegação por páginas

---

# 📈 Resultados

O pipeline automatiza completamente a transformação de DFPs da CVM em indicadores financeiros.

O projeto calcula, entre outros:

- Liquidez
- Capital de Giro
- Endividamento
- Cobertura de Juros
- ROE
- ROA
- ROIC
- ROI
- DuPont
- Fluxo de Caixa Livre
- Conversão de Caixa
- EVA
- NOPAT
- CAGR
- Crescimento YoY

---

# 📐 Premissas Financeiras

- NOPAT calculado utilizando alíquota estatutária de **34%**
- WACC padrão de **12%**, ajustável no dashboard
- Indicadores de retorno utilizam média dos saldos patrimoniais
- Prazos calculados com base de **360 dias**
- Plano de contas padronizado da CVM

---

# 🔍 Insights do Caso Embraer (2023–2025)

- Receita cresceu aproximadamente **18%** em 2025.
- EBITDA apresentou retração de aproximadamente **6%**, indicando perda de margem operacional.
- Cobertura de juros caiu de **2,1x para 0,9x**.
- Empresa encerrou o período com posição de caixa líquido.
- Ciclo de Conversão de Caixa reduziu de **161 para 138 dias**.
- ROIC permaneceu abaixo do WACC, indicando destruição econômica de valor.

---

# 🚀 Como Executar

Clone o projeto:

```bash
git clone https://github.com/danilo-justino/decisor-financeiro.git

cd decisor-financeiro
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure os caminhos do PDF e das pastas de saída nos scripts.

Execute o pipeline:

```bash
python extrair_demonstrativos.py
```

```bash
python tratar_dados.py
```

```bash
streamlit run desenvolvimento.py
```

---

# 📁 Estrutura do Projeto

```text
decisor-financeiro/

├── assets/
│   └── dashboard.png
│
├── csv/
├── csv_tratados/
│
├── extrair_demonstrativos.py
├── tratar_dados.py
├── desenvolvimento.py
│
├── requirements.txt
└── README.md
```

---

# 🎯 Próximas Evoluções

- [ ] Upload de PDFs pelo usuário
- [ ] Comparação entre empresas
- [ ] Exportação para Excel
- [ ] Deploy no Streamlit Community Cloud
- [ ] Integração com APIs de mercado
- [ ] Geração automática de relatório em PDF

---

## 👨‍💻 Autor

**Danilo Justino**

Projeto desenvolvido para demonstrar competências em:

- Engenharia de Dados
- Análise Financeira
- Business Intelligence
- Python
- Streamlit
- Pandas
- Automação de Processos
