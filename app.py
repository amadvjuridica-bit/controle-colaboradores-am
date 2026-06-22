from __future__ import annotations

import hashlib
import io
import json
import re
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from typing import Any

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from supabase import Client, create_client


APP_NAME = "Controle de Colaboradores | Assis & Mollerke"
LOGO_PATH = "assets/logo.png"
BRAND_NAME = "Assis & Mollerke"
CONFIDENTIAL_NOTICE = (
    "Sistema interno e confidencial. Uso restrito aos usuários autorizados da Assis & Mollerke."
)
CRITICAL_ACTIONS = {
    "cadastrar_colaborador",
    "alterar_dados_pessoais",
    "alterar_dados_bancarios",
    "registrar_admissao",
    "registrar_rescisao",
    "confirmar_contabilidade",
    "confirmar_pagamento_rescisao",
    "anexar_carta_rescisao",
    "alterar_status",
}

TIPO_ESTAGIARIO = "Estagi\u00e1rio"
DOC_CONTRATO_ESTAGIO = "Contrato de est\u00e1gio"
PAGE_DASHBOARD = "Dashboard"
PAGE_COLABORADORES = "Colaboradores"
PAGE_DOCUMENTACAO = "Documenta\u00e7\u00e3o"
PAGE_RESCISOES = "Desligamentos"
PAGE_VAGAS = "Vagas"
PAGE_ANIVERSARIOS = "Anivers\u00e1rios"
PAGE_RELATORIOS = "Relat\u00f3rios"
PAGE_CONFIGURACOES = "Configura\u00e7\u00f5es"
PAGE_AUDITORIA = "Auditoria"

