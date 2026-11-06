# Inventário validado — CosmoTech AWS EKS

Consolidação das consultas: 2026-11-06T16:47:00.532753+00:00. Laboratório pessoal, ambiente DEV, região **us-east-1**. Consultas em instantes distintos; não constituem um snapshot transacional. IDs de conta/recurso, endereços IP, CIDRs privados e identidades pessoais foram omitidos. A evidência reproduz os fatos necessários ao case, não um backup de configuração.

## Escopo e fontes

Foram consultados AWS/EKS/EC2/ECR/SQS/DynamoDB, metadados de Secrets Manager, Pod Identity, IAM OIDC, DNS/TLS, AWS Backup, Kubernetes e Helm; Argo CD e GMUDs por consultas no host existente. Apenas GETs, listagens, comandos de inspeção e SQLite `mode=ro`. Não foram executados deploys, rollback, coleta de mensagens ou escrita em dados de negócio. NLB e CloudTrail permaneceram fora da investigação.

Fontes: [inventário sanitizado](evidence/inventory-current.json), [Argo CD](evidence/argocd-current.json), [telemetria](evidence/observability-current.json), [releases](evidence/releases-current.json), [heads locais](evidence/repository-heads.json). Arquivos Terraform/configuração descrevem intenção; presença na AWS/Kubernetes comprova provisionamento; dados de consulta comprovam apenas a operação observada.

## Rede, exposição e segurança

A VPC do laboratório tem **quatro subnets em duas AZs**: duas públicas e duas privadas. Há um Internet Gateway, um NAT Gateway disponível e três route tables. Rotas padrão públicas usam IGW e privadas usam NAT. Não há VPC Endpoints no inventário consultado. Há outra VPC na região, fora do desenho EKS.

| Subnet lógica | Zona | Tipo |
| --- | --- | --- |
| aws-eks-istio-lab-dev-private_b | us-east-1b | privada |
| aws-eks-istio-lab-dev-private_a | us-east-1a | privada |
| aws-eks-istio-lab-dev-public_a | us-east-1a | pública |
| aws-eks-istio-lab-dev-public_b | us-east-1b | pública |

Os nós e os três servidores de ferramentas estão em subnets privadas, sem IP público. O NAT único concentra a saída; não apresentar a rede como tolerante à perda de qualquer AZ. O acesso público usa DNS CosmoTech, TLS e roteamento da borda existente para Istio/ferramentas. Ingresses, gateways e Terraform comprovam a configuração; esta rodada não auditou o load balancer ou a política WAF em runtime.

O endpoint Kubernetes está habilitado em modo público e privado. A allowlist de rede pública é ampla; autenticação/autorização continuam exigidas. É um ponto de endurecimento pendente, não evidência de isolamento privado absoluto. Oito security groups da VPC foram inspecionados por metadados; não foi realizada auditoria completa das políticas IAM/rede.

Route 53: registros públicos consultados sem publicar valores sensíveis. ACM: certificado wildcard CosmoTech em estado ISSUED. HTTPS foi validado nos endpoints listados; portal e API Kestra anônimos retornaram 401. Um HTTP 200 de página/login não comprova toda a funcionalidade do produto.

## EKS e capacidade

**Kubernetes 1.37**, plataforma eks.7, cluster ACTIVE. EKS Auto Mode desabilitado. Managed node group Spot `c7i-flex.large`: mínimo1, desejado3, máximo3; três nós Ready distribuídos entre duas AZs. AMI AL2023. Não foi feito teste de perda de nó/AZ, SLA ou benchmark de disponibilidade.

| Nó anonimizado | Zona | Kubelet | Ready |
| --- | --- | --- | --- |
| node-1 | us-east-1a | v1.37.1-eks-6e7947a | True |
| node-2 | us-east-1a | v1.37.1-eks-6e7947a | True |
| node-3 | us-east-1b | v1.37.1-eks-6e7947a | True |

Add-ons presentes: aws-ebs-csi-driver, coredns, eks-pod-identity-agent, kube-proxy, snapshot-controller, vpc-cni. Node Exporter e Alloy são DaemonSets. EBS CSI Windows pode ter zero nós elegíveis; zero desejado nesse DaemonSet não comprova falha.

