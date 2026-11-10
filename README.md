# 🚀 SMARTDESK AI

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
- ⚛️ React 18
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
- Nginx
- PostgreSQL com volume persistente

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

Crie o arquivo `.env.docker` na raiz do projeto.

Exemplo de configuração:

```dotenv
POSTGRES_PASSWORD=substitua_por_uma_senha_forte
JWT_SECRET_KEY=substitua_por_um_segredo_aleatorio
OPENAI_API_KEY=sua_chave_openai

OPENAI_MODEL=gpt-6-luna
AI_TIMEOUT_SECONDS=15
AI_MAX_OUTPUT_TOKENS=300
AI_MAX_DESCRIPTION_CHARS=4000
AI_DAILY_USER_LIMIT=20
```

> ⚠️ Nunca publique o arquivo `.env.docker` ou suas credenciais no GitHub. A senha do PostgreSQL deve ser compatível com uma URL de conexão.

### 3️⃣ Construir e iniciar os contêineres

```bash
docker compose --env-file .env.docker -f compose.yml up -d --build
```

### 4️⃣ Aplicar as migrações do banco de dados

```bash
docker compose --env-file .env.docker -f compose.yml exec backend alembic upgrade head
```

### 5️⃣ Acessar a aplicação

Após iniciar os serviços e aplicar as migrações:

- 🌐 **Frontend:** http://localhost:8080
- 📚 **Documentação da API:** http://localhost:8080/api/v1/docs (verificar a configuração da rota de documentação do FastAPI)

### 6️⃣ Consultar os logs

```bash
docker compose --env-file .env.docker -f compose.yml logs -f backend
```

### 7️⃣ Encerrar os serviços

```bash
docker compose --env-file .env.docker -f compose.yml down
```

> 💾 O volume persistente do PostgreSQL é mantido. Não utilize `down -v` sem antes avaliar as consequências para os dados.

## 🧪 Testes e qualidade

O projeto utiliza testes automatizados para verificar autenticação, gerenciamento de chamados, permissões e integração com IA.

**Última validação registrada:**

- ✅ 186 testes de backend aprovados
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
├── compose.yml
├── .gitignore
└── README.md
```

## 🚀 Próxima atualização — SMARTDESK AI 2.0: evolução da IA

### 🧠 Uma Inteligência Artificial mais avançada

A próxima grande atualização será focada em **melhorar a Inteligência Artificial do SMARTDESK AI**, tornando a análise dos chamados mais contextualizada, útil e inteligente.

### 🔮 Funcionalidades planejadas

**🧠 1. Análise inteligente aprimorada**

Melhorar a capacidade da IA de compreender o problema relatado, identificar possíveis causas e produzir classificações mais precisas.

**💡 2. Sugestões automáticas de solução**

A IA poderá sugerir procedimentos técnicos e possíveis soluções para os chamados.

**📚 3. RAG — Recuperação de conhecimento**

Estudar a implementação de RAG (*Retrieval-Augmented Generation*) para permitir que a IA consulte uma base de conhecimento técnico antes de gerar recomendações.

**🤖 4. Agentes de IA**

Investigar o uso de agentes para executar fluxos controlados de diagnóstico, consulta e recomendação.

**🔍 5. Identificação de chamados semelhantes**

Utilizar técnicas de busca semântica para encontrar problemas já registrados e suas possíveis soluções.

**📊 6. Análises mais explicativas**

Evoluir as justificativas da IA, oferecendo recomendações mais transparentes e úteis para as equipes de suporte.

**💰 7. Otimização de custos**

Melhorar o uso dos modelos de linguagem para reduzir chamadas desnecessárias e controlar o consumo da API.

> 🚧 **Em desenvolvimento:** essas funcionalidades fazem parte do planejamento e ainda não estão disponíveis na versão atual.

## 🎯 Objetivo do projeto

O SMARTDESK AI também é um projeto de desenvolvimento e aprendizado prático, com foco em:

- Arquitetura Full Stack
- Desenvolvimento de APIs REST
- Segurança e autenticação
- Banco de dados relacional
- Testes automatizados
- Docker e infraestrutura
- Integração de LLMs
- Evolução para RAG e agentes de IA

## 👨‍💻 Desenvolvedor

**Sergio Henrique**

🔗 [GitHub — SMARTDESK AI](https://github.com/sergiohscl/smartdesk-ai)

---

⭐ **Se você gostou do projeto, deixe uma estrela no repositório!**

**SMARTDESK AI — Transformando chamados em soluções inteligentes.** 🤖
