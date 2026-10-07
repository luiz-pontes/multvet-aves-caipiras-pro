from io import BytesIO
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def numero(v, casas=2):
    return f'{float(v):,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def gerar_pdf(resultado, tipo, quantidade):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=40)
    estilos = getSampleStyleSheet()
    estilos['Title'].textColor = colors.HexColor('#1F4A2B')
    estilos['Heading2'].textColor = colors.HexColor('#1F4A2B')
    texto = lambda t: Paragraph(escape(str(t)), estilos['BodyText'])
    elementos = [Paragraph('MULTVET | Aves Caipiras PRO', estilos['Title']), texto('Relatório de formulação - avaliação técnica'), Spacer(1, 12)]
    for item in [f'Finalidade: {tipo}', f'Fase: {resultado["fase"]["Fase"]}', f'Lote: {numero(quantidade)} kg', 'Emitido em: '+datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')]:
        elementos.append(texto(item))
    elementos += [Spacer(1, 14), Paragraph('Ingredientes da mistura', estilos['Heading2'])]
    dados = [['Ingrediente', 'Inclusão (%)', 'Peso (kg)', 'R$/kg', 'Custo (R$)']]
    for _, r in resultado['ingredientes'].iterrows():
        dados.append([texto(r['Ingrediente']), numero(r['Inclusao_pct'], 3), numero(r['Kg_no_lote'], 3), numero(r['Preco_kg']), numero(r['Custo'])])
    dados.append(['TOTAL', numero(resultado['ingredientes'].Inclusao_pct.sum(), 3), numero(resultado['ingredientes'].Kg_no_lote.sum(), 3), '', numero(resultado['custo_lote'])])
    def tabela(dados, larguras):
        t = Table(dados, colWidths=larguras, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1F4A2B')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(1,0),(-1,-1),'RIGHT'),('ALIGN',(0,0),(0,-1),'LEFT'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F1E9')]),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
        return t
    elementos += [tabela(dados,[185,85,85,70,98]), Spacer(1,14), Paragraph('Composição nutricional e limites',estilos['Heading2'])]
    dados=[['Nutriente','Calculado','Mínimo','Máximo']]
    for key,nome,un in [('PB','Proteína bruta','%'),('EM','Energia metabolizável','kcal/kg'),('Ca','Cálcio','%'),('P_disp','Fósforo disponível','%')]:
        fase=resultado['fase']; mx=fase.get(key+'_max')
        dados.append([nome,numero(resultado['nutrientes'][key])+' '+un,numero(fase[key+'_min'])+' '+un,numero(mx)+' '+un if mx is not None else 'Não definido'])
    elementos += [tabela(dados,[185,115,115,108]),Spacer(1,14),Paragraph('Custos',estilos['Heading2']),texto('Custo por kg: R$ '+numero(resultado['custo_kg'],4)),texto('Custo do lote: R$ '+numero(resultado['custo_lote'])),Spacer(1,14),texto('Observação: solução matemática para os parâmetros informados. Tabelas pendentes de revisão nutricional. O modelo não verifica todos os nutrientes necessários a uma ração completa. Conferir núcleo, garantias dos ingredientes e parâmetros antes do uso produtivo.'),Spacer(1,8),texto('Valores arredondados apenas na apresentação; os cálculos utilizam a precisão integral.')]
    def rodape(canvas, doc):
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#7A5A3A'))
        canvas.drawString(36,22,'MultVet - Consultoria e Gestão da Produção Animal')
        canvas.drawRightString(A4[0]-36,22,f'Página {doc.page}')
    doc.build(elementos,onFirstPage=rodape,onLaterPages=rodape)
    return buf.getvalue()