| Recurso Kubernetes | Quantidade |
| --- | --- |
| Namespace | 13 |
| Deployment | 20 |
| ReplicaSet | 40 |
| Pod | 46 |
| Node | 3 |
| Service | 40 |
| Ingress | 6 |
| StatefulSet | 4 |
| DaemonSet | 7 |
| HorizontalPodAutoscaler | 4 |
| PersistentVolumeClaim | 11 |
| StorageClass | 2 |
| ServiceAccount | 86 |
| NetworkPolicy | 1 |

**Duas aplicações de negócio**, três Deployments de negócio contando a candidata Canary; os outros17 Deployments são infraestrutura/ferramentas. São duas Applications Argo CD de negócio. Não confundir20 Deployments com20 microsserviços nem40 ReplicaSets totais do cluster com o limite por Deployment das aplicações.

## Namespaces e Deployments

Namespaces: `cosmotech-recovery`, `default`, `external-integration`, `istio-system `, `kube-node-lease`, `kube-public`, `kube-system `, `kyverno`, `loki`, `observability`, `orders-api`, `orders-worker`, `platform-system `.

| Namespace | Deployment | Desejadas | Prontas | Históricos permitidos | ReplicaSets |
| --- | --- | --- | --- | --- | --- |
| istio-system | istio-ingressgateway | 1 | 1 | 10 | 1 |
| istio-system | istiod | 1 | 1 | 10 | 1 |
| kube-system | aws-load-balancer-controller | 2 | 2 | 10 | 2 |
| kube-system | cluster-autoscaler | 1 | 1 | 10 | 4 |
| kube-system | coredns | 2 | 2 | 10 | 2 |
| kube-system | ebs-csi-controller | 2 | 2 | 10 | 1 |
| kube-system | metrics-server | 1 | 1 | 10 | 1 |
| kube-system | snapshot-controller | 2 | 2 | 10 | 1 |
| kyverno | kyverno-admission-controller | 1 | 1 | 10 | 1 |
| kyverno | kyverno-background-controller | 1 | 1 | 10 | 1 |
| kyverno | kyverno-cleanup-controller | 1 | 1 | 10 | 1 |
| kyverno | kyverno-reports-controller | 1 | 1 | 10 | 1 |
| loki | loki-gateway | 1 | 1 | 10 | 1 |
| observability | otel-collector-opentelemetry-collector | 1 | 1 | 10 | 5 |
| observability | prometheus-grafana | 1 | 1 | 10 | 6 |
| observability | prometheus-kube-prometheus-operator | 1 | 1 | 10 | 1 |
| observability | prometheus-kube-state-metrics | 1 | 1 | 10 | 1 |
| orders-api | orders-api | 2 | 2 | 2 | 3 |
| orders-worker | orders-worker | 1 | 1 | 2 | 3 |
| orders-worker | orders-worker-canary | 0 | 0 | 2 | 3 |

Nos Deployments Orders: API 2/2 em dois nós/zonas; Worker 1/1; Canary 0/0 após rollback da candidata 1.0.6. **Não existe padrão global de dois pods já concluído.** Manter duas réplicas estáveis é uma intenção parcialmente aplicada; o Canary tem ciclo próprio0→1→2→0. Não alteramos escala nesta preparação.

Retenção aplicada: `revisionHistoryLimit: 2` nos três Deployments Orders. Atual mais dois históricos, com excesso temporário possível durante rollout incompleto. A Application Worker pode exibir seis ReplicaSets porque contém dois Deployments. Publisher/coletor protegidos normalizam a regra no fluxo oficial futuro. Recursos criados fora desse fluxo não possuem política de admissão de retenção implantada.

HPAs atuais:

| Namespace | HPA | Mínimo | Máximo |
| --- | --- | --- | --- |
| istio-system | istio-ingressgateway | 1 | 5 |
| istio-system | istiod | 1 | 5 |
| orders-api | orders-api | 2 | 2 |
| orders-worker | orders-worker | 1 | 4 |

## Services, Ingress e mesh

| Namespace | Ingress | Classe | Hosts |
| --- | --- | --- | --- |
| istio-system | grafana-public | alb | grafana.cosmotechsolutions.com.br, prometheus-aws-eks-istio-lab-dev.cosmotechsolutions.com.br, alertmanager.cosmotechsolutions.com.br, tempo.cosmotechsolutions.com.br |
| istio-system | management-tools-public | alb | glpi.cosmotechsolutions.com.br, kestra.cosmotechsolutions.com.br, argocd.cosmotechsolutions.com.br |
| istio-system | zabbix-public | alb | zabbix.cosmotechsolutions.com.br |
| observability | zabbix-legacy-redirect | alb | zabix.cosmotechsolutions.com.br |
| orders-api | orders-api-dev | alb | orders-api-dev.cosmotechsolutions.com.br |
| orders-worker | orders-worker-dev | alb | orders-worker-dev.cosmotechsolutions.com.br |

