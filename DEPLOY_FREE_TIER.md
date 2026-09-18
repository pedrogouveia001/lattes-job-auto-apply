# Guia de Implantação Web com Custo Zero (R$ 0,00)
## Plataforma LattesJobAutoApply

Este documento detalha o passo a passo para colocar a plataforma **LattesJobAutoApply** no ar na web, com suporte multi-usuário e sem gastar nenhum centavo (100% Free Tier vitalício).

---

### 1. Arquitetura de Custo Zero

| Camada | Tecnologia | Custo | Benefícios |
| :--- | :--- | :--- | :--- |
| **Hospedagem Web** | **Streamlit Community Cloud** | **R$ 0,00** | Grátis vitalício, sem cartão de crédito, deploy direto do GitHub, HTTPS automático, não hiberna. |
| **Banco de Dados** | **SQLite (ou Supabase PostgreSQL)** | **R$ 0,00** | Multi-usuário isolado com senhas criptografadas em SHA-256 e AES. |
| **Servidor de E-mail** | **SMTP Gmail / Outlook Pessoal** | **R$ 0,00** | Cada usuário conecta seu próprio e-mail via Senha de Aplicativo oficial. |
| **Motor PDF & Parsing**| **ReportLab + PyPDF (Python Nativo)** | **R$ 0,00** | Processamento rápido dentro da própria instância sem limites de API. |

---

### 2. Como Rodar Localmente (Teste Imediato)

Para testar no seu computador antes de subir para a nuvem:

```bash
# 1. Acesse a pasta da plataforma
cd "g:\Meu Drive\Pedro - Projetos\3 Estudos e Cursos\job_hunter\lattes_auto_apply"

# 2. Inicie a aplicação web
streamlit run web_app.py
```

A interface abrirá automaticamente no seu navegador em `http://localhost:8501`.

---

### 3. Como Colocar na Web em 5 Minutos (Passo a Passo)

#### Passo 1: Criar um Repositório no GitHub
1. Crie um repositório no seu GitHub (pode ser **Privado** para total discrição):
   * Nome sugerido: `lattes-job-auto-apply`
2. Suba o conteúdo da pasta `lattes_auto_apply` para o repositório:
   ```bash
   git init
   git add .
   git commit -m "feat: initial commit lattes auto apply"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/lattes-job-auto-apply.git
   git push -u origin main
   ```

#### Passo 2: Conectar ao Streamlit Community Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com sua conta do GitHub.
2. Clique no botão **"New app"**.
3. Selecione:
   * **Repository:** `SEU_USUARIO/lattes-job-auto-apply`
   * **Branch:** `main`
   * **Main file path:** `web_app.py`
4. Em **Advanced settings**, adicione a chave secreta de criptografia:
   ```toml
   APP_SECRET_KEY = "sua-chave-secreta-forte-aqui"
   ```
5. Clique em **"Deploy!"**.

Em menos de 2 minutos, sua aplicação estará online em uma URL pública segura (ex: `https://lattes-auto-apply.streamlit.app`).

---

### 4. Como Funciona para Diferentes Usuários (Multi-Tenant)

* **Cadastro e Login Independentes:** Cada usuário cria sua própria conta (com hash SHA-256).
* **Isolamento Total de Dados:**
  * As vagas importadas por Joyce ficam visíveis **apenas** para o login de Joyce.
  * Se outro candidato (ex: de Medicina ou Direito) criar uma conta, ele terá seu próprio perfil, seu próprio Lattes e suas próprias vagas importadas.
* **Segurança de E-mail:**
  * As senhas de e-mail (Senhas de App) são armazenadas com criptografia simétrica AES.
  * O sistema nunca compartilha credenciais de um usuário com outro.
* **Modo Simulação Ativado por Padrão:**
  * Permite ao candidato testar e visualizar o PDF e o e-mail sem disparar nada acidentalmente.
