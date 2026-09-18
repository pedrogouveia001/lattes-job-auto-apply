# Lattes Job Auto Apply — Plataforma de Docência & Candidatura Automatizada

Plataforma multiusuário para prospecção ativa de vagas acadêmicas e corporativas em faculdades privadas e redes EAD, com tailoring semântico de currículo baseado no Lattes e envio automático via SMTP pessoal.

## Recursos
- **Multiusuário (Multi-tenant):** Isolamento completo de credenciais, perfis Lattes, vagas e históricos.
- **Segurança de Nível Bancário:** Criptografia AES-256 (Fernet) para senhas de app SMTP.
- **Importação Flexível:** Mapeamento inteligente de planilhas Excel (.xlsx) e CSV com contatos de faculdades e coordenações.
- **Tailoring de Currículo:** Geração de currículo executivo de 2 páginas (ReportLab) personalizado para a área de cada vaga.
- **Envio Ativo & Simulação (Dry-Run):** Disparo supervisionado de e-mails com anexo do PDF personalizado.
- **100% Gratuito:** Compatível com Streamlit Community Cloud (R$ 0,00 de hospedagem).

## Como Executar Localmente
```bash
pip install -r requirements.txt
streamlit run web_app.py
```
