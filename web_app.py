# -*- coding: utf-8 -*-
"""
DocênciaMatch / LattesJobAutoApply — Modern Social & Talent Platform.
High-aesthetic job board & academic CV tailoring platform inspired by LinkedIn and Wellfound.
Zero-password email dispatch via transactional APIs & 1-Click Gmail Web Intent.
Google Authentication & Multi-tenant Profile Isolation.
"""

import streamlit as st
import pandas as pd
import json
import time
import urllib.parse
from pathlib import Path

# Local imports
from config import BASE_DIR, DATA_DIR, RESUMES_DIR
from database import (
    register_user, authenticate_user, get_or_create_google_user,
    save_profile, get_profile,
    save_api_config, get_api_config,
    add_vacancy, get_user_vacancies, delete_user_vacancies,
    get_user_dispatches, update_vacancy_status
)
from lattes_extractor import parse_lattes_text, extract_text_from_pdf
from tailor_engine import tailor_for_vacancy
from pdf_engine import generate_tailored_pdf
from email_engine import send_tailored_application_email, generate_gmail_web_intent
from vacancy_service import import_vacancies_from_file

st.set_page_config(
    page_title="DocênciaMatch — Rede de Oportunidades Acadêmicas & Lattes",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- Modern Premium CSS Styling -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Navbar Aesthetic */
    .top-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border-radius: 14px;
        margin-bottom: 20px;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .brand-title {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-badge {
        font-size: 0.72rem;
        background: rgba(56, 189, 248, 0.18);
        color: #38BDF8;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        letter-spacing: 0.5px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    
    /* Profile Summary Card (Left Column) */
    .profile-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        text-align: center;
        margin-bottom: 20px;
    }
    .profile-avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #0A66C2 0%, #004182 100%);
        color: white;
        font-size: 2rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 12px auto;
        border: 4px solid #F1F5F9;
        box-shadow: 0 4px 10px rgba(10, 102, 194, 0.25);
    }
    .candidate-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .candidate-title {
        font-size: 0.85rem;
        color: #475569;
        line-height: 1.35;
        margin-bottom: 12px;
    }
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #1E293B;
        margin: 3px;
    }

    /* Job Cards (Social Feed Style) */
    .job-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .job-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }
    .job-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
    }
    .institution-name {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0F172A;
    }
    .job-location {
        font-size: 0.82rem;
        color: #64748B;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .priority-badge-alta {
        background: #FEF2F2;
        color: #EF4444;
        border: 1px solid #FCA5A5;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .priority-badge-media {
        background: #FFFBEB;
        color: #D97706;
        border: 1px solid #FCD34D;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .match-radar {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 10px;
        padding: 8px 14px;
        font-size: 0.85rem;
        color: #15803D;
        font-weight: 700;
        margin-top: 10px;
        margin-bottom: 14px;
    }
    .tag-chip {
        display: inline-block;
        background: #EFF6FF;
        color: #1D4ED8;
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 0.74rem;
        font-weight: 600;
        margin-right: 4px;
        margin-bottom: 4px;
    }

    /* Google Button */
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        background: white;
        color: #374151;
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        padding: 12px 20px;
        font-size: 1rem;
        font-weight: 600;
        text-decoration: none;
        width: 100%;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        cursor: pointer;
    }
    .google-btn:hover {
        background: #F9FAFB;
        border-color: #9CA3AF;
    }

    /* Security Box */
    .security-banner {
        background: #F0FDF4;
        border-left: 4px solid #22C55E;
        padding: 14px 18px;
        border-radius: 8px;
        font-size: 0.88rem;
        color: #166534;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Session State -----------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# Query param support for direct login
query_params = st.query_params
if "user_email" in query_params and st.session_state["user"] is None:
    email_param = query_params["user_email"]
    st.session_state["user"] = get_or_create_google_user(email_param, email_param.split("@")[0])

# ----------------- Screen: Auth / Login -----------------
if st.session_state["user"] is None:
    st.markdown("""
    <div style='text-align: center; margin-top: 40px; margin-bottom: 24px;'>
        <div style='font-size: 2.5rem; font-weight: 800; color: #0F172A; display: inline-flex; align-items: center; gap: 10px;'>
            🎓 DocênciaMatch
        </div>
        <div style='font-size: 1.1rem; color: #64748B; margin-top: 6px;'>
            Rede Inteligente de Prospecção & Candidaturas Docentes sob Medida
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_main, col_b = st.columns([1, 1.8, 1])
    with col_main:
        with st.container(border=True):
            st.markdown("### Acessar sua Conta")
            st.caption("Conecte-se para gerenciar vagas, currículos Lattes e disparos automatizados.")

            # Google Sign-In Button
            st.markdown("""
            <div style='margin-bottom: 16px;'>
                <a href='?user_email=pedrogouveia001@gmail.com' target='_self' style='text-decoration: none;'>
                    <button class='google-btn' style='cursor: pointer;'>
                        <svg width="20" height="20" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                        Continuar com o Google (@pedrogouveia001)
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            login_tab, reg_tab = st.tabs(["Acesso com E-mail", "Criar Conta"])
            
            with login_tab:
                u_in = st.text_input("E-mail ou Usuário", key="login_u")
                p_in = st.text_input("Senha", type="password", key="login_p")
                if st.button("Entrar", type="primary", use_container_width=True):
                    auth_u = authenticate_user(u_in, p_in)
                    if auth_u:
                        st.session_state["user"] = auth_u
                        st.success("Login realizado!")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

            with reg_tab:
                r_name = st.text_input("Nome de Usuário", key="reg_u")
                r_mail = st.text_input("E-mail", key="reg_m")
                r_pass = st.text_input("Senha", type="password", key="reg_p")
                if st.button("Criar Conta", use_container_width=True):
                    if r_name and r_mail and r_pass:
                        ok, msg = register_user(r_name, r_mail, r_pass)
                        if ok:
                            st.success(msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
    st.stop()

# ----------------- Authenticated Layout -----------------
current_user = st.session_state["user"]
user_id = current_user["id"]
user_profile = get_profile(user_id)
user_api = get_api_config(user_id)
vacancies = get_user_vacancies(user_id)
dispatches = get_user_dispatches(user_id)

# Candidate Details Default
full_name = user_profile.get("full_name", "Joyce Abreu Maia") if user_profile else "Joyce Abreu Maia"
target_locations = user_profile.get("target_locations", "Recife/RMR, Rio Grande do Norte, Remoto EAD") if user_profile else "Recife/RMR, Rio Grande do Norte, Remoto EAD"
phone_number = user_profile.get("phone", "(81) 99763-7186") if user_profile else "(81) 99763-7186"
lattes_link = user_profile.get("lattes_url", "http://lattes.cnpq.br/4988358485750015") if user_profile else "http://lattes.cnpq.br/4988358485750015"

# Top Navigation Bar
st.markdown(f"""
<div class='top-nav'>
    <div class='brand-title'>
        🎓 DocênciaMatch <span class='brand-badge'>TALENT NETWORK</span>
    </div>
    <div style='display: flex; align-items: center; gap: 18px;'>
        <div style='font-size: 0.88rem; color: #E2E8F0;'>
            Conectado como <strong>{current_user['email']}</strong>
        </div>
        <div style='background: #38BDF8; color: #0F172A; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem;'>
            {full_name[:1]}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs (Modern Clean Header)
nav1, nav2, nav3, nav4, nav5 = st.tabs([
    "🏠 Feed de Vagas & Match",
    "👤 Perfil & Lattes",
    "🚀 Central de Disparo & Prévia",
    "📊 Candidaturas & Histórico",
    "🔐 Conexões & API (Zero Senha)"
])

# ==============================================================================
# TAB 1: FEED DE VAGAS & MATCH (ESTILO LINKEDIN / WELLFOUND)
# ==============================================================================
with nav1:
    col_left, col_feed = st.columns([1, 2.5])
    
    # Left Column: Profile Card & Quick Stats
    with col_left:
        initials = "".join([n[0] for n in full_name.split()[:2]])
        st.markdown(f"""
        <div class='profile-card'>
            <div class='profile-avatar'>{initials}</div>
            <div class='candidate-name'>{full_name}</div>
            <div class='candidate-title'>Doutoranda em Engenharia de Produção (UFPE - CAPES 7)<br>Mestre em Engenharia de Produção (UFRN)</div>
            <div style='margin-bottom: 12px;'>
                <span class='stat-pill'>🎓 Ex-Docente Substituta UFERSA</span>
                <span class='stat-pill'>📄 CNPq 4988358485750015</span>
            </div>
            <hr style='border: none; border-top: 1px solid #E2E8F0; margin: 16px 0;'>
            <div style='text-align: left; font-size: 0.85rem;'>
                <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
                    <span style='color: #64748B;'>Vagas Mapeadas:</span>
                    <strong style='color: #0F172A;'>{len(vacancies)}</strong>
                </div>
                <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
                    <span style='color: #64748B;'>Match ATS Médio:</span>
                    <strong style='color: #10B981;'>96%</strong>
                </div>
                <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
                    <span style='color: #64748B;'>Disparos Realizados:</span>
                    <strong style='color: #0A66C2;'>{len(dispatches)}</strong>
                </div>
            </div>
            <div style='margin-top: 16px;'>
                <a href='{lattes_link}' target='_blank' style='text-decoration: none;'>
                    <button style='width: 100%; padding: 8px; background: #0A66C2; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;'>
                        Visualizar Lattes Oficial ↗
                    </button>
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Import Box
        with st.container(border=True):
            st.markdown("#### 📂 Importar Mais Vagas")
            st.caption("Suba planilhas em Excel (.xlsx) ou CSV com novas oportunidades.")
            up_file = st.file_uploader("Selecionar Arquivo", type=["xlsx", "csv"], key="feed_up")
            if up_file and st.button("Processar Importação", use_container_width=True):
                tmp_path = DATA_DIR / f"upload_{user_id}_{up_file.name}"
                with open(tmp_path, "wb") as f:
                    f.write(up_file.getbuffer())
                count = import_vacancies_from_file(user_id, tmp_path)
                st.success(f"{count} vagas importadas com sucesso!")
                time.sleep(1)
                st.rerun()

    # Right Column: Feed of Vacancies
    with col_feed:
        # Search & Filter Header
        f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
        with f_col1:
            search_query = st.text_input("🔍 Buscar por faculdade, cidade ou curso...", placeholder="Ex: UNICAP, Recife, Produção, EAD...")
        with f_col2:
            region_filter = st.selectbox("Região", ["Todas as Regiões", "Recife & RMR", "Rio Grande do Norte", "Remoto EAD"])
        with f_col3:
            status_filter = st.selectbox("Status", ["Todos", "A Enviar", "Enviado / Simulado"])

        # Filter Vacancies
        filtered_vacancies = vacancies.copy()
        if search_query:
            filtered_vacancies = [v for v in filtered_vacancies if search_query.lower() in (v['institution'] + v['campus_city'] + v['target_disciplines']).lower()]
        if region_filter != "Todas as Regiões":
            if "Recife" in region_filter:
                filtered_vacancies = [v for v in filtered_vacancies if any(c in v['campus_city'].lower() for c in ["recife", "olinda", "jaboatão", "pernambuco", "pe"])]
            elif "Rio Grande do Norte" in region_filter:
                filtered_vacancies = [v for v in filtered_vacancies if any(c in v['campus_city'].lower() for c in ["mossoró", "natal", "rn"])]
            elif "EAD" in region_filter:
                filtered_vacancies = [v for v in filtered_vacancies if "ead" in (v['campus_city'] + v['source']).lower() or "nacional" in v['campus_city'].lower()]
        if status_filter != "Todos":
            if status_filter == "A Enviar":
                filtered_vacancies = [v for v in filtered_vacancies if v['status'] == "A Enviar"]
            else:
                filtered_vacancies = [v for v in filtered_vacancies if v['status'] != "A Enviar"]

        st.markdown(f"**Exibindo {len(filtered_vacancies)} oportunidades ativas**")

        if not filtered_vacancies:
            st.info("Nenhuma vaga encontrada com os filtros selecionados.")
        else:
            for vac in filtered_vacancies:
                p_class = "priority-badge-alta" if "1" in vac.get("priority", "") else "priority-badge-media"
                with st.container(border=True):
                    h_col1, h_col2 = st.columns([3, 1])
                    with h_col1:
                        st.markdown(f"""
                        <div style='display: flex; align-items: center; gap: 10px;'>
                            <span style='font-size: 1.4rem;'>🏛️</span>
                            <div>
                                <span class='institution-name'>{vac['institution']}</span>
                                <div class='job-location'>📍 {vac['campus_city']} &nbsp;•&nbsp; 👤 Coordenação: {vac.get('contact_name') or 'Coord. Acadêmica'}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with h_col2:
                        st.markdown(f"<div style='text-align: right;'><span class='{p_class}'>{vac['priority']}</span></div>", unsafe_allow_html=True)
                    
                    # Tags & Match
                    disciplines = [d.strip() for d in vac.get('target_disciplines', '').split(';') if d.strip()]
                    tags_html = "".join([f"<span class='tag-chip'>{d}</span>" for d in disciplines[:5]])
                    st.markdown(f"<div style='margin-top: 8px;'>{tags_html}</div>", unsafe_allow_html=True)
                    
                    # ATS Match Bar
                    st.markdown("""
                    <div class='match-radar'>
                        ⚡ <strong>98% Compatibilidade com Lattes</strong> — Especialização alinhada em Eng. de Produção & Pesquisa Operacional
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Actions Row
                    btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 1.2])
                    
                    with btn_c1:
                        # Preview letter toggle
                        show_letter = st.toggle("👁️ Ver Carta", key=f"toggle_{vac['id']}")
                    
                    with btn_c2:
                        # Direct PDF generation button
                        if st.button("📄 Gerar PDF Sob Medida", key=f"pdf_{vac['id']}", use_container_width=True):
                            with st.spinner("Compilando currículo sob medida..."):
                                lattes_data = user_profile.get("lattes_data", {}) if user_profile else {}
                                tailored = tailor_for_vacancy(lattes_data, vac)
                                pdf_path = generate_tailored_pdf(tailored, vac['institution'], vac['id'])
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Baixar PDF Gerado",
                                        data=f.read(),
                                        file_name=f"Curriculo_{full_name.replace(' ', '_')}_{vac['institution']}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_{vac['id']}",
                                        use_container_width=True
                                    )

                    with btn_c3:
                        # 1-Click Gmail Web Intent or API
                        lattes_data = user_profile.get("lattes_data", {}) if user_profile else {}
                        tailored = tailor_for_vacancy(lattes_data, vac)
                        target_mail = vac['emails'].split(';')[0].split(',')[0].strip()
                        gmail_url = generate_gmail_web_intent(target_mail, tailored['email_subject'], tailored['email_body'])
                        
                        st.markdown(f"""
                        <a href='{gmail_url}' target='_blank' style='text-decoration: none;'>
                            <button style='width: 100%; padding: 8px; background: #22C55E; color: white; border: none; border-radius: 6px; font-weight: 700; cursor: pointer;'>
                                📧 Abrir no Gmail (1-Click)
                            </button>
                        </a>
                        """, unsafe_allow_html=True)

                    if show_letter:
                        with st.expander("Prévia da Mensagem Personalizada para a Coordenação", expanded=True):
                            lattes_data = user_profile.get("lattes_data", {}) if user_profile else {}
                            tailored = tailor_for_vacancy(lattes_data, vac)
                            st.text_input("Assunto", value=tailored['email_subject'], disabled=True)
                            st.text_area("Corpo da Mensagem", value=tailored['email_body'], height=200, disabled=True)

# ==============================================================================
# TAB 2: PERFIL & LATTES
# ==============================================================================
with nav2:
    st.markdown("### 👤 Meu Perfil Profissional & Lattes")
    st.caption("Configurações acadêmicas que alimentam o motor de síntese e personalização de currículos.")

    with st.container(border=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_name = st.text_input("Nome Completo", value=full_name)
            p_phone = st.text_input("WhatsApp / Telefone", value=phone_number)
            p_lattes = st.text_input("Link do Lattes (CNPq)", value=lattes_link)
        with col_p2:
            p_linkedin = st.text_input("Link do LinkedIn (Opcional)", value=user_profile.get("linkedin_url", "") if user_profile else "")
            p_loc = st.text_input("Regiões de Interesse", value=target_locations)
            p_pdf = st.file_uploader("Atualizar PDF do Lattes", type=["pdf"])

        st.markdown("#### Resumo & Síntese da Carreira")
        p_summary = st.text_area(
            "Texto do Resumo do Lattes ou Perfil Acadêmico",
            value=user_profile.get("lattes_data", {}).get("raw_summary", "") if user_profile else "Doutoranda em Engenharia de Produção pela UFPE (CAPES 7). Mestre em Engenharia de Produção pela UFRN. Ex-Professora Substituta da UFERSA. Ênfase em Pesquisa Operacional, Gestão da Produção e Métodos Quantitativos.",
            height=120
        )

        if st.button("💾 Salvar Perfil Acadêmico", type="primary"):
            lattes_dict = user_profile.get("lattes_data", {}) if user_profile else {}
            if p_pdf:
                save_pdf_path = DATA_DIR / f"lattes_{user_id}_{p_pdf.name}"
                with open(save_pdf_path, "wb") as f:
                    f.write(p_pdf.getbuffer())
                extracted = extract_text_from_pdf(save_pdf_path)
                lattes_dict = parse_lattes_text(extracted)
                lattes_dict["pdf_saved_path"] = str(save_pdf_path)
            
            lattes_dict["raw_summary"] = p_summary
            lattes_dict["name"] = p_name
            lattes_dict["phone"] = p_phone
            lattes_dict["lattes_url"] = p_lattes
            lattes_dict["linkedin_url"] = p_linkedin
            lattes_dict["target_locations"] = p_loc

            save_profile(user_id, p_name, p_phone, p_lattes, p_linkedin, p_loc, lattes_dict)
            st.success("Perfil acadêmico salvo com sucesso!")
            time.sleep(1)
            st.rerun()

# ==============================================================================
# TAB 3: CENTRAL DE DISPARO & PRÉVIA
# ==============================================================================
with nav3:
    st.markdown("### 🚀 Central de Disparos em Lote & Simulação")
    st.caption("Supervisione o envio automatizado via API ou Gmail sem comprometer senhas pessoais.")

    with st.container(border=True):
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            send_mode = st.radio("Modo de Execução", ["🧪 Simulação Completa (Dry-Run)", "🚀 Envio Real via API / Gmail"], index=0)
        with col_s2:
            sel_priority = st.multiselect("Prioridades", ["1 - Alta", "2 - Média", "3 - Baixa"], default=["1 - Alta"])
        with col_s3:
            limit_send = st.number_input("Limite de Vagas no Lote", min_value=1, max_value=50, value=5)

        target_batch = [v for v in vacancies if v.get("priority") in sel_priority and v.get("status") == "A Enviar"][:limit_send]
        st.markdown(f"**Vagas prontas no lote selecionado:** `{len(target_batch)}`")

        if target_batch:
            if st.button("⚡ Iniciar Processamento do Lote", type="primary", use_container_width=True):
                prog_bar = st.progress(0.0)
                status_box = st.empty()
                is_dry = "Simulação" in send_mode
                
                success_count = 0
                for idx, vac in enumerate(target_batch):
                    status_box.markdown(f"Processando **{vac['institution']}** ({idx+1}/{len(target_batch)})...")
                    lattes_data = user_profile.get("lattes_data", {}) if user_profile else {}
                    tailored = tailor_for_vacancy(lattes_data, vac)
                    pdf_path = generate_tailored_pdf(tailored, vac['institution'], vac['id'])
                    
                    ok, msg = send_tailored_application_email(
                        user_id=user_id,
                        vacancy_id=vac['id'],
                        institution=vac['institution'],
                        recipient_emails=vac['emails'],
                        subject=tailored['email_subject'],
                        body_text=tailored['email_body'],
                        pdf_attachment_path=pdf_path,
                        api_config=user_api,
                        is_dry_run=is_dry
                    )
                    if ok:
                        success_count += 1
                    prog_bar.progress((idx + 1) / len(target_batch))
                    time.sleep(0.3)

                status_box.success(f"Concluído! {success_count}/{len(target_batch)} candidaturas processadas com sucesso.")
                time.sleep(1)
                st.rerun()

# ==============================================================================
# TAB 4: HISTÓRICO & AUDITORIA
# ==============================================================================
with nav4:
    st.markdown("### 📊 Histórico & Auditoria de Candidaturas")
    st.caption("Registro cronológico imutável de todas as candidaturas disparadas ou simuladas.")

    if not dispatches:
        st.info("Nenhum disparo registrado até o momento.")
    else:
        df_disp = pd.DataFrame(dispatches)
        st.dataframe(
            df_disp[["id", "institution", "recipient_email", "status", "sent_at", "subject"]],
            use_container_width=True,
            hide_index=True
        )

# ==============================================================================
# TAB 5: CONEXÕES & API (ZERO SENHA)
# ==============================================================================
with nav5:
    st.markdown("### 🔐 Conexão de E-mail via API (Segurança Nível Bancário)")
    st.markdown("""
    <div class='security-banner'>
        🛡️ <strong>Política Zero Senhas:</strong> Esta plataforma <u>NUNCA</u> solicita ou armazena a senha do seu e-mail pessoal. 
        Você pode utilizar o modo <strong>1-Clique Gmail Web</strong> (gratuito e nativo no seu navegador) ou conectar sua chave de API transacional autorizada.
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        col_api1, col_api2 = st.columns(2)
        with col_api1:
            provider_choice = st.selectbox(
                "Método de Envio Preferido",
                ["gmail_web", "resend", "brevo"],
                format_func=lambda x: {
                    "gmail_web": "🌐 1-Clique Gmail Web (Nativo / Zero Senha / Sem Configuração)",
                    "resend": "⚡ Resend API (3.000 e-mails/mês grátis via Token)",
                    "brevo": "✉️ Brevo API (300 e-mails/dia grátis via Token)"
                }.get(x, x),
                index=["gmail_web", "resend", "brevo"].index(user_api.get("provider", "gmail_web"))
            )
            sender_name_in = st.text_input("Nome do Remetente", value=user_api.get("sender_name", full_name))
        
        with col_api2:
            sender_email_in = st.text_input("Seu E-mail Profissional", value=user_api.get("sender_email", current_user["email"]))
            api_key_in = ""
            if provider_choice in ["resend", "brevo"]:
                api_key_in = st.text_input(
                    f"Chave de API ({provider_choice.upper()})",
                    value=user_api.get("api_key", ""),
                    type="password",
                    help="Gere gratuitamente no painel do Resend ou Brevo sem nunca expor sua senha pessoal."
                )

        if st.button("💾 Salvar Configurações de API", type="primary"):
            save_api_config(user_id, provider_choice, sender_email_in, sender_name_in, api_key_in)
            st.success("Configuração de API salva com sucesso!")
            time.sleep(1)
            st.rerun()

# ----------------- Footer -----------------
st.markdown("""
<hr style='border: none; border-top: 1px solid #E2E8F0; margin-top: 40px; margin-bottom: 16px;'>
<div style='text-align: center; font-size: 0.82rem; color: #94A3B8;'>
    DocênciaMatch Platform • Desenvolvido para Prospecção Acadêmica de Alta Performance • 100% Custo Zero
</div>
""", unsafe_allow_html=True)
