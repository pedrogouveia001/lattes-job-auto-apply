# -*- coding: utf-8 -*-
"""
LattesJobAutoApply — Web Application Interface.
Full multi-tenant web platform for candidate profile management,
vacancy importing/matching, dynamic PDF tailoring, and automated email dispatching.
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path

# Local imports
from config import BASE_DIR, DATA_DIR, RESUMES_DIR
from database import (
    register_user, authenticate_user,
    save_profile, get_profile,
    save_smtp_config, get_smtp_config,
    add_vacancy, get_user_vacancies, delete_user_vacancies,
    get_user_dispatches
)
from lattes_extractor import parse_lattes_text, extract_text_from_pdf
from tailor_engine import tailor_for_vacancy
from pdf_engine import generate_tailored_pdf
from email_engine import test_smtp_connection, send_tailored_application_email
from vacancy_service import import_vacancies_from_file

st.set_page_config(
    page_title="LattesJobAutoApply — Automação de Candidaturas Acadêmicas",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, high-aesthetic styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1A365D;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4A5568;
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background-color: #F7FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Session State Management -----------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# ----------------- Auth Screen -----------------
if st.session_state["user"] is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='main-header'>🎓 LattesJobAutoApply</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Plataforma de Candidaturas Acadêmicas Inteligentes e Personalizadas</div>", unsafe_allow_html=True)
        
        auth_tab1, auth_tab2 = st.tabs(["🔑 Entrar na Conta", "📝 Criar Nova Conta"])
        
        with auth_tab1:
            st.subheader("Login de Usuário")
            login_username = st.text_input("Usuário ou E-mail", key="log_user")
            login_password = st.text_input("Senha", type="password", key="log_pass")
            if st.button("Acessar Plataforma", type="primary", use_container_width=True):
                user = authenticate_user(login_username, login_password)
                if user:
                    st.session_state["user"] = user
                    st.success(f"Bem-vindo(a), {user['username']}!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Verifique usuário e senha.")

        with auth_tab2:
            st.subheader("Cadastro Multi-usuário")
            st.info("Cada usuário possui perfil, vagas, credenciais e histórico 100% isolados.")
            reg_username = st.text_input("Nome de Usuário", key="reg_user")
            reg_email = st.text_input("Seu E-mail", key="reg_email")
            reg_password = st.text_input("Defina uma Senha", type="password", key="reg_pass")
            if st.button("Cadastrar", use_container_width=True):
                if reg_username and reg_email and reg_password:
                    ok, msg = register_user(reg_username, reg_email, reg_password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Preencha todos os campos para cadastrar.")
    st.stop()

# ----------------- Authenticated Layout -----------------
user = st.session_state["user"]
user_id = user["id"]

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 Usuário: **{user['username']}**")
    st.caption(f"E-mail da conta: {user['email']}")
    
    nav_option = st.radio(
        "Navegação",
        [
            "👤 Meu Perfil & Lattes",
            "⚙️ Conexão de E-mail (SMTP)",
            "📂 Importar & Gerenciar Vagas",
            "🚀 Central de Disparo & Prévia",
            "📊 Histórico & Auditoria"
        ]
    )
    
    st.divider()
    if st.button("🚪 Sair da Conta", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()

# =========================================================================
# PAGE 1: MEU PERFIL & LATTES
# =========================================================================
if nav_option == "👤 Meu Perfil & Lattes":
    st.markdown("<div class='main-header'>👤 Perfil Profissional & Lattes</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Configure suas credenciais acadêmicas para alimentar o gerador de currículos sob medida.</div>", unsafe_allow_html=True)

    profile = get_profile(user_id) or {}
    lattes_data = profile.get("lattes_data", {})

    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Nome Completo", value=profile.get("full_name", ""))
        phone = st.text_input("Telefone / WhatsApp", value=profile.get("phone", ""))
        lattes_url = st.text_input("Link do Currículo Lattes (CNPq)", value=profile.get("lattes_url", ""))
    with col2:
        linkedin_url = st.text_input("Link do LinkedIn (Opcional)", value=profile.get("linkedin_url", ""))
        target_locations = st.text_input("Localidades Preferenciais", value=profile.get("target_locations", "Recife - PE / Mossoró - RN / Remoto"))
        lattes_pdf = st.file_uploader("Upload do PDF do Currículo Lattes", type=["pdf"])

    st.subheader("Resumo Acadêmico & Extração de Dados")
    lattes_text_manual = st.text_area(
        "Texto do Resumo do Lattes ou Conteúdo Completo (opcional se fez upload do PDF)",
        value=lattes_data.get("summary", ""),
        height=140
    )

    if st.button("💾 Salvar Perfil & Atualizar Dados", type="primary"):
        parsed_data = lattes_data
        pdf_saved_path = profile.get("lattes_pdf_path", "")

        if lattes_pdf:
            save_dest = DATA_DIR / f"lattes_{user_id}.pdf"
            with open(save_dest, "wb") as f:
                f.write(lattes_pdf.read())
            pdf_saved_path = str(save_dest)
            extracted_txt = extract_text_from_pdf(save_dest)
            parsed_data = parse_lattes_text(extracted_txt)
            st.success("PDF do Lattes processado com sucesso!")
        elif lattes_text_manual:
            parsed_data = parse_lattes_text(lattes_text_manual)

        save_profile(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            lattes_url=lattes_url,
            linkedin_url=linkedin_url,
            target_locations=target_locations,
            lattes_data=parsed_data,
            lattes_pdf_path=pdf_saved_path
        )
        st.success("Perfil salvo e estruturado com sucesso!")
        st.rerun()

    if lattes_data:
        st.divider()
        st.markdown("### 🔍 Dados Estruturados Detectados no Lattes:")
        c1, c2, c3 = st.columns(3)
        c1.metric("Orientações de TCC", lattes_data.get("advising_count", 0))
        c2.metric("Bancas Examinadoras", lattes_data.get("jury_count", 0))
        c3.metric("Artigos Listados", len(lattes_data.get("publications", {}).get("articles", [])))

        if lattes_data.get("degrees"):
            st.markdown("**Titulações Detectadas:**")
            for d in lattes_data.get("degrees", []):
                st.write(f"- **{d.get('type')}:** {d.get('description')}")

# =========================================================================
# PAGE 2: CONEXÃO DE E-MAIL (SMTP)
# =========================================================================
elif nav_option == "⚙️ Conexão de E-mail (SMTP)":
    st.markdown("<div class='main-header'>⚙️ Configuração de E-mail (SMTP)</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Conecte a conta de e-mail pela qual os currículos serão enviados aos coordenadores.</div>", unsafe_allow_html=True)

    st.info("🔒 **Segurança:** Sua senha é armazenada com criptografia AES-256 e nunca exposta. Se você usa Gmail, utilize uma **Senha de Aplicativo (App Password)**.")

    smtp_cfg = get_smtp_config(user_id) or {}

    provider = st.selectbox("Provedor Rápido", ["Gmail (Google)", "Outlook / Hotmail", "Outro / Personalizado"])
    
    default_host = "smtp.gmail.com" if "Gmail" in provider else ("smtp.office365.com" if "Outlook" in provider else smtp_cfg.get("smtp_host", ""))
    default_port = 587

    col1, col2 = st.columns(2)
    with col1:
        smtp_host = st.text_input("Servidor SMTP", value=default_host)
        smtp_port = st.number_input("Porta SMTP", value=int(smtp_cfg.get("smtp_port", default_port)), step=1)
        use_ssl = st.checkbox("Usar SSL direto (Porta 465)", value=bool(smtp_cfg.get("use_ssl", 0)))
    with col2:
        sender_name = st.text_input("Nome do Remetente (Como aparecerá no e-mail)", value=smtp_cfg.get("sender_name", ""))
        smtp_user = st.text_input("E-mail do Remetente", value=smtp_cfg.get("smtp_user", ""))
        smtp_password = st.text_input("Senha / Senha de Aplicativo", value=smtp_cfg.get("smtp_password", ""), type="password")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔍 Testar Conexão SMTP", use_container_width=True):
            if smtp_host and smtp_user and smtp_password:
                with st.spinner("Conectando ao servidor SMTP..."):
                    ok, msg = test_smtp_connection(smtp_host, int(smtp_port), smtp_user, smtp_password, use_ssl)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
            else:
                st.warning("Preencha servidor, e-mail e senha antes de testar.")

    with col_btn2:
        if st.button("💾 Salvar Configurações", type="primary", use_container_width=True):
            if smtp_user and smtp_password:
                save_smtp_config(user_id, smtp_host, int(smtp_port), smtp_user, smtp_password, sender_name, use_ssl)
                st.success("Configuração de e-mail salva com sucesso!")
            else:
                st.warning("Preencha os campos obrigatórios.")

# =========================================================================
# PAGE 3: IMPORTAR & GERENCIAR VAGAS
# =========================================================================
elif nav_option == "📂 Importar & Gerenciar Vagas":
    st.markdown("<div class='main-header'>📂 Importação & Gestão de Vagas</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Importe planilhas Excel/CSV mapeadas ou cadastre vagas avulsas.</div>", unsafe_allow_html=True)

    tab_import, tab_manual = st.tabs(["📥 Importar Arquivo (Excel/CSV)", "➕ Cadastrar Vaga Manual"])

    with tab_import:
        st.markdown("##### Upload da Planilha de Contatos")
        st.write("Você pode fazer upload direto da `Planilha_Contatos_Docencia_Joyce_Maia.xlsx` ou qualquer planilha CSV/XLSX com colunas de Instituição e E-mail.")
        uploaded_sheet = st.file_uploader("Selecione o arquivo (.xlsx ou .csv)", type=["xlsx", "xls", "csv"])
        
        if uploaded_sheet:
            temp_path = DATA_DIR / f"import_temp_{user_id}_{uploaded_sheet.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_sheet.read())
            
            if st.button("Executar Importação", type="primary"):
                with st.spinner("Processando e normalizando dados..."):
                    count, errs = import_vacancies_from_file(user_id, temp_path)
                    if count > 0:
                        st.success(f"{count} vagas importadas com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Nenhuma vaga importada: {errs}")

    with tab_manual:
        st.markdown("##### Nova Vaga / Oportunidade Avulsa")
        col1, col2 = st.columns(2)
        with col1:
            m_inst = st.text_input("Instituição", placeholder="Ex: UNICAP")
            m_city = st.text_input("Polo / Cidade", placeholder="Ex: Recife (Boa Vista)")
            m_emails = st.text_input("E-mails de Contato", placeholder="Ex: coordenacao@faculdade.edu.br")
        with col2:
            m_contact = st.text_input("Nome do Contato / Coordenador", placeholder="Ex: Prof. Dr. Mário Gomes")
            m_job = st.text_input("Cargo / Disciplina", value="Docência no Ensino Superior")
            m_prio = st.selectbox("Prioridade", ["1 - Alta", "2 - Média", "3 - Baixa"])

        if st.button("➕ Adicionar Vaga"):
            if m_inst and m_emails:
                add_vacancy(user_id, m_inst, m_city, m_emails, m_contact, m_job, "", m_prio, "Manual")
                st.success(f"Vaga da instituição {m_inst} adicionada com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha no mínimo Instituição e E-mail.")

    # Table of registered vacancies
    st.divider()
    vacancies = get_user_vacancies(user_id)
    st.markdown(f"### 📋 Vagas Cadastradas no seu Painel ({len(vacancies)})")

    if vacancies:
        df_vac = pd.DataFrame(vacancies)
        st.dataframe(
            df_vac[["id", "priority", "institution", "campus_city", "emails", "contact_name", "status"]],
            use_container_width=True,
            hide_index=True
        )
        if st.button("🗑️ Limpar Todas as Minhas Vagas"):
            delete_user_vacancies(user_id)
            st.success("Lista de vagas limpa.")
            st.rerun()
    else:
        st.info("Nenhuma vaga cadastrada ainda. Faça o upload de uma planilha ou cadastre manualmente acima.")

# =========================================================================
# PAGE 4: CENTRAL DE DISPARO & PRÉVIA
# =========================================================================
elif nav_option == "🚀 Central de Disparo & Prévia":
    st.markdown("<div class='main-header'>🚀 Central de Disparo & Prévia Customizada</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Gere o currículo sob medida, revise o e-mail personalizado e aprove o envio.</div>", unsafe_allow_html=True)

    profile = get_profile(user_id)
    smtp_cfg = get_smtp_config(user_id)
    vacancies = get_user_vacancies(user_id)

    if not profile or not profile.get("full_name"):
        st.warning("⚠️ Preencha seu perfil na aba 'Meu Perfil & Lattes' antes de gerar candidaturas.")
        st.stop()

    if not vacancies:
        st.warning("⚠️ Importe ou cadastre vagas na aba 'Importar & Gerenciar Vagas' primeiro.")
        st.stop()

    # Select vacancy to preview
    vac_options = {f"[{v['priority']}] {v['institution']} — {v['campus_city']} ({v['emails'].split(',')[0].strip()})": v for v in vacancies}
    selected_label = st.selectbox("Selecione a Vaga para Personalizar e Enviar:", list(vac_options.keys()))
    selected_vac = vac_options[selected_label]

    # Generate Tailored Application
    tailored_app = tailor_for_vacancy(profile, selected_vac)

    col_meta1, col_meta2 = st.columns([2, 1])
    with col_meta1:
        st.markdown(f"### Vaga: **{selected_vac['institution']}**")
        st.write(f"**Destinatário:** `{selected_vac['emails']}` | **Polo:** {selected_vac['campus_city']}")
    with col_meta2:
        st.metric("Índice de Aderência (Match ATS)", f"{tailored_app.match_score}%")

    # Email Preview & Editing
    st.subheader("📧 E-mail de Apresentação Gerado")
    c_subj = st.text_input("Assunto do E-mail", value=tailored_app.email_subject)
    c_body = st.text_area("Corpo da Mensagem", value=tailored_app.email_body, height=280)

    # Tailored PDF Generation
    st.subheader("📄 Currículo PDF Sob Medida")
    pdf_col1, pdf_col2 = st.columns([1, 2])
    with pdf_col1:
        if st.button("⚙️ Compilar Currículo PDF Sob Medida", type="primary", use_container_width=True):
            with st.spinner("Gerando PDF executivo em ReportLab..."):
                pdf_path = generate_tailored_pdf(tailored_app, profile)
                st.session_state["last_pdf"] = pdf_path
                st.success("PDF compilado com sucesso!")

    last_pdf = st.session_state.get("last_pdf", "")
    if last_pdf and Path(last_pdf).exists():
        with open(last_pdf, "rb") as f:
            pdf_bytes = f.read()
        st.download_button(
            label="📥 Baixar Currículo PDF Gerado",
            data=pdf_bytes,
            file_name=Path(last_pdf).name,
            mime="application/pdf"
        )

    st.divider()
    st.markdown("### 🚀 Disparo de Candidatura")

    is_dry_run = st.toggle("Modo Simulação (Dry-Run)", value=True, help="Se ativado, simula e grava o log de auditoria sem disparar e-mail real.")

    if not smtp_cfg and not is_dry_run:
        st.error("⚠️ Para disparo real, configure suas credenciais na aba 'Conexão de E-mail (SMTP)'.")
    else:
        if st.button("✉️ Enviar Candidatura para esta Instituição", type="primary"):
            if not last_pdf or not Path(last_pdf).exists():
                pdf_path = generate_tailored_pdf(tailored_app, profile)
            else:
                pdf_path = last_pdf

            with st.spinner("Enviando e-mail e registrando auditoria..."):
                ok, msg = send_tailored_application_email(
                    user_id=user_id,
                    vacancy_id=selected_vac["id"],
                    institution=selected_vac["institution"],
                    recipient_emails=selected_vac["emails"],
                    subject=c_subj,
                    body_text=c_body,
                    pdf_attachment_path=pdf_path,
                    smtp_config=smtp_cfg,
                    is_dry_run=is_dry_run
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

# =========================================================================
# PAGE 5: HISTÓRICO & AUDITORIA
# =========================================================================
elif nav_option == "📊 Histórico & Auditoria":
    st.markdown("<div class='main-header'>📊 Histórico de Envios & Auditoria</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Rastreamento completo de todos os e-mails disparados ou simulados.</div>", unsafe_allow_html=True)

    dispatches = get_user_dispatches(user_id)
    if dispatches:
        df_disp = pd.DataFrame(dispatches)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Ações", len(df_disp))
        c2.metric("Enviados com Sucesso", len(df_disp[df_disp['status'] == 'Enviado']))
        c3.metric("Simulações (Dry-Run)", len(df_disp[df_disp['status'].str.contains('Simulado', na=False)]))

        st.dataframe(
            df_disp[["sent_at", "institution", "recipient_email", "subject", "status", "error_message"]],
            use_container_width=True,
            hide_index=True
        )

        csv_data = df_disp.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Exportar Histórico em CSV",
            data=csv_data,
            file_name=f"historico_candidaturas_user_{user_id}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum envio realizado ainda. Suas candidaturas disparadas aparecerão aqui.")
