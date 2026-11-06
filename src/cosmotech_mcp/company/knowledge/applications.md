# Catálogo das aplicações

Duas aplicações de negócio Python 3.12, com imagens independentes; um terceiro Deployment representa o canal Canary do mesmo Worker. Os repositórios ainda contêm handlers Lambda e código compartilhado, mas isso não comprova execução Lambda no fluxo EKS. O servidor HTTP atual é `http.server.HTTPServer` da biblioteca padrão, **não FastAPI/Spring**.

## Orders API — entrada e consulta de pedidos

**Problema:** aceitar pedidos sem aguardar todo o processamento e permitir consulta do resultado. Recebe HTTP, valida tamanho/esquema, normaliza itens e publica evento na SQS. Retorna 202 quando aceito; consulta DynamoDB por identificador. Healthchecks e limites de requisição fazem parte do runtime.

- Linguagem/framework: Python 3.12, HTTPServer/BaseHTTPRequestHandler, boto3 e OpenTelemetry.
- Endpoints: `POST /orders`, `GET /orders/{id}`, `/health/live`, `/health/ready`, `/version`, `/diagnostics/ping`.
- Comunicação: cliente→borda/Istio→Service API; API→SQS; API→DynamoDB para leitura. Diagnóstico de conectividade não é transação de negócio.
- AWS: ECR, SQS, DynamoDB e Pod Identity. IAM separado da role Worker.
- Deploy: CI real→GLPI/RCL→gate Kestra→aprovação humana autenticada→publisher GitOps assinado→Argo CD→RollingUpdate. Criticidade CRÍTICA; não tem Canary.
- Estado consultado:2.0.4-lab, tag `api-2.0.4-lab-20`, 2/2 pods em dois nós/zonas, RCL000009/GLPI 13 em observação. A release_pipeline SUCCESS não encerra a GMUD.
- Observabilidade: traces OTel, logs coletados pelo Alloy, métricas de Kubernetes/Istio e consultas Prometheus. Readiness HTTP do código não testa todas as dependências AWS; não anunciar monitoramento funcional completo.
- Rollback: versão/bundle anterior pelo fluxo protegido, sujeito a identidade, elegibilidade, ausência de concorrência e janela 12 h; GitOps é dono do estado.
- Disponibilidade: duas instâncias e RollingUpdate; teste de perda de nó/AZ não executado. API serial por processo: não apresentar como dimensionamento de produção.

Fontes: `cosmotech-orders-api/src/orders/runtime/api.py`, workflows e [snapshot](evidence/inventory-current.json).

## Orders Worker — processamento assíncrono

**Problema:** concluir pedidos tolerando reentrega, falhas de persistência e interrupções. Faz long polling da mesma SQS; só confirma/apaga a mensagem após processamento concluído. DynamoDB mantém pedidos, checkpoints, estoque e controle de idempotência/lease com operações condicionais/transações.

- Linguagem: Python 3.12, boto3, consumidor próprio, HTTP de health/metrics da biblioteca padrão. Não é servidor HTTP de pedidos.
- Eventos: mensagem Order validada v2; tentativas limitadas, visibility 180 s e DLQ após cinco recebimentos conforme configuração SQS.
- Comunicação: SQS→Worker→DynamoDB; métricas `cosmotech_worker_*` expostas em `/metrics`; `/version` e probes em 8000.
- Processamento: pagamento e expedição são **simulações explícitas** no código. Estoque/checkpoints em DynamoDB são reais no laboratório. Não há provedor de pagamento/logística integrado a anunciar.
- Deploy: pipeline e gate únicos, política NÃO CRÍTICA permite automática quando controles passam. Mudanças sensíveis podem exigir humano mesmo nessa categoria; a RCL000010 recebeu decisão humana por mudança de HPA.
- Estado atual: stable 1.0.5, tag `worker-1.0.5-16`, 1/1 pod. Canary 1.0.6 existe, 0/0 após rollback, RCL000010/GLPI 14. A CI 1.0.6 passou; isso não significa promoção bem-sucedida.
- Observabilidade: Prometheus coleta contadores de mensagens/erros/retries/inflight, histogramas e heartbeat; Loki agrega logs; OTel exporta traces. A amostra atual não substitui janela Canary histórica.
- Rollback: drenar candidato, esperar inflight, controlar lease/visibility e restaurar bundle/digest pelo publisher. Idempotência reduz efeitos duplicados da entrega ao menos uma vez; não afirmar exatamente uma vez ponta a ponta.
- Disponibilidade: fila desacopla entrada/processamento e tolera reentrega; um stable atual **não é redundância de consumidores**. Três nós prontos não tornam automaticamente o Worker altamente disponível.

