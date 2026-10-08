from io import BytesIO
from html import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from relatorio import numero

def gerar_pdf(r,tipo,fase,lote,nucleo,dose):
    buf=BytesIO(); styles=getSampleStyleSheet(); styles['Title'].textColor=colors.HexColor('#1F4A2B')
    styles['BodyText'].fontSize=9
    p=lambda s:Paragraph(escape(str(s)),styles['BodyText'])
    elements=[Paragraph('MULTVET | Aves Caipiras PRO',styles['Title']),p('Avaliação técnica - cálcio total e fósforo total'),Spacer(1,10)]
    for s in [f'{tipo} | {fase} | Lote: {numero(lote)} kg',f'{nucleo} | Dose: {numero(dose)} kg/tonelada','Mistura com desvios nutricionais - requer revisão técnica antes do uso.' if r['ressalvas'] else 'Solução matemática para as metas verificadas.']:
        elements += [p(s),Spacer(1,5)]
    for aviso in r.get("avisos",[]): elements += [p(aviso),Spacer(1,5)]
    def table(rows,widths):
        t=Table(rows,colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1F4A2B')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ALIGN',(1,0),(-1,-1),'RIGHT'),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F1E9')])]))
        return t
    rows=[['Ingrediente','%','kg','R$/kg','Custo R$']]
    for _,x in r['ingredientes'].iterrows(): rows.append([p(x.Ingrediente),numero(x.Inclusao_pct,3),numero(x.Kg_no_lote,3),numero(x.Preco_kg),numero(x.Custo)])
    rows.append(['TOTAL',numero(r['ingredientes'].Inclusao_pct.sum(),3),numero(lote,3),'',numero(r['custo_lote'])])
    elements +=[Spacer(1,10),table(rows,[185,75,85,70,108]),Spacer(1,12)]
    rows=[['Nutriente','Calculado*','Meta mín.','Meta máx.','Situação']]
    fmt=lambda x:'Não informado' if pd.isna(x) else numero(x,4)
    for _,x in r['conferencia'].iterrows():
        val=fmt(x.Min_calculado)
        if x.Nutriente=='Cálcio total': val+=' a '+fmt(x.Max_calculado)
        rows.append([p(x.Nutriente),p(val),p(fmt(x.Meta_min)),p(fmt(x.Meta_max)),p(x.Situacao.replace('.',','))])
    t=table(rows,[100,115,75,75,158])
    for i,(_,x) in enumerate(r['conferencia'].iterrows(),1):
        col='#FFE3D6' if 'Abaixo' in x.Situacao or 'Acima' in x.Situacao else '#FFF4CC' if x.Situacao=='Não verificado' or 'Parcial' in x.Situacao else '#EAF7E2'
        t.setStyle(TableStyle([('BACKGROUND',(0,i),(-1,i),colors.HexColor(col))]))
    elements +=[t,Spacer(1,10),p('* EM em kcal/kg; demais nutrientes em %. Cálcio: intervalo cadastrado. Fósforo total: usa os valores cadastrados, incluindo mínimos garantidos; não equivale a fósforo disponível.'),Spacer(1,8),p('Custo por kg: R$ '+numero(r['custo_kg'],4)),p('Custo do lote: R$ '+numero(r['custo_lote'])),Spacer(1,10),p('O modelo não verifica aminoácidos, sódio, vitaminas nem todos os nutrientes de uma ração completa. Dados ausentes e metas desativadas não são certificados. Fontes e garantias devem ser conferidas antes do uso produtivo. Valores arredondados apenas na apresentação.')]
    SimpleDocTemplate(buf,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36).build(elements)
    return buf.getvalue()
