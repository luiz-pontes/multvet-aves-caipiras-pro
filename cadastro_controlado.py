import pandas as pd
from motor import validar

EDITAVEIS=['Ativo','Preco_kg']

def eh_nucleo(d):
    return d.Ingrediente.fillna('').str.startswith('Núcleo — ')

def mesclar_cadastro(base, recebidos):
    if 'Ingrediente' not in recebidos: raise ValueError('Arquivo sem nomes de ingredientes.')
    if recebidos.Ingrediente.isna().any() or recebidos.Ingrediente.duplicated().any(): raise ValueError('Nomes ausentes ou repetidos.')
    fixos=base[~eh_nucleo(base)].copy()
    # Ignore imported compositions for fixed items; the shipped table is authoritative.
    for _,row in recebidos.iterrows():
        mask=fixos.Ingrediente.eq(row.Ingrediente)
        if mask.any():
            for c in EDITAVEIS:
                if c in row: fixos.loc[mask,c]=row[c]
        elif not str(row.Ingrediente).startswith('Núcleo — '):
            raise ValueError('Cadastro incompatível: só ingredientes da base e núcleos com prefixo Núcleo — podem ser importados.')
    nuc=recebidos[recebidos.Ingrediente.fillna('').str.startswith('Núcleo — ')].copy()
    if not nuc.empty:
        nuc['Liberado']=True
        nuc['Criterio']='Garantias do núcleo cadastradas pelo usuário; conferir rótulo e fase.'
    total=pd.concat([fixos,nuc],ignore_index=True)
    total['Ativo']=total.Ativo.astype(str).str.lower().map({'true':True,'false':False,'1':True,'0':False})
    total.loc[~total.Liberado.fillna(False).astype(bool),'Ativo']=False
    return validar(total)
