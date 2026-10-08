from pathlib import Path
import pandas as pd
import streamlit as st
from motor import calcular, validar, NUTRIENTES
from relatorio_total import gerar_pdf, numero
BASE=Path(__file__).resolve().parent
st.set_page_config(page_title='MultVet Aves Caipiras PRO',page_icon='🐔',layout='wide')
st.markdown('<style>.stApp{background:#E8DCC8} h1,h2,h3{color:#1F4A2B}</style>',unsafe_allow_html=True)
st.title('🐔 MultVet Aves Caipiras PRO')
st.caption('Modelo de avaliação técnica — cálcio total e fósforo total')
if (BASE/'assets/banner.png').exists(): st.image(str(BASE/'assets/banner.png'),use_container_width=True)
if 'cadastro_total_v1' not in st.session_state:
    st.session_state.cadastro_total_v1=pd.read_csv(BASE/'data/ingredientes_total.csv')
    st.session_state.rev_total=0
cad=st.session_state.cadastro_total_v1
aba1,aba2,aba3=st.tabs(['Formular ração','Minhas matérias-primas','Orientações'])
with aba1:
    tipo=st.radio('Finalidade',['Corte','Postura'],horizontal=True)
    fases=['Pré-inicial','Inicial','Crescimento/Engorda','Final/Abate'] if tipo=='Corte' else ['Postura']
    fase=st.selectbox('Fase',fases)
    nucleos=cad[cad.Ingrediente.str.contains('núcleo',case=False,na=False)]
    escolhido=st.selectbox('Núcleo para esta simulação',nucleos.Ingrediente.tolist()) if len(nucleos) else None
    dose_padrao={'Núcleo Inicial Corte':50.,'Núcleo Engorda Corte':50.,'Núcleo Abate Corte':40.,'Núcleo Postura':50.}
    dose=st.number_input('Dose do núcleo (kg/tonelada)',min_value=0.,max_value=1000.,value=dose_padrao.get(escolhido,0.),key='dose_'+str(escolhido))
    st.caption('Somente o núcleo selecionado entra no cálculo. Confira sua adequação à fase e a dose do rótulo.')
    lote=st.number_input('Quantidade do lote (kg)',min_value=1.,value=100.,step=25.)
    st.markdown('### Metas nutricionais')
    st.info('Não usamos as antigas metas de fósforo disponível como fósforo total. Defina metas com a mesma base dos ingredientes. Desmarcar uma meta deixa seu atendimento não verificado.')
    ref=pd.read_csv(BASE/'data/fases_corte.csv')
    linha=ref[ref.Fase==fase]
    padrao=linha.iloc[0] if len(linha) else {'PB_min':0.,'EM_min':0.,'Ca_min':0.}
    metas={}
    for k,(col,label) in NUTRIENTES.items():
        with st.expander(label,expanded=True):
            usar=st.checkbox('Verificar '+label,value=k in ['PB','EM'],key='usar_'+k+'_'+fase)
            a,b=st.columns(2)
            minimo=a.number_input('Mínimo'+(' (kcal/kg)' if k=='EM' else ' (%)'),min_value=0.,value=float(padrao.get(k+'_min',0.)),key='min_'+k+'_'+fase)
            limitar=b.checkbox('Definir máximo',key='maxon_'+k+'_'+fase)
            maximo=b.number_input('Máximo'+(' (kcal/kg)' if k=='EM' else ' (%)'),min_value=0.,value=float(padrao.get(k+'_min',0.)),key='max_'+k+'_'+fase)
            metas[k]=(minimo if usar else None,maximo if usar and limitar else None)
    st.caption('Valores iniciais de PB, EM e Ca são referências herdadas, pendentes de revisão. Não são novas recomendações. Desvios relativos têm pesos iguais no modo aproximado; o custo é minimizado depois dos desvios.')
    modo=st.radio('Modo de cálculo',['Atender às metas','Buscar alternativa com ressalvas'])
    dados=cad.copy()
    mask=dados.Ingrediente.str.contains('núcleo',case=False,na=False)
    dados.loc[mask,'Ativo']=False
    if escolhido:
        sel=dados.Ingrediente==escolhido
        dados.loc[sel,'Ativo']=True
        dados.loc[sel,['Inclusao_min_pct','Inclusao_max_pct']]=dose/10
    st.markdown('### Ingredientes disponíveis para esta simulação')
    st.dataframe(dados[dados.Ativo],hide_index=True,use_container_width=True)
    confirmar=st.checkbox('Conferi as composições, a base total dos minerais, o núcleo e os parâmetros desta simulação.')
    assinatura=(dados.to_csv(index=False),str(metas),tipo,fase,lote,dose,modo,confirmar)
    if st.session_state.get('assinatura_total')!=assinatura: st.session_state.pop('resultado_total',None)
    if st.button('FORMULAR',type='primary'):
        st.session_state.pop('resultado_total',None)
        if not confirmar or not escolhido or dose<=0: st.error('Confira os dados e informe um núcleo com dose positiva.')
        else:
            try:
                r=calcular(dados,metas,lote,modo=='Buscar alternativa com ressalvas')
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
            cor='#FFE3D6' if 'Abaixo' in row.Situacao or 'Acima' in row.Situacao else '#FFF4CC' if row.Situacao=='Não verificado' or 'Parcial' in row.Situacao else '#EAF7E2'
            return ['background-color: '+cor]*len(row)
        st.dataframe(r['conferencia'].style.apply(destaque,axis=1).format({c:lambda v:'Não informado' if pd.isna(v) else numero(v,4) for c in ['Min_calculado','Max_calculado','Meta_min','Meta_max']}),hide_index=True,use_container_width=True)
        st.metric('Custo por kg','R$ '+numero(r['custo_kg'],4));st.metric('Custo do lote','R$ '+numero(r['custo_lote']))
        export=tabela.to_csv(index=False,sep=';',decimal=',')+'\nConferência nutricional\n'+r['conferencia'].to_csv(index=False,sep=';',decimal=',')
        st.download_button('Baixar fórmula e conferência em CSV',export.encode('utf-8-sig'),'formula_total_multvet.csv','text/csv')
        st.download_button('Baixar relatório PDF',gerar_pdf(r,tipo,fase,lote,escolhido,dose),'relatorio_total_multvet.pdf','application/pdf')
