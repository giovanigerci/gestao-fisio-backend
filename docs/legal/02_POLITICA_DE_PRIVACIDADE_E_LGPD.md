# Política de Privacidade e Proteção de Dados Pessoais (LGPD) — Gestão Fisio

*Última atualização: 24 de Setembro de 2026*  
*Versão: 1.1*

A presente **Política de Privacidade e Proteção de Dados Pessoais** ("Política") tem como objetivo informar, de maneira clara, objetiva e transparente, como o **Gestão Fisio** ("Nós" ou "Plataforma") coleta, utiliza, armazena, compartilha e protege os dados pessoais e dados pessoais sensíveis dos seus Usuários e respectivos pacientes, em estrita conformidade com a **Lei Geral de Proteção de Dados Pessoais (Lei Federal nº 13.709/2018 — LGPD)**, o **Marco Civil da Internet (Lei Federal nº 12.965/2014)** e os regulamentos editados pela **Autoridade Nacional de Proteção de Dados (ANPD)**.

---

## 1. Glossário Essencial

Para a melhor compreensão deste documento, aplicam-se as seguintes definições previstas no Art. 5º da LGPD:
- **Dado Pessoal**: Informação relacionada a pessoa natural identificada ou identificável (ex: nome, CPF, e-mail, telefone).
- **Dado Pessoal Sensível**: Dado pessoal sobre origem racial ou étnica, convicção religiosa, opinião política, filiação a sindicato ou a organização de caráter religioso, filosófico ou político, **dado referente à saúde** ou à vida sexual, dado genético ou biométrico.
- **Titular**: Pessoa natural a quem se referem os dados pessoais que são objeto de tratamento (o Profissional e o Paciente).
- **Tratamento**: Toda operação realizada com dados pessoais, como coleta, produção, recepção, classificação, utilização, acesso, reprodução, transmissão, distribuição, processamento, arquivamento, armazenamento, eliminação, avaliação ou controle da informação, modificação, comunicação, transferência, difusão ou extração.
- **Controlador**: Pessoa natural ou jurídica a quem competem as decisões referentes ao tratamento de dados pessoais.
- **Operador**: Pessoa natural ou jurídica que realiza o tratamento de dados pessoais em nome do Controlador.
- **Encarregado de Proteção de Dados (DPO)**: Pessoa indicada para atuar como canal de comunicação entre o Controlador, os titulares dos dados e a ANPD.

---

## 2. Divisão de Papéis e Responsabilidade sob a LGPD

No ecossistema do **Gestão Fisio**, os papéis jurídicos distribuem-se da seguinte forma:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DADOS DO PROFISSIONAL (USUÁRIO CADASTRADO NO SAAS)       │
│    Controlador: Plataforma Gestão Fisio                     │
│    Finalidade: Execução do contrato de SaaS, gestão de      │
│                acesso, faturamento e segurança de rede.     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. DADOS DO PACIENTE (PRONTUÁRIO, HISTÓRICO E AGENDA)       │
│    Controlador: O Profissional Fisioterapeuta / Clínica     │
│    Operador:    Plataforma Gestão Fisio                     │
│    Finalidade: O Gestão Fisio armazena e processa dados sob │
│                as instruções técnicas exclusivas do         │
│                fisioterapeuta, sem finalidade própria.      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Dados Coletados, Finalidades e Bases Legais

### 3.1. Dados Tratados dos Profissionais de Saúde (Usuários)

| Dado Coletado | Finalidade | Base Legal (LGPD) |
| :--- | :--- | :--- |
| **Nome de Usuário e Senha (*hash* PBKDF2)** | Autenticação, controle de sessão e segurança da conta. | Execução de Contrato (Art. 7º, V) |
| **Telefone** | Contato direto, segurança e validação cadastral (obrigatório no cadastro). | Execução de Contrato (Art. 7º, V) |
| **CREFITO e Especialidade** | Validação mandatória de registro de classe e regularidade perante o COFFITO/CREFITO. | Cumprimento de Obrigação Legal e Legítimo Interesse (Art. 7º, II e IX) |
| **Nome, Sobrenome e E-mail (Perfil)** | Identificação nominal do profissional e envio de tokens de redefinição de senha. | Execução de Contrato (Art. 7º, V) |
| **Foto de Perfil** (opcional) | Personalização visual da interface do profissional. A imagem é guardada em serviço de armazenamento de arquivos em nuvem, sob um endereço (URL) aleatório que não revela o nome original do arquivo; quem tiver esse endereço consegue visualizá-la. O profissional pode removê-la a qualquer momento, o que exclui o arquivo definitivamente. | Execução de Contrato (Art. 7º, V) |
| **Endereço IP, Data/Hora e Logs de Conexão** | Rastreabilidade de transações e cumprimento obrigatório do Marco Civil da Internet. | Cumprimento de Obrigação Legal (Art. 7º, II c/c Art. 15 da Lei nº 12.965/2014) |

### 3.2. Dados Tratados dos Pacientes (Inseridos pelo Profissional)

| Dado Coletado | Categoria | Finalidade | Base Legal (LGPD) |
| :--- | :--- | :--- | :--- |
| **Nome, CPF, Data de Nascimento** | Dado Pessoal Comum | Identificação inequívoca do paciente, prontuário e emissão de recibos. | Tutela da Saúde (Art. 11, II, "f") e Obrigação Legal (Art. 7º, II) |
| **Telefone e E-mail** | Dado Pessoal Comum | Contato para agendamentos, confirmações de horário e avisos clínicos. | Tutela da Saúde (Art. 11, II, "f") e Contrato |
| **Endereço Residencial** | Dado Pessoal Comum | Prontuário, faturamento e atendimentos domiciliares (*home care*). | Execução de Contrato / Tutela da Saúde |
| **Histórico Médico e Queixas Clínicas** | **DADO PESSOAL SENSÍVEL DE SAÚDE** | Composição do prontuário fisioterapêutico, registro de patologias pregressas, diagnósticos e evolução clínica. | **Tutela da Saúde em procedimento realizado por profissionais de saúde (Art. 11, II, "f")** e Resolução COFFITO nº 414/2012 |
| **Agendamentos (Data, Hora, Status e Flag Experimental)** | Dado Pessoal / Operacional | Controle de sessões (`AGENDADO`, `REALIZADO`, `CANCELADO`), presença e apuração da receita do profissional. | Tutela da Saúde (Art. 11, II, "f") e Cumprimento de Obrigação Legal |

> [!IMPORTANT]
> **Proibição de Fins Comerciais e Publicitários**: Os dados de saúde dos pacientes jamais são comercializados, cedidos a terceiros, utilizados para treinamento de inteligência artificial de terceiros ou utilizados para fins de publicidade dirigida.

---

## 4. Como os Dados São Protegidos (Segurança da Informação Implementada)

O Gestão Fisio implementa controles técnicos defensivos consolidados diretamente no código da aplicação e banco de dados:

1. **Isolamento Estrito de Dados Multi-tenant**: Toda consulta aos modelos de dados (`Clinica`, `Paciente`, `Agendamento`) é filtrada obrigatoriamente pela chave estrangeira do profissional autenticado (`request.user.profissional`), impedindo no nível de banco de dados que um profissional acerte ou visualize registros de outro.
2. **Criptografia de Senhas (PBKDF2 com Salt)**: As credenciais de acesso são submetidas a algoritmos criptográficos irreversíveis de derivação de chaves homologados pelo Django, com validação mínima de complexidade.
3. **Autenticação Segura por Cookies HttpOnly (`CookieJWTAuthentication`)**: O sistema não armazena tokens em `localStorage` ou `sessionStorage`. Utiliza cookies protegidos com `HttpOnly=True`, `SameSite='Lax'` e `Secure` em produção, transmitidos via HTTPS (`withCredentials: true`), com validade de 5 minutos para `access_token` e rotação automática de `refresh_token`.
4. **Proteção Ativa contra Ataques de Força Bruta (Rate Limiting/Throttling)**: A API restringe requisições automatizadas abusivas com limites estritos: máximo de 5 tentativas por minuto para login, 3 por minuto para registro de contas e 3 por hora para solicitações de reset de senha.
5. **Comunicação Segura (TLS/HTTPS) e CORS Restritivo**: Tráfego integralmente cifrado em trânsito com origens de requisição restritas às URLs autorizadas do frontend (`CORS_ALLOWED_ORIGINS`).
6. **Logs de Auditoria e Acesso**: Registros invioláveis de data, hora, IP de origem e rota acessada são mantidos de forma protegida para cumprimento do Art. 15 da Lei nº 12.965/2014.

---

## 5. Compartilhamento de Dados com Terceiros

Os dados tratados pelo Gestão Fisio são compartilhados estritamente na medida técnica necessária para a operacionalização dos serviços, limitando-se a:

1. **Infraestrutura de Hospedagem e Banco de Dados PostgreSQL**: Servidores dedicados ao processamento da aplicação e persistência do banco relacional, operando com regras de firewall e isolamento de rede.
2. **Serviço de Correio Eletrônico Transacional (SMTP)**: Utilizado exclusivamente para envio de links autenticados de redefinição de senha requisitados pelo próprio profissional.
3. **Armazenamento de Arquivos em Nuvem**: Utilizado exclusivamente para guardar a foto de perfil enviada pelo próprio profissional. Não recebe dados de pacientes.
4. **Hospedagem da Interface Web**: Entrega ao navegador os arquivos da aplicação e recebe apenas dados técnicos de acesso (como endereço IP e data/hora). Não tem acesso aos dados de pacientes, que trafegam diretamente entre o navegador e a API.
5. **Autoridades Judiciais e Regulatórias**: Mediante ordem judicial fundamentada ou solicitação formal expedida pela ANPD ou conselhos de fiscalização profissional (COFFITO/CREFITO).

A Plataforma **NÃO vende, NÃO aluga e NÃO monetiza** dados pessoais de qualquer natureza.

---

## 6. Retenção e Descarte de Dados

6.1. **Dados dos Profissionais**: Serão mantidos enquanto o cadastro estiver ativo. Após o encerramento da conta, os dados cadastrais serão eliminados ou anonimizados, ressalvada a guarda obrigatória dos registros de conexão por 6 (seis) meses (Art. 15 da Lei nº 12.965/2014) e dados fiscais/tributários pelo prazo prescricional aplicável.

6.2. **Dados dos Pacientes e Prontuários**: Por imposição legal e ética dos conselhos de saúde (Resolução COFFITO nº 414/2012 e legislação correlata), os prontuários de pacientes devem ser guardados pelo prazo mínimo regulamentar de **20 (vinte) anos** a contar do último atendimento. Caso o Profissional decida encerrar sua conta no Gestão Fisio, será disponibilizado mecanismo de exportação integral das fichas clínicas de seus pacientes para que ele continue garantindo a custódia legal dos prontuários em seus arquivos próprios.

---

## 7. Direitos dos Titulares de Dados (Profissionais e Pacientes)

Nos termos do Artigo 18 da LGPD, o Titular de dados pessoais possui os seguintes direitos garantidos:
- **Confirmação e Acesso**: Confirmar a existência de tratamento e obter cópia dos dados tratados;
- **Correção**: Solicitar a retificação imediata de dados incompletos, inexatos ou desatualizados;
- **Anonimização, Bloqueio ou Eliminação**: De dados desnecessários, excessivos ou tratados em desconformidade com a LGPD;
- **Portabilidade**: Solicitar a exportação dos seus dados em formato estruturado e legível por máquina;
- **Informação sobre Compartilhamento**: Saber com quais entidades públicas ou privadas os dados foram compartilhados;
- **Revogação do Consentimento**: Revogar autorizações anteriormente concedidas, quando essa tiver sido a base legal aplicada.

### 7.1. Como Exercer Seus Direitos

- **Profissionais**: Podem visualizar e retificar seus dados cadastrais diretamente na aba "Perfil" da Plataforma ou acionar o Encarregado pelo canal de privacidade.
- **Pacientes**: Visto que o Controlador primário do prontuário é o seu fisioterapeuta, o paciente deve, preferencialmente, direcionar a solicitação de acesso ou correção diretamente ao profissional responsável por seu atendimento. Caso a solicitação seja encaminhada ao canal do Gestão Fisio, esta será direcionada ao Profissional responsável para validação clínica e operacional.

---

## 8. Canal de Comunicação com o Encarregado de Dados (DPO)

Para esclarecer quaisquer dúvidas sobre esta Política, solicitar o exercício de direitos ou relatar qualquer inconformidade com a LGPD, o titular poderá entrar em contato com o Encarregado de Proteção de Dados:

- **Encarregado pelo Tratamento de Dados Pessoais (DPO)**: Setor de Privacidade e Proteção de Dados Gestão Fisio  
- **E-mail de Contato**: `dpo@gestaofisio.com.br`  
- **Prazo de Atendimento**: As solicitações de titulares serão respondidas no prazo legal de até 15 (quinze) dias úteis, na forma da regulamentação da ANPD.

---

## 9. Atualizações desta Política

Esta Política de Privacidade poderá ser alterada a qualquer tempo para adequação a novas exigências legais ou aprimoramentos técnicos de segurança. A versão em vigor estará sempre acessível na Plataforma com indicação expressa da data de atualização.
