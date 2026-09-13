# Gestão Fisio — Governança Legal, Proteção de Dados e Conformidade (LGPD)

Este diretório reúne o pacote oficial de documentação jurídica e de conformidade com a **Lei Geral de Proteção de Dados (Lei nº 13.709/2018 - LGPD)**, **Marco Civil da Internet (Lei nº 12.965/2014)**, **Código de Defesa do Consumidor (Lei nº 8.078/1990)** e normativas do **Conselho Federal de Fisioterapia e Terapia Ocupacional (COFFITO - Resoluções nº 414/2012 e nº 424/2013)**.

---

## 📋 Sumário dos Documentos

| Arquivo | Documento | Finalidade e Obrigatoriedade |
| :--- | :--- | :--- |
| **`01_TERMOS_DE_USO_E_SERVICO.md`** | Termos de Uso e Condições Gerais de Serviço | **Obrigatório para deploy**. Define as regras de uso do SaaS pelo profissional/clínica, limites de responsabilidade, propriedade intelectual e obrigações éticas. |
| **`02_POLITICA_DE_PRIVACIDADE_E_LGPD.md`** | Política de Privacidade e Tratamento de Dados | **Obrigatório por lei (LGPD Art. 9º)**. Esclarece a coleta de dados de profissionais e de pacientes, bases legais (Tutela da Saúde, Execução de Contrato), retenção e direitos dos titulares. |
| **`03_ACORDO_PROCESSAMENTO_DADOS_DPA.md`** | Data Processing Agreement (DPA) / Acordo de Operador | **Obrigatório para SaaS B2B na área da saúde**. Define formalmente que o Fisioterapeuta é o **Controlador** dos dados dos pacientes e o Gestão Fisio é o **Operador** técnico. |
| **`04_MODELO_CONSENTIMENTO_E_CIENCIA_PACIENTE_TCLE.md`** | Termo de Consentimento e Ciência para o Paciente (TCLE) | **Essencial para mitigação de riscos**. Modelo fornecido para que o Fisioterapeuta colha a ciência e autorização de seus pacientes para registro de prontuário e avisos de agendamento. |
| **`05_POLITICA_DE_COOKIES_E_ARMAZENAMENTO_LOCAL.md`** | Política de Cookies e Armazenamento Local | **Obrigatório para aplicações web**. Detalha o uso de Cookies HttpOnly seguros (Tokens JWT via `withCredentials`), cache de Service Worker (PWA) e a ausência de armazenamento vulnerável em LocalStorage ou rastreadores de terceiros. |
| **`06_PLANO_RESPOSTA_INCIDENTES_E_SEGURANCA_LGPD.md`** | Política de Segurança da Informação e Incidentes | **Obrigatório pela ANPD (Resolução CD/ANPD nº 15/2024 e Art. 46/48 LGPD)**. Estabelece o fluxo de contenção, auditoria e notificação obrigatória em caso de incidente de segurança. |

---

## 🛡️ Matriz de Mitigação de Riscos e Denúncias

1. **Risco de Denúncia na ANPD por Coleta de Dados Pessoais Sensíveis (Saúde)**:
   - *Mitigação*: Enquadramento técnico na base legal da **Tutela da Saúde (Art. 11, II, "f" da LGPD)** e formalização da divisão de papéis (**Controlador vs. Operador**) via DPA.
2. **Risco de Denúncia em Órgãos de Defesa do Consumidor (PROCON)**:
   - *Mitigação*: Termos de Uso transparentes quanto à disponibilidade da aplicação, limites de cálculo financeiro e direito de cancelamento e exportação de dados.
3. **Risco de Denúncia Ético-Profissional (CREFITO / COFFITO)**:
   - *Mitigação*: Cláusula expressa de inviolabilidade do sigilo profissional, garantia de guarda do histórico médico pelo tempo regulamentar e proibição absoluta de mercantilização de dados clínicos de pacientes.
4. **Risco de Sanções por Falta de Segurança (Art. 46 da LGPD e Marco Civil)**:
   - *Mitigação*: Plano de segurança documentado, criptografia de credenciais, logs de acesso ao sistema (Art. 15 da Lei 12.965/2014) e isolamento multi-tenant por ORM.
