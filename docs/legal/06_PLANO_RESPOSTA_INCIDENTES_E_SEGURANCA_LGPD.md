# Plano de Segurança da Informação e Resposta a Incidentes com Dados Pessoais

*Versão: 1.0 — Em conformidade com os Arts. 46 a 49 da LGPD e a Resolução CD/ANPD nº 15/2024*

---

## 1. Objetivo e Escopo

Este documento estabelece as diretrizes técnicas e operacionais adotadas pela plataforma **Gestão Fisio** para:
1. Garantir a integridade, confidencialidade e disponibilidade dos dados pessoais e dados pessoais sensíveis de saúde;
2. Padronizar as ações imediatas de contenção, investigação e mitigação em caso de suspeita ou confirmação de incidente de segurança;
3. Assegurar o cumprimento dos prazos e ritos formais de comunicação perante a **Autoridade Nacional de Proteção de Dados (ANPD)** e aos titulares de dados afetados.

---

## 2. Medidas de Segurança Implementadas no Software e Infraestrutura

Em consonância com as boas práticas de segurança defensiva (*Security by Design e Security by Default*), a arquitetura do Gestão Fisio contempla:

### 2.1. Controle de Acesso e Multi-tenancy Rígido
- **Isolamento de Queries no Backend**: Todo acesso aos modelos de dados (`Clinica`, `Paciente`, `Agendamento`) é estritamente restrito por filtro do profissional autenticado (`request.user.profissional`), garantindo que nenhum usuário consiga visualizar, consultar ou modificar dados de terceiros.
- **Proteção de Rotas com Guards**: O frontend Angular possui guardiões de rota (`auth.guard`) que impedem a renderização de telas protegidas sem autenticação ativa e válida.
- **Restrição de Origem (CORS)**: A API aceita requisições exclusivamente de domínios explicitamente autorizados (`CORS_ALLOWED_ORIGINS`) com suporte estrito a credenciais (`CORS_ALLOW_CREDENTIALS = True`).

### 2.2. Proteção Criptográfica, Cookies e Credenciais
- **Senhas com Algoritmo Forte**: Senhas são processadas com *hashing* criptográfico irreversível (*PBKDF2* com salt aleatório), não sendo armazenadas em texto legível em nenhuma circunstância.
- **Autenticação via Cookies HttpOnly (`CookieJWTAuthentication`)**: Tokens JWT são transmitidos e gerenciados exclusivamente via Cookies com as diretivas `HttpOnly=True` e `SameSite='Lax'`, impossibilitando a leitura via JavaScript no cliente e eliminando o risco de sequestro de credenciais via *XSS*.
- **Validade Curta e Rotação**: O token de acesso possui validade curta de 5 minutos, e a renovação é intermediada por token de atualização rotativo (`refresh_token`).
- **Revogação Imediata no Logout**: Ao acionar o endpoint de logout, o backend emite instrução expressa de remoção imediata dos cookies de autenticação do navegador.
- **Mitigação de Ataques de Força Bruta (Rate Limiting)**: Implementação de `ScopedRateThrottle` com tetos rígidos: 5 tentativas/minuto para login, 3 cadastros/minuto para novos registros e 3 solicitações/hora para recuperação de senha.
- **Transporte Seguro (TLS/HTTPS)**: Tráfego cifrado em repouso e em trânsito com certificados TLS modernos, mitigando interceptações do tipo *Man-in-the-Middle*.

### 2.3. Rastreabilidade e Auditoria
- **Logs de Acesso a Aplicação**: Registros obrigatórios de conexão conforme Art. 15 do Marco Civil da Internet (data, hora, IP de origem e rota acessada), mantidos em ambiente seguro por no mínimo 6 meses.

---

## 3. Classificação de Incidentes com Dados Pessoais

Para fins deste plano, considera-se incidente qualquer evento adverso confirmado ou sob fundada suspeita que resulte em:
- **Acesso não autorizado**: Visualização de cadastros de pacientes ou profissionais por terceiros não credenciados;
- **Vazamento ou Exfiltração**: Cópia, divulgação pública ou envio indevido de dados clínicos ou cadastrais;
- **Destruição ou Perda Irreversível**: Corrupção do banco de dados sem possibilidade de restauração imediata;
- **Alteração Indevida**: Modificação fraudulenta de prontuários ou registros de agendamento.

---

## 4. Fluxo Operacional de Resposta a Incidentes (4 Fases)

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: DETECÇÃO E REGISTRO IMEDIATO                        │
│ - Identificação de anomalia em logs ou relato de usuário.   │
│ - Abertura de chamado interno de crise de segurança.        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: CONTENÇÃO E ISOLAMENTO                              │
│ - Revogação imediata de credenciais ou tokens suspeitos.    │
│ - Bloqueio temporário de endpoints ou IPs hostis via firewall│
│ - Preservação de logs e evidências forenses.                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: ANÁLISE DE IMPACTO E GRAVIDADE                      │
│ - Identificação dos dados expostos (comuns vs. sensíveis).  │
│ - Verificação do número de titulares atingidos.             │
│ - Avaliação de risco a direitos e liberdades individuais.   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: COMUNICAÇÃO E REMEDIAÇÃO DEFINITIVA                 │
│ - Notificação aos Controladores (Profissionais) e à ANPD.   │
│ - Aplicação de correção de código / patch de segurança.     │
│ - Elaboração do Relatório Pós-Incidente (Post-Mortem).      │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Protocolo de Notificação à ANPD e aos Controladores

Conforme a **Resolução CD/ANPD nº 15/2024**:

1. **Prazo de Notificação à ANPD**: Havendo risco relevante aos direitos e liberdades individuais dos titulares, a comunicação oficial à ANPD deve ser realizada no prazo de **3 (três) dias úteis**, contados a partir da confirmação de que o incidente envolve dados pessoais.
2. **Conteúdo Obrigatório da Notificação**:
   - Descrição da natureza dos dados afetados (destacando dados de saúde);
   - Medidas técnicas e de segurança utilizadas para proteção dos dados antes do evento;
   - Riscos potenciais aos titulares;
   - Medidas que foram ou serão adotadas para reverter ou mitigar os prejuízos;
   - Contato do Encarregado pelo Tratamento de Dados Pessoais (DPO).
3. **Notificação aos Profissionais e Pacientes**: Na condição de Operador técnico perante os dados de pacientes, o Gestão Fisio comunicará formalmente os Profissionais afetados para que estes, enquanto Controladores, adotem as providências éticas perante seus pacientes.

---

## 6. Governança e Revisão Periódica

6.1. Este plano é revisado anualmente ou sempre que houver modificações substanciais na arquitetura tecnológica da Plataforma.

6.2. Testes de integridade de backups e varreduras de dependências de código (`npm audit` e scanners de vulnerabilidades do Django/Python) devem ser executados a cada ciclo de deploy em produção.
