# MultVet Aves Caipiras PRO — versão de avaliação técnica

Aplicação Streamlit com motor de custo mínimo para PB, EM, cálcio e fósforo disponível.

## Executar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Organização no GitHub
Coloque app.py, validacao.py, requirements.txt e README.md na raiz. Mantenha os três CSV dentro de data/ e banner.png dentro de assets/.

## Alterações
- Validação de nomes, campos numéricos, limites e ingredientes ativos.
- Dose fixa do núcleo informada em kg/tonelada; conversão para porcentagem por divisão por 10.
- Limites máximos ajustáveis de cálcio e fósforo disponível.
- Exportação da fórmula e exportação/importação do cadastro.
- Arte e paleta MultVet.

## Antes do uso produtivo
As tabelas foram preservadas do projeto anterior e NÃO estão certificadas como valores nutricionais validados. Rever especialmente o fósforo disponível dos vegetais, valores de energia, referências por fase e garantias do núcleo. Os limites máximos inicialmente iguais aos mínimos são parâmetros de teste, não recomendações nutricionais. Não há restrições de aminoácidos, sódio, cloro, vitaminas ou todos os microminerais. Uma solução matemática não comprova uma ração completa. Não usar matrizes de fitase sem validação.

Referência de consulta: https://www.infoteca.cnptia.embrapa.br/handle/doc/1122469

## Salvamento
O cadastro permanece na sessão. Para guardar alterações, use Baixar meu cadastro e depois Recuperar cadastro salvo. Não há banco de dados, login ou integração de pagamento nesta versão. A fórmula pode desaparecer ao interagir com outros controles; exporte o resultado após calcular.

## Imprimir relatório
Após formular, clique em Baixar relatório em PDF para imprimir. Abra o PDF baixado e use Ctrl+P. O relatório inclui finalidade, fase, lote, ingredientes, nutrientes, limites e custos. Inclua relatorio.py na raiz e atualize requirements.txt no GitHub.