with aba2:
    st.write('Proteína e energia ausentes somente no núcleo permitem simulação parcial: as respectivas metas ficam fora da otimização e o relatório mostra subtotais com ressalva. Valores em % do ingrediente. Campo vazio significa desconhecido; zero significa contribuição zero. Preencha o fósforo TOTAL de cada matéria-prima com fonte técnica. Núcleos têm garantias do usuário; demais dados são referências herdadas.')
    with st.form('salvar_total'):
        edit=st.data_editor(cad,num_rows='dynamic',hide_index=True,use_container_width=True,key='cad_total_'+str(st.session_state.rev_total))
        salvar=st.form_submit_button('Salvar alterações')
    if salvar:
        try:
            st.session_state.cadastro_total_v1=validar(edit);st.session_state.rev_total+=1;st.session_state.salvou_total=True;st.rerun()
        except ValueError as exc: st.error(str(exc))
    if st.session_state.pop('salvou_total',False): st.success('Cadastro salvo nesta sessão.')
    st.download_button('Baixar meu cadastro',cad.to_csv(index=False).encode('utf-8-sig'),'meus_ingredientes_total.csv','text/csv')
    up=st.file_uploader('Importar cadastro do modelo total',type=['csv'])
    if up and st.button('Importar cadastro'):
        try:
            st.session_state.cadastro_total_v1=validar(pd.read_csv(up));st.session_state.rev_total+=1;st.rerun()
        except ValueError as exc: st.error(str(exc))
with aba3:
    st.write('Este cadastro permanece nesta sessão. Baixe o CSV para conservar os dados. Cadastros antigos com fósforo disponível não são importados como total. Escolha somente um núcleo por simulação. A alternativa com ressalvas mantém dose e limites de inclusão e reduz desvios relativos das metas conhecidas; ela pode continuar inviável se os limites não fecharem 100%.')
    st.write('No relatório, cálcio calculado é um intervalo; fósforo é total mínimo quando cadastrado com garantias mínimas. Atingir metas desses nutrientes não comprova uma ração completa. Revise os dados e todos os nutrientes antes do uso produtivo.')
