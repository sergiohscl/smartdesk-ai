# 🚀 SMARTDESK AI

[![SMARTDESK AI - CI/CD](https://github.com/sergiohscl/smartdesk-ai/actions/workflows/ci-cd.yml/badge.svg?branch=main)](https://github.com/sergiohscl/smartdesk-ai/actions/workflows/ci-cd.yml)


### 🎫 Sistema inteligente de gerenciamento de chamados com Inteligência Artificial

O **SMARTDESK AI** é uma aplicação Full Stack desenvolvida para facilitar o gerenciamento de chamados de suporte técnico, combinando uma interface moderna, autenticação segura, controle de permissões e recursos de Inteligência Artificial.

O objetivo do projeto é evoluir um sistema tradicional de chamados para uma plataforma inteligente, capaz de auxiliar equipes de suporte na análise, classificação e priorização de solicitações.

## 🛠️ Tecnologias utilizadas

### ⚙️ Backend
- 🐍 Python 3.13
- ⚡ FastAPI
- 🗄️ PostgreSQL
- 🔗 SQLAlchemy (Async)
- 🔄 Alembic
- 🔐 JWT e RBAC
- 🧪 Pytest e Ruff
- 🤖 OpenAI API

### 🎨 Frontend
- ⚛️ React 19
- 📘 TypeScript
- ⚡ Vite
- 🎨 Tailwind CSS
- 🧩 shadcn/ui
- 🔀 TanStack Router
- 📡 TanStack Query
- 🌐 Axios

### 🐳 Infraestrutura
- Docker
- Docker Compose
- GitHub Actions (CI/CD)
- Docker Hub (registro de imagens)
- Nginx
- PostgreSQL com volume persistente
- Prometheus 3.5.0
- Grafana 12.1.1

## ✨ Funcionalidades implementadas

### 🔐 Autenticação e segurança

- Cadastro e login de usuários
- Autenticação com JWT
- Rotas protegidas
- Controle de acesso baseado em papéis (RBAC)
- Três perfis: `USER`, `SUPPORT` e `ADMIN`

### 🎫 Gerenciamento de chamados

- Criação, edição e exclusão de chamados
- Listagem e visualização detalhada
- Pesquisa por título
- Filtros por status e prioridade
- Paginação
- Indicadores estatísticos no dashboard
- Controle de permissões para edição e exclusão

### 🤖 Inteligência Artificial

Integração com modelos de linguagem da OpenAI para auxiliar na análise de chamados.

**Recursos disponíveis:**

- Classificação automática de prioridade
- Identificação da categoria do problema
- Justificativa da classificação
- Histórico de análises realizadas
- Aplicação manual da prioridade sugerida
- Registro de quem realizou e aplicou cada análise
- Controle de permissões para utilização da IA
- Tratamento de erros e logging seguro
- Limite diário configurável de utilização

A IA atua como ferramenta de apoio à decisão. A aplicação da prioridade sugerida depende de uma ação autorizada do usuário.

## 📊 Monitoramento e observabilidade

O SmartDesk AI possui monitoramento local com
Prometheus e Grafana.

### Recursos implementados

- Coleta de métricas HTTP.
- Monitoramento de latência e erros HTTP 5xx.
- Métricas de classificação por IA.
- Endpoint de métricas protegido.
- Dashboards provisionados automaticamente.
- Central de monitoramento com RBAC.
- Regras de alerta e testes automatizados.

### Serviços locais

| Serviço | Endereço |
|---|---|
| Frontend | http://localhost:8080 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

### Alertas configurados

- Backend indisponível.
- Taxa elevada de erros HTTP 5xx.
- Latência elevada.

O envio externo de notificações permanece fora
da implementação atual.

## 👥 Controle de permissões

| Funcionalidade | USER | SUPPORT | ADMIN |
|---|---|---|---|
| Visualizar chamados | ✅ | ✅ | ✅ |
| Criar chamados | ✅ | ✅ | ✅ |
| Editar próprios chamados | ✅ | ✅ | ✅ |
| Editar chamados de terceiros | ❌ | ✅ | ✅ |
| Analisar próprios chamados com IA | ✅ | ✅ | ✅ |
| Analisar chamados de terceiros com IA | ❌ | ✅ | ✅ |
| Aplicar prioridade em chamados de terceiros | ❌ | ✅ | ✅ |

## 🔄 CI/CD — GitHub Actions e Docker Hub

O SMARTDESK AI possui uma esteira automatizada em [GitHub Actions](https://github.com/sergiohscl/smartdesk-ai/actions/workflows/ci-cd.yml), definida em `.github/workflows/ci-cd.yml`.

| Job | Verificações |
|---|---|
| 🐍 **Backend** | Python 3.13, Poetry, Ruff (lint e formatação) e Pytest |
| ⚛️ **Frontend** | Node.js 24, `npm ci`, TypeScript, ESLint e build Vite |
| 🐳 **Docker** | Build das imagens de backend e frontend; publicação no Docker Hub somente em push para `main` |

- **Pull requests para `main`:** executam os testes e validam os builds Docker, sem publicar imagens.
- **Pushes para `main`:** publicam as imagens somente depois da aprovação dos jobs de backend e frontend (dependência `needs`).
- **Credenciais:** autenticação no Docker Hub com os secrets `DOCKER_USERNAME` e `DOCKER_TOKEN` do GitHub Actions. Não inclua credenciais no repositório.
- **Tags:** cada imagem é publicada como `latest` e `sha-<commit-sha>`, permitindo identificar a versão gerada por cada commit.

### 📦 Imagens no Docker Hub

| Serviço | Repositório |
|---|---|
| Backend — FastAPI | [sergiohscl/smartdesk-ai-backend](https://hub.docker.com/r/sergiohscl/smartdesk-ai-backend) |
| Frontend — React + Nginx | [sergiohscl/smartdesk-ai-frontend](https://hub.docker.com/r/sergiohscl/smartdesk-ai-frontend) |

Para baixar as versões mais recentes:

```bash
docker pull sergiohscl/smartdesk-ai-backend:latest
docker pull sergiohscl/smartdesk-ai-frontend:latest
```

> ℹ️ O CI/CD automatiza testes, builds e **publicação de imagens**. O **deploy automático em servidor de produção ainda não foi implementado**. Para executar a aplicação completa localmente, siga as instruções do Docker Compose abaixo.

## 🐳 Executando com Docker

### 📋 Pré-requisitos

- Git
- Docker
- Docker Compose

### 1️⃣ Clonar o repositório

```bash
git clone https://github.com/sergiohscl/smartdesk-ai.git

cd smartdesk-ai
```

### 2️⃣ Configurar as variáveis de ambiente

Crie o arquivo `backend/.env` a partir do exemplo:

```bash
cp -n backend/.env.example backend/.env
```

Edite o arquivo e configure as credenciais locais.

Exemplo de configuração:

```dotenv
POSTGRES_PASSWORD=substitua_por_uma_senha_forte
JWT_SECRET_KEY=substitua_por_um_segredo_aleatorio
OPENAI_API_KEY=

OPENAI_MODEL=gpt-6-luna
AI_TIMEOUT_SECONDS=15
AI_MAX_OUTPUT_TOKENS=300
AI_MAX_DESCRIPTION_CHARS=4000
AI_DAILY_USER_LIMIT=20
```

> ⚠️ Nunca publique o arquivo `backend/.env` ou suas credenciais no GitHub. A senha do PostgreSQL deve ser compatível com uma URL de conexão.

### Política de utilização da inteligência artificial

A variável `OPENAI_API_KEY` pode permanecer vazia
quando a classificação de chamados não for utilizada.

A integração existente com OpenAI pode gerar
cobranças externas de API.

O SmartDesk Assistant utilizará inferência local
com Ollama, sem fallback automático para
provedores pagos.

A integração local ainda está em desenvolvimento.

### Configurar os secrets de monitoramento

Para uma nova instalação Linux, instale o OpenSSL
caso ainda não esteja disponível.

Crie os diretórios:

```bash
mkdir -p monitoring/prometheus/secrets
mkdir -p monitoring/grafana/secrets
```

Gere os secrets sem sobrescrever arquivos existentes:

```bash
(
    umask 077
    set -C

    if [ ! -e monitoring/prometheus/secrets/metrics_token ]; then
        openssl rand -hex 32 > monitoring/prometheus/secrets/metrics_token
    fi

    if [ ! -e monitoring/grafana/secrets/admin_password ]; then
        openssl rand -hex 24 > monitoring/grafana/secrets/admin_password
    fi
)
```

Configure os grupos e as permissões:

```bash
sudo chgrp 999 monitoring/prometheus/secrets/metrics_token
sudo chgrp 472 monitoring/grafana/secrets/admin_password

chmod 640 monitoring/prometheus/secrets/metrics_token
chmod 640 monitoring/grafana/secrets/admin_password
```

O token de métricas é compartilhado entre o backend
e o Prometheus.

O secret do Grafana define a senha administrativa
inicial de uma instalação nova.

Não sobrescreva os secrets de uma instalação existente.

Os arquivos de secrets são ignorados pelo Git.
Nunca publique seus valores no repositório.

Estas permissões consideram Docker convencional
em Linux. Outros ambientes podem exigir adaptações.

### 3️⃣ Construir e iniciar os contêineres

```bash
docker compose --env-file backend/.env -f compose.yml up -d --build
```

### 4️⃣ Aplicar as migrações do banco de dados

```bash
docker compose --env-file backend/.env -f compose.yml exec backend alembic upgrade head
```

### 5️⃣ Acessar a aplicação

Após iniciar os serviços e aplicar as migrações:

- 🌐 **Frontend:** http://localhost:8080
- 📊 **Prometheus:** http://localhost:9090
- 📈 **Grafana:** http://localhost:3000

A documentação Swagger do FastAPI está disponível
internamente no backend, na rota `/docs`.

Na configuração Docker atual, essa rota não é
exposta pelo Nginx.

O acesso externo ao Swagger será tratado em uma
etapa futura, sem expor desnecessariamente o backend.

### 6️⃣ Consultar os logs

```bash
docker compose --env-file backend/.env -f compose.yml logs -f backend
```

### 7️⃣ Encerrar os serviços

```bash
docker compose --env-file backend/.env -f compose.yml down
```

> 💾 O volume persistente do PostgreSQL é mantido. Não utilize `down -v` sem antes avaliar as consequências para os dados.

## 🧪 Testes e qualidade

O projeto utiliza testes automatizados para verificar autenticação, gerenciamento de chamados, permissões e integração com IA.

**Última validação registrada:**

- ✅ 351 testes de backend aprovados
- ✅ Ruff sem erros
- ✅ TypeScript sem erros
- ✅ ESLint sem erros
- ✅ Build de produção concluído
- ✅ Integração Docker validada

Para executar os testes de backend no ambiente local configurado:

```bash
cd backend
poetry run pytest -v
```

Para validar o frontend:

```bash
cd frontend
npx tsc --noEmit -p tsconfig.app.json
npm run lint
npm run build
```

## 📂 Estrutura do projeto

```text
smartdesk-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   ├── Dockerfile
│   └── nginx.conf
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── compose.yml
├── .gitignore
└── README.md
```

## 🧠 Próxima atualização — SmartDesk Assistant

**Status: planejamento arquitetural e validação experimental.**

O SmartDesk Assistant será um chatbot especializado
em suporte técnico, utilizando inferência local.

### Tecnologias selecionadas

- Ollama.
- Qwen 2.5 7B.
- Quantização Q4_K_M.
- FastAPI Server-Sent Events.
- PostgreSQL.
- React e TypeScript.

### Funcionalidades planejadas

- Conversas privadas por usuário.
- Histórico persistente.
- Contexto conversacional.
- Respostas em streaming.
- Cancelamento e regeneração de respostas.
- Renderização Markdown e blocos de código.
- Sugestões de diagnóstico técnico.
- Abertura de chamados mediante confirmação.
- Limites de consumo e concorrência.
- Segurança e observabilidade.

### Arquitetura planejada

React → FastAPI → ChatService → AIProvider
→ OllamaProvider → Ollama → Qwen 2.5 7B.

O chatbot ainda não está disponível na aplicação.

A classificação existente com OpenAI permanece
independente e pode gerar cobranças de API.

RAG, bancos vetoriais, MCP e agentes autônomos
estão fora do escopo atual.

## 🧪 Benchmarks de IA local

Foram avaliadas 150 inferências em 10 cenários
de suporte técnico, com 3017 amostras de recursos.

### Comparação em condição Warm

| Métrica | 3B V1 | 7B V1 | 7B V2 |
|---|---:|---:|---:|
| TTFT mediano (s) | 0.642 | 1.122 | 1.516 |
| Tokens/s mediano | 16.45 | 5.85 | 6.39 |
| Tempo total mediano (s) | 25.443 | 61.102 | 59.564 |
| Pico amostrado de RAM (GiB) | 2.41 | 5.16 | 5.26 |
| Truncamento | 30% | 10% | 0% |

O Qwen 7B V2 foi selecionado para integração
experimental através do Ollama.

- Streaming válido: 30/30 na configuração V2.
- Truncamento observado: 0%.
- Cobranças externas de API: R$ 0,00.
- Fallback para provedores pagos: desabilitado.

A avaliação qualitativa permanece provisória.

O modelo não está aprovado para utilização
irrestrita em produção ou execução autônoma.

A inferência local utiliza recursos computacionais
e energia elétrica.

### Documentação técnica

- [ADR-001](docs/architecture/ADR-001-local-ai-provider.md)
- [Relatório dos benchmarks](docs/benchmarks/llm-benchmark-summary.md)

## 🎯 Objetivo do projeto

O SMARTDESK AI também é um projeto de desenvolvimento e aprendizado prático, com foco em:

- Arquitetura Full Stack
- Desenvolvimento de APIs REST
- Segurança e autenticação
- Banco de dados relacional
- Testes automatizados
- Docker e infraestrutura
- Integração de LLMs
- Observabilidade e monitoramento
- Inferência local com Ollama
- Desenvolvimento do SmartDesk Assistant
- Possível evolução futura para RAG e agentes de IA

## 📄 Licenciamento

O código-fonte do SmartDesk AI é disponibilizado
sob a Licença MIT.

O modelo Qwen 2.5 7B utiliza a licença Apache 2.0.

Os componentes externos permanecem sujeitos
às suas respectivas licenças.

- [Licença MIT](LICENSE)
- [Licença Qwen](docs/licenses/QWEN-APACHE-2.0.txt)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

Os pesos dos modelos não são distribuídos
no repositório.

## 👨‍💻 Desenvolvedor

**Sergio Henrique**

🔗 [GitHub — SMARTDESK AI](https://github.com/sergiohscl/smartdesk-ai)

---

⭐ **Se você gostou do projeto, deixe uma estrela no repositório!**

**SMARTDESK AI — Transformando chamados em soluções inteligentes.** 🤖
