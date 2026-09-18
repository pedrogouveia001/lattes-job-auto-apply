# -*- coding: utf-8 -*-
"""
DocênciaMatch / LattesJobAutoApply — Universal Talent & Job Platform.
- Dynamic Semantic Matching (Unbiased, driven by Candidate Resume & Target Search Criteria)
- Universal Resume Parser (Supports ANY PDF or Text resume: Corporate, Academic, Tech)
- Explicit Job Search Criteria Configuration (Cargos, Áreas, Modalidades, Cidades)
- Manual Vacancy Registration + Master Spreadsheet Importer
- Zero-Password Email Dispatch (1-Click Gmail Web & Transactional APIs)
- Google OAuth & Multi-tenant Architecture
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
from cv_extractor import parse_universal_resume, extract_text_from_pdf
from tailor_engine import tailor_for_vacancy, calculate_vacancy_match
from pdf_engine import generate_tailored_pdf
from email_engine import send_tailored_application_email, generate_gmail_web_intent
from vacancy_service import import_vacancies_from_file

st.set_page_config(
    page_title="DocênciaMatch — Plataforma Inteligente de Vagas & Currículos",
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
    
    /* Top Navbar */
    .top-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 24px;
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
    
    /* Left Profile Card */
    .profile-card {
        background: white;
        border-radius: 16px;
        padding: 22px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        text-align: center;
        margin-bottom: 18px;
    }
    .profile-avatar {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        background: linear-gradient(135deg, #0A66C2 0%, #004182 100%);
        color: white;
        font-size: 1.8rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 10px auto;
        border: 3px solid #F1F5F9;
        box-shadow: 0 4px 10px rgba(10, 102, 194, 0.2);
    }
    .candidate-name {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .candidate-title {
        font-size: 0.84rem;
        color: #475569;
        line-height: 1.35;
        margin-bottom: 12px;
    }
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 4px 10px;
        font-size: 0.74rem;
        font-weight: 600;
        color: #1E293B;
        margin: 2px;
    }

    /* Match Indicators */
    .match-high {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        color: #15803D;
    }
    .match-med {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        color: #B45309;
    }
    .match-low {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        color: #64748B;
    }
    .match-banner {
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 0.84rem;
        font-weight: 600;
        margin-top: 8px;
        margin-bottom: 12px;
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

    .tag-chip {
        display: inline-block;
        background: #EFF6FF;
        color: #1D4ED8;
        border-radius: 6px;
        padding: 2px 7px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-right: 4px;
        margin-bottom: 4px;
    }
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
    <div style='text-align: center; margin-top: 36px; margin-bottom: 20px;'>
        <div style='font-size: 2.4rem; font-weight: 800; color: #0F172A; display: inline-flex; align-items: center; gap: 10px;'>
            🎓 DocênciaMatch
        </div>
        <div style='font-size: 1.05rem; color: #64748B; margin-top: 4px;'>
            Plataforma Universal de Prospecção de Vagas e Adaptação Semântica de Currículos
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_main, col_b = st.columns([1, 1.8, 1])
    with col_main:
        with st.container(border=True):
            st.markdown("### Acessar sua Conta")
            st.caption("Conecte-se para buscar oportunidades compatíveis com seu currículo real.")

            # Google Sign-In Button
            st.markdown("""
            <div style='margin-bottom: 16px;'>
                <a href='?user_email=pedrogouveia001@gmail.com' target='_self' style='text-decoration: none;'>
                    <button class='google-btn'>
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

# ----------------- Authenticated Application -----------------
current_user = st.session_state["user"]
user_id = current_user["id"]
user_profile = get_profile(user_id) or {}
user_api = get_api_config(user_id)
vacancies = get_user_vacancies(user_id)
dispatches = get_user_dispatches(user_id)

# Candidate Defaults & Real Data (Zero Hardcoded Bias)
full_name = user_profile.get("full_name") or current_user.get("username", "Candidato(a)")
target_roles = user_profile.get("target_roles") or ""
target_disciplines = user_profile.get("target_disciplines") or ""
target_locations = user_profile.get("target_locations") or ""
target_modalities = user_profile.get("target_modalities") or "Presencial, Remoto / EAD, Híbrido"
phone_number = user_profile.get("phone") or ""
lattes_link = user_profile.get("lattes_url") or ""
linkedin_link = user_profile.get("linkedin_url") or ""

candidate_context = {
    "full_name": full_name,
    "phone": phone_number,
    "lattes_url": lattes_link,
    "linkedin_url": linkedin_link,
    "target_roles": target_roles,
    "target_disciplines": target_disciplines,
    "target_locations": target_locations,
    "target_modalities": target_modalities,
    "lattes_data": user_profile.get("lattes_data", {})
}

# Top Navigation Bar
st.markdown(f"""
<div class='top-nav'>
    <div class='brand-title'>
        🎓 DocênciaMatch <span class='brand-badge'>SISTEMA UNIVERSAL</span>
    </div>
    <div style='display: flex; align-items: center; gap: 18px;'>
        <div style='font-size: 0.88rem; color: #E2E8F0;'>
            Conectado: <strong>{current_user['email']}</strong>
        </div>
        <div style='background: #38BDF8; color: #0F172A; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem;'>
            {full_name[:1].upper()}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
nav1, nav2, nav3, nav4, nav5 = st.tabs([
    "🏠 Feed de Vagas & Match Dinâmico",
    "🎯 Critérios de Vagas Buscadas",
    "👤 Meu Currículo (Qualquer Formato)",
    "🚀 Central de Disparos & Preview",
    "🔐 Conexões & API (Zero Senha)"
])

# ==============================================================================
# TAB 1: FEED DE VAGAS & MATCH DINÂMICO (SEM VIÉS)
# ==============================================================================
with nav1:
    col_sidebar, col_feed = st.columns([1, 2.5])
    
    with col_sidebar:
        # Candidate Profile Card
        initials = "".join([n[0] for n in full_name.split()[:2]]).upper() if full_name else "CV"
        summary_short = user_profile.get("lattes_data", {}).get("summary", "")[:120]
        if summary_short:
            summary_short += "..."
        else:
            summary_short = "Suba seu currículo ou preencha as vagas buscadas para ativar o Match ATS."

        roles_chip = target_roles.split(',')[0].strip() if target_roles else "Defina seus cargos-alvo"

        st.markdown(f"""
        <div class='profile-card'>
            <div class='profile-avatar'>{initials}</div>
            <div class='candidate-name'>{full_name}</div>
            <div class='candidate-title'>{summary_short}</div>
            <div style='margin-bottom: 12px;'>
                <span class='stat-pill'>🎯 {roles_chip}</span>
            </div>
            <hr style='border: none; border-top: 1px solid #E2E8F0; margin: 12px 0;'>
            <div style='text-align: left; font-size: 0.85rem;'>
                <div style='display: flex; justify-content: space-between; margin-bottom: 6px;'>
                    <span style='color: #64748B;'>Vagas no Banco:</span>
                    <strong style='color: #0F172A;'>{len(vacancies)}</strong>
                </div>
                <div style='display: flex; justify-content: space-between; margin-bottom: 6px;'>
                    <span style='color: #64748B;'>Modalidades:</span>
                    <strong style='color: #0A66C2;'>{target_modalities}</strong>
                </div>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='color: #64748B;'>Candidaturas Enviadas:</span>
                    <strong style='color: #10B981;'>{len(dispatches)}</strong>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick Manual Registration of Vacancies
        with st.expander("➕ Cadastrar Nova Vaga Buscada Manualmente", expanded=False):
            st.caption("Adicione uma vaga específica que você encontrou para aplicar sob medida.")
            nv_inst = st.text_input("Instituição / Empresa", placeholder="Ex: UFPE, UNICAP, IBM, Nubank...", key="nv_inst")
            nv_title = st.text_input("Cargo / Curso", placeholder="Ex: Professor de Direito, Analista de Dados...", key="nv_title")
            nv_disc = st.text_input("Disciplinas / Requisitos", placeholder="Ex: Direito Civil, Python, SQL...", key="nv_disc")
            nv_city = st.text_input("Cidade / Campus ou EAD", placeholder="Ex: Recife, São Paulo, Remoto EAD...", key="nv_city")
            nv_email = st.text_input("E-mail para Envio", placeholder="recrutamento@empresa.com.br", key="nv_email")
            nv_cont = st.text_input("Nome do Contato / Coordenação", placeholder="Ex: Dr. Fulano / RH", key="nv_cont")
            nv_prio = st.selectbox("Prioridade", ["1 - Alta", "2 - Média", "3 - Baixa"], key="nv_prio")
            
            if st.button("Salvar Nova Vaga", type="primary", use_container_width=True):
                if nv_inst and nv_email:
                    add_vacancy(user_id, nv_inst, nv_city, nv_email, nv_cont, nv_title, nv_disc, nv_prio, "Manual")
                    st.success("Vaga cadastrada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Informe pelo menos a Instituição/Empresa e o E-mail de contato.")

        # Batch Excel Import
        with st.expander("📂 Importar Planilha (Excel / CSV)", expanded=False):
            st.caption("Suba arquivos com centenas de vagas de uma vez.")
            up_f = st.file_uploader("Arquivo de Vagas", type=["xlsx", "csv"], key="feed_up_vac")
            if up_f and st.button("Processar Planilha", use_container_width=True):
                tmp_p = DATA_DIR / f"upload_{user_id}_{up_f.name}"
                with open(tmp_p, "wb") as f:
                    f.write(up_f.getbuffer())
                count, errs = import_vacancies_from_file(user_id, tmp_p)
                st.success(f"{count} vagas importadas com sucesso!")
                time.sleep(1)
                st.rerun()

    with col_feed:
        # Dedicated interactive card for filling sought jobs (Campo de Preenchimento das Vagas Buscadas)
        with st.container(border=True):
            st.markdown("#### 🎯 Preenchimento das Vagas Buscadas (Alvo Ativo)")
            st.caption("Digite os cargos e localidades que você está buscando. O Match ATS de todas as vagas é recalculado imediatamente.")
            
            cp1, cp2, cp3 = st.columns([2.5, 1.8, 1])
            with cp1:
                live_roles = st.text_input(
                    "💼 Cargos / Funções Buscadas",
                    value=target_roles,
                    placeholder="Ex: Docência, Engenharia de Software, Administração, Direito...",
                    key="live_roles_input"
                )
            with cp2:
                live_loc = st.text_input(
                    "📍 Cidades ou Modalidades",
                    value=target_locations,
                    placeholder="Ex: Recife, São Paulo, Remoto, EAD...",
                    key="live_loc_input"
                )
            with cp3:
                st.write("")
                st.write("")
                if st.button("💾 Fixar na Conta", help="Salva estes termos no seu perfil para buscas futuras", use_container_width=True):
                    save_profile(
                        user_id=user_id,
                        full_name=full_name,
                        phone=phone_number,
                        lattes_url=lattes_link,
                        linkedin_url=linkedin_link,
                        target_locations=live_loc,
                        lattes_data=user_profile.get("lattes_data", {}),
                        lattes_pdf_path=user_profile.get("lattes_pdf_path", ""),
                        target_roles=live_roles,
                        target_disciplines=target_disciplines,
                        target_modalities=target_modalities
                    )
                    st.toast("Critérios de vagas buscadas salvos no seu perfil!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()

        # Dynamic context incorporating live target roles/locations
        active_candidate_context = {
            **candidate_context,
            "target_roles": live_roles if live_roles else target_roles,
            "target_locations": live_loc if live_loc else target_locations
        }

        # Search & Real Filters Header
        sf1, sf2, sf3 = st.columns([2, 1, 1])
        with sf1:
            search_query = st.text_input("🔍 Filtrar por palavra-chave rápida...", placeholder="Filtrar por instituição, palavra-chave, cidade ou disciplina...")
        with sf2:
            sort_by = st.selectbox("Ordenar por", ["🎯 Maior Match com Meu Currículo", "⭐ Prioridade", "Mais Recentes"])
        with sf3:
            filter_match = st.selectbox("Compatibilidade Mínima", ["Todas as Vagas", "Match >= 50% (Relevantes)", "Match >= 75% (Alta Aderência)"])

        # Calculate Real Match for each vacancy
        scored_vacancies = []
        for vac in vacancies:
            match_res = calculate_vacancy_match(active_candidate_context, vac)
            scored_vacancies.append({
                **vac,
                "calculated_score": match_res["score"],
                "match_reasons": match_res["reasons"]
            })

        # Apply Filters
        filtered = scored_vacancies.copy()
        if search_query:
            q = search_query.lower()
            filtered = [v for v in filtered if q in (v['institution'] + v.get('campus_city', '') + v.get('target_disciplines', '') + v.get('job_title', '')).lower()]
        
        if "75%" in filter_match:
            filtered = [v for v in filtered if v["calculated_score"] >= 75]
        elif "50%" in filter_match:
            filtered = [v for v in filtered if v["calculated_score"] >= 50]

        # Apply Sorting
        if "Maior Match" in sort_by:
            filtered.sort(key=lambda x: x["calculated_score"], reverse=True)
        elif "Prioridade" in sort_by:
            filtered.sort(key=lambda x: x.get("priority", "3 - Baixa"))

        st.markdown(f"**Exibindo {len(filtered)} vagas analisadas contra o seu currículo e critérios:**")

        if not filtered:
            st.info("Nenhuma vaga encontrada. Utilize o menu à esquerda para cadastrar ou importar novas vagas.")
        else:
            for vac in filtered:
                score = vac["calculated_score"]
                reasons = vac["match_reasons"]
                
                # Dynamic visual class based on REAL score
                if score >= 80:
                    badge_style = "match-high"
                    score_icon = "🟢"
                elif score >= 60:
                    badge_style = "match-med"
                    score_icon = "🟡"
                else:
                    badge_style = "match-low"
                    score_icon = "⚪"

                with st.container(border=True):
                    h_col1, h_col2 = st.columns([3, 1])
                    with h_col1:
                        st.markdown(f"""
                        <div style='display: flex; align-items: center; gap: 10px;'>
                            <span style='font-size: 1.4rem;'>🏛️</span>
                            <div>
                                <span style='font-size: 1.15rem; font-weight: 700; color: #0F172A;'>{vac['institution']}</span>
                                <div style='font-size: 0.82rem; color: #64748B;'>
                                    📍 {vac.get('campus_city') or 'Localidade a combinar'} &nbsp;•&nbsp; 
                                    💼 {vac.get('job_title') or 'Docência / Consultoria'} &nbsp;•&nbsp; 
                                    👤 {vac.get('contact_name') or 'Coordenação Acadêmica'}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with h_col2:
                        st.markdown(f"<div style='text-align: right;'><span style='font-size: 0.74rem; font-weight: 700; padding: 3px 8px; border-radius: 12px; background: #F1F5F9;'>{vac.get('priority', '1 - Alta')}</span></div>", unsafe_allow_html=True)

                    # Disciplines Tags
                    disciplines = [d.strip() for d in vac.get('target_disciplines', '').split(';') if d.strip()]
                    if not disciplines:
                        disciplines = [d.strip() for d in vac.get('target_disciplines', '').split(',') if d.strip()]
                    tags_html = "".join([f"<span class='tag-chip'>{d}</span>" for d in disciplines[:6]])
                    if tags_html:
                        st.markdown(f"<div style='margin-top: 6px;'>{tags_html}</div>", unsafe_allow_html=True)

                    # Dynamic ATS Match Banner with Real Calculated Reasons
                    reasons_text = " • ".join(reasons)
                    st.markdown(f"""
                    <div class='match-banner {badge_style}'>
                        {score_icon} <strong>Match ATS: {score}%</strong> — {reasons_text}
                    </div>
                    """, unsafe_allow_html=True)

                    # Actions Row
                    btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 1.2])
                    
                    with btn_c1:
                        show_letter = st.toggle("👁️ Ver Carta", key=f"tog_{vac['id']}")
                    
                    with btn_c2:
                        if st.button("📄 Gerar PDF Sob Medida", key=f"btn_pdf_{vac['id']}", use_container_width=True):
                            with st.spinner("Compilando currículo sob medida para esta instituição..."):
                                tailored = tailor_for_vacancy(candidate_context, vac)
                                pdf_path = generate_tailored_pdf(tailored, candidate_context, vac['id'])
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Baixar PDF Gerado",
                                        data=f.read(),
                                        file_name=f"Curriculo_{full_name.replace(' ', '_')}_{vac['institution'][:15]}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_{vac['id']}",
                                        use_container_width=True
                                    )

                    with btn_c3:
                        # 1-Click Zero Password Dispatch (Gmail Web Intent)
                        tailored = tailor_for_vacancy(candidate_context, vac)
                        target_mail = vac.get('emails', '').replace(';', ',').split(',')[0].strip()
                        gmail_url = generate_gmail_web_intent(target_mail, tailored.email_subject, tailored.email_body)
                        st.markdown(f"""
                        <a href='{gmail_url}' target='_blank' style='text-decoration: none;'>
                            <button style='width: 100%; padding: 8px; background: #22C55E; color: white; border: none; border-radius: 6px; font-weight: 700; cursor: pointer;'>
                                📧 Abrir no Gmail (1-Click)
                            </button>
                        </a>
                        """, unsafe_allow_html=True)

                    if show_letter:
                        with st.expander("Carta de Apresentação Gerada Dinamicamente", expanded=True):
                            tailored = tailor_for_vacancy(candidate_context, vac)
                            st.text_input("Assunto do E-mail", value=tailored.email_subject, disabled=True)
                            st.text_area("Mensagem Personalizada", value=tailored.email_body, height=220, disabled=True)

# ==============================================================================
# TAB 2: CRITÉRIOS DE VAGAS BUSCADAS (CONFIGURAÇÃO EXPLÍCITA DE BUSCA)
# ==============================================================================
with nav2:
    st.markdown("### 🎯 Critérios de Vagas Buscadas & Preferências de Alvo")
    st.caption("Especifique exatamente os tipos de vagas que você deseja para orientar o cálculo de compatibilidade (Match ATS) e o tailoring de currículos.")

    with st.container(border=True):
        col_crit1, col_crit2 = st.columns(2)
        
        with col_crit1:
            st.markdown("#### 💼 Funções & Cargos Desejados")
            in_target_roles = st.text_area(
                "Cargos ou Funções Alvo (separados por vírgula)",
                value=target_roles,
                placeholder="Ex: Professor Universitário, Engenheiro de Software, Consultor Financeiro, Analista de Dados, Coordenador Pedagógico...",
                help="Informe os cargos que você deseja que o algoritmo busque e priorize.",
                height=90
            )

            st.markdown("#### 📚 Áreas de Atuação & Disciplinas de Domínio")
            in_target_disciplines = st.text_area(
                "Disciplinas / Especialidades Prioritárias",
                value=target_disciplines,
                placeholder="Ex: Inteligência Artificial, Direito Tributário, Finanças Corporativas, Gestão da Qualidade, Logística...",
                help="Termos técnicos e disciplinas que você domina.",
                height=90
            )

        with col_crit2:
            st.markdown("#### 📍 Localização & Cidades de Interesse")
            in_target_locations = st.text_area(
                "Cidades, Estados ou Regiões Alvo",
                value=target_locations,
                placeholder="Ex: Recife/RMR - PE, São Paulo - SP, Remoto, Todo o Brasil...",
                help="Deixe em branco para considerar todas as localidades.",
                height=90
            )

            st.markdown("#### 🌐 Modalidades Aceitas")
            in_target_modalities = st.text_input(
                "Modalidades de Trabalho",
                value=target_modalities,
                placeholder="Ex: Presencial, Remoto / EAD, Híbrido"
            )

        if st.button("💾 Salvar Critérios de Vagas Buscadas", type="primary"):
            current_lattes = user_profile.get("lattes_data", {})
            save_profile(
                user_id=user_id,
                full_name=full_name,
                phone=phone_number,
                lattes_url=lattes_link,
                linkedin_url=linkedin_link,
                target_locations=in_target_locations,
                lattes_data=current_lattes,
                lattes_pdf_path=user_profile.get("lattes_pdf_path", ""),
                target_roles=in_target_roles,
                target_disciplines=in_target_disciplines,
                target_modalities=in_target_modalities
            )
            st.success("Critérios de busca salvos com sucesso! O cálculo de match de todas as vagas foi atualizado.")
            time.sleep(1)
            st.rerun()

# ==============================================================================
# TAB 3: MEU CURRÍCULO (IMPORTAÇÃO DE QUALQUER CURRÍCULO EM PDF OU TEXTO)
# ==============================================================================
with nav3:
    st.markdown("### 👤 Meu Currículo Profissional & Acadêmico (Qualquer Formato)")
    st.caption("Importe QUALQUER formato de currículo: PDF corporativo, LinkedIn, Lattes ou texto livre. O motor universal extrai competências, formações e experiências sem restrição de área.")

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        st.markdown("#### 📄 Upload de Arquivo (Qualquer PDF)")
        uploaded_cv = st.file_uploader("Selecione seu currículo em PDF", type=["pdf"], key="cv_pdf_universal")
    with col_up2:
        st.markdown("#### 🔗 Informações de Contato & Links")
        in_phone = st.text_input("WhatsApp / Telefone de Contato", value=phone_number, placeholder="Ex: (81) 99999-9999")
        in_linkedin = st.text_input("Link do LinkedIn (Opcional)", value=linkedin_link, placeholder="https://linkedin.com/in/seuperfil")
        in_lattes = st.text_input("Link do Lattes CNPq (Opcional para quem tem)", value=lattes_link, placeholder="http://lattes.cnpq.br/...")

    st.markdown("#### 📝 Resumo Profissional / Texto do Currículo")
    current_cv_data = user_profile.get("lattes_data", {})
    in_summary = st.text_area(
        "Resumo Executivo ou Cole aqui o texto do seu currículo",
        value=current_cv_data.get("summary", ""),
        placeholder="Cole aqui o texto do seu currículo, resumo profissional ou memorial acadêmico...",
        height=140
    )

    col_btn_cv1, col_btn_cv2 = st.columns([1, 1])
    with col_btn_cv1:
        save_cv_btn = st.button("💾 Processar e Salvar Currículo", type="primary", use_container_width=True)
    with col_btn_cv2:
        sync_crit_btn = st.button("🪄 Preencher Vagas Buscadas com Base no Currículo", help="Extrai cargos e competências do currículo para preencher a aba de Vagas Buscadas", use_container_width=True)

    if save_cv_btn or sync_crit_btn:
        parsed_data = current_cv_data.copy()
        
        # If PDF was uploaded, parse universally
        if uploaded_cv:
            save_path = DATA_DIR / f"cv_{user_id}_{uploaded_cv.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded_cv.getbuffer())
            pdf_text = extract_text_from_pdf(save_path)
            extracted = parse_universal_resume(pdf_text)
            parsed_data.update(extracted)
            parsed_data["pdf_saved_path"] = str(save_path)
            
            if extracted.get("full_name"):
                full_name = extracted["full_name"]
            if extracted.get("phone") and not in_phone:
                in_phone = extracted["phone"]
            if extracted.get("linkedin_url") and not in_linkedin:
                in_linkedin = extracted["linkedin_url"]
            if extracted.get("summary"):
                in_summary = extracted["summary"]
        elif in_summary:
            # Parse pasted text
            extracted = parse_universal_resume(in_summary)
            for k, v in extracted.items():
                if v and not parsed_data.get(k):
                    parsed_data[k] = v
            if extracted.get("full_name") and full_name == "Candidato(a)":
                full_name = extracted["full_name"]

        parsed_data["summary"] = in_summary

        # Auto-sync target criteria if requested or if currently blank
        new_target_roles = target_roles
        new_target_disc = target_disciplines
        if sync_crit_btn or not new_target_roles:
            if parsed_data.get("headline"):
                new_target_roles = parsed_data["headline"]
            elif parsed_data.get("degrees"):
                new_target_roles = f"Profissional em {parsed_data['degrees'][0].get('description', '')[:40]}"
        if sync_crit_btn or not new_target_disc:
            if parsed_data.get("skills"):
                new_target_disc = ", ".join(parsed_data["skills"][:6])
        
        save_profile(
            user_id=user_id,
            full_name=full_name,
            phone=in_phone,
            lattes_url=in_lattes,
            linkedin_url=in_linkedin,
            target_locations=target_locations,
            lattes_data=parsed_data,
            lattes_pdf_path=parsed_data.get("pdf_saved_path", ""),
            target_roles=new_target_roles,
            target_disciplines=new_target_disc,
            target_modalities=target_modalities
        )
        st.success("Currículo processado e salvo com sucesso! O algoritmo foi recalibrado.")
        time.sleep(1)
        st.rerun()

    # Display extracted breakdown
    if current_cv_data.get("degrees") or current_cv_data.get("skills"):
        with st.expander("🔍 Detalhes Extraídos do seu Currículo (Visão do Algoritmo)", expanded=True):
            det1, det2 = st.columns(2)
            with det1:
                st.markdown("**Formações & Titulações Identificadas:**")
                for deg in current_cv_data.get("degrees", []):
                    st.markdown(f"- **{deg.get('type')}:** {deg.get('description')}")
            with det2:
                st.markdown("**Competências & Palavras-Chave de Domínio:**")
                skills = current_cv_data.get("skills", [])
                st.write(", ".join(skills) if skills else "Nenhuma competência específica isolada.")

# ==============================================================================
# TAB 4: CENTRAL DE DISPAROS & PREVIEW
# ==============================================================================
with nav4:
    st.markdown("### 🚀 Central de Disparos em Lote & Automação Supervisionada")
    st.caption("Envie candidaturas em lote para as coordenações ou realize testes em modo de simulação.")

    with st.container(border=True):
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            send_mode = st.radio("Modo de Operação", ["🧪 Simulação Completa (Dry-Run)", "🚀 Envio Real via API"], index=0)
        with col_d2:
            min_match = st.slider("Filtrar por Match Mínimo (%)", 0, 100, 70)
        with col_d3:
            limit_batch = st.number_input("Tamanho do Lote", min_value=1, max_value=50, value=5)

        # Filter target batch
        eligible_batch = []
        for v in vacancies:
            if v.get("status") == "A Enviar":
                m_res = calculate_vacancy_match(candidate_context, v)
                if m_res["score"] >= min_match:
                    eligible_batch.append({**v, "score": m_res["score"]})
        
        eligible_batch.sort(key=lambda x: x["score"], reverse=True)
        batch_to_run = eligible_batch[:limit_batch]

        st.markdown(f"**Vagas qualificadas para o lote (Match >= {min_match}%):** `{len(batch_to_run)}`")

        if batch_to_run:
            if st.button("⚡ Iniciar Disparo do Lote Selecionado", type="primary", use_container_width=True):
                prog = st.progress(0.0)
                status_txt = st.empty()
                is_dry = "Simulação" in send_mode
                
                success_count = 0
                for idx, vac in enumerate(batch_to_run):
                    status_txt.markdown(f"Processando **{vac['institution']}** ({idx+1}/{len(batch_to_run)})...")
                    tailored = tailor_for_vacancy(candidate_context, vac)
                    pdf_path = generate_tailored_pdf(tailored, candidate_context, vac['id'])
                    
                    ok, msg = send_tailored_application_email(
                        user_id=user_id,
                        vacancy_id=vac['id'],
                        institution=vac['institution'],
                        recipient_emails=vac['emails'],
                        subject=tailored.email_subject,
                        body_text=tailored.email_body,
                        pdf_attachment_path=pdf_path,
                        api_config=user_api,
                        is_dry_run=is_dry
                    )
                    if ok:
                        success_count += 1
                    prog.progress((idx + 1) / len(batch_to_run))
                    time.sleep(0.3)

                status_txt.success(f"Concluído! {success_count}/{len(batch_to_run)} processadas.")
                time.sleep(1)
                st.rerun()

    # Audit Dispatches Table
    st.markdown("#### 📋 Histórico de Disparos Registrados")
    if not dispatches:
        st.info("Nenhum disparo registrado ainda.")
    else:
        df_d = pd.DataFrame(dispatches)
        st.dataframe(
            df_d[["id", "institution", "recipient_email", "status", "sent_at", "subject"]],
            use_container_width=True,
            hide_index=True
        )

# ==============================================================================
# TAB 5: CONEXÕES & API (ZERO SENHA)
# ==============================================================================
with nav5:
    st.markdown("### 🔐 Conexão de E-mail via API (Política Zero Senhas)")
    st.markdown("""
    <div class='security-banner'>
        🛡️ <strong>Segurança em Primeiro Lugar:</strong> Esta plataforma <u>NUNCA</u> solicita, lê ou armazena a senha da sua conta de e-mail. 
        Você pode optar por utilizar o modo <strong>1-Clique Gmail Web</strong> (direto no seu navegador sem intermediários) ou cadastrar uma <strong>Chave de API</strong> de envio transacional (Resend ou Brevo).
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        c_api1, c_api2 = st.columns(2)
        with c_api1:
            provider_choice = st.selectbox(
                "Método de Envio",
                ["gmail_web", "resend", "brevo"],
                format_func=lambda x: {
                    "gmail_web": "🌐 1-Clique Gmail Web (Nativo no Navegador / Sem Senha / Sem Cadastro)",
                    "resend": "⚡ Resend API (3.000 e-mails/mês grátis via Token Bearer)",
                    "brevo": "✉️ Brevo API (300 e-mails/dia grátis via Token)"
                }.get(x, x),
                index=["gmail_web", "resend", "brevo"].index(user_api.get("provider", "gmail_web"))
            )
            in_sender_name = st.text_input("Nome do Remetente", value=user_api.get("sender_name") or full_name)

        with c_api2:
            in_sender_email = st.text_input("Seu E-mail Profissional", value=user_api.get("sender_email") or current_user["email"])
            in_api_key = ""
            if provider_choice in ["resend", "brevo"]:
                in_api_key = st.text_input(
                    f"Chave de API ({provider_choice.upper()})",
                    value=user_api.get("api_key", ""),
                    type="password",
                    help="Insira apenas o token de API gerado no painel da ferramenta (não a senha do seu e-mail)."
                )

        if st.button("💾 Salvar Configurações de Envio", type="primary"):
            save_api_config(user_id, provider_choice, in_sender_email, in_sender_name, in_api_key)
            st.success("Configuração de envio salva com segurança!")
            time.sleep(1)
            st.rerun()

# ----------------- Footer -----------------
st.markdown("""
<hr style='border: none; border-top: 1px solid #E2E8F0; margin-top: 40px; margin-bottom: 16px;'>
<div style='text-align: center; font-size: 0.82rem; color: #94A3B8;'>
    DocênciaMatch Platform • Matching Semântico Sem Viés • 100% Gratuito
</div>
""", unsafe_allow_html=True)
