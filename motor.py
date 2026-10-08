import numpy as np
import pandas as pd
from scipy.optimize import linprog

NUTRIENTES = {'PB': ('PB_pct', 'Proteína bruta'), 'EM': ('EM_kcal_kg', 'Energia metabolizável'), 'Ca': ('Ca_min_pct', 'Cálcio total'), 'P_total': ('P_total_pct', 'Fósforo total')}

def validar(df):
    d=df.copy()
    required=['Ingrediente','Ativo','Preco_kg','Inclusao_min_pct','Inclusao_max_pct','Ca_max_pct']+[v[0] for v in NUTRIENTES.values()]
    if set(required)-set(d): raise ValueError('Cadastro de versão anterior: não converta fósforo disponível em total. Use o cadastro novo.')
    if d.empty or d.Ingrediente.isna().any() or d.Ingrediente.astype(str).str.strip().eq('').any(): raise ValueError('Preencha o nome de todos os ingredientes.')
    if d.Ingrediente.astype(str).str.strip().str.casefold().duplicated().any(): raise ValueError('Nomes repetidos no cadastro.')
    d['Ativo']=d.Ativo.astype(str).str.lower().map({'true':True,'false':False,'1':True,'0':False})
    if d.Ativo.isna().any(): raise ValueError('Preencha Ativo em todas as linhas.')
    for col in required:
        if col in ['Ingrediente','Ativo']: continue
        raw=d[col]; d[col]=pd.to_numeric(raw,errors='coerce')
        if (raw.notna() & d[col].isna()).any() or np.isinf(d[col]).any() or (d[col].dropna()<0).any(): raise ValueError('Valor inválido em '+col)
        if col.endswith('pct') and (d[col].dropna()>100).any(): raise ValueError('Percentual superior a 100 em '+col)
    if d[['Preco_kg','Inclusao_min_pct','Inclusao_max_pct']].isna().any().any(): raise ValueError('Informe preços e limites de inclusão.')
    if (d.Inclusao_min_pct>d.Inclusao_max_pct).any() or (d.Ca_min_pct>d.Ca_max_pct).any(): raise ValueError('Mínimo superior ao máximo.')
    return d

def calcular(df, metas, lote, aproximada=False):
    d=validar(df); d=d[d.Ativo].copy()
    if not np.isfinite(lote) or lote<=0: raise ValueError('Lote inválido.')
    if d.empty: raise ValueError('Nenhum ingrediente ativo.')
    bounds=list(zip(d.Inclusao_min_pct/100,d.Inclusao_max_pct/100)); n=len(d)
    if sum(a for a,b in bounds)>1+1e-8 or sum(b for a,b in bounds)<1-1e-8: raise ValueError('Limites de inclusão não permitem completar 100%.')
    rows=[]; rhs=[]; scales=[]; parciais={}
    for k in ["PB","EM"]:
        col=NUTRIENTES[k][0]
        missing=d[col].isna() & (d.Inclusao_max_pct>0)
        if missing.any() and d.loc[missing,"Ingrediente"].str.contains("núcleo",case=False,na=False).all():
            parciais[k]=", ".join(d.loc[missing,"Ingrediente"])
    for k,(col,label) in NUTRIENTES.items():
        lo,hi=metas[k]
        for target,ismax in [(lo,False),(hi,True)]:
            if target is None: continue
            if not np.isfinite(target) or target<0: raise ValueError('Meta inválida: '+label)
            if k in parciais: continue
            use='Ca_max_pct' if k=='Ca' and ismax else col
            if d[use].isna().any(): raise ValueError(label+': composição não informada em '+', '.join(d.loc[d[use].isna(),'Ingrediente'])+'. Preencha o dado ou desative a meta desse nutriente.')
            rows.append(d[use].to_numpy()* (1 if ismax else -1)); rhs.append(target*(1 if ismax else -1)); scales.append(max(abs(target),1e-6))
        if lo is not None and hi is not None and lo>hi: raise ValueError('Meta mínima superior à máxima: '+label)
    A=np.array(rows) if rows else None; B=np.array(rhs) if rows else None
    cost=d.Preco_kg.to_numpy(); eq=np.ones((1,n))
    res=linprog(cost,A_ub=A,b_ub=B,A_eq=eq,b_eq=[1],bounds=bounds,method='highs')
    relaxed=False
    if not res.success:
        if res.status!=2: raise ValueError('Falha de cálculo: '+res.message)
        if not aproximada: raise ValueError('Não há mistura que atenda simultaneamente às metas. Revise os dados ou escolha Buscar alternativa com ressalvas.')
        m=len(rows); penalty=1/np.array(scales)
        extended=np.hstack([A,-np.eye(m)])
        eqx=np.hstack([eq,np.zeros((1,m))]); bx=bounds+[(0,None)]*m
        first=linprog(np.r_[np.zeros(n),penalty],A_ub=extended,b_ub=B,A_eq=eqx,b_eq=[1],bounds=bx,method='highs')
        if not first.success: raise ValueError('Não foi possível encontrar alternativa com os limites de inclusão.')
        second=linprog(np.r_[cost,np.zeros(m)],A_ub=np.vstack([extended,np.r_[np.zeros(n),penalty]]),b_ub=np.r_[B,first.fun+1e-8],A_eq=eqx,b_eq=[1],bounds=bx,method='highs')
        res=second if second.success else first; relaxed=True
    x=res.x[:n]; output=d.copy(); output['Inclusao_pct']=x*100; output['Kg_no_lote']=x*lote; output['Custo']=x*lote*cost
    used=x>1e-9; checks=[]
    for k,(col,label) in NUTRIENTES.items():
        def nutrient(c): return None if d.loc[used,c].isna().any() else float(x[used]@d.loc[used,c].to_numpy())
        low=float(x[used]@d.loc[used,col].fillna(0).to_numpy()) if k in parciais else nutrient(col); high=nutrient('Ca_max_pct') if k=='Ca' else low
        lo,hi=metas[k]; deviations=[]
        if lo is not None and low is not None and low<lo-1e-6: deviations.append('Abaixo do mínimo por '+f'{lo-low:.4f}')
        if hi is not None and high is not None and high>hi+1e-6: deviations.append('Acima do máximo por '+f'{high-hi:.4f}')
        status=('Parcial — contribuição do núcleo não informada; meta não verificada' if k in parciais and d.loc[used,col].isna().any() else '; '.join(deviations)) or ('Não verificado' if low is None or high is None or (lo is None and hi is None) else 'Dentro das metas')
        checks.append(dict(Nutriente=label,Min_calculado=low,Max_calculado=high,Meta_min=lo,Meta_max=hi,Situacao=status))
    return dict(ingredientes=output.loc[used].copy(),conferencia=pd.DataFrame(checks),custo_kg=float(x@cost),custo_lote=float(x@cost*lote),ressalvas=relaxed,avisos=[NUTRIENTES[k][1]+": subtotal dos ingredientes com dados; contribuição de "+nome+" não contabilizada. A meta foi retirada da otimização e não está verificada." for k,nome in parciais.items()])