Fontes: `cosmotech-orders-worker/src/orders/runtime/{worker,controlled_consumer,worker_metrics}.py`, `consumer/{processing,idempotency}.py`.

## Orders Worker Canary — canal temporário

É outro Deployment da mesma aplicação, com ServiceAccount/recursos do Worker, não um terceiro microsserviço independente. Compete por mensagens SQS com stable; **não há percentual de tráfego HTTP**. Receber uma fração observada de mensagens depende da concorrência e da fila, não de um peso de roteador.

Ciclo controlado 0→1→2 consumidores candidatos, coleta de amostras, promoção e drenagem para 0. Lease ausente/inválida implica drain. Gatilhos consideram disponibilidade, heartbeat, amostra mínima, falhas/ack/poll/visibility/retries/DynamoDB, p95 e DLQ. Falta de evidência não autoriza avanço.

RCL000008/1.0.5 concluiu Canary com carga sintética em serviços AWS reais. RCL000010/1.0.6 terminou ROLLED_BACK; candidata atual inativa. Não reconstruímos imagem, geramos carga ou executamos rollback para preparar o material.

## Ferramentas internas e aplicações de suporte

| Componente | Papel e tecnologia | Integração/estado | Disponibilidade e limites |
|---|---|---|---|
| Portal CosmoTech | Python, autenticação e interface de releases | RCL, etapas, links GLPI/Kestra/Argo, aprovação/rollback | Serviço ativo no EC2 ITSM; não é autoridade GitOps; identidade/CSRF preservados |
| Kestra | Orquestração OSS 2.0.8 | Gate único, release_pipeline e scheduler persistente | Execuções técnicas separadas; SUCCESS não é GMUD encerrada; RBAC nativo limitado |
| GLPI | Registro ITSM, objeto Change | RCL corporativo sobre ID nativo, planos/auditoria/estado | Registro oficial; cache consulta não autoriza promoção; versão exata não revalidada |
| Argo CD | Controlador GitOps 3.6.1 | Dois apps Synced/Healthy no EKS | k3s dedicado em EC2, não HA comprovada |
| Grafana | Visualização 13.3.0 | Fontes Prometheus/Loki/Tempo e 35 ConfigMaps de dashboards | SQLite/PVC RWO, uma instância; captura manual e catálogo API completo pendentes |
| Prometheus / Alertmanager | Métricas e alertas | Targets, regras, painéis; notificações SNS previstas/ensaiadas historicamente | Retenção/dependências limitadas do laboratório; não há SLA 24x7 demonstrado |
| Loki / Alloy | Logs e coleta DaemonSet | Consulta agregada de logs Orders disponível | Não exportar mensagens brutas com possíveis identificadores |
| Tempo / OTel Collector | Traces e OTLP | Exportação configurada para Tempo e APM Zabbix | Diferenciar consulta real de traces de configuração de exporter |
| Zabbix | Monitoramento em EC2 e configuração APM | Endpoint HTTPS 200, código/config presente | Não inferir ingestão APM integral nem disponibilidade de todos os hosts |
| Coletor de laboratório | Python/AWS CLI, timer e cache | Inventário, custos Cost Explorer e saúde→Prometheus | Custos estimados da conta; falha não vira custo zero |
| Istio / Kyverno / CSI / CNI | Plataforma | Mesh, admissão, storage e rede | Componentes de suporte; instalação não comprova política Deny global |

Services e todos os Deployments de suporte estão enumerados no inventário JSON. Não foi encontrado outro microsserviço de negócio ativo no conjunto consultado. Recursos do laboratório serverless separado não são apresentados como aplicações EKS.

[Fluxo de dados editável](architecture/C-applications.svg) · [PNG](architecture/C-applications.png).
