# CosmoTech Infrastructure MCP

Servidor Python baseado no **Model Context Protocol (MCP)** para consultar, em modo somente leitura, informações de AWS, Kubernetes, Terraform, Git, Linux, Docker e observabilidade Kubernetes. Disponibiliza 19 ferramentas por STDIO local ou HTTP com autenticação.

**Estado:** MVP inicial. Integrações AWS e CLI locais implementadas; Kubernetes utiliza o contexto `kubectl` ativo. Ainda não há integrações nativas Azure/GCP, APIs específicas OpenShift, OAuth para clientes hospedados ou operações de escrita/automação.

## Funcionalidades

- Consultar identidade AWS e resumos de EKS, ECR, EC2, SQS, DynamoDB e IAM.
- Inspecionar saúde Kubernetes, recursos permitidos, logs recentes, descrições e releases Helm.
- Executar `terraform validate` e `plan` sem atualização de estado; não executa `init`, `apply`, `destroy` ou planos salvos.
- Consultar informações do Linux, metadados Docker, estado Git e disponibilidade de componentes de observabilidade.
- Restringir comandos e diretórios, ocultar possíveis segredos e registrar auditoria JSONL.

## Instalação rápida

**Pré-requisitos:** Python 3.12 ou superior e Git. AWS CLI e CLIs dos provedores são opcionais conforme as integrações utilizadas. Leia os guias de [instalação](docs/installation.md) e [configuração](docs/configuration.md).

```bash
git clone https://github.com/rlcosmo/cosmotech-infrastructure-mcp.git
cd cosmotech-infrastructure-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Configure o arquivo `.env` localmente, sem versionar credenciais. Para iniciar via STDIO:

```bash
.venv/bin/python -m cosmotech_mcp serve --transport stdio
```

Em seguida, configure seu cliente seguindo o [guia de clientes](docs/clients.md) e consulte os [exemplos](docs/examples.md). Para HTTP autenticado local, veja a [configuração HTTP](docs/clients.md#openai-codex-cli-local-streamable-http).

## Documentação

- [Instalação e pré-requisitos](docs/installation.md)
- [Configuração e credenciais](docs/configuration.md)
- [Clientes: Codex, ChatGPT, Claude Code e Cursor](docs/clients.md)
- [Exemplos de ferramentas](docs/examples.md)
- [Modelo de segurança](docs/security.md)
- [Solução de problemas](docs/troubleshooting.md)
- [Arquitetura e limitações](docs/architecture.md)
- [Registro de validações](docs/testing.md)

## Licença

MIT. Consulte [LICENSE](LICENSE).
