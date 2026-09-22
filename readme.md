# Gestão-Fisio — Backend

API REST para fisioterapeutas e instrutores de Pilates autônomos que atuam em múltiplas clínicas,
com cálculo automático de receita por clínica, semana e mês.

Este é o backend de um sistema full-stack construído como projeto de portfólio, com foco em
fundamentos sólidos de **Django** e **Django REST Framework**. O [frontend em Angular](https://github.com/giovanigerci/gestao-fisio-frontend)
está em um repositório separado.

## O problema que o projeto resolve

Um profissional de fisioterapia/Pilates que atende em 2 ou 3 clínicas diferentes — cada uma
pagando um valor distinto por atendimento — perde facilmente o controle de quanto realmente
ganhou no mês. Isso piora quando há atendimentos em grupo (aulas de Pilates com vários pacientes
no mesmo horário) misturados com atendimentos individuais e aulas experimentais.

O sistema resolve isso agregando os agendamentos diretamente no backend, evitando duplicar
lógica de cálculo financeiro no frontend.

## Stack

| Camada         | Tecnologia                           |
|----------------|--------------------------------------|
| Backend        | Django 5.2 + Django REST Framework   |
| Banco de dados | PostgreSQL 16 (via Docker)           |
| Autenticação   | JWT via `djangorestframework-simplejwt`, entregue em cookies HttpOnly |
| Frontend       | Angular 22 (repositório separado)    |

## Arquitetura

O domínio foi dividido em apps Django com responsabilidade única:

| App              | Responsabilidade                                                          |
|------------------|---------------------------------------------------------------------------|
| `profissionais`  | Dados do profissional autenticado (extensão do `User` nativo do Django), autenticação via cookie, recuperação de senha e foto de perfil |
| `clinicas`       | Clínicas cadastradas por cada profissional, com valor por atendimento     |
| `pacientes`      | CRUD de pacientes, isolado por profissional                               |
| `agenda`         | Agendamentos, regras de horário, conflito, recorrência e marcação de sessão experimental |
| `financeiro`     | Camada de leitura/agregação de receita, construída sobre os dados de `agenda` |

O app `financeiro` não possui Models próprios — ele existe exclusivamente para agregar dados já
persistidos em `agenda`, mantendo a responsabilidade de **cálculo** separada da responsabilidade
de **CRUD**.

### Isolamento multi-tenant

Todos os dados (clínicas, pacientes, agendamentos) pertencem a um único profissional. Cada
`ViewSet` sobrescreve `get_queryset()` para filtrar os registros pelo profissional autenticado
(`self.request.user.profissional`), garantindo que um profissional nunca acesse dados de outro.

### Regra de negócio central: cálculo de receita por bloco

Um **bloco** é o conjunto de agendamentos de um mesmo profissional, mesma clínica, mesma data e
mesmo horário de início — o que permite representar atendimentos em grupo (Pilates) no mesmo
horário. A receita de um bloco é:

```
receita_do_bloco = valor_por_atendimento × count(agendamentos do bloco, excluindo eh_experimental=True)
```

**Exemplo:** às 14h, o profissional atende 3 pacientes na Clínica X (`valor_por_atendimento = R$ 40`),
sendo um deles uma sessão experimental. A receita do bloco é `R$ 80` (2 pacientes não-experimentais),
calculada em tempo real — nunca persistida no banco, já que é um dado derivado que pode mudar se o
valor por atendimento da clínica for reajustado.

O endpoint de resumo financeiro usa agregação agrupada do ORM (`values()` + `annotate()` +
`F()` + `TruncWeek`/`TruncMonth`) para consolidar a receita por clínica e por período,
sem trazer os registros para a aplicação e calcular em Python.

## Modelagem de dados

```
User (nativo do Django)
  └── Profissional (OneToOneField)
        ├── Clinica (ForeignKey)
        │     - nome, cor
        │     - valor_por_atendimento
        │     - ativo
        ├── Paciente (ForeignKey)
        │     - nome, telefone, data_nascimento, historico_medico
        └── Agendamento (ForeignKey: profissional, clinica, paciente)
              - data, hora_inicio, hora_fim
              - status ('AG' Agendado | 'RE' Realizado | 'CA' Cancelado)
              - eh_experimental (boolean)
              - grupo_recorrencia (UUID, nullable — para séries de recorrência)
```

A sessão experimental **não é um tipo de evento separado** — é um `Agendamento` comum marcado com
`eh_experimental=True`. Agendamentos experimentais são excluídos do cálculo de receita
(`valor_calculado = 0`), mas permanecem registrados para fins de acompanhamento.

## Autenticação

O sistema usa **JWT via `djangorestframework-simplejwt`**, mas os tokens são entregues como
**cookies HttpOnly** (não via header `Authorization`). Isso elimina a exposição dos tokens ao
JavaScript do navegador e mitiga ataques XSS.

O backend define uma classe customizada `CookieJWTAuthentication` (em `profissionais/authentication.py`)
que lê o `access_token` diretamente do cookie da requisição.

**Clientes que consomem a API devem:**
- Enviar requisições com credenciais: `credentials: "include"` (fetch) ou `withCredentials: true` (Angular `HttpClient`).
- **Não** enviar o header `Authorization: Bearer <token>` — ele é ignorado.

**Ciclo de vida dos tokens:**
- `access_token` expira em **5 minutos**.
- `refresh_token` expira em **1 dia** e é rotacionado a cada uso (`ROTATE_REFRESH_TOKENS = True`).
- O logout invalida o refresh token (blacklist via `rest_framework_simplejwt.token_blacklist`).

## Endpoints completos

### Autenticação (`/api/auth/`)

| Método      | Rota                             | Descrição                                       |
|-------------|----------------------------------|-------------------------------------------------|
| POST        | `/api/auth/registrar/`           | Cria `User` + `Profissional` numa transação     |
| POST        | `/api/auth/token/`               | Login — define cookies `access_token` + `refresh_token` |
| POST        | `/api/auth/token/refresh/`       | Renova o `access_token` via `refresh_token` no cookie |
| POST        | `/api/auth/logout/`              | Invalida o `refresh_token` e limpa os cookies   |
| GET / PATCH | `/api/auth/me/`                  | Perfil do profissional autenticado              |
| PUT         | `/api/auth/me/foto/`             | Upload ou remoção da foto de perfil             |
| POST        | `/api/auth/trocar-senha/`        | Troca de senha (requer senha atual)             |
| POST        | `/api/auth/esqueci-senha/`       | Solicita e-mail de recuperação de senha         |
| POST        | `/api/auth/redefinir-senha/`     | Redefine a senha via token do e-mail            |

### Clínicas (`/api/clinicas/`)

| Método          | Rota                        | Descrição                                    |
|-----------------|-----------------------------|----------------------------------------------|
| GET / POST      | `/api/clinicas/`            | Lista ou cria clínicas do profissional       |
| GET/PUT/PATCH/DELETE | `/api/clinicas/{id}/`  | Detalhe, atualização e remoção               |
| GET             | `/api/clinicas/opcoes/`     | Lista simplificada (id, nome, cor) para selects |

### Pacientes (`/api/pacientes/`)

| Método          | Rota                        | Descrição                                    |
|-----------------|-----------------------------|----------------------------------------------|
| GET / POST      | `/api/pacientes/`           | Lista ou cria pacientes do profissional      |
| GET/PUT/PATCH/DELETE | `/api/pacientes/{id}/` | Detalhe, atualização e remoção               |

### Agenda (`/api/agendamentos/`)

| Método          | Rota                           | Descrição                                         |
|-----------------|--------------------------------|---------------------------------------------------|
| GET / POST      | `/api/agendamentos/`           | Lista agendamentos (filtráveis por data, clínica) ou cria |
| GET/PUT/PATCH/DELETE | `/api/agendamentos/{id}/` | Detalhe, atualização e remoção                    |
| POST            | `/api/agendamentos/` (com `recorrencia`) | Cria série de agendamentos recorrentes |

### Financeiro

| Método | Rota                                          | Descrição                                  |
|--------|-----------------------------------------------|--------------------------------------------|
| GET    | `/api/resumo-financeiro/?periodo=mes`         | Receita agregada por clínica (mês atual)   |
| GET    | `/api/resumo-financeiro/?periodo=semana`      | Receita agregada por clínica (semana atual)|

Todas as rotas de domínio e financeiro exigem autenticação — o `access_token` deve estar presente
no cookie da requisição (enviado automaticamente pelo navegador quando `credentials: include`).

## Rodando o projeto localmente

### Pré-requisitos
- Python 3.11+
- Docker Desktop

### Passo a passo

```bash
# Clonar o repositório
git clone https://github.com/giovanigerci/gestao-fisio-backend.git
cd gestao-fisio-backend

# Criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source venv/bin/activate       # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
copy .env.example .env           # Windows
# cp .env.example .env           # Linux/Mac
# Editar .env com seus valores (ver seção abaixo)

# Subir o banco de dados via Docker
docker-compose up -d

# Aplicar as migrations
python manage.py migrate

# Criar um superusuário (opcional, para acessar o /admin/)
python manage.py createsuperuser

# Rodar o servidor de desenvolvimento
python manage.py runserver
```

A API estará disponível em `http://127.0.0.1:8000/api/`, com interface navegável (Browsable API)
do DRF em cada endpoint, e o Django Admin em `http://127.0.0.1:8000/admin/`.

### Variáveis de ambiente (`.env`)

Todas as variáveis estão documentadas em `.env.example`. As principais:

| Variável              | Obrigatória | Descrição                                            |
|-----------------------|-------------|------------------------------------------------------|
| `SECRET_KEY`          | ✅          | Chave secreta do Django                              |
| `DEBUG`               | —           | `True` em dev, `False` em produção (padrão: `False`) |
| `ALLOWED_HOSTS`       | —           | Hosts permitidos, separados por vírgula              |
| `POSTGRES_DB`         | ✅ (local)  | Nome do banco de dados                               |
| `POSTGRES_USER`       | ✅ (local)  | Usuário do PostgreSQL                                |
| `POSTGRES_PASSWORD`   | ✅ (local)  | Senha do PostgreSQL                                  |
| `POSTGRES_HOST`       | —           | Host do banco (padrão: `localhost`)                  |
| `DATABASE_URL`        | ✅ (produção) | URL completa do banco — substitui as vars `POSTGRES_*` se definida |
| `CORS_ALLOWED_ORIGINS`| —           | Origens permitidas para CORS (padrão: `http://localhost:4200`) |
| `COOKIE_SECURE`       | —           | `True` em produção com HTTPS, `False` em dev         |
| `COOKIE_DOMAIN`       | —           | Domínio dos cookies JWT (necessário em produção)     |
| `FRONTEND_URL`        | —           | URL do frontend para links de e-mail (padrão: `http://localhost:4200`) |
| `EMAIL_BACKEND`       | —           | Backend de e-mail (padrão: `console` — imprime no terminal) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | — | Configuração SMTP para envio de e-mails reais |

## Próximos passos

- [ ] Cobertura de testes automatizados (regras de cálculo de receita e isolamento multi-tenant)
- [ ] Pipeline de CI via GitHub Actions
- [ ] Documentação OpenAPI/Swagger
- [ ] Migrar armazenamento de mídia (fotos de perfil) para serviço externo (AWS S3 ou Cloudinary) — necessário para plataformas com filesystem efêmero
- [ ] Deploy em produção (configurar `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `COOKIE_SECURE=True`, banco de dados gerenciado)