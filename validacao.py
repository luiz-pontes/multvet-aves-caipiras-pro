import numpy as np
import pandas as pd

COLUNAS = ["Preco_kg", "PB_pct", "EM_kcal_kg", "Ca_pct", "P_disp_pct", "Inclusao_min_pct", "Inclusao_max_pct"]
def validar_ingredientes(df):
    df = df.copy()
    obrigatorias = ["Ingrediente", "Ativo"] + COLUNAS
    faltam = set(obrigatorias) - set(df.columns)
    if faltam:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(faltam)))
    if df.empty:
        raise ValueError("Cadastre pelo menos uma matéria-prima.")
    if df["Ingrediente"].isna().any() or df["Ingrediente"].astype(str).str.strip().eq("").any():
        raise ValueError("Toda matéria-prima precisa de nome.")
    if df["Ingrediente"].astype(str).str.strip().str.casefold().duplicated().any():
        raise ValueError("Há nomes de ingredientes repetidos.")
    mapa = {"true": True, "false": False, "1": True, "0": False}
    ativos = df["Ativo"].astype(str).str.strip().str.lower().map(mapa)
    if ativos.isna().any():
        raise ValueError("Preencha Ativo com True ou False em todas as linhas.")
    df["Ativo"] = ativos.astype(bool)
    for c in COLUNAS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        if not np.isfinite(df[c]).all() or (df[c] < 0).any():
            raise ValueError(f"Preencha {c} com números finitos e não negativos.")
        if c.endswith("pct") and (df[c] > 100).any():
            raise ValueError(f"{c} não pode ultrapassar 100%.")
    if (df["Inclusao_min_pct"] > df["Inclusao_max_pct"]).any():
        raise ValueError("A inclusão mínima não pode superar a máxima.")
    ativos = df[df.Ativo]
    if ativos.empty:
        raise ValueError("Selecione ao menos um ingrediente ativo.")
    if ativos.Inclusao_min_pct.sum() > 100 + 1e-8 or ativos.Inclusao_max_pct.sum() < 100 - 1e-8:
        raise ValueError("Os limites dos ingredientes ativos não permitem fechar 100% da mistura.")
    return df
