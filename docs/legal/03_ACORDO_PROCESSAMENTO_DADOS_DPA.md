# Acordo de Processamento de Dados Pessoais (Data Processing Agreement — DPA)

*Versão: 1.0 — Em vigor a partir de: 13 de Setembro de 2026*

Este **Acordo de Processamento de Dados Pessoais** ("Acordo" ou "DPA") constitui anexo indissociável dos **Termos de Uso e Condições Gerais de Serviço** da plataforma **Gestão Fisio**, celebrado entre:

1. **O PROFISSIONAL / CLÍNICA CONTRATANTE**: Identificado pelo cadastro individual realizado na Plataforma ("**CONTROLADOR**"); e
2. **GESTÃO FISIO TECNOLOGIA**: Provedora da plataforma de software de gestão em nuvem ("**OPERADOR**").

Ambos doravante denominados individualmente como "Parte" e conjuntamente como "Partes".

---

## 1. Contexto e Finalidade

1.1. Considerando que o **CONTROLADOR** utiliza a plataforma Gestão Fisio para gerenciar informações cadastrais, sessões de atendimento e prontuários clínicos de seus pacientes;

1.2. Considerando que esses registros contêm dados pessoais e **dados pessoais sensíveis relativos à saúde**, sujeitos às regras estritas da **Lei nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais — LGPD)**;

1.3. O presente instrumento formaliza as diretrizes, garantias e obrigações técnicas e jurídicas assumidas pelo **OPERADOR** no tratamento de dados pessoais em nome e sob as instruções do **CONTROLADOR**.

---

## 2. Escopo do Tratamento e Instruções do Controlador

2.1. **Objeto do Tratamento**: O OPERADOR realizará operações de processamento (coleta de dados via API REST, armazenamento em banco de dados relacional PostgreSQL, autenticação segura via cookies HttpOnly com classes customizadas `CookieJWTAuthentication`, renderização de interface reativa em Angular e exclusão lógica/física) exclusivamente com o intuito de fornecer as funcionalidades contratadas da Plataforma Gestão Fisio.

2.2. **Categorias de Titulares**: Pacientes cadastrados pelo CONTROLADOR.

2.3. **Categorias de Dados**:
- Dados Pessoais Cadastrais: Nome completo, CPF, telefone, e-mail, data de nascimento, endereço residencial;
- Dados Pessoais Sensíveis: Histórico médico, relatos de lesões, queixas de dor, diagnósticos e evolução do tratamento fisioterapêutico;
- Dados Operacionais: Datas, horários de início e fim, status (`AGENDADO`, `REALIZADO`, `CANCELADO`), recorrência e modalidade de atendimento (individual ou Pilates em grupo com flag experimental).

2.4. **Estrita Subordinação**: O OPERADOR compromete-se expressamente a processar os dados pessoais apenas de acordo com as instruções documentadas do CONTROLADOR e para os fins estritos da prestação do serviço SaaS, sendo expressamente vedado ao OPERADOR:
- Utilizar os dados de pacientes para finalidade própria, mercantilização ou publicidade;
- Ceder, transferir, alienar ou compartilhar tais dados com terceiros não autorizados;
- Rastrear ou criar perfis comportamentais de consumo dos pacientes.

---

## 3. Obrigações e Garantias do Operador

3.1. O OPERADOR obriga-se a:
- **Segregação Lógica de Dados (Multi-tenancy Rígido)**: Implementar e manter no código da aplicação (`get_queryset()` filtrando por `self.request.user.profissional`) e no banco de dados PostgreSQL restrições estritas de acesso, de modo a garantir que nenhum outro usuário do sistema tenha acesso ou visibilidade sobre os pacientes, clínicas ou agendamentos do CONTROLADOR;
- **Dever de Confidencialidade**: Garantir que todo pessoal técnico autorizado a prestar suporte ou manutenção na infraestrutura tenha firmado compromisso formal e vinculante de sigilo profissional;
- **Medidas Técnicas de Segurança**: Manter medidas de segurança consolidadas (criptografia em trânsito com TLS/HTTPS, cookies com flag `HttpOnly` e `SameSite='Lax'`, senhas criptografadas com salt irreversível, proteção de taxa por `ScopedRateThrottle` e bloqueio de acessos não autenticados);
- **Auxílio ao Controlador**: Auxiliar o CONTROLADOR, por meio de ferramentas de exportação ou suporte técnico, no atendimento de solicitações de titulares de dados (Art. 18 da LGPD) e em auditorias que venham a ser deflagradas pela ANPD.

---

## 4. Obrigações e Garantias do Controlador

4.1. O CONTROLADOR declara e garante que:
- Possui base legal lícita e legítima, sob a égide dos Arts. 7º e 11 da LGPD, para coletar e inserir os dados pessoais e dados de saúde de seus pacientes na Plataforma;
- Informou previamente seus pacientes sobre a utilização de sistema eletrônico para gestão de seus prontuários e agendamentos;
- Mantém em sigilo absoluto suas credenciais de login e senha, não as compartilhando com secretárias, estagiários ou terceiros sem as devidas cautelas de segurança;
- É o único e exclusivo responsável pela exatidão, adequação, atualização e pertinência dos dados clínicos que imputa no sistema.

---

## 5. Suboperadores (Subcontratação Técnica de Infraestrutura)

5.1. O CONTROLADOR autoriza a utilização pelo OPERADOR dos seguintes serviços de infraestrutura indispensáveis ao funcionamento do serviço:
- Servidores de aplicação e banco de dados relacional PostgreSQL em nuvem operando em rede privada e protegida por firewall;
- Servidor de envio de e-mails transacionais (protocolo SMTP seguro com TLS) para redefinição de senhas solicitadas pelos usuários.

5.2. O OPERADOR assegura que exigirá dos referidos suboperadores nível equivalente de proteção de dados e salvaguardas de segurança àquelas estabelecidas neste Acordo.

---

## 6. Gestão de Incidentes e Notificação de Violações

6.1. O OPERADOR deverá notificar o CONTROLADOR por escrito, sem demora injustificada (em consonância com as diretrizes da Resolução CD/ANPD nº 15/2024), após tomar conhecimento comprovado de qualquer incidente de segurança da informação que resulte em violação, perda, vazamento, acesso não autorizado ou alteração indevida de dados pessoais de pacientes.

6.2. A notificação deverá conter, no mínimo:
- Descrição da natureza do incidente e das categorias de dados pessoais afetadas;
- Número aproximado de titulares atingidos;
- Medidas técnicas de contenção e remediação já adotadas ou em andamento;
- Informações de contato do Encarregado de Proteção de Dados (DPO) do OPERADOR.

---

## 7. Término do Tratamento e Devolução dos Dados

7.1. Mediante a rescisão dos Termos de Uso e o encerramento do contrato de prestação de serviços, o OPERADOR:
- Manterá os dados disponíveis para exportação pelo CONTROLADOR por um período mínimo de tolerância de 30 (trinta) dias;
- Após o decurso do prazo de tolerância, procederá à eliminação segura e definitiva de todos os registros e cópias existentes nos bancos de dados de produção, ressalvada a retenção de dados estritamente necessária ao cumprimento de deveres legais ou regulatórios da Plataforma (ex: Marco Civil da Internet).

---

## 8. Disposições Finais

8.1. A nulidade ou invalidade de qualquer cláusula deste Acordo não prejudicará a validade das demais estipulações.

8.2. Este Acordo de Processamento de Dados entra em vigor na data do primeiro acesso ou aceite eletrônico dos Termos de Uso pelo CONTROLADOR e vigerá por prazo idêntico ao da prestação dos serviços do Gestão Fisio.
