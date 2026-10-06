
from pathlib import Path
import streamlit as st
BASE = Path(__file__).resolve().parent
import pandas as pd
import numpy as np
from scipy.optimize import linprog
from validacao import validar_ingredientes
from relatorio import gerar_pdf

st.set_page_config(
    page_title="MultVet Aves Caipiras PRO",
    page_icon="🐔",
    layout="wide"
)

# =========================
# IDENTIDADE MULTVET
# =========================
DARK_GREEN = "#1F4A2B"
LIME_GREEN = "#2F6B3E"
LIGHT_BG = "#E8DCC8"

st.markdown(f"""
<style>
.stApp {{ background: {LIGHT_BG}; }}
.multvet-header {{
    background: {DARK_GREEN};
    padding: 18px 24px;
    border-radius: 12px;
    color: white;
    margin-bottom: 20px;
}}
.multvet-header h1 {{ margin: 0; font-size: 30px; }}
.multvet-header p {{ margin: 5px 0 0; color: #DDEBDD; }}
.result-ok {{
    background: #EAF7E2;
    border-left: 6px solid {LIME_GREEN};
    padding: 14px;
    border-radius: 8px;
}}
.result-warn {{
    background: #FFF4E5;
    border-left: 6px solid #E09B32;
    padding: 14px;
    border-radius: 8px;
}}
.metric-card {{
    background: white;
    border-radius: 10px;
    padding: 12px;
    border: 1px solid #DDE5DD;
}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="multvet-header">
<h1>🐔 MultVet Aves Caipiras PRO</h1>
<p>Formulador Inteligente de Rações de Custo Mínimo</p>
</div>
""", unsafe_allow_html=True)

# =========================
# DADOS DE REFERÊNCIA
# =========================
if (BASE / "assets/banner.png").exists():
    st.image(str(BASE / "assets/banner.png"), use_container_width=True)

ingredientes_padrao = pd.read_csv(BASE / "data/ingredientes.csv")
fases_corte = pd.read_csv(BASE / "data/fases_corte.csv")
fases_postura = pd.read_csv(BASE / "data/fases_postura.csv")

if "ingredientes" not in st.session_state:
    st.session_state.ingredientes = ingredientes_padrao.copy()

# =========================
# FUNÇÕES
# =========================
def formular(df, fase, quantidade_kg):
    try:
        df = validar_ingredientes(df)
        if not np.isfinite(quantidade_kg) or quantidade_kg <= 0:
            raise ValueError("A quantidade do lote deve ser positiva e finita.")
    except (ValueError, KeyError, TypeError) as exc:
        return None, str(exc)
    ativos = df[df["Ativo"] == True].copy()

    if ativos.empty:
        return None, "Nenhuma matéria-prima está ativa."

    nomes = ativos["Ingrediente"].tolist()
    custo = ativos["Preco_kg"].astype(float).to_numpy()

    pb = ativos["PB_pct"].astype(float).to_numpy()
    em = ativos["EM_kcal_kg"].astype(float).to_numpy()
    ca = ativos["Ca_pct"].astype(float).to_numpy()
    pdisp = ativos["P_disp_pct"].astype(float).to_numpy()

    # x = fração da matéria-prima na mistura (0 a 1)
    A_ub = np.array([
        -pb,
        -em,
        -ca,
        -pdisp
    ])
    b_ub = np.array([
        -float(fase["PB_min"]),
        -float(fase["EM_min"]),
        -float(fase["Ca_min"]),
        -float(fase["P_disp_min"])
    ])

    for coluna, vetor in [("Ca", ca), ("P_disp", pdisp), ("PB", pb), ("EM", em)]:
        maximo = fase.get(coluna + "_max", np.nan)
        if pd.notna(maximo):
            if not np.isfinite(float(maximo)) or float(maximo) < float(fase[coluna + "_min"]):
                return None, f"Limite máximo inválido: {coluna}."
            A_ub = np.vstack([A_ub, vetor])
            b_ub = np.append(b_ub, float(maximo))

    bounds = []
    for _, r in ativos.iterrows():
        bounds.append((float(r["Inclusao_min_pct"]) / 100,
                       float(r["Inclusao_max_pct"]) / 100))

    result = linprog(
        c=custo,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=np.ones((1, len(nomes))),
        b_eq=np.array([1.0]),
        bounds=bounds,
        method="highs"
    )

    if not result.success:
        return None, result.message

    x = result.x
    saida = ativos[["Ingrediente", "PB_pct", "EM_kcal_kg", "Ca_pct", "P_disp_pct", "Preco_kg"]].copy()
    saida["Inclusao_pct"] = x * 100
    saida["Kg_no_lote"] = x * quantidade_kg
    saida["Custo"] = x * quantidade_kg * saida["Preco_kg"].astype(float)

    # Pequenos valores numéricos ficam como zero
    saida.loc[saida["Inclusao_pct"].abs() < 0.00001, "Inclusao_pct"] = 0
    saida = saida[saida["Inclusao_pct"] > 0.00001].copy()

    total = x @ custo
    nutrientes = {
        "PB": x @ pb,
        "EM": x @ em,
        "Ca": x @ ca,
        "P_disp": x @ pdisp
    }

    return {
        "ingredientes": saida,
        "custo_kg": total,
        "custo_lote": total * quantidade_kg,
        "nutrientes": nutrientes,
        "fase": fase
    }, None

