from pathlib import Path
import pandas as pd
import streamlit as st
from motor import calcular, validar, NUTRIENTES
from cadastro_controlado import eh_nucleo, mesclar_cadastro
from relatorio_total import gerar_pdf, numero
BASE=Path(__file__).resolve().parent
FONTE_POSTURA='Embrapa 051 — Recomendações para o sistema de produção com poedeiras livres de gaiola para o Estado do Paraná, Anexo 7, p. 30.'
METAS_POSTURA={
    'Pré-postura (16–21 semanas)': {'PB_min':16.,'PB_max':18.,'EM_min':2800.,'Ca_min':3.70},
    'Produção I (22–37 semanas)': {'PB_min':15.,'PB_max':15.5,'EM_min':2750.,'Ca_min':3.90},
    'Produção II (38–65 semanas)': {'PB_min':15.,'PB_max':15.5,'EM_min':2750.,'Ca_min':3.80},
    'Produção III (acima de 65 semanas)': {'PB_min':15.,'EM_min':2750.,'Ca_min':3.85},
}
AVISO_FOSFORO='Fósforo total calculado com os dados cadastrados; atendimento à exigência de fósforo disponível não avaliado.'
st.set_page_config(page_title='MultVet Aves Caipiras PRO',page_icon='🐔',layout='wide')
st.markdown('<style>.stApp{background:#E8DCC8} h1,h2,h3{color:#1F4A2B}</style>',unsafe_allow_html=True)
st.title('🐔 MultVet Aves Caipiras PRO')
st.caption('Modelo de avaliação técnica — cálcio total e fósforo total')
if (BASE/'assets/banner.png').exists(): st.image(str(BASE/'assets/banner.png'),use_container_width=True)
if 'cadastro_hyline_v1' not in st.session_state:
    st.session_state.cadastro_hyline_v1=pd.read_csv(BASE/'data/ingredientes_hyline.csv')
    st.session_state.rev_total=0
