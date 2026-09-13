# Política de Cookies e Armazenamento Local — Gestão Fisio

*Última atualização: 13 de Setembro de 2026*  
*Versão: 1.0*

A presente **Política de Cookies e Armazenamento Local** tem por finalidade explicar de forma clara, precisa e transparente aos Usuários do **Gestão Fisio** como são utilizadas as tecnologias de armazenamento no navegador (*cookies*, *HTTP-only cookies*, *Cache Storage* e *Service Workers*), em estrita observância à **Lei Geral de Proteção de Dados Pessoais (LGPD — Lei nº 13.709/2018)** e ao **Guia Orientativo de Cookies e Proteção de Dados Pessoais da ANPD**.

---

## 1. O que são Cookies e Tecnologias de Armazenamento Local?

- **Cookies**: Pequenos arquivos de texto gravados no computador ou dispositivo móvel do Usuário pelo navegador web durante o acesso a aplicações na internet.
- **Cookies HTTP-Only**: Cookies com atributo de segurança especial que impede sua leitura direta por scripts JavaScript no navegador, conferindo proteção de ponta contra ataques de roubo de credenciais (*Cross-Site Scripting — XSS*).
- **Service Worker e Cache Storage**: Mecanismos nativos de navegadores modernos (arquitetura PWA — *Progressive Web App*) que armazenam cópias locais de arquivos estáticos (como folhas de estilo CSS, fontes e ícones) para acelerar o carregamento e garantir estabilidade da aplicação.

---

## 2. Princípio da Minimização e Ausência de Rastreamento Publicitário

> [!IMPORTANT]
> **Compromisso de Privacidade Ética**: O Gestão Fisio **NÃO utiliza cookies de rastreamento publicitário, pixels de retargeting de terceiros (como Facebook Pixel ou Google Ads Remarketing) e NÃO comercializa histórico de navegação**. Todos os identificadores utilizados são **estritamente necessários** para a autenticação, integridade do sistema e entrega das funcionalidades solicitadas pelo Profissional.

---

## 3. Categorias e Relação de Tecnologias Utilizadas

### 3.1. Cookies Estritamente Necessários (Essenciais)
Esses cookies são indispensáveis para o funcionamento e segurança da Plataforma. Sem eles, o login seguro, a proteção contra ataques de falsificação de requisição (*CSRF*) e a navegação entre rotas autenticadas não podem ser realizados.

| Identificador / Tipo | Origem | Finalidade e Caminho | Duração Exata |
| :--- | :--- | :--- | :--- |
| **`access_token`** | Próprio (Django / JWT) | Autorização das chamadas à API REST (`path=/api/`), transmitido com `HttpOnly=True` e `SameSite=Lax`. | **5 minutos** (300 segundos) de validade. |
| **`refresh_token`** | Próprio (Django / JWT) | Renovação silenciosa do token de acesso expirado (`path=/api/auth/token/refresh/`), com `HttpOnly=True` e `SameSite=Lax`. | **24 horas** (padrão) ou **30 dias** (caso ativada a opção "Manter Conectado" no login). |
| **`csrftoken`** | Próprio (Django Backend) | Protege as requisições contra ataques de falsificação de requisição entre sites (*Cross-Site Request Forgery*). | Duração da sessão de navegação. |

### 3.2. Cache de Recursos Estáticos (PWA / Service Worker)
Para garantir desempenho e tempo de resposta rápido durante a rotina clínica do fisioterapeuta:

| Recurso | Tipo de Armazenamento | Finalidade |
| :--- | :--- | :--- |
| **Arquivos de Interface (`ngsw-config.json`)** | Cache Storage / Service Worker | Armazena em cache local o código JavaScript, arquivos CSS e imagens da interface para carregamento instantâneo da aplicação. | Atualizado automaticamente a cada novo deploy da aplicação. |
| **Tipografia (Google Fonts)** | Cache do Navegador | Carregamento da fonte tipográfica da interface para correta renderização visual. | Conforme política de cache HTTP padrão. |

### 3.3. Não Utilização de LocalStorage / SessionStorage para Credenciais
Por diretriz de *Security by Design* e conformidade com as recomendações de segurança da **OWASP (Open Worldwide Application Security Project)** e da **ANPD**:
- O Gestão Fisio **NÃO armazena tokens JWT de acesso ou de atualização (`refresh_token`) em `localStorage` ou `sessionStorage` do navegador**.
- O armazenamento em `localStorage` é intencionalmente evitado pois seus dados ficam expostos a scripts em execução no cliente, criando vulnerabilidade a ataques de roubo de credenciais (*XSS*). 
- Todo o ciclo de vida de autenticação da aplicação opera exclusivamente por meio de **Cookies com a flag `HttpOnly`**, transmitidos de forma segura via HTTPS (`withCredentials: true`), inacessíveis via JavaScript malicioso.

---

## 4. Base Legal para o Tratamento

Conforme o entendimento consolidado da **ANPD** em seu Guia Orientativo:
- O uso de **cookies e identificadores estritamente necessários** fundamenta-se na **Execução de Contrato (Art. 7º, V da LGPD)** e no **Legítimo Interesse de Segurança (Art. 7º, IX da LGPD)**, sendo dispensado o consentimento prévio do usuário para esta categoria exclusiva, já que sua desativação inviabilizaria a própria prestação do serviço contratado.

---

## 5. Como Gerenciar ou Excluir Cookies no Navegador

O Usuário pode, a qualquer tempo, consultar, restringir ou bloquear os cookies configurando as preferências do seu navegador de internet:

- **Google Chrome**: Configurações > Privacidade e segurança > Cookies e dados de sites.
- **Mozilla Firefox**: Opções > Privacidade e Segurança > Cookies e dados de sites.
- **Microsoft Edge**: Configurações > Permissões de site > Cookies e dados armazenados.
- **Apple Safari**: Preferências > Privacidade > Bloquear todos os cookies.

> [!WARNING]
> **Aviso de Funcionalidade**: Caso o Usuário bloqueie a gravação de cookies estritamente necessários no navegador, o sistema Gestão Fisio não conseguirá autenticar a conta, impedindo o acesso à agenda, aos pacientes e ao resumo financeiro.

---

## 6. Canal para Dúvidas

Em caso de dúvidas sobre as práticas de cookies e armazenamento técnico da Plataforma, entre em contato com nosso Encarregado pelo Tratamento de Dados Pessoais:

- **E-mail**: `dpo@gestaofisio.com.br`