40 Services catalogados individualmente no JSON. Orders API/Worker usam ClusterIP; a presença do Service Worker não o transforma em processador HTTP de pedidos. Istio tem ingress gateway e sidecars 1.31.3; o Canary Worker compete pela mesma fila SQS, sem pesos HTTP do Istio. Uma NetworkPolicy foi observada; isso não comprova segmentação abrangente de todos os namespaces.

## Storage, dados e serviços gerenciados

Quatro StatefulSets (Prometheus, Alertmanager, Loki, Tempo); onze PVCs Bound, incluindo seis de recuperação. Grafana usa PVC RWO e SQLite, com uma instância. Não afirmar HA de todas as ferramentas. EBS gp3 e snapshots/backups constam de configuração e metadados; existência de backup não comprova restauração bem-sucedida nesta rodada.

| Namespace | PVC | Tamanho | Acesso | Estado |
| --- | --- | --- | --- | --- |
| cosmotech-recovery | recovered-alertmanager | 2Gi | ReadWriteOnce | Bound |
| cosmotech-recovery | recovered-grafana | 5Gi | ReadWriteOnce | Bound |
| cosmotech-recovery | recovered-loki | 10Gi | ReadWriteOnce | Bound |
| cosmotech-recovery | recovered-prometheus | 10Gi | ReadWriteOnce | Bound |
| cosmotech-recovery | recovered-tempo | 10Gi | ReadWriteOnce | Bound |
| cosmotech-recovery | recovered-tempo-consistent | 10Gi | ReadWriteOnce | Bound |
| loki | storage-loki-0 | 10Gi | ReadWriteOnce | Bound |
| observability | alertmanager-prometheus-kube-prometheus-alertmanager-db-alertmanager-prometheus-kube-prometheus-alertmanager-0 | 2Gi | ReadWriteOnce | Bound |
| observability | grafana-data | 5Gi | ReadWriteOnce | Bound |
| observability | prometheus-prometheus-kube-prometheus-prometheus-db-prometheus-prometheus-kube-prometheus-prometheus-0 | 10Gi | ReadWriteOnce | Bound |
| observability | storage-tempo-0 | 10Gi | ReadWriteOnce | Bound |

ECR: dois repositórios Orders, tags IMMUTABLE, scan-on-push e criptografia AES256. Deployments usam tags legíveis; digest verificado e persistido no processo controlado. Scan obrigatório Trivy e scan ECR não são a mesma verificação.

SQS: fila Orders EKS e DLQ ativas, criptografia gerenciada SQS, visibility 180 s na principal, retenção 4 dias e maxReceiveCount 5. DLQ retém 14 dias. Backlog aproximado zero no snapshot EKS. Duas filas adicionais do laboratório serverless separado não pertencem ao fluxo EKS; sua DLQ tinha uma mensagem e não foi consumida.

DynamoDB EKS: tabela orders-data ACTIVE/PAY_PER_REQUEST, sem stream. **TTL desabilitado na tabela EKS**; a existência de atributo TTL no código não significa expiração operacional. PITR não foi confirmado pelo retorno do conector; não anunciar recuperação pontual habilitada. Outra tabela serverless tem TTL habilitado e pertence ao laboratório separado. Não foram lidos itens.

Um bucket S3 na conta suporta o backend Terraform segundo a configuração; nome sanitizado. AWS Backup tem plano diário ITSM com execução registrada em 06/11; não foi validada restauração nesta preparação. KMS é usado nas integrações previstas no Terraform, sem exportação de chaves ou IDs.

## IAM, OIDC e segredos

Seis associações Pod Identity presentes: API, Worker, Cluster Autoscaler, EBS CSI, Alertmanager e AWS Load Balancer Controller. OIDC está presente na conta; workflows GitHub usam federação OIDC para credenciais temporárias. Não confundir esse OIDC com o modo Pod Identity dos workloads. Anotações IRSA legadas, se existentes, estão separadas na evidência; não são prova de uso ativo.