cad=st.session_state.cadastro_hyline_v1
aba1,aba2,aba3=st.tabs(['Formular ração','Minhas matérias-primas','Orientações'])
with aba1:
    tipo=st.radio('Finalidade',['Corte','Postura'],horizontal=True)
    fases=['Pré-inicial','Inicial','Crescimento/Engorda','Final/Abate'] if tipo=='Corte' else list(METAS_POSTURA)
    fase=st.selectbox('Fase',fases)
    if tipo=='Postura':
        st.info('Fases e referências nutricionais da Embrapa 051 por idade. Avalie também consumo de ração, produção e condição do lote. Metas editáveis para revisão técnica.')
        st.markdown('[Referência: Embrapa 051, Anexo 7, página 30](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1154157/1/Recomendacoes-para-o-sistema-de-producao-com-poedeiras.pdf). A referência informa fósforo disponível; esse valor não é usado como meta de fósforo total.')
    nucleos=cad[cad.Ingrediente.str.contains('núcleo',case=False,na=False)]
    escolhido=st.selectbox('Núcleo para esta simulação',[None]+nucleos.Ingrediente.tolist(),format_func=lambda x:'Selecione o produto e confira o rótulo' if x is None else x,key='nucleo_'+tipo)
    dose_padrao={'Núcleo Inicial Corte':50.,'Núcleo Engorda Corte':50.,'Núcleo Abate Corte':40.,'Núcleo Postura':50.}
    dose=st.number_input('Dose do núcleo (kg/tonelada)',min_value=0.,max_value=1000.,value=float(nucleos.loc[nucleos.Ingrediente==escolhido,'Inclusao_min_pct'].iloc[0])*10 if escolhido else 0.,key='dose_'+str(escolhido))
    st.caption('Somente o núcleo selecionado entra no cálculo. Confira sua adequação à fase e a dose do rótulo.')
    nucleo_mineral=st.checkbox('Este produto é um núcleo vitamínico-mineral: considerar PB e EM iguais a zero quando não informadas.',value=True)
    st.caption('Critério de cálculo confirmado pelo usuário. Para concentrado proteico, desmarque e cadastre sua composição própria. Valores informados são preservados.')
    lote=st.number_input('Quantidade do lote (kg)',min_value=1.,value=100.,step=25.)
    st.markdown('### Metas nutricionais')
    st.info('Não usamos as antigas metas de fósforo disponível como fósforo total. Defina metas com a mesma base dos ingredientes. Desmarcar uma meta deixa seu atendimento não verificado.')
    ref=pd.read_csv(BASE/'data/fases_corte.csv')
    linha=ref[ref.Fase==fase]
    padrao=METAS_POSTURA[fase] if tipo=='Postura' else linha.iloc[0] if len(linha) else {'PB_min':0.,'EM_min':0.,'Ca_min':0.}
    chave_meta=tipo+'_'+fase+'_embrapa_v2'
    metas={}
    for k,(col,label) in NUTRIENTES.items():
        with st.expander(label,expanded=True):
            usar=st.checkbox('Verificar '+label,value=k in ['PB','EM'] or (tipo=='Postura' and k=='Ca'),key='usar_'+k+'_'+chave_meta)
            a,b=st.columns(2)
            minimo=a.number_input('Mínimo'+(' (kcal/kg)' if k=='EM' else ' (%)'),min_value=0.,value=float(padrao.get(k+'_min',0.)),key='min_'+k+'_'+chave_meta)
            limitar=b.checkbox('Definir máximo',value=tipo=='Postura' and k+'_max' in padrao,key='maxon_'+k+'_'+chave_meta)
            maximo=b.number_input('Máximo'+(' (kcal/kg)' if k=='EM' else ' (%)'),min_value=0.,value=float(padrao.get(k+'_max',padrao.get(k+'_min',0.))),key='max_'+k+'_'+chave_meta)
            metas[k]=(minimo if usar else None,maximo if usar and limitar else None)
            if k=='Ca' and usar and not limitar:
                st.warning('Somente o mínimo de cálcio será verificado. O resultado ficará amarelo: excesso não avaliado. A fonte usada não define um limite máximo; informe-o após revisão técnica. O máximo será comparado ao limite superior calculado das garantias dos ingredientes.')
    st.caption('Postura: PB na faixa da fonte; EM e Ca usados como mínimos de cálculo, editáveis. Corte: referências herdadas, pendentes de revisão. Desvios relativos têm pesos iguais no modo aproximado; o custo é minimizado depois dos desvios.')
    modo=st.radio('Modo de cálculo',['Atender às metas','Buscar alternativa com ressalvas'])
    dados=cad.copy()
    dados.loc[~dados.Liberado.fillna(False).astype(bool),'Ativo']=False
    criterios_nucleo=[]
    mask=dados.Ingrediente.str.contains('núcleo',case=False,na=False)
    dados.loc[mask,'Ativo']=False
    if escolhido:
        sel=dados.Ingrediente==escolhido
        dados.loc[sel,'Ativo']=True
        dados.loc[sel,['Inclusao_min_pct','Inclusao_max_pct']]=dose/10
        if nucleo_mineral:
            for coluna,nome in [('PB_pct','proteína bruta'),('EM_kcal_kg','energia metabolizável')]:
                ausente=sel & dados[coluna].isna()
                if ausente.any():
                    dados.loc[ausente,coluna]=0.0
                    criterios_nucleo.append(nome)
        if criterios_nucleo: st.info('Critério adotado: contribuição zero de '+', '.join(criterios_nucleo)+' do núcleo. As metas continuam ativas; o cadastro original permanece sem alteração.')
    st.markdown('### Ingredientes disponíveis para esta simulação')
    st.dataframe(dados.loc[dados.Ativo,['Ingrediente','Preco_kg','PB_pct','EM_kcal_kg','Ca_min_pct','Ca_max_pct','P_total_pct','Inclusao_min_pct','Inclusao_max_pct']],hide_index=True,use_container_width=True)
    confirmar=st.checkbox('Conferi as composições, a base total dos minerais, o núcleo e os parâmetros desta simulação.')
    assinatura=(dados.to_csv(index=False),str(metas),tipo,fase,lote,dose,modo,confirmar,nucleo_mineral)
    if st.session_state.get('assinatura_total')!=assinatura: st.session_state.pop('resultado_total',None)
    if st.button('FORMULAR',type='primary'):
        st.session_state.pop('resultado_total',None)
        if not confirmar or not escolhido or dose<=0: st.error('Confira os dados e informe um núcleo com dose positiva.')
        elif (dados.loc[dados.Ativo,'Preco_kg']<=0).any():
            st.error('Informe preço positivo para todos os ingredientes selecionados.')
        elif any(lo is not None and lo<=0 for lo,hi in metas.values()):
            st.error('Informe um mínimo positivo para cada meta marcada ou desmarque sua verificação. Zero não representa uma exigência nutricional válida.')
        else:
            try:
                r=calcular(dados,metas,lote,modo=='Buscar alternativa com ressalvas')
                for criterio in dados.loc[dados.Ativo,'Criterio'].dropna().unique():
                    r['avisos'].append(str(criterio))
                r['avisos'].append('Composição da base fixa: Hy-Line Brown 2009–2011, página 40; fonte da tabela: Feedstuff Magazine. Garantias dos núcleos: rótulos cadastrados. As composições são referências, não análises dos lotes.')
                if tipo=='Postura':
                    r['avisos'].append(FONTE_POSTURA+' Metas editáveis: confira os valores da tabela de conferência. EM e Ca usados como mínimos de cálculo.')
                if metas['Ca'][0] is not None and metas['Ca'][1] is None:
                    r['avisos'].append('Cálcio: somente a meta mínima foi verificada; excesso não avaliado. O intervalo calculado usa os mínimos e máximos cadastrados. Defina um limite máximo após revisão técnica para verificar ambos os limites.')
                p_calculado=r['conferencia'].loc[r['conferencia'].Nutriente=='Fósforo total','Min_calculado'].iloc[0]
                r['avisos'].append(AVISO_FOSFORO if pd.notna(p_calculado) else 'Fósforo total não calculado integralmente: faltam dados de ingredientes utilizados. Atendimento à exigência de fósforo disponível não avaliado.')
                if metas['P_total']==(None,None):
                    r['conferencia'].loc[r['conferencia'].Nutriente=='Fósforo total','Situacao']='Não verificado — fósforo disponível não avaliado'
                if criterios_nucleo:
                    r['avisos'].append('Critério de cálculo confirmado pelo usuário: '+escolhido+' tratado como núcleo vitamínico-mineral, com contribuição zero de '+', '.join(criterios_nucleo)+'. Valores não fornecidos no rótulo; metas mantidas na otimização. Este critério não se aplica a concentrados proteicos.')
                st.session_state.resultado_total=r
                st.session_state.assinatura_total=assinatura
            except ValueError as exc: st.error(str(exc))
    if 'resultado_total' in st.session_state:
        r=st.session_state.resultado_total
        for aviso in r.get('avisos',[]): st.warning(aviso)
        if r['ressalvas']: st.warning('Mistura com desvios nutricionais — requer revisão técnica antes do uso.')
        else: st.success('Solução matemática encontrada para as metas verificadas.')
        st.caption('O modelo não verifica aminoácidos, sódio, vitaminas nem todos os nutrientes de uma ração completa. Fósforo total mínimo e cálcio em intervalo não representam composição exata.')
        tabela=r['ingredientes'][['Ingrediente','Inclusao_pct','Kg_no_lote','Preco_kg','Custo']]
        st.dataframe(tabela.style.format({c:lambda v:numero(v,3) for c in tabela.columns if c!='Ingrediente'}),hide_index=True,use_container_width=True)
        def destaque(row):
            cor='#FFE3D6' if 'Abaixo' in row.Situacao or 'Acima' in row.Situacao else '#FFF4CC' if 'Não verificado' in row.Situacao or 'Parcial' in row.Situacao else '#EAF7E2'
            return ['background-color: '+cor]*len(row)
        st.dataframe(r['conferencia'].style.apply(destaque,axis=1).format({c:lambda v:'Não informado' if pd.isna(v) else numero(v,4) for c in ['Min_calculado','Max_calculado','Meta_min','Meta_max']}),hide_index=True,use_container_width=True)
        st.metric('Custo por kg','R$ '+numero(r['custo_kg'],4));st.metric('Custo do lote','R$ '+numero(r['custo_lote']))
        export=tabela.to_csv(index=False,sep=';',decimal=',')+'\nConferência nutricional\n'+r['conferencia'].to_csv(index=False,sep=';',decimal=',')
        st.download_button('Baixar fórmula e conferência em CSV',export.encode('utf-8-sig'),'formula_total_multvet.csv','text/csv')
        st.download_button('Baixar relatório PDF',gerar_pdf(r,tipo,fase,lote,escolhido,dose),'relatorio_total_multvet.pdf','application/pdf')
