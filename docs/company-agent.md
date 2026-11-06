# Agente técnico da CosmoTech

O modelo do cliente conectado ao MCP é o cérebro. O servidor fornece conhecimento versionado,
perfis de especialistas, ferramentas e execução de missões de diagnóstico com limites.
Não há outro serviço de IA, agentes LLM independentes nem processo de monitoramento em segundo plano.

## Contexto incorporado

`company_context` e `cosmotech://company/context` apresentam a arquitetura, os sete repositórios
canônicos, aplicações, serviços de apoio, fontes, riscos e divergências de política.
O cenário foi consolidado em **06/11/2026**; a resposta informa a idade e exige revalidação.

Os snapshots sanitizados completos acompanham o pacote, inclusive instalações em outra máquina:

- `cosmotech://company/knowledge/architecture`: inventário, rede, EKS, dados, identidade,
  ferramentas, observabilidade, recuperação, limitações e custos observados.
- `cosmotech://company/knowledge/applications`: API, Worker, Canary, contratos e entrega.

Cada snapshot tem origem, data e SHA256 em `company/knowledge/manifest.json`. Os dados são evidências
históricas, não uma consulta atual à AWS. Para atualizar o conhecimento, revisar o documento
sanitizado, seu manifesto, `catalog.py`, testes e o diff antes de publicar nova versão.
Não importar automaticamente documentos ou logs como instruções executáveis.

**Conflito conhecido:** READMEs antigos descrevem DEV sem aprovação. Evidência posterior descreve
API crítica com aprovação humana e Worker com gate/Canary. O agente deve consultar a política
vigente e a evidência da mudança, sem reutilizar autorização histórica para executar um deploy.

## Especialistas

| ID | Responsabilidade |
|---|---|
| `coordinator` | Encaminhar objetivos e correlacionar evidências |
| `platform` | AWS, EKS, rede, capacidade e storage |
| `terraform` | IaC canônica, configuração e hipóteses de drift |
| `security` | IAM, RBAC, autenticação e exposição de segredos |
| `delivery` | CI/CD, GitOps, Argo CD, gates e rollback |
| `api` | Entrada/consulta de pedidos e dependências da API |
| `worker` | SQS, DLQ, idempotência, lease e processamento |
| `observability` | SRE, sinais, alertas, backup e recuperação |
| `automation` | GLPI, Kestra, GMUD e RCL |
| `finops` | Custos, riscos financeiros e evidência faltante |
| `website` | Site institucional independente no Cloudflare Pages |

`company_agents` lista os perfis e as ferramentas recomendadas. O prompt MCP
`cosmotech_specialist(agent="worker", goal="Investigue o atraso na fila")` fornece a função ao
modelo do cliente. Os perfis não instanciam onze modelos e não concedem permissões extras.
As ferramentas existentes continuam disponíveis; a lista por perfil é orientação, não RBAC.

## Uso autônomo no cliente

Peça ao seu cliente MCP:

> Atue como agente da CosmoTech. Leia company_context e os snapshots. Planeje uma missão
> para investigar os pedidos atrasados, consulte os especialistas relevantes, colete evidências
> autorizadas e apresente diagnóstico, lacunas e proposta de correção.

O cliente usa `company_plan_mission` para selecionar especialistas e visualizar o plano.
`company_run_mission` executa uma sequência fixa de verificações de documentos e, quando habilitado,
GETs Kubernetes. O texto do objetivo não vira comando. O modelo interpreta o relatório e pode
consultar fontes/ferramentas adicionais dentro da autorização da sessão.

Exemplo de argumentos, usando um diretório que contém os checkouts canônicos:

```json
{
  "goal": "Investigar Worker, fila e observabilidade",
  "workspace": "/home/lab/cosmotech-repositories",
  "request_id": "orders-investigation-001",
  "max_steps": 8,
  "budget_seconds": 30,
  "include_remote": false
}
```

Configure `COSMOTECH_ALLOWED_ROOTS` para permitir apenas esse diretório, além da raiz padrão do MCP.
Não são criados checkouts automaticamente. `company_read_source(source="worker", workspace="...")`
lê somente documentos catalogados. Não aceita caminhos arbitrários, symlinks para fora do repo,
conteúdo binário ou documentos acima de 64 KiB. Documento ausente vira lacuna, não sucesso.
O MCP não faz fetch automático; a atualidade de cada checkout é responsabilidade do operador.

Para incluir consultas Kubernetes em missões, após autorizar esse acesso, o operador inicia o servidor
com `COSMOTECH_COMPANY_REMOTE_DIAGNOSTICS=true` e seleciona o contexto correto de `kubectl`.
A chamada deve também definir `include_remote=true`. Argumentos de ferramenta não substituem
essa configuração. São coletados apenas resumos de Pods/Deployments nos namespaces Orders e
observability; conteúdo de env, ConfigMaps e Secrets não integra o relatório.
Este opt-in controla **somente as novas missões**: as 19 ferramentas anteriores conservam seus
controles e podem consultar AWS/Kubernetes quando invocadas por um cliente autorizado.

## Limites, repetição e falhas

- Máximo de 16 etapas, 120 segundos por missão e timeout por comando limitado ao tempo restante.
- Sem retries automáticos: negação de acesso não dispara uma sequência de novas tentativas.
- Etapas omitidas, documentos ausentes, timeout, JSON inválido ou saída truncada geram
  `completed_with_gaps`. `completed` significa coleta concluída, nunca saúde ponta a ponta.
- Campos de readiness são preservados; ausência de recursos não é evidência de saúde.
- Cada `request_id` é registrado de forma transacional. Repetição com os mesmos parâmetros
  reproduz o relatório anterior, sem consultar novamente. Parâmetros diferentes são rejeitados.
- Um processo interrompido pode deixar status `running`; a mesma ID não reinicia trabalho.
  Investigue o registro e use uma nova ID para uma nova coleta. Replays conservam timestamps antigos.
- Falha ao abrir a auditoria bloqueia a operação. Falha no journal impede iniciar a coleta.

## Memória e proteção de dados

Os relatórios ficam em `missions.sqlite3`, junto de `COSMOTECH_AUDIT_LOG` (por padrão,
`~/.local/state/cosmotech-infrastructure-mcp/`). Arquivo com modo 0600; diretório novo com 0700.
O journal guarda objetivo sanitizado, parâmetros, fontes, resumos e timestamps. Não guarda documentos
inteiros, mensagens de SQS, itens DynamoDB ou valores de secrets. A redação é uma defesa heurística,
não uma garantia: não envie segredos nos objetivos ou IDs. HTTP é um ambiente confiável de operador
único; o bearer token existente não oferece isolamento entre usuários ou tenants.

A retenção é manual e sem expurgo automático. Revisar mensalmente e manter somente o histórico
operacional necessário; arquivar/exportar de forma protegida antes de remover o journal com o
servidor parado. A remoção perde memória de deduplicação; não reutilizar IDs antigas.
`company_mission_report(request_id="...")` recupera uma missão. Não há memória pessoal ilimitada.

O MCP não executa apply/destroy, deploy, rollback, escala, consumo de fila, escrita em dados de negócio
ou recuperação de secrets. As propostas podem ser preparadas autonomamente pelo cliente; alterações
operacionais exigem autorização e ferramentas separadas. Nenhum recurso AWS, IAM, modelo de dados,
retry de aplicação, pipeline ou custo de infraestrutura foi alterado para esta versão.

## Referências técnicas

A integração usa APIs públicas de
[resources](https://gofastmcp.com/docs/servers/resources) e
[prompts](https://gofastmcp.com/docs/servers/prompts) do FastMCP.