| Namespace | ServiceAccount | Role lógica |
| --- | --- | --- |
| kube-system | cluster-autoscaler | aws-eks-istio-lab-dev-cluster-autoscaler-role |
| kube-system | ebs-csi-controller-sa | aws-eks-istio-lab-dev-ebs-csi-driver |
| observability | prometheus-kube-prometheus-alertmanager | cosmotech-alertmanager-notifications |
| orders-api | orders-api-sa | aws-eks-istio-lab-dev-orders-api-role |
| orders-worker | orders-worker-sa | aws-eks-istio-lab-dev-orders-worker-role |
| kube-system | aws-load-balancer-controller | AWSLoadBalancerControllerRole |

Secrets Manager: 14 registros de metadados na região. Nenhum valor de secret foi exportado. Credenciais protegidas e sessões/CSRF/auditoria pertencem ao portal existente; a integração de consulta Kestra OSS não é RBAC nativo multiusuário. Kyverno está implantado; presença do controlador não equivale a políticas Deny para todos os controles.

## Servidores de ferramentas e versões

| Servidor lógico | Tipo | Estado | Zona |
| --- | --- | --- | --- |
| cosmotech-eks-dev-worker | c7i-flex.large | running | us-east-1b |
| cosmotech-itsm-dev | t3.large | running | us-east-1a |
| cosmotech-eks-dev-worker | c7i-flex.large | running | us-east-1a |
| cosmotech-argocd-dev | t3.large | running | us-east-1a |
| cosmotech-zabbix-dev | m7i.xlarge | running | us-east-1a |
| cosmotech-eks-dev-worker | c7i-flex.large | running | us-east-1a |

Argo CD 3.6.1 roda em k3s no servidor EC2 dedicado, **fora do EKS**. ITSM hospeda GLPI/Kestra/portal e bancos de suporte; Zabbix roda em outro EC2. HTTP 200 do Zabbix comprova endpoint acessível; integração OTel/APM está configurada, sem comprovação completa de ingestão por esta preparação.

| Release Helm | Namespace | Chart | App version | Estado |
| --- | --- | --- | --- | --- |
| alloy | observability | alloy-1.15.0 | v1.21.3 | deployed |
| aws-load-balancer-controller | kube-system | aws-load-balancer-controller-3.6.2 | v3.6.2 | deployed |
| kyverno | kyverno | kyverno-3.9.2 | v1.19.2 | deployed |
| loki | loki | loki-20.2.1 | 3.7.9 | deployed |
| otel-collector | observability | opentelemetry-collector-0.178.2 | 0.163.2 | deployed |
| prometheus | observability | kube-prometheus-stack-92.17.0 | v0.94.2 | deployed |
| tempo | observability | tempo-3.2.1 | 3.1.1 | deployed |

Versões adicionais observadas: Grafana 13.3.0 por API health, Prometheus 3.15.1 por imagem, Alertmanager 0.34.2 por imagem, Argo CD 3.6.1 por imagem. Kestra OSS 2.0.8 é a versão confirmada no histórico de protocolo existente; GLPI tem objeto Change real, mas a versão exata da imagem não foi identificada nesta rodada. Não derivar versão de IDs locais de imagem Docker.

## Custos e limites

[Consulta financeira](evidence/costs-current.json): coletor existente de Cost Explorer, cache de 2026-11-06T15:20:07.404046+00:00. Acumulado estimado da conta no mês: **US$ 46,21 bruto**, US$ 46,21 em créditos aplicados; líquido aproximadamente US$ 0,00 por créditos, com resíduo numérico no valor líquido da série. Não é previsão mensal, custo isolado EKS, preço sustentável sem créditos ou economia obtida pela retenção de ReplicaSets.

Principais fontes potenciais de custo: seis EC2 em execução, EKS control plane, NAT, borda, EBS/backups, telemetria e serviços gerenciados. Não houve nova consulta paga Cost Explorer nesta tarefa: foram lidas métricas do coletor existente. Nenhum recurso criado, deployment ou rollback executado. Custos marginais de chamadas de leitura não foram isolados.

## Estados que não devem ser promovidos a conclusão

- Bedrock opcional e desabilitado; sem chamadas novas. Não desenhar IA como gate ativo.
- HA global de ferramentas, duas réplicas globais e isolamento de rede abrangente: não concluídos.
- Crítica customizada: código/testes isolados; não há cinco GMUDs reais encerradas com sucesso para comprovar autorização automática integrada.
- Observação 12 h e rollback humano pós-promoção: não validados como ciclo completo no conjunto atual.
- Capturas de UI: pendentes; ver roteiro manual. Diagramas são arquitetura explicativa, não screenshots.