with aba2:
    st.write('Base fixa: Hy-Line Brown 2009–2011, página 40. A composição é protegida; você pode atualizar preços e selecionar ingredientes liberados. Campos vazios são dados ausentes, não zero. Núcleos têm cadastro próprio.')
    st.caption('Os limites existentes são parâmetros herdados de teste, pendentes de revisão técnica; não são limites fornecidos pelo manual. Os demais itens estão catalogados e aguardam liberação.')
    fixos=cad[~eh_nucleo(cad)]
    liberados=fixos[fixos.Liberado.fillna(False).astype(bool)]
    with st.form('precos_hyline'):
        ed=st.data_editor(liberados[['Ingrediente','Ativo','Preco_kg']],disabled=['Ingrediente'],hide_index=True,key='precos_'+str(st.session_state.rev_total))
        st.caption('Preços dos ingredientes catalogados que ainda aguardam liberação:')
        pend=st.data_editor(fixos[~fixos.Liberado.fillna(False).astype(bool)][['Ingrediente','Preco_kg']],disabled=['Ingrediente'],hide_index=True,key='pendentes_'+str(st.session_state.rev_total))
        save=st.form_submit_button('Salvar preços e seleção')
    if save:
        try:
            novo=cad.copy()
            for _,row in ed.iterrows(): novo.loc[novo.Ingrediente==row.Ingrediente,['Ativo','Preco_kg']]=[row.Ativo,row.Preco_kg]
            for _,row in pend.iterrows(): novo.loc[novo.Ingrediente==row.Ingrediente,'Preco_kg']=row.Preco_kg
            st.session_state.cadastro_hyline_v1=validar(novo);st.session_state.rev_total+=1;st.rerun()
        except ValueError as exc: st.error(str(exc))
    with st.expander('Composição da base e ingredientes aguardando liberação'):
        st.dataframe(fixos[['Ingrediente','PB_pct','EM_kcal_kg','Ca_min_pct','P_total_pct','Liberado','Criterio']],hide_index=True)
    st.markdown('### Cadastrar ou atualizar meu núcleo')
    meus=cad[eh_nucleo(cad)]
    alvo=st.selectbox('Produto para editar',['Novo núcleo']+meus.Ingrediente.tolist())
    anterior=meus[meus.Ingrediente==alvo]
    anterior=anterior.iloc[0].to_dict() if len(anterior) else {}
    unidade=st.radio('Unidade das garantias minerais',['g/kg do produto','% do produto'],key='unidade_nucleo')
    mult_unidade=10 if unidade=='g/kg do produto' else 1
    with st.form('meu_nucleo_'+alvo):
        nome=st.text_input('Nome e marca do núcleo',value=alvo.removeprefix('Núcleo — ') if anterior else '')
        preco=st.number_input('Preço do núcleo (R$/kg)',min_value=0.,value=float(anterior.get('Preco_kg',0.)))
        dose_n=st.number_input('Inclusão indicada no rótulo (kg/tonelada)',min_value=0.,max_value=1000.,value=float(anterior.get('Inclusao_min_pct',0.))*10)
        st.caption('Exemplo de conversão: 130 g/kg = 13%. Copie os dados do produto comprado. Proteína e energia não informadas continuam vazias.')
        ca_lo=st.number_input('Cálcio mínimo',min_value=0.,value=float(anterior.get('Ca_min_pct',0.))*mult_unidade)
        ca_hi=st.number_input('Cálcio máximo',min_value=0.,value=float(anterior.get('Ca_max_pct',0.))*mult_unidade)
        p_n=st.number_input('Fósforo total mínimo',min_value=0.,value=float(anterior.get('P_total_pct',0.))*mult_unidade)
        pb_n=st.text_input('Proteína bruta (%) — deixe vazio se não informada',value='' if pd.isna(anterior.get('PB_pct')) else str(anterior['PB_pct']))
        em_n=st.text_input('Energia metabolizável (kcal/kg) — deixe vazio se não informada',value='' if pd.isna(anterior.get('EM_kcal_kg')) else str(anterior['EM_kcal_kg']))
        fonte_n=st.text_input('Identificação do rótulo / fabricante',value=str(anterior.get('Fonte','')))
        enviar=st.form_submit_button('Salvar meu núcleo')
    if enviar:
        try:
            if not nome.strip() or preco<=0 or dose_n<=0 or ca_lo<=0 or ca_hi<ca_lo or p_n<=0: raise ValueError('Preencha nome, preço, dose e garantias positivas; cálcio máximo deve ser maior ou igual ao mínimo.')
            fator=10 if unidade=='g/kg do produto' else 1
            try:
                pb_val=float(pb_n.replace(',','.')) if pb_n.strip() else None
                em_val=float(em_n.replace(',','.')) if em_n.strip() else None
            except ValueError: raise ValueError('Proteína e energia devem ser números ou campos vazios.')
            registro=dict(Ingrediente='Núcleo — '+nome.strip(),Ativo=False,Preco_kg=preco,PB_pct=pb_val,EM_kcal_kg=em_val,Ca_min_pct=ca_lo/fator,Ca_max_pct=ca_hi/fator,P_total_pct=p_n/fator,Inclusao_min_pct=dose_n/10,Inclusao_max_pct=dose_n/10,Fonte=fonte_n,Liberado=True,Criterio='Garantias do núcleo informadas pelo usuário; conferir rótulo e adequação à fase.')
            novo=cad[cad.Ingrediente!=alvo].copy() if anterior else cad.copy()
            if novo.Ingrediente.str.casefold().eq(registro['Ingrediente'].casefold()).any(): raise ValueError('Já existe um núcleo com esse nome.')
            st.session_state.cadastro_hyline_v1=validar(pd.concat([novo,pd.DataFrame([registro])],ignore_index=True));st.session_state.rev_total+=1;st.rerun()
        except ValueError as exc: st.error(str(exc))
    st.download_button('Baixar meu cadastro',cad.to_csv(index=False).encode('utf-8-sig'),'meu_cadastro_hyline_multvet.csv','text/csv')
    up=st.file_uploader('Restaurar preços e núcleos desta versão',type=['csv'])
    if up and st.button('Restaurar meu cadastro'):
        try:
            base_fixa=pd.read_csv(BASE/'data/ingredientes_hyline.csv')
            st.session_state.cadastro_hyline_v1=mesclar_cadastro(base_fixa,pd.read_csv(up));st.session_state.rev_total+=1;st.rerun()
        except ValueError as exc: st.error(str(exc))
with aba3:
    st.write('A base fixa não permite cadastro de novas matérias-primas pelo comprador. Núcleos podem ser cadastrados pelas garantias do rótulo. A edição 2009–2011 é uma referência histórica e não uma análise do lote comprado. As metas de postura continuam sendo da Embrapa 051.')
    st.write('Este cadastro permanece nesta sessão. Baixe o CSV para conservar os dados. Cadastros antigos com fósforo disponível não são importados como total. Escolha somente um núcleo por simulação. A alternativa com ressalvas mantém dose e limites de inclusão e reduz desvios relativos das metas conhecidas; ela pode continuar inviável se os limites não fecharem 100%.')
    st.write('No relatório, cálcio calculado é um intervalo; fósforo é total mínimo quando cadastrado com garantias mínimas. Atingir metas desses nutrientes não comprova uma ração completa. Revise os dados e todos os nutrientes antes do uso produtivo.')