TIPOS_VINCULO = ["CLT", TIPO_ESTAGIARIO, "PJ", "Outro"]
CARGAS_HORARIAS_CLT = ["6 horas", "8 horas", "Outra"]
CARGA_HORARIA_RE = re.compile(r"^Carga horária CLT:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
DOCUMENTOS_ESTAGIARIO = [
    DOC_CONTRATO_ESTAGIO,
    "RG",
    "CPF",
    "Comprovante de resid\u00eancia",
    "Declara\u00e7\u00e3o de matr\u00edcula",
]

DOCUMENTOS_CLT = [
    "RG",
    "CPF",
    "Comprovante de endere\u00e7o",
    "Exame admissional",
    "PIS/PASEP",
    "Certid\u00e3o de nascimento/casamento",
    "T\u00edtulo de eleitor",
    "Certificado de reservista",
    "Comprovante de escolaridade",
]

SOCIOS_EMAILS = ["am@amcob.com.br", "amadvjuridica@gmail.com"]
SUPERVISOR_EMAIL = "comercial@amcob.com.br"


st.set_page_config(page_title=APP_NAME, page_icon="AM", layout="wide")


def css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root {
            --am-navy: #17213f;
            --am-blue: #22315f;
            --am-blue-soft: #eef3fb;
            --am-gold: #b49358;
            --am-ink: #161a25;
            --am-muted: #657085;
            --am-line: #e6e9ef;
            --am-surface: #ffffff;
            --am-bg: #f8f9fb;
            --am-red: #b42318;
            --am-yellow: #9a6700;
            --am-green: #067647;
        }
        html, body, .stApp, .stApp * { font-family: "Inter", "Segoe UI", Arial, sans-serif; }
        .stApp { background: linear-gradient(180deg, #ffffff 0%, var(--am-bg) 280px), var(--am-bg); color: var(--am-ink); }
        .block-container { padding-top: 1.25rem; padding-bottom: 3rem; max-width: 1180px; }
        #MainMenu, footer, header { visibility: hidden; }
        [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--am-line); }
        [data-testid="stSidebar"] img { max-width: 188px; margin: .35rem auto 1rem; display: block; }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--am-muted); text-align: center; letter-spacing: .02em; }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .28rem; }
        [data-testid="stSidebar"] label[data-baseweb="radio"] { border-radius: 8px; padding: .55rem .75rem; margin: .1rem 0; border: 1px solid transparent; }
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) { background: var(--am-blue-soft); border-color: #d9e2f2; color: var(--am-navy); font-weight: 700; }
        h1, h2, h3 { color: var(--am-navy); letter-spacing: 0; font-weight: 760; }
        h1 { font-size: 1.65rem; margin-bottom: .55rem; }
        h2 { font-size: 1.16rem; margin-top: 1.35rem; }
        h3 { font-size: 1rem; margin-top: 1.1rem; }
        p, li { color: #394150; }
        label, [data-testid="stWidgetLabel"] p { color: #273049; font-weight: 650; font-size: .9rem; }
        input, textarea, [data-baseweb="select"] > div { border-radius: 8px !important; border-color: #d9dee8 !important; background: #ffffff !important; }
        input:focus, textarea:focus { border-color: var(--am-gold) !important; box-shadow: 0 0 0 3px rgba(180, 147, 88, .16) !important; }
        .stButton > button, button[kind="primary"] { border-radius: 8px !important; font-weight: 700 !important; letter-spacing: 0 !important; border: 1px solid var(--am-navy) !important; min-height: 2.55rem; }
        .stButton > button[kind="primary"], button[kind="primary"] { background: var(--am-navy) !important; color: #ffffff !important; }
        .stButton > button:hover { border-color: var(--am-gold) !important; box-shadow: 0 8px 20px rgba(23, 33, 63, .10); }
        [data-testid="stDataFrame"] { border: 1px solid var(--am-line); border-radius: 8px; overflow: hidden; background: #ffffff; box-shadow: 0 1px 2px rgba(16, 24, 40, .04); }
        div[data-testid="stMetric"] { background: var(--am-surface); border: 1px solid var(--am-line); border-radius: 8px; padding: 13px 15px; box-shadow: 0 1px 2px rgba(16, 24, 40, .04); }
        div[data-testid="stMetric"] label { color: var(--am-muted); font-size: .78rem; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--am-navy); font-size: 1.55rem; font-weight: 780; }
        .status-ok { color: var(--am-green); font-weight: 700; }
        .status-warn { color: var(--am-yellow); font-weight: 700; }
        .status-bad { color: var(--am-red); font-weight: 700; }
        .am-page-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 1.25rem; border-bottom: 1px solid var(--am-line); padding: .25rem 0 1rem; margin-bottom: 1.15rem; }
        .am-page-kicker { color: var(--am-gold); font-size: .72rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; margin-bottom: .38rem; }
        .am-page-title { color: var(--am-navy); font-size: 1.72rem; line-height: 1.15; font-weight: 800; }
        .am-page-copy { color: var(--am-muted); font-size: .92rem; max-width: 620px; margin-top: .35rem; }
        .am-page-badge { border: 1px solid #e4d7bd; color: #70572e; background: #fffaf1; border-radius: 999px; padding: .42rem .7rem; font-size: .78rem; font-weight: 700; white-space: nowrap; }\n        .am-logo-fallback { color: var(--am-navy); font-size: 2.25rem; font-weight: 800; letter-spacing: -.01em; border-bottom: 3px solid var(--am-gold); display: inline-block; padding-bottom: .2rem; margin-top: .35rem; }
        .am-footer { margin-top: 28px; padding: 14px 0 0; border-top: 1px solid var(--am-line); color: var(--am-muted); font-size: .82rem; }
        .notice { border: 1px solid #eadfc9; background: #fffaf1; color: #614819; padding: 12px 14px; border-radius: 8px; font-weight: 650; }
        div[data-testid="stTabs"] { margin-top: .35rem; }
        div[data-testid="stTabs"] button { font-weight: 720; color: var(--am-muted); border-radius: 0; }
        div[data-testid="stTabs"] button[aria-selected="true"] { color: var(--am-navy); }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--am-gold); }
        .am-section { border-top: 1px solid var(--am-line); margin-top: 1.15rem; padding-top: 1rem; }
        .email-ok { border: 1px solid #bbf7d0; background: #f0fdf4; color: #14532d; border-radius: 8px; padding: 12px 14px; font-weight: 650; }
        .email-warn { border: 1px solid #fed7aa; background: #fff7ed; color: #7c2d12; border-radius: 8px; padding: 12px 14px; font-weight: 650; }
        @media (max-width: 760px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .am-page-head { display: block; }
            .am-page-badge { display: inline-block; margin-top: .85rem; }
            .am-page-title { font-size: 1.42rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

@st.cache_resource(show_spinner=False)
def supabase_client() -> Client | None:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def sb() -> Client:
    client = supabase_client()
    if client is None:
        st.error("Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nos secrets para usar o sistema.")
        st.stop()
    return client


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_date(value: Any) -> date | None:
    if value in (None, "", "-", "NaT"):
        return None
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def br_date(value: Any) -> str:
    parsed = parse_date(value)
    return parsed.strftime("%d/%m/%Y") if parsed else ""


def format_full_name(value: str) -> str:
    particles = {"da", "de", "do", "das", "dos", "e"}
    words = []
    for raw in value.strip().split():
        lower = raw.lower()
        words.append(lower if lower in particles and words else lower.capitalize())
    return " ".join(words)

def normalize_tipo_vinculo(value: Any) -> str:
    if value == "8 horas":
        return "CLT"
    return value if value in TIPOS_VINCULO else "CLT"


def carga_horaria_from_colaborador(colaborador: dict[str, Any]) -> str:
    if colaborador.get("tipo_vinculo") == "8 horas":
        return "8 horas"
    explicit = colaborador.get("carga_horaria")
    if explicit:
        return str(explicit)
    match = CARGA_HORARIA_RE.search(colaborador.get("observacoes") or "")
    return match.group(1).strip() if match else ""


def observacoes_sem_carga(value: str | None) -> str:
    cleaned = CARGA_HORARIA_RE.sub("", value or "")
    return "\n".join(line for line in cleaned.splitlines() if line.strip()).strip()


def merge_carga_horaria_observacoes(observacoes: str, carga_horaria: str) -> str:
    observacoes = observacoes_sem_carga(observacoes)
    if carga_horaria:
        line = f"Carga horária CLT: {carga_horaria}"
        return f"{line}\n{observacoes}".strip()
    return observacoes


def colaborador_tipo_label(colaborador: dict[str, Any]) -> str:
    tipo = normalize_tipo_vinculo(colaborador.get("tipo_vinculo"))
    carga = carga_horaria_from_colaborador(colaborador)
    if tipo == "CLT" and carga:
        return f"CLT ({carga})"
    return tipo


def colaboradores_dataframe(colaboradores: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for c in colaboradores:
        rows.append(
            {
                "nome": c.get("nome_completo"),
                "tipo": colaborador_tipo_label(c),
                "carga_horaria": carga_horaria_from_colaborador(c) if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "CLT" else "",
                "cargo": c.get("cargo"),
                "status": c.get("status"),
                "data_admissao": br_date(c.get("data_admissao")),
                "email": c.get("email"),
                "telefone": c.get("telefone"),
                "cpf": c.get("cpf"),
            }
        )
    return pd.DataFrame(rows)


def required_documents_for_tipo(tipo_vinculo: str) -> list[str]:
    return DOCUMENTOS_ESTAGIARIO if tipo_vinculo == TIPO_ESTAGIARIO else DOCUMENTOS_CLT


def docs_by_name(docs: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    return {doc.get("documento"): doc for doc in (docs or [])}


def document_checklist_form(prefix: str, tipo_vinculo: str, docs: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    existing = docs_by_name(docs)
    rows = []
    st.markdown('<div class="am-section"></div>', unsafe_allow_html=True)
    st.subheader("Documentação")
    st.caption("Marque o que já foi recebido. O que ficar desmarcado entra como pendência automática.")
    for index, documento in enumerate(required_documents_for_tipo(tipo_vinculo)):
        current = existing.get(documento, {})
        cols = st.columns([1.4, 1, 1.6])
        recebido = cols[0].checkbox(documento, value=bool(current.get("recebido") or current.get("status") == "recebido"), key=f"{prefix}_doc_{index}_recebido")
        data_recebimento = cols[1].date_input(
            "Recebido em",
            value=parse_date(current.get("data_recebimento")) if recebido else None,
            format="DD/MM/YYYY",
            key=f"{prefix}_doc_{index}_data",
        )
        referencia = cols[2].text_input(
            "Referência/pasta",
            value=current.get("arquivo_url", "") or "",
            key=f"{prefix}_doc_{index}_ref",
        )
        rows.append(
            {
                "documento": documento,
                "recebido": recebido,
                "data_recebimento": data_recebimento.isoformat() if recebido and data_recebimento else None,
                "arquivo_url": referencia.strip(),
                "status": "recebido" if recebido else current.get("status", "pendente"),
            }
        )
    return rows


def save_document_checklist(colaborador: dict[str, Any], docs_state: list[dict[str, Any]]) -> None:
    existing = docs_by_name(sb().table("documentos_colaborador").select("*").eq("colaborador_id", colaborador["id"]).execute().data or [])
    for item in docs_state:
        payload = {
            "colaborador_id": colaborador["id"],
            "documento": item["documento"],
            "recebido": item["recebido"],
            "data_recebimento": item.get("data_recebimento"),
            "arquivo_url": item.get("arquivo_url"),
            "status": item.get("status") or ("recebido" if item["recebido"] else "pendente"),
            "updated_at": now_iso(),
        }
        current = existing.get(item["documento"])
        if current:
            sb().table("documentos_colaborador").update(payload).eq("id", current["id"]).execute()
        else:
            payload["created_at"] = now_iso()
            sb().table("documentos_colaborador").insert(payload).execute()


def document_status_label(colaborador: dict[str, Any], docs: list[dict[str, Any]]) -> str:
    _, pendings = status_documental(colaborador, docs)
    return "Completa" if not pendings else f"{len(pendings)} pendência(s)"
def page_header(title: str, subtitle: str, badge: str = "Sistema interno") -> None:
    st.markdown(
        f"""
        <div class="am-page-head">
            <div>
                <div class="am-page-kicker">{BRAND_NAME}</div>
                <div class="am-page-title">{title}</div>
                <div class="am-page-copy">{subtitle}</div>
            </div>
            <div class="am-page-badge">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def institutional_header(section: str | None = None) -> None:
    subtitle = CONFIDENTIAL_NOTICE
    if section:
        subtitle = f"{section} | {subtitle}"
    page_header(BRAND_NAME, subtitle, "Confidencial")


def institutional_footer() -> None:
    st.markdown(
        f'<div class="am-footer">Todos os direitos reservados a {BRAND_NAME}. '
        "As informações exibidas neste sistema são confidenciais e destinadas exclusivamente ao controle interno.</div>",
        unsafe_allow_html=True,
    )


def age(birth: Any, ref: date | None = None) -> int | None:
    birth_date = parse_date(birth)
    if not birth_date:
        return None
    ref = ref or date.today()
    return relativedelta(ref, birth_date).years


def company_time(start: Any, ref: date | None = None) -> str:
    start_date = parse_date(start)
    if not start_date:
        return ""
    ref = ref or date.today()
    delta = relativedelta(ref, start_date)
    parts = []
    if delta.years:
        parts.append(f"{delta.years} ano{'s' if delta.years != 1 else ''}")
    if delta.months:
        parts.append(f"{delta.months} mês{'es' if delta.months != 1 else ''}")
    if not parts:
        parts.append(f"{delta.days} dia{'s' if delta.days != 1 else ''}")
    return " e ".join(parts)


def sha256_pin(pin: str) -> str:
    salt = st.secrets.get("PIN_SALT", "troque-este-salt-em-producao")
    return hashlib.sha256(f"{salt}:{pin}".encode("utf-8")).hexdigest()


def fetch_table(table: str, order: str = "created_at", desc: bool = True) -> list[dict[str, Any]]:
    try:
        query = sb().table(table).select("*")
        if order:
            query = query.order(order, desc=desc)
        return query.execute().data or []
    except Exception as exc:
        st.error(f"Erro ao carregar {table}: {exc}")
        return []


def get_colaboradores() -> list[dict[str, Any]]:
    return fetch_table("colaboradores", "nome_completo", False)


def get_usuarios() -> list[dict[str, Any]]:
    return fetch_table("usuarios", "nome", False)


def select_colaborador(label: str, colaboradores: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not colaboradores:
        st.info("Nenhum colaborador cadastrado.")
        return None
    options = {f"{c['nome_completo']} | {c.get('tipo_vinculo', '')} | {c.get('status', '')}": c for c in colaboradores}
    selected = st.selectbox(label, list(options.keys()))
    return options[selected]


def require_login() -> None:
    if "logged" not in st.session_state:
        st.session_state.logged = False
    if st.session_state.logged:
        return

    col1, col2 = st.columns([0.85, 2.15])
    with col1:
        try:
            st.image(LOGO_PATH, use_container_width=True)
        except Exception:
            st.markdown('<div class="am-logo-fallback">A&M</div>', unsafe_allow_html=True)
    with col2:
        page_header(
            "Controle de Colaboradores",
            "Acesso restrito para acompanhamento interno da equipe, documentos e desligamentos.",
            "Login",
        )
        password = st.text_input("Senha principal do app", type="password")
        expected = st.secrets.get("APP_PASSWORD", "")
        if st.button("Entrar", type="primary"):
            if expected and password == expected:
                st.session_state.logged = True
                st.rerun()
            else:
                st.error("Senha inválida ou APP_PASSWORD não configurado.")
    institutional_footer()
    st.stop()

def pin_form(action: str, key: str) -> dict[str, Any] | None:
    usuarios = get_usuarios()
    if not usuarios:
        st.warning("Cadastre usuários e hashes de PIN na tabela usuarios antes de executar ações críticas.")
        return None
    st.markdown("**Confirmação por PIN individual**")
    user_map = {f"{u['nome']} - {u.get('perfil', '')}": u for u in usuarios if u.get("ativo", True)}
    user_label = st.selectbox("Usuário responsável", list(user_map.keys()), key=f"{key}_pin_user")
    pin = st.text_input("PIN", type="password", key=f"{key}_pin")
    if not pin:
        return None
    user = user_map[user_label]
    if user.get("pin_hash") != sha256_pin(pin):
        st.error("PIN inválido.")
        return None
    return {"id": user["id"], "nome": user["nome"], "perfil": user.get("perfil"), "action": action}


def audit(action: str, colaborador_id: str | None, usuario: dict[str, Any] | None, before: Any, after: Any) -> None:
    payload = {
        "usuario_id": usuario.get("id") if usuario else None,
        "usuario_nome": usuario.get("nome") if usuario else "Sistema",
        "acao": action,
        "colaborador_id": colaborador_id,
        "antes": before,
        "depois": after,
        "created_at": now_iso(),
    }
    sb().table("historico_acoes").insert(payload).execute()


def send_email(subject: str, body: str, to: list[str], cc: list[str] | None = None) -> bool:
    host = st.secrets.get("SMTP_HOST", "mail.amcob.com.br")
    port = int(st.secrets.get("SMTP_PORT", 465))
    user = st.secrets.get("SMTP_USER", "")
    password = st.secrets.get("SMTP_PASS", "")
    sender = st.secrets.get("SMTP_FROM", user)
    sender_name = st.secrets.get("SMTP_FROM_NAME", "Assis & Mollerke")
    cc = cc or []

    if not user or not password or not sender:
        st.warning("SMTP não configurado. O e-mail foi registrado como pendente.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender}>"
    msg["Reply-To"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        return True
    except Exception as exc:
        st.error(f"Falha ao enviar e-mail: {exc}")
        return False


def log_email(tipo: str, subject: str, to: list[str], cc: list[str], body: str, sent: bool) -> None:
    sb().table("alertas_email").insert(
        {
            "tipo": tipo,
            "assunto": subject,
            "destinatarios": to,
            "cc": cc,
            "corpo": body,
            "enviado": sent,
            "created_at": now_iso(),
        }
    ).execute()


def email_and_log(tipo: str, subject: str, body: str, to: list[str], cc: list[str] | None = None) -> None:
    cc = cc or []
    sent = send_email(subject, body, to, cc)
    log_email(tipo, subject, to, cc, body, sent)


def pending_fields(payload: dict[str, Any], required: list[str]) -> list[str]:
    return [field for field in required if not payload.get(field)]


def status_documental(colaborador: dict[str, Any], docs: list[dict[str, Any]]) -> tuple[str, list[str]]:
    required = DOCUMENTOS_ESTAGIARIO if colaborador.get("tipo_vinculo") == TIPO_ESTAGIARIO else DOCUMENTOS_CLT
    by_name = {d.get("documento"): d for d in docs if d.get("colaborador_id") == colaborador.get("id")}
    pendings = []
    for item in required:
        doc = by_name.get(item)
        if not doc or doc.get("status") != "recebido":
            pendings.append(item)
    fields = pending_fields(
        colaborador,
        [
            "nome_completo",
            "cpf",
            "rg",
            "data_nascimento",
            "telefone",
            "email",
            "endereco",
            "cep",
            "cargo",
            "tipo_vinculo",
            "data_admissao",
        ],
    )
    pendings.extend([f"Campo obrigatório: {f}" for f in fields])
    return ("completo" if not pendings else "parcial", pendings)


def novo_colaborador_email(colaborador: dict[str, Any], usuario: dict[str, Any], pendings: list[str]) -> None:
    today = date.today().strftime("%d/%m/%Y")
    subject = f"[Novo colaborador cadastrado] Assis & Mollerke - {colaborador['nome_completo']} - {today}"
    body = f"""Novo colaborador cadastrado no sistema.

Nome completo: {colaborador.get('nome_completo', '')}
Tipo de vínculo: {colaborador.get('tipo_vinculo', '')}
Cargo: {colaborador.get('cargo', '')}
Data de admissão: {br_date(colaborador.get('data_admissao'))}
E-mail: {colaborador.get('email', '')}
Telefone: {colaborador.get('telefone', '')}
CPF: {colaborador.get('cpf', '')}
Cidade/UF de nascimento: {colaborador.get('cidade_nascimento', '')}/{colaborador.get('estado_nascimento', '')}
Status documental: {'completo' if not pendings else 'parcial'}
Documentos pendentes: {', '.join(pendings) if pendings else 'Nenhum'}
Dados bancários informados: {'sim' if colaborador.get('banco') and colaborador.get('conta') else 'não'}
Pix informado: {'sim' if colaborador.get('pix') else 'não'}
Data e hora do cadastro: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    email_and_log("novo_colaborador", subject, body, SOCIOS_EMAILS)


def collaborator_form(prefix: str, current: dict[str, Any] | None = None, docs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    current = current or {}
    tipo_atual = normalize_tipo_vinculo(current.get("tipo_vinculo", "CLT"))
    carga_atual = carga_horaria_from_colaborador(current)
    observacoes_atual = observacoes_sem_carga(current.get("observacoes", ""))

    st.markdown('<div class="am-section"></div>', unsafe_allow_html=True)
    st.subheader("Dados principais")
    c1, c2, c3 = st.columns(3)
    with c1:
        nome = st.text_input("Nome completo*", value=current.get("nome_completo", ""), key=f"{prefix}_nome")
        cpf = st.text_input("CPF*", value=current.get("cpf", ""), key=f"{prefix}_cpf")
        rg = st.text_input("RG*", value=current.get("rg", ""), key=f"{prefix}_rg")
        data_nascimento = st.date_input(
            "Data de nascimento*",
            value=parse_date(current.get("data_nascimento")),
            format="DD/MM/YYYY",
            key=f"{prefix}_nasc",
        )
        cidade_nascimento = st.text_input("Cidade de nascimento", value=current.get("cidade_nascimento", ""), key=f"{prefix}_cid_nasc")
        estado_nascimento = st.text_input("Estado de nascimento", value=current.get("estado_nascimento", ""), key=f"{prefix}_uf_nasc")
    with c2:
        telefone = st.text_input("Telefone*", value=current.get("telefone", ""), key=f"{prefix}_telefone")
        email = st.text_input("E-mail obrigatório*", value=current.get("email", ""), key=f"{prefix}_email")
        endereco = st.text_area("Endereço completo*", value=current.get("endereco", ""), key=f"{prefix}_endereco")
        cep = st.text_input("CEP*", value=current.get("cep", ""), key=f"{prefix}_cep")
    with c3:
        cargo = st.text_input("Cargo/função*", value=current.get("cargo", ""), key=f"{prefix}_cargo")
        tipo_vinculo = st.selectbox(
            "Tipo de vínculo*",
            TIPOS_VINCULO,
            index=TIPOS_VINCULO.index(tipo_atual) if tipo_atual in TIPOS_VINCULO else 0,
            key=f"{prefix}_tipo",
        )
        carga_horaria = ""
        if tipo_vinculo == "CLT":
            carga_opcoes = CARGAS_HORARIAS_CLT
            carga_index = carga_opcoes.index(carga_atual) if carga_atual in carga_opcoes else 1
            carga_escolhida = st.selectbox("Carga horária CLT*", carga_opcoes, index=carga_index, key=f"{prefix}_carga")
            carga_horaria = st.text_input("Descreva a carga horária", value=carga_atual if carga_escolhida == "Outra" else "", key=f"{prefix}_carga_outro") if carga_escolhida == "Outra" else carga_escolhida
        status = st.selectbox(
            "Status*",
            ["ativo", "inativo", "rescindido"],
            index=["ativo", "inativo", "rescindido"].index(current.get("status", "ativo"))
            if current.get("status", "ativo") in ["ativo", "inativo", "rescindido"]
            else 0,
            key=f"{prefix}_status",
        )
        data_admissao = st.date_input(
            "Data de admissão/início*",
            value=parse_date(current.get("data_admissao")),
            format="DD/MM/YYYY",
            key=f"{prefix}_admissao",
        )
        observacoes = st.text_area("Observações", value=observacoes_atual, key=f"{prefix}_obs")

    st.subheader("Dados bancários e Pix")
    st.markdown(
        '<div class="notice">ATENÇÃO: confira cuidadosamente os dados bancários e a chave Pix antes de salvar. '
        "Informações incorretas podem gerar pagamento indevido.</div>",
        unsafe_allow_html=True,
    )
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        banco = st.text_input("Banco", value=current.get("banco", ""), key=f"{prefix}_banco")
        agencia = st.text_input("Agência", value=current.get("agencia", ""), key=f"{prefix}_agencia")
    with b2:
        conta = st.text_input("Conta", value=current.get("conta", ""), key=f"{prefix}_conta")
        tipo_conta = st.text_input("Tipo de conta", value=current.get("tipo_conta", ""), key=f"{prefix}_tipo_conta")
    with b3:
        pix = st.text_input("Chave Pix", value=current.get("pix", ""), key=f"{prefix}_pix")
        tipo_pix = st.text_input("Tipo de chave Pix", value=current.get("tipo_pix", ""), key=f"{prefix}_tipo_pix")
    with b4:
        titular_conta = st.text_input("Nome do titular", value=current.get("titular_conta", ""), key=f"{prefix}_titular")
        cpf_titular = st.text_input("CPF/CNPJ do titular", value=current.get("cpf_titular", ""), key=f"{prefix}_cpf_titular")

    bank_confirmed = st.checkbox(
        "Dados bancários conferidos.",
        key=f"{prefix}_bank_confirmed",
    )
    docs_state = document_checklist_form(prefix, tipo_vinculo, docs)

    return {
        "nome_completo": format_full_name(nome),
        "cpf": cpf.strip(),
        "rg": rg.strip(),
        "data_nascimento": data_nascimento.isoformat() if data_nascimento else None,
        "cidade_nascimento": cidade_nascimento.strip(),
        "estado_nascimento": estado_nascimento.strip(),
        "telefone": telefone.strip(),
        "email": email.strip(),
        "endereco": endereco.strip(),
        "cep": cep.strip(),
        "cargo": cargo.strip(),
        "tipo_vinculo": tipo_vinculo,
        "status": status,
        "data_admissao": data_admissao.isoformat() if data_admissao else None,
        "banco": banco.strip(),
        "agencia": agencia.strip(),
        "conta": conta.strip(),
        "tipo_conta": tipo_conta.strip(),
        "pix": pix.strip(),
        "tipo_pix": tipo_pix.strip(),
        "titular_conta": titular_conta.strip(),
        "cpf_titular": cpf_titular.strip(),
        "observacoes": merge_carga_horaria_observacoes(observacoes.strip(), carga_horaria.strip()),
        "_bank_confirmed": bank_confirmed,
        "_docs": docs_state,
    }

def validate_colaborador(payload: dict[str, Any]) -> list[str]:
    required = [
        "nome_completo",
        "cpf",
        "rg",
        "data_nascimento",
        "telefone",
        "email",
        "endereco",
        "cep",
        "cargo",
        "tipo_vinculo",
        "status",
        "data_admissao",
    ]
    errors = [f"Preencha: {field}" for field in required if not payload.get(field)]
    if payload.get("tipo_vinculo") == "CLT" and not carga_horaria_from_colaborador({"tipo_vinculo": "CLT", "observacoes": payload.get("observacoes", "")}):
        errors.append("Informe a carga horária do CLT.")
    if "@" not in payload.get("email", ""):
        errors.append("E-mail obrigatório inválido.")
    bank_fields = ["banco", "agencia", "conta", "pix"]
    if any(payload.get(field) for field in bank_fields) and not payload.get("_bank_confirmed"):
        errors.append("Confirme a conferência dos dados bancários e Pix.")
    return errors


def dashboard() -> None:
    st.title(PAGE_DASHBOARD)
    colaboradores = get_colaboradores()
    docs = fetch_table("documentos_colaborador", "created_at", True)
    rescisoes = fetch_table("rescisoes", "created_at", True)
    vagas = fetch_table("vagas", "tipo_vinculo", False)
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    pendencias = sum(len(status_documental(c, docs)[1]) for c in colaboradores)
    contratos_pendentes = sum(1 for d in docs if d.get("documento") == DOC_CONTRATO_ESTAGIO and d.get("status") != "recebido")
    contratos_atraso = sum(1 for d in docs if d.get("documento") == DOC_CONTRATO_ESTAGIO and d.get("status") == "em atraso")
    exames_pendentes = sum(1 for d in docs if d.get("documento") == "Exame admissional" and d.get("status") != "recebido")
    resc_abertas = [r for r in rescisoes if r.get("status_prazo") not in ("regularizado", "pago")]
    vencidas = [r for r in rescisoes if r.get("status_prazo") == "prazo legal vencido"]
    proximas = [r for r in rescisoes if r.get("status_prazo") in ("dia 8", "dia 9", "dia 10")]
    aniversariantes = [c for c in colaboradores if parse_date(c.get("data_nascimento")) and parse_date(c.get("data_nascimento")).month == date.today().month]
    vagas_disp = sum((v.get("quantidade_total") or 0) - (v.get("quantidade_ocupada") or 0) for v in vagas)

    metrics = [
        ("Ativos", len(ativos)),
        ("CLT", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "CLT")),
        ("CLT 6h", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "CLT" and carga_horaria_from_colaborador(c) == "6 horas")),
        ("CLT 8h", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "CLT" and carga_horaria_from_colaborador(c) == "8 horas")),
        ("Estagi\u00e1rios", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == TIPO_ESTAGIARIO)),
        ("PJ", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "PJ")),
        ("Docs pendentes", pendencias),
        ("Contratos pendentes", contratos_pendentes),
        ("Contratos em atraso", contratos_atraso),
        ("Exames pendentes", exames_pendentes),
        ("Rescisões abertas", len(resc_abertas)),
        ("Próximas do prazo", len(proximas)),
        ("Rescisões vencidas", len(vencidas)),
        ("Aniversariantes mês", len(aniversariantes)),
        ("Vagas disponíveis", vagas_disp),
    ]
    cols = st.columns(4)
    for idx, (label, value) in enumerate(metrics):
        cols[idx % 4].metric(label, value)

    st.subheader("Pendências críticas")
    critical_rows = []
    for c in colaboradores:
        status, pend = status_documental(c, docs)
        if pend:
            critical_rows.append({"nome": c["nome_completo"], "status": status, "pendências": "; ".join(pend[:8])})
    st.dataframe(pd.DataFrame(critical_rows), use_container_width=True, hide_index=True)


def render_novo_cadastro() -> None:
    payload = collaborator_form("new")
    if st.button("Cadastrar colaborador", type="primary"):
        errors = validate_colaborador(payload)
        if errors:
            for err in errors:
                st.error(err)
            return
        docs_state = payload.pop("_docs", [])
        payload.pop("_bank_confirmed", None)
        payload["cadastro_incompleto"] = bool(pending_fields(payload, ["cpf", "rg", "email", "endereco", "cep"]))
        payload["created_at"] = now_iso()
        payload["updated_at"] = now_iso()
        result = sb().table("colaboradores").insert(payload).execute().data[0]
        save_document_checklist(result, docs_state)
        audit("cadastrar_colaborador", result["id"], None, None, result)
        _, pendings = status_documental(result, fetch_table("documentos_colaborador", "created_at", True))
        novo_colaborador_email(result, {"nome": "Sistema"}, pendings)
        st.success("Colaborador cadastrado e e-mail aos sócios processado automaticamente.")
        st.rerun()


def page_colaboradores() -> None:
    page_header("Colaboradores", "Cadastro, consulta, edição e documentos em uma experiência única e limpa.", "Equipe")
    colaboradores = get_colaboradores()
    docs = fetch_table("documentos_colaborador", "created_at", True)
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    pendencias_doc = sum(1 for c in ativos if status_documental(c, docs)[1])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ativos", len(ativos))
    m2.metric("CLT", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "CLT"))
    m3.metric("Estagiários", sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == TIPO_ESTAGIARIO))
    m4.metric("Com pendência", pendencias_doc)

    tab_lista, tab_novo, tab_editar = st.tabs(["Equipe", "Cadastrar", "Editar"])

    with tab_lista:
        if not colaboradores:
            st.info("Nenhum colaborador cadastrado.")
            return
        f1, f2 = st.columns([2, 1])
        busca = f1.text_input("Buscar", placeholder="Nome, cargo, e-mail ou CPF", key="colab_busca")
        status_filtro = f2.selectbox("Status", ["ativo", "todos", "inativo", "rescindido"], key="colab_status")
        busca_lower = busca.strip().lower()
        rows = []
        for c in colaboradores:
            if status_filtro != "todos" and c.get("status") != status_filtro:
                continue
            haystack = " ".join(str(c.get(k, "")) for k in ["nome_completo", "cargo", "email", "cpf", "telefone"]).lower()
            if busca_lower and busca_lower not in haystack:
                continue
            rows.append(
                {
                    "Nome": c.get("nome_completo"),
                    "Vínculo": colaborador_tipo_label(c),
                    "Cargo": c.get("cargo"),
                    "Admissão": br_date(c.get("data_admissao")),
                    "Documentos": document_status_label(c, docs),
                    "E-mail": c.get("email"),
                    "Telefone": c.get("telefone"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab_novo:
        render_novo_cadastro()

    with tab_editar:
        if not colaboradores:
            st.info("Cadastre o primeiro colaborador na aba Cadastrar.")
            return
        selected = select_colaborador("Colaborador", colaboradores)
        selected_docs = [d for d in docs if d.get("colaborador_id") == selected.get("id")]
        payload = collaborator_form("edit", selected, selected_docs)
        if st.button("Salvar alterações", type="primary"):
            errors = validate_colaborador(payload)
            if errors:
                for err in errors:
                    st.error(err)
                return
            docs_state = payload.pop("_docs", [])
            payload.pop("_bank_confirmed", None)
            payload["updated_at"] = now_iso()
            sb().table("colaboradores").update(payload).eq("id", selected["id"]).execute()
            save_document_checklist(selected, docs_state)
            audit("alterar_dados_pessoais", selected["id"], None, selected, payload)
            st.success("Colaborador atualizado.")
            st.rerun()

def page_novo_cadastro() -> None:
    st.title("Novo cadastro")
    render_novo_cadastro()

def create_default_docs(colaborador: dict[str, Any]) -> None:
    docs = DOCUMENTOS_ESTAGIARIO if colaborador.get("tipo_vinculo") == TIPO_ESTAGIARIO else DOCUMENTOS_CLT
    rows = []
    for item in docs:
        status = "pendente"
        if item == DOC_CONTRATO_ESTAGIO and parse_date(colaborador.get("data_admissao")):
            if date.today() > parse_date(colaborador["data_admissao"]) + timedelta(days=7):
                status = "em atraso"
        rows.append(
            {
                "colaborador_id": colaborador["id"],
                "documento": item,
                "recebido": False,
                "status": status,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
    sb().table("documentos_colaborador").insert(rows).execute()


def page_documentacao() -> None:
    st.title(PAGE_DOCUMENTACAO)
    colaboradores = get_colaboradores()
    selected = select_colaborador("Colaborador", colaboradores)
    if not selected:
        return
    docs = sb().table("documentos_colaborador").select("*").eq("colaborador_id", selected["id"]).execute().data or []
    if not docs:
        if st.button("Criar checklist de documentos"):
            create_default_docs(selected)
            st.rerun()
        return
    st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)

    st.subheader("Atualizar documento")
    doc_map = {d["documento"]: d for d in docs}
    doc_name = st.selectbox("Documento", list(doc_map.keys()))
    doc = doc_map[doc_name]
    recebido = st.checkbox("Recebido", value=bool(doc.get("recebido")))
    data_recebimento = st.date_input("Data de recebimento", value=parse_date(doc.get("data_recebimento")), format="DD/MM/YYYY")
    status = st.selectbox("Status", ["pendente", "recebido", "em atraso"], index=["pendente", "recebido", "em atraso"].index(doc.get("status", "pendente")))
    referencia_pasta = st.text_input(
        "Referência na pasta interna",
        value=doc.get("arquivo_url", "") or "",
        help="Informe o nome da pasta, caminho interno ou identificação onde o documento foi salvo.",
    )
    observacoes = st.text_area("Observações", value=doc.get("observacoes", ""))
    usuario = pin_form("anexar_documento", "doc")
    if st.button("Salvar documento", type="primary"):
        if not usuario:
            st.error("Informe um PIN valido.")
            return
        payload = {
            "recebido": recebido,
            "data_recebimento": data_recebimento.isoformat() if data_recebimento else None,
            "arquivo_url": referencia_pasta,
            "observacoes": observacoes,
            "status": "recebido" if recebido else status,
            "updated_at": now_iso(),
        }
        sb().table("documentos_colaborador").update(payload).eq("id", doc["id"]).execute()
        audit("anexar_documento", selected["id"], usuario, doc, payload)
        st.success("Documento atualizado.")
        st.rerun()


def page_rescisoes() -> None:
    page_header(PAGE_RESCISOES, "Registro e acompanhamento de saídas com prazos e comprovantes concentrados.", "Operação")
    colaboradores = [c for c in get_colaboradores() if c.get("status") == "ativo"]
    selected = select_colaborador("Colaborador ativo", colaboradores)
    if not selected:
        return
    tipo = st.selectbox("Tipo de desligamento", ["Pedido do colaborador", "Dispensa pela empresa"])
    data_rescisao = st.date_input("Data da rescisão", value=date.today(), format="DD/MM/YYYY")
    ultimo_dia = st.date_input("Último dia trabalhado", value=date.today(), format="DD/MM/YYYY")
    motivo = st.text_area("Motivo")
    observacoes = st.text_area("Observações")
    carta_anexada = st.checkbox("Carta assinada salva na pasta interna")
    referencia_carta = st.text_input("Referência da carta na pasta interna")
    referencia_comprovante = st.text_input("Referência do comprovante na pasta interna")
    data_pagamento = st.date_input("Data de pagamento", value=None, format="DD/MM/YYYY")
    valor_pago = st.number_input("Valor pago", min_value=0.0, step=100.0)
    if st.button("Registrar desligamento", type="primary"):
        if tipo == "Pedido do colaborador" and not carta_anexada:
            st.error("Carta assinada é obrigatória para pedido do colaborador.")
            return
        status_prazo = calculate_rescisao_status(ultimo_dia, bool(data_pagamento))
        payload = {
            "colaborador_id": selected["id"],
            "tipo_desligamento": tipo,
            "data_rescisao": data_rescisao.isoformat(),
            "ultimo_dia_trabalhado": ultimo_dia.isoformat(),
            "carta_obrigatoria": tipo == "Pedido do colaborador",
            "carta_anexada": bool(carta_anexada),
            "data_carta_anexada": now_iso() if carta_anexada else None,
            "rescisao_paga": bool(data_pagamento),
            "data_pagamento": data_pagamento.isoformat() if data_pagamento else None,
            "valor_pago": valor_pago if valor_pago else None,
            "comprovante_pagamento_url": referencia_comprovante,
            "status_prazo": status_prazo,
            "motivo": motivo,
            "observacoes": f"{observacoes}\nCarta: {referencia_carta}".strip(),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        res = sb().table("rescisoes").insert(payload).execute().data[0]
        sb().table("colaboradores").update({"status": "rescindido", "data_rescisao": data_rescisao.isoformat(), "ultimo_dia_trabalhado": ultimo_dia.isoformat(), "updated_at": now_iso()}).eq("id", selected["id"]).execute()
        audit("registrar_rescisao", selected["id"], None, selected, res)
        st.success("Desligamento registrado.")
        st.rerun()

    st.subheader("Rescisões cadastradas")
    resc = fetch_table("rescisoes", "created_at", True)
    st.dataframe(pd.DataFrame(resc), use_container_width=True, hide_index=True)
    if not resc:
        return

    st.subheader("Atualizar acompanhamento da rescisão")
    col_by_id = {c["id"]: c for c in get_colaboradores()}
    resc_options = {
        f"{col_by_id.get(r.get('colaborador_id'), {}).get('nome_completo', 'Colaborador')} | {r.get('status_prazo', '')} | {br_date(r.get('ultimo_dia_trabalhado'))}": r
        for r in resc
    }
    chosen = st.selectbox("Rescisão", list(resc_options.keys()))
    current = resc_options[chosen]
    comunicada = st.checkbox("Contabilidade comunicada", value=bool(current.get("contabilidade_comunicada")))
    data_comunicacao = st.date_input(
        "Data da comunicação à contabilidade",
        value=parse_date(current.get("data_comunicacao_contabilidade")),
        format="DD/MM/YYYY",
        key="rescisao_data_comunicacao",
    )
    paga = st.checkbox("Rescisão paga", value=bool(current.get("rescisao_paga")))
    data_pagamento_update = st.date_input(
        "Data do pagamento",
        value=parse_date(current.get("data_pagamento")),
        format="DD/MM/YYYY",
        key="rescisao_data_pagamento_update",
    )
    valor_pago_update = st.number_input(
        "Valor pago atualizado",
        min_value=0.0,
        value=float(current.get("valor_pago") or 0),
        step=100.0,
        key="rescisao_valor_pago_update",
    )
    carta_update = st.checkbox("Carta de rescisão salva na pasta interna", value=bool(current.get("carta_anexada")))
    referencia_comprovante_update = st.text_input("Referência do comprovante na pasta interna", value=current.get("comprovante_pagamento_url", "") or "")
    if st.button("Salvar acompanhamento", type="primary"):
        carta_path = carta_update and not current.get("carta_anexada")
        comprovante_path = referencia_comprovante_update
        ultimo = parse_date(current.get("ultimo_dia_trabalhado")) or date.today()
        payload = {
            "contabilidade_comunicada": comunicada,
            "data_comunicacao_contabilidade": data_comunicacao.isoformat() if data_comunicacao else None,
            "rescisao_paga": paga,
            "data_pagamento": data_pagamento_update.isoformat() if data_pagamento_update else None,
            "valor_pago": valor_pago_update if valor_pago_update else None,
            "status_prazo": calculate_rescisao_status(ultimo, paga),
            "updated_at": now_iso(),
        }
        if carta_path:
            payload["carta_anexada"] = True
            payload["data_carta_anexada"] = now_iso()
        if comprovante_path:
            payload["comprovante_pagamento_url"] = referencia_comprovante_update
        sb().table("rescisoes").update(payload).eq("id", current["id"]).execute()
        action = "confirmar_pagamento_rescisao" if paga else "confirmar_contabilidade"
        audit(action, current["colaborador_id"], None, current, payload)
        st.success("Acompanhamento atualizado.")
        st.rerun()


def calculate_rescisao_status(ultimo_dia: date, pago: bool) -> str:
    if pago:
        return "regularizado"
    days = (date.today() - ultimo_dia).days + 1
    if days <= 0:
        return "em aberto"
    if 1 <= days <= 7:
        return f"dia {days}"
    if 8 <= days <= 10:
        return f"dia {days}"
    return "prazo legal vencido"


def page_vagas() -> None:
    st.title(PAGE_VAGAS)
    vagas = fetch_table("vagas", "tipo_vinculo", False)
    colaboradores = get_colaboradores()
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    for tipo in ["CLT", TIPO_ESTAGIARIO, "PJ"]:
        occupied = sum(1 for c in ativos if normalize_tipo_vinculo(c.get("tipo_vinculo")) == tipo)
        existing = next((v for v in vagas if v.get("tipo_vinculo") == tipo), {})
        total = st.number_input(f"Vagas totais - {tipo}", min_value=0, value=int(existing.get("quantidade_total") or occupied), key=f"vaga_{tipo}")
        available = total - occupied
        pct = (occupied / total * 100) if total else 0
        st.write(f"Ocupadas: **{occupied}** | Disponíveis: **{available}** | Ocupação: **{pct:.1f}%**")
        if st.button(f"Salvar {tipo}", key=f"save_vaga_{tipo}"):
            payload = {"tipo_vinculo": tipo, "quantidade_total": total, "quantidade_ocupada": occupied, "updated_at": now_iso()}
            if existing.get("id"):
                sb().table("vagas").update(payload).eq("id", existing["id"]).execute()
            else:
                payload["created_at"] = now_iso()
                sb().table("vagas").insert(payload).execute()
            st.success("Vagas atualizadas.")
            st.rerun()


def page_aniversarios() -> None:
    st.title(PAGE_ANIVERSARIOS)
    colaboradores = [c for c in get_colaboradores() if c.get("data_nascimento")]
    rows = []
    for c in colaboradores:
        birth = parse_date(c.get("data_nascimento"))
        rows.append(
            {
                "nome": c["nome_completo"],
                "tipo": colaborador_tipo_label(c),
                    "cargo": c.get("cargo"),
                "data_nascimento": br_date(birth),
                "idade": age(birth),
                "tempo_empresa": company_time(c.get("data_admissao")),
                "mês": birth.month if birth else None,
                "dia": birth.day if birth else None,
            }
        )
    st.dataframe(pd.DataFrame(rows).sort_values(["mês", "dia"]), use_container_width=True, hide_index=True)
    st.info("Os alertas de aniversário são enviados pela rotina automática diária, quando scripts/run_daily_jobs.py estiver agendado.")


def send_birthday_alerts() -> None:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    for c in get_colaboradores():
        birth = parse_date(c.get("data_nascimento"))
        if not birth:
            continue
        for target, label in [(tomorrow, "amanhã"), (today, "hoje")]:
            if birth.month == target.month and birth.day == target.day:
                new_age = age(birth, target)
                subject = f"[Aniversário {label}] Assis & Mollerke - {c['nome_completo']}"
                body = f"""Olá,

{('Amanhã é' if label == 'amanhã' else 'Hoje é')} aniversário de {c['nome_completo']}.

Dados:
Nome: {c['nome_completo']}
Tipo de vínculo: {c.get('tipo_vinculo', '')}
Cargo: {c.get('cargo', '')}
Data de nascimento: {br_date(birth)}
Idade: {new_age}
Tempo de empresa: {company_time(c.get('data_admissao'))}

Mensagem automática do sistema de controle de colaboradores.
"""
                email_and_log("aniversario", subject, body, SOCIOS_EMAILS + [SUPERVISOR_EMAIL])


def dataframe_to_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Relatório")
    return output.getvalue()


def dataframe_to_pdf(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    data = [list(df.columns)] + df.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24294f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8dde6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
            ]
        )
    )
    doc.build([table])
    return output.getvalue()


def page_relatorios() -> None:
    page_header(PAGE_RELATORIOS, "Consultas e exportações essenciais para acompanhamento interno.", "Dados")
    tipo = st.selectbox(
        "Relatório",
        [
            "Colaboradores ativos",
            "Colaboradores inativos/rescindidos",
            "Documentação pendente",
            "Rescisões",
            "Aniversariantes",
            "Quadro semanal",
            "Histórico de alterações",
            "Vagas disponíveis",
        ],
    )
    df = build_report(tipo)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Exportar Excel", dataframe_to_excel(df), file_name=f"{tipo}.xlsx")
    st.download_button("Exportar PDF", dataframe_to_pdf(df), file_name=f"{tipo}.pdf")
    if tipo == "Quadro semanal":
        st.info("O quadro semanal é enviado automaticamente pela rotina diária agendada, sem clique manual.")


def build_report(tipo: str) -> pd.DataFrame:
    colaboradores = get_colaboradores()
    docs = fetch_table("documentos_colaborador", "created_at", True)
    if tipo == "Colaboradores ativos":
        return colaboradores_dataframe([c for c in colaboradores if c.get("status") == "ativo"])
    if tipo == "Colaboradores inativos/rescindidos":
        return colaboradores_dataframe([c for c in colaboradores if c.get("status") != "ativo"])
    if tipo == "Documentação pendente":
        rows = []
        for c in colaboradores:
            _, pend = status_documental(c, docs)
            if pend:
                rows.append({"nome": c["nome_completo"], "tipo": colaborador_tipo_label(c), "pendências": "; ".join(pend)})
        return pd.DataFrame(rows)
    if tipo == "Rescisões":
        return pd.DataFrame(fetch_table("rescisoes", "created_at", True))
    if tipo == "Aniversariantes":
        return pd.DataFrame(
            [
                {
                    "nome": c["nome_completo"],
                    "data_nascimento": br_date(c.get("data_nascimento")),
                    "idade": age(c.get("data_nascimento")),
                    "tipo": colaborador_tipo_label(c),
                    "cargo": c.get("cargo"),
                }
                for c in colaboradores
                if c.get("data_nascimento")
            ]
        )
    if tipo == "Histórico de alterações":
        return pd.DataFrame(fetch_table("historico_acoes", "created_at", True))
    if tipo == "Vagas disponíveis":
        return pd.DataFrame(fetch_table("vagas", "tipo_vinculo", False))
    rows = []
    for c in colaboradores:
        doc_status, pend = status_documental(c, docs)
        rows.append(
            {
                "Nome": c.get("nome_completo"),
                "Tipo de vínculo": colaborador_tipo_label(c),
                "Carga horária": carga_horaria_from_colaborador(c) if normalize_tipo_vinculo(c.get("tipo_vinculo")) == "CLT" else "",
                "Cargo": c.get("cargo"),
                "Data de admissão": br_date(c.get("data_admissao")),
                "Tempo de empresa": company_time(c.get("data_admissao")),
                "Data de nascimento": br_date(c.get("data_nascimento")),
                "Idade": age(c.get("data_nascimento")),
                "Status documental": doc_status,
                "Pendências": "; ".join(pend),
            }
        )
    return pd.DataFrame(rows)


def send_weekly_report(df: pd.DataFrame) -> None:
    colaboradores = get_colaboradores()
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    subject = f"[Quadro semanal de colaboradores] Assis & Mollerke - Semana de {date.today().strftime('%d/%m/%Y')}"
    body = f"""Bom dia,

Segue o quadro atualizado de colaboradores da Assis & Mollerke.

Resumo:
Total de colaboradores ativos: {len(ativos)}
Total CLT: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'CLT')}
Total CLT 6h: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'CLT' and carga_horaria_from_colaborador(c) == '6 horas')}
Total CLT 8h: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'CLT' and carga_horaria_from_colaborador(c) == '8 horas')}
Total estagi\u00e1rios: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == TIPO_ESTAGIARIO)}
Total PJ: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'PJ')}
Total inativos/rescindidos: {sum(1 for c in colaboradores if c.get('status') != 'ativo')}
Tabela:
{df.to_string(index=False)}

Este relatório é enviado automaticamente pelo sistema de controle de funcionários e estagiários.
"""
    email_and_log("quadro_semanal", subject, body, SOCIOS_EMAILS + [SUPERVISOR_EMAIL])
    sb().table("relatorios_semanais_log").insert({"data_referencia": date.today().isoformat(), "enviado": True, "created_at": now_iso()}).execute()


def page_configuracoes() -> None:
    st.title(PAGE_CONFIGURACOES)

    st.subheader("Automação de e-mails")
    smtp_ok = bool(st.secrets.get("SMTP_USER", "") and st.secrets.get("SMTP_PASS", "") and st.secrets.get("SMTP_FROM", st.secrets.get("SMTP_USER", "")))
    if smtp_ok:
        st.markdown('<div class="email-ok">SMTP configurado: os e-mails conseguem sair pelo app quando uma rotina é executada.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="email-warn">SMTP incompleto: o sistema registra o e-mail como pendente, mas não consegue enviar até configurar SMTP_USER, SMTP_PASS e SMTP_FROM.</div>', unsafe_allow_html=True)
    st.write("Cadastro novo: e-mail automático aos sócios assim que o colaborador é salvo.")
    st.write("Rescisões: alertas automáticos são checados quando o app é aberto e também pela rotina diária.")
    st.write("Aniversários, pendências documentais e quadro semanal: automáticos somente quando `scripts/run_daily_jobs.py` estiver agendado em GitHub Actions, servidor ou cron.")

    st.subheader("Usuários internos e PIN")
    st.info("Por segurança, cadastre apenas o hash do PIN. Gere o hash abaixo e salve na tabela usuarios.")
    pin = st.text_input("PIN para gerar hash", type="password")
    if pin:
        st.code(sha256_pin(pin))
    st.subheader("Teste de SMTP")
    to = st.text_input("Destinatário de teste", value="amadvjuridica@gmail.com")
    if st.button("Enviar teste"):
        email_and_log("teste_smtp", "[Teste SMTP] Assis & Mollerke", "E-mail de teste do sistema.", [to])
        st.success("Teste processado.")


def page_auditoria() -> None:
    st.title("Auditoria")
    rows = fetch_table("historico_acoes", "created_at", True)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def update_deadlines_and_alerts() -> None:
    if st.session_state.get("alerts_checked_today") == date.today().isoformat():
        return
    st.session_state.alerts_checked_today = date.today().isoformat()
    client = sb()
    rescisoes = fetch_table("rescisoes", "created_at", True)
    colaboradores = {c["id"]: c for c in get_colaboradores()}
    for r in rescisoes:
        ultimo = parse_date(r.get("ultimo_dia_trabalhado"))
        if not ultimo or r.get("rescisao_paga"):
            continue
        status = calculate_rescisao_status(ultimo, False)
        if status != r.get("status_prazo"):
            client.table("rescisoes").update({"status_prazo": status, "updated_at": now_iso()}).eq("id", r["id"]).execute()
        nome = colaboradores.get(r.get("colaborador_id"), {}).get("nome_completo", "colaborador")
        days = (date.today() - ultimo).days + 1
        if 1 <= days <= 7 and not r.get("contabilidade_comunicada"):
            subject = f"[Rescisao] Contabilidade comunicada? - {nome}"
            body = f"A contabilidade já foi comunicada sobre a rescisão de {nome}?"
            email_and_log("rescisao_contabilidade", subject, body, SOCIOS_EMAILS, [SUPERVISOR_EMAIL])
        elif days >= 8 and not r.get("rescisao_paga"):
            subject = f"[Rescisao] Pagamento pendente - {nome}"
            body = f"A rescisão de {nome} já foi paga? Status atual: {status}."
            email_and_log("rescisao_pagamento", subject, body, SOCIOS_EMAILS, [SUPERVISOR_EMAIL])


def main() -> None:
    css()
    require_login()
    try:
        st.sidebar.image(LOGO_PATH, use_container_width=True)
    except Exception:
        st.sidebar.title("A&M")
    st.sidebar.caption(f"{BRAND_NAME} | Confidencial")
    page = st.sidebar.radio(
        "Menu",
        [
            PAGE_COLABORADORES,
            PAGE_RESCISOES,
            PAGE_RELATORIOS,
        ],
    )
    update_deadlines_and_alerts()
    pages = {
        PAGE_COLABORADORES: page_colaboradores,
        PAGE_RESCISOES: page_rescisoes,
        PAGE_RELATORIOS: page_relatorios,
    }
    pages[page]()
    institutional_footer()

if __name__ == "__main__":
    main()



