def formatar_numero(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =========================
# MENU
# =========================
aba1, aba2, aba3 = st.tabs([
    "🐔 Formular Ração",
    "🌾 Minhas Matérias-Primas",
    "ℹ️ Sobre o aplicativo"
])

with aba1:
    st.subheader("1. Escolha o tipo de ave")

    tipo = st.radio(
        "Finalidade da criação",
        ["Frango caipira — Corte", "Ave caipira — Postura"],
        horizontal=True
    )

    if tipo.startswith("Frango"):
        fases = fases_corte
    else:
        fases = fases_postura

    fase_nome = st.selectbox("2. Escolha a fase de desenvolvimento", fases["Fase"].tolist())
    fase = fases[fases["Fase"] == fase_nome].iloc[0]

    st.caption("Versão de avaliação técnica: tabelas herdadas do projeto, ainda pendentes de revisão nutricional. O cálculo cobre PB, EM, Ca e P disponível; não verifica aminoácidos, sódio nem todos os micronutrientes.")
    with st.expander("Parâmetros da formulação", expanded=True):
        fase = fase.copy()
        st.write("Defina os máximos de cálcio e fósforo conforme a referência técnica adotada. Os valores iniciais abaixo igualam o mínimo para testar o controle; não são recomendações universais.")
        fase["Ca_max"] = st.number_input("Cálcio máximo (%)", min_value=float(fase["Ca_min"]), value=float(fase["Ca_min"]), step=0.01, key=f"ca_{tipo}_{fase_nome}")
        fase["P_disp_max"] = st.number_input("Fósforo disponível máximo (%)", min_value=float(fase["P_disp_min"]), value=float(fase["P_disp_min"]), step=0.01, key=f"p_{tipo}_{fase_nome}")
        dose = st.number_input("Dose do núcleo indicada no rótulo (kg/tonelada)", min_value=0.0, value=0.0, step=0.5)
        confirmar = st.checkbox("Conferi a composição dos ingredientes, o núcleo adequado à fase e os parâmetros desta simulação.")

    st.markdown("### 3. Quantidade de ração a fabricar")
    quantidade = st.number_input(
        "Quantidade desejada (kg)",
        min_value=1.0,
        value=100.0,
        step=25.0
    )

    st.markdown("### 4. Matérias-primas disponíveis")
    ativos = st.session_state.ingredientes[st.session_state.ingredientes["Ativo"] == True]
    st.dataframe(
        ativos[["Ingrediente", "Preco_kg", "PB_pct", "EM_kcal_kg", "Ca_pct", "P_disp_pct",
                "Inclusao_min_pct", "Inclusao_max_pct"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ingrediente": st.column_config.TextColumn("Ingrediente", width="medium"),
            "Preco_kg": st.column_config.NumberColumn("R$/kg", width="small", format="%.2f"),
            "PB_pct": st.column_config.NumberColumn("PB %", width="small"),
            "EM_kcal_kg": st.column_config.NumberColumn("EM kcal/kg", width="small"),
            "Ca_pct": st.column_config.NumberColumn("Ca %", width="small"),
            "P_disp_pct": st.column_config.NumberColumn("P disp. %", width="small"),
            "Inclusao_min_pct": st.column_config.NumberColumn("Mín. %", width="small"),
            "Inclusao_max_pct": st.column_config.NumberColumn("Máx. %", width="small"),
        }
    )

    st.info(
        "Os valores nutricionais são referências. Sempre que houver análise laboratorial "
        "ou garantia do fornecedor, use os valores reais da matéria-prima."
    )

    if st.button("🟢 FORMULAR RAÇÃO DE CUSTO MÍNIMO", type="primary", use_container_width=True):
        if not confirmar or dose <= 0:
            st.error("Informe a dose do núcleo e confirme os dados antes de calcular.")
            st.stop()
        dados_calculo = st.session_state.ingredientes.copy()
        mascara = dados_calculo["Ingrediente"].astype(str).str.contains("núcleo", case=False, regex=False) & (dados_calculo["Ativo"] == True)
        if mascara.sum() != 1:
            st.error("Cadastre exatamente um núcleo ativo, com a palavra núcleo no nome e a composição do produto adquirido.")
            st.stop()
        dados_calculo.loc[mascara, ["Inclusao_min_pct", "Inclusao_max_pct"]] = dose / 10
        resultado, erro = formular(dados_calculo, fase, quantidade)

        if erro:
            st.error(
                "Não foi encontrada uma formulação que atenda simultaneamente às restrições. "
                "Confira os dados, limites de inclusão e ingredientes disponíveis. Alterar somente preços não resolve a inviabilidade nutricional."
            )
            st.caption(f"Detalhe técnico: {erro}")
        else:
            st.success("Solução matemática encontrada para os parâmetros informados.")

            r = resultado
            n = r["nutrientes"]

            st.markdown("### 📋 Formulação")
            tabela = r["ingredientes"][[
                "Ingrediente", "Inclusao_pct", "Kg_no_lote", "Preco_kg", "Custo"
            ]].copy()
            tabela.columns = ["Ingrediente", "%", "kg", "R$/kg", "Custo"]
            st.dataframe(
                tabela.style.format({
                    "%": "{:.2f}",
                    "kg": "{:.2f}",
                    "R$/kg": "R$ {:.2f}",
                    "Custo": "R$ {:.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.download_button("Baixar fórmula em CSV", tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), "formula_multvet.csv", "text/csv")
            st.download_button("Baixar relatório em PDF para imprimir", gerar_pdf(r, tipo, quantidade), "relatorio_multvet.pdf", "application/pdf")
            st.markdown("### 📊 Composição nutricional calculada")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Proteína Bruta", f"{n['PB']:.2f}%")
            c2.metric("Energia Metabolizável", f"{n['EM']:,.0f} kcal/kg")
            c3.metric("Cálcio", f"{n['Ca']:.2f}%")
            c4.metric("Fósforo disponível", f"{n['P_disp']:.2f}%")

            st.markdown("### 💰 Custo")
            c1, c2 = st.columns(2)
            c1.metric("Custo por kg", f"R$ {r['custo_kg']:.4f}".replace(".", ","))
            c2.metric(f"Custo do lote ({quantidade:.0f} kg)", f"R$ {r['custo_lote']:.2f}".replace(".", ","))

            st.markdown("### 🎯 Conferência das exigências")
            checks = [
                ("PB", n["PB"], float(fase["PB_min"]), "%"),
                ("EM", n["EM"], float(fase["EM_min"]), "kcal/kg"),
                ("Ca", n["Ca"], float(fase["Ca_min"]), "%"),
                ("P disponível", n["P_disp"], float(fase["P_disp_min"]), "%")
            ]
            for nome, valor, minimo, unidade in checks:
                if valor >= minimo - 1e-7:
                    st.markdown(f"🟢 **{nome}:** {valor:.2f} {unidade} — mínimo {minimo:.2f} {unidade}")
                else:
                    st.markdown(f"🔴 **{nome}:** {valor:.2f} {unidade} — mínimo {minimo:.2f} {unidade}")

            st.caption(
                "A formulação matemática busca o menor custo entre as matérias-primas ativas, "
                "respeitando as inclusões mínima/máxima e os níveis nutricionais cadastrados."
            )

with aba2:
    st.subheader("🌾 Cadastro das minhas matérias-primas")
    st.write(
        "Edite preços e composição nutricional conforme a realidade da sua propriedade. "
        "Você também pode acrescentar ingredientes."
    )

    if st.session_state.pop("cadastro_salvo", False):
        st.success("Cadastro salvo nesta sessão. A formulação usará os ingredientes ativos abaixo.")
    st.caption("Marque Ativo para usar um ingrediente. As caixas à esquerda selecionam linhas para exclusão.")
    with st.form("form_cadastro", clear_on_submit=False):
        edited = st.data_editor(
            st.session_state.ingredientes,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "ID": None,
                "Ingrediente": st.column_config.TextColumn("Ingrediente", width="medium"),
                "Ativo": st.column_config.CheckboxColumn("Ativo", width="small"),
                "Preco_kg": st.column_config.NumberColumn("R$/kg", width="small", min_value=0.0, format="R$ %.2f"),
                "PB_pct": st.column_config.NumberColumn("PB %", width="small", min_value=0.0),
                "EM_kcal_kg": st.column_config.NumberColumn("EM kcal/kg", width="small", min_value=0.0),
                "Ca_pct": st.column_config.NumberColumn("Ca %", width="small", min_value=0.0),
                "P_disp_pct": st.column_config.NumberColumn("P disp. %", width="small", min_value=0.0),
                "Inclusao_min_pct": st.column_config.NumberColumn("Mín. %", width="small", min_value=0.0),
                "Inclusao_max_pct": st.column_config.NumberColumn("Máx. %", width="small", min_value=0.0),
            },
            disabled=["ID"],
            hide_index=True,
            column_order=["Ingrediente", "Ativo", "Preco_kg", "PB_pct", "EM_kcal_kg", "Ca_pct", "P_disp_pct", "Inclusao_min_pct", "Inclusao_max_pct"],
            key=f"editor_ingredientes_{st.session_state.get('cadastro_revisao', 0)}"
        )
    
        salvar = st.form_submit_button("💾 Salvar alterações")
    if salvar:
        try:
            novos_dados = validar_ingredientes(edited)
            st.session_state.ingredientes = novos_dados.copy(deep=True)
            st.session_state.cadastro_revisao = st.session_state.get("cadastro_revisao", 0) + 1
            st.session_state.cadastro_salvo = True
            st.rerun()
        except (ValueError, KeyError, TypeError) as exc:
            st.error(str(exc))

    st.info("O cadastro fica nesta sessão. Baixe uma cópia para guardar seus preços e ingredientes e importe-a quando voltar.")
    st.download_button("Baixar meu cadastro", st.session_state.ingredientes.to_csv(index=False).encode("utf-8-sig"), "meus_ingredientes.csv", "text/csv")
    arquivo = st.file_uploader("Recuperar cadastro salvo (CSV)", type="csv")
    if st.button("Importar cadastro", disabled=arquivo is None):
        try:
            st.session_state.ingredientes = validar_ingredientes(pd.read_csv(arquivo))
            st.session_state.cadastro_revisao = st.session_state.get("cadastro_revisao", 0) + 1
            st.session_state.cadastro_salvo = True
            st.rerun()
        except Exception as exc:
            st.error(f"Cadastro não importado: {exc}")

    st.warning(
        "Atenção: o fosfato bicálcico foi cadastrado inicialmente com 23% de Ca e 18% de P. "
        "Confira a garantia do produto comercial adquirido antes de formular."
    )

with aba3:
    st.subheader("ℹ️ Sobre o MultVet Aves Caipiras PRO")
    st.markdown("""
**Objetivo:** auxiliar o produtor na formulação de rações de custo mínimo para aves caipiras.

### O aplicativo trabalha nesta versão com:
- Proteína Bruta (PB)
- Energia Metabolizável (EM)
- Cálcio (Ca)
- Fósforo disponível (P)
- Custo por kg
- Limites mínimo/máximo de inclusão

### Importante
Esta é uma ferramenta de apoio à formulação. A composição real dos ingredientes pode variar
entre lotes, fornecedores e condições de processamento. O usuário deve conferir garantias,
análises e recomendações do fabricante de núcleos e suplementos.

**Desenvolvimento:** MultVet  
**Identidade:** MultVet — Nutrição, Manejo e Sanidade
""")
