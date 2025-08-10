# Projeto Integrador — Visão Geral (para utilizadores)

## O que é
Uma aplicação web que **ajuda a transformar questionários em PDF** (ex.: formulários de saúde) em metadados. O sistema identifica perguntas e opções de resposta, atribui identificadores consistentes e **gera um ficheiro Excel** com os dados organizados. Também guarda os resultados numa base de dados para consulta futura.

## Para quem é
- Estudantes e equipas académicas que recolhem dados a partir de questionários;
- Profissionais que precisam de padronizar questionários e exportar resultados para Excel/BD;
- Quem quer **menos trabalho manual** a copiar/colar perguntas e respostas.

## O que dá para fazer
- **Upload de PDF** de um questionário;
- **Pré‑visualização** do que será extraído (modo “Preview”);
- **Processamento automático** e exportação para Excel (modo “Automático”);
- **Atribuição de identificadores** às perguntas (útil para cruzamentos e consistência);
- **Histórico de uploads** por utilizador e gestão básica de perfil (nome, avatar).

## Como funciona (passo a passo)
1. **Entrar na aplicação:** abre o site do Projeto Integrador. Podes **registar** uma conta ou **iniciar sessão**.
2. **Ir a “Ingestão / Upload”:** escolhe o ficheiro **PDF** do questionário.
3. **Escolher o modo:**
   - **Preview** — mostra uma pré‑visualização dos blocos (perguntas e respostas). Podes rever e depois avançar para o processamento.
   - **Automático** — processa diretamente e gera o Excel.
4. **Acompanhar o progresso:** a aplicação mostra quando o motor interno está pronto e o andamento do processamento.
5. **Descarregar o Excel:** quando terminar, o Excel fica disponível para download.
6. **Consultar histórico:** a área de perfil mostra a lista de PDFs enviados por ti (com data/hora).

## O que é gerado
- Um ficheiro **Excel** com as perguntas (e, quando aplicável, opções de resposta);
- Registos na base de dados para permitir consistência de identificadores e consultas futuras.

## Onde ficam os meus ficheiros
- Os PDFs enviados e os Excel gerados são **guardados no servidor da aplicação** para que possas descarregar depois.
- As informações de conta (nome, email, palavra‑passe cifrada) e o histórico de uploads ficam na **base de dados** da aplicação.

## Boas práticas para PDFs
- Prefere **PDFs digitais** (não digitalizações com baixa qualidade).
- Evita fontes muito decorativas; títulos e perguntas claras funcionam melhor.
- Se o questionário tiver muitas páginas, o **Preview** ajuda a confirmar se a extração está a sair correta.

## Limitações conhecidas
- PDFs com **qualidade muito baixa** ou com formatação incomum podem exigir revisão manual.
- A ferramenta foi pensada para **questionários**. Documentos livres (ex.: relatórios) podem ter resultados limitados.
- O processamento ocorre no servidor; **não feches a página** até o upload terminar.

## Perguntas frequentes (resumo)
- **Qual é a diferença entre “Preview” e “Automático”?** O *Preview* mostra um rascunho do que será extraído; o *Automático* já exporta para Excel.
- **Onde está o download?** Na página principal, aparece quando o processamento termina.
- **E se algo vier errado?** Refaz com *Preview* e ajusta o PDF/orientações.
- **Posso ver os uploads antigos?** Sim, no teu perfil aparece o histórico.

---

**Dica:** para melhores resultados, começa com um PDF de questionário claro e usa o modo *Preview* no primeiro envio.
