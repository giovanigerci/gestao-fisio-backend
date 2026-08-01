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

| Camada         | Tecnologia                          |
|----------------|--------------------------------------|
| Backend        | Django 5.2 + Django REST Framework   |
| Banco de dados | PostgreSQL 16 (via Docker)           |
| Autenticação   | JWT (`djangorestframework-simplejwt`)|
| Frontend       | Angular (repositório separado)       |

## Arquitetura

O domínio foi dividido em apps Django com responsabilidade única:

| App             | Responsabilidade                                                          |
|------------------|----------------------------------------------------------------------------|
| `profissionais`  | Dados do profissional autenticado (extensão do `User` nativo do Django)   |
| `clinicas`       | Clínicas cadastradas por cada profissional, com valor por atendimento     |
| `pacientes`      | CRUD de pacientes, isolado por profissional                               |
| `agenda`         | Agendamentos, regras de horário, status e marcação de aula experimental   |
| `financeiro`      | Camada de leitura/agregação de receita, construída sobre os dados de `agenda` |

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
receita_do_bloco = valor_por_atendimento × count(agendamentos do bloco, excluindo eh_gratuito=True)
```

**Exemplo:** às 14h, o profissional atende 3 pacientes na Clínica X (`valor_por_atendimento = R$ 40`),
sendo um deles uma aula experimental gratuita. A receita do bloco é `R$ 80` (2 pacientes pagantes),
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
        │     - valor_por_atendimento
        │     - ativo
        ├── Paciente (ForeignKey)
        └── Agendamento (ForeignKey: profissional, clinica, paciente)
              - data, hora_inicio, hora_fim
              - status (agendado, realizado, cancelado)
              - eh_experimental
              - eh_gratuito
```

A aula experimental **não é um tipo de evento separado** — é um `Agendamento` comum, marcado com
`eh_experimental=True`, que pode ou não ser gratuito (`eh_gratuito`). Quando gratuita, o
agendamento é excluído do cálculo de receita, mas permanece registrado para fins de
acompanhamento (ex: taxa de conversão de experimentais em pacientes fixos).

## Endpoints principais

### Autenticação
| Método | Rota                        | Descrição                                   |
|--------|------------------------------|----------------------------------------------|
| POST   | `/api/auth/registrar/`       | Cria `User` + `Profissional` numa transação  |
| POST   | `/api/auth/token/`           | Login — retorna par de tokens JWT             |
| POST   | `/api/auth/token/refresh/`   | Renova o access token                         |

### Domínio
| Método             | Rota                     | Descrição                          |
|---------------------|---------------------------|--------------------------------------|
| GET/POST            | `/api/clinicas/`          | Clínicas do profissional autenticado |
| GET/POST            | `/api/pacientes/`         | Pacientes do profissional autenticado|
| GET/POST            | `/api/agendamentos/`      | Agendamentos, com `valor_calculado` por item |
| PUT/PATCH/DELETE    | `.../{id}/`                | Detalhe, atualização e remoção       |

### Financeiro
| Método | Rota                                          | Descrição                          |
|--------|-------------------------------------------------|--------------------------------------|
| GET    | `/api/resumo-financeiro/?periodo=mes`           | Receita agregada por clínica (mês, padrão) |
| GET    | `/api/resumo-financeiro/?periodo=semana`        | Receita agregada por clínica (semana)      |

Todas as rotas de domínio e financeiro exigem autenticação via JWT (`Authorization: Bearer <token>`)
e retornam apenas dados pertencentes ao profissional autenticado.

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
# preencher POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

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

## Próximos passos

- [ ] Cobertura de testes automatizados (regras de cálculo de receita e isolamento multi-tenant)
- [ ] Pipeline de CI via GitHub Actions
- [ ] Documentação OpenAPI/Swagger