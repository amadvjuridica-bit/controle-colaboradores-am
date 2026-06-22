from __future__ import annotations

import hashlib
import io
import json
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

DOCUMENTOS_ESTAGIARIO = [
    "Contrato de estágio",
    "RG",
    "CPF",
    "Comprovante de residência",
    "Declaração de matrícula",
]

DOCUMENTOS_CLT = [
    "RG",
    "CPF",
    "Comprovante de endereço",
    "Exame admissional",
    "PIS/PASEP",
    "Certidão de nascimento/casamento",
    "Título de eleitor",
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
        :root {
            --am-blue: #24294f;
            --am-blue-2: #34507e;
            --am-gray: #f4f6f8;
            --am-border: #d8dde6;
            --am-red: #b42318;
            --am-yellow: #b7791f;
            --am-green: #067647;
        }
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        [data-testid="stSidebar"] { background: #f7f8fa; border-right: 1px solid #e3e7ee; }
        h1, h2, h3 { color: var(--am-blue); letter-spacing: 0; }
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--am-border);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, .06);
        }
        .status-ok { color: var(--am-green); font-weight: 700; }
        .status-warn { color: var(--am-yellow); font-weight: 700; }
        .status-bad { color: var(--am-red); font-weight: 700; }
        .notice {
            border: 1px solid #f5c2c7;
            background: #fff5f5;
            color: #7a271a;
            padding: 12px 14px;
            border-radius: 8px;
            font-weight: 650;
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

    col1, col2 = st.columns([1, 2])
    with col1:
        try:
            st.image(LOGO_PATH, use_container_width=True)
        except Exception:
            st.title("A&M")
    with col2:
        st.title("Controle de Colaboradores")
        st.caption("Assis & Mollerke")
        password = st.text_input("Senha principal do app", type="password")
        expected = st.secrets.get("APP_PASSWORD", "")
        if st.button("Entrar", type="primary"):
            if expected and password == expected:
                st.session_state.logged = True
                st.rerun()
            else:
                st.error("Senha inválida ou APP_PASSWORD não configurado.")
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


def upload_document(file: Any, folder: str) -> str | None:
    if not file:
        return None
    safe_name = file.name.replace(" ", "_")
    path = f"{folder}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
    data = file.getvalue()
    sb().storage.from_(st.secrets.get("SUPABASE_STORAGE_BUCKET", "documentos")).upload(
        path,
        data,
        {"content-type": file.type or "application/octet-stream", "upsert": "false"},
    )
    return path


def pending_fields(payload: dict[str, Any], required: list[str]) -> list[str]:
    return [field for field in required if not payload.get(field)]


def status_documental(colaborador: dict[str, Any], docs: list[dict[str, Any]]) -> tuple[str, list[str]]:
    required = DOCUMENTOS_ESTAGIARIO if colaborador.get("tipo_vinculo") == "Estagiário" else DOCUMENTOS_CLT
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
Usuário/PIN responsável pelo cadastro: {usuario.get('nome')}
Data e hora do cadastro: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    email_and_log("novo_colaborador", subject, body, SOCIOS_EMAILS)


def collaborator_form(prefix: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    current = current or {}
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
        cargo = st.text_input("Cargo/função*", value=current.get("cargo", ""), key=f"{prefix}_cargo")
        tipo_vinculo = st.selectbox(
            "Tipo de vínculo*",
            ["CLT", "Estagiário", "PJ", "8 horas", "Outro"],
            index=["CLT", "Estagiário", "PJ", "8 horas", "Outro"].index(current.get("tipo_vinculo", "CLT"))
            if current.get("tipo_vinculo", "CLT") in ["CLT", "Estagiário", "PJ", "8 horas", "Outro"]
            else 0,
            key=f"{prefix}_tipo",
        )
    with c3:
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
        observacoes = st.text_area("Observações", value=current.get("observacoes", ""), key=f"{prefix}_obs")

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
        "Confirmo que conferi os dados bancários e o Pix informado.",
        key=f"{prefix}_bank_confirmed",
    )

    return {
        "nome_completo": nome.strip(),
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
        "observacoes": observacoes.strip(),
        "_bank_confirmed": bank_confirmed,
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
    if "@" not in payload.get("email", ""):
        errors.append("E-mail obrigatório inválido.")
    bank_fields = ["banco", "agencia", "conta", "pix"]
    if any(payload.get(field) for field in bank_fields) and not payload.get("_bank_confirmed"):
        errors.append("Confirme a conferência dos dados bancários e Pix.")
    return errors


def dashboard() -> None:
    st.title("Dashboard")
    colaboradores = get_colaboradores()
    docs = fetch_table("documentos_colaborador", "created_at", True)
    rescisoes = fetch_table("rescisoes", "created_at", True)
    vagas = fetch_table("vagas", "tipo_vinculo", False)
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    pendencias = sum(len(status_documental(c, docs)[1]) for c in colaboradores)
    contratos_pendentes = sum(1 for d in docs if d.get("documento") == "Contrato de estágio" and d.get("status") != "recebido")
    contratos_atraso = sum(1 for d in docs if d.get("documento") == "Contrato de estágio" and d.get("status") == "em atraso")
    exames_pendentes = sum(1 for d in docs if d.get("documento") == "Exame admissional" and d.get("status") != "recebido")
    resc_abertas = [r for r in rescisoes if r.get("status_prazo") not in ("regularizado", "pago")]
    vencidas = [r for r in rescisoes if r.get("status_prazo") == "prazo legal vencido"]
    proximas = [r for r in rescisoes if r.get("status_prazo") in ("dia 8", "dia 9", "dia 10")]
    aniversariantes = [c for c in colaboradores if parse_date(c.get("data_nascimento")) and parse_date(c.get("data_nascimento")).month == date.today().month]
    vagas_disp = sum((v.get("quantidade_total") or 0) - (v.get("quantidade_ocupada") or 0) for v in vagas)

    metrics = [
        ("Ativos", len(ativos)),
        ("CLT", sum(1 for c in ativos if c.get("tipo_vinculo") == "CLT")),
        ("Estagiários", sum(1 for c in ativos if c.get("tipo_vinculo") == "Estagiário")),
        ("PJ", sum(1 for c in ativos if c.get("tipo_vinculo") == "PJ")),
        ("8 horas", sum(1 for c in ativos if c.get("tipo_vinculo") == "8 horas")),
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


def page_colaboradores() -> None:
    st.title("Colaboradores")
    colaboradores = get_colaboradores()
    if not colaboradores:
        st.info("Nenhum colaborador cadastrado.")
        return
    df = pd.DataFrame(colaboradores)
    visible = [
        "nome_completo",
        "tipo_vinculo",
        "cargo",
        "status",
        "data_admissao",
        "email",
        "telefone",
        "cpf",
    ]
    st.dataframe(df[[c for c in visible if c in df.columns]], use_container_width=True, hide_index=True)

    st.subheader("Editar colaborador")
    selected = select_colaborador("Selecione", colaboradores)
    if not selected:
        return
    payload = collaborator_form("edit", selected)
    usuario = pin_form("alterar_dados_pessoais", "edit")
    if st.button("Salvar alterações", type="primary"):
        errors = validate_colaborador(payload)
        if errors:
            for err in errors:
                st.error(err)
            return
        if not usuario:
            st.error("Informe um PIN válido.")
            return
        payload.pop("_bank_confirmed", None)
        payload["updated_at"] = now_iso()
        sb().table("colaboradores").update(payload).eq("id", selected["id"]).execute()
        audit("alterar_dados_pessoais", selected["id"], usuario, selected, payload)
        st.success("Colaborador atualizado.")
        st.rerun()


def page_novo_cadastro() -> None:
    st.title("Novo cadastro")
    payload = collaborator_form("new")
    usuario = pin_form("cadastrar_colaborador", "new")
    if st.button("Cadastrar colaborador", type="primary"):
        errors = validate_colaborador(payload)
        if errors:
            for err in errors:
                st.error(err)
            return
        if not usuario:
            st.error("Informe um PIN válido.")
            return
        payload.pop("_bank_confirmed", None)
        payload["cadastro_incompleto"] = bool(pending_fields(payload, ["cpf", "rg", "email", "endereco", "cep"]))
        payload["created_at"] = now_iso()
        payload["updated_at"] = now_iso()
        result = sb().table("colaboradores").insert(payload).execute().data[0]
        create_default_docs(result)
        audit("cadastrar_colaborador", result["id"], usuario, None, result)
        _, pendings = status_documental(result, fetch_table("documentos_colaborador", "created_at", True))
        novo_colaborador_email(result, usuario, pendings)
        st.success("Colaborador cadastrado e e-mail aos sócios processado.")
        st.rerun()


def create_default_docs(colaborador: dict[str, Any]) -> None:
    docs = DOCUMENTOS_ESTAGIARIO if colaborador.get("tipo_vinculo") == "Estagiário" else DOCUMENTOS_CLT
    rows = []
    for item in docs:
        status = "pendente"
        if item == "Contrato de estágio" and parse_date(colaborador.get("data_admissao")):
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
    st.title("Documentação")
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
    file = st.file_uploader("Upload do arquivo", type=None)
    observacoes = st.text_area("Observações", value=doc.get("observacoes", ""))
    usuario = pin_form("anexar_documento", "doc")
    if st.button("Salvar documento", type="primary"):
        if not usuario:
            st.error("Informe um PIN válido.")
            return
        path = upload_document(file, f"colaboradores/{selected['id']}") if file else doc.get("arquivo_url")
        payload = {
            "recebido": recebido,
            "data_recebimento": data_recebimento.isoformat() if data_recebimento else None,
            "arquivo_url": path,
            "observacoes": observacoes,
            "status": "recebido" if recebido else status,
            "updated_at": now_iso(),
        }
        sb().table("documentos_colaborador").update(payload).eq("id", doc["id"]).execute()
        audit("anexar_documento", selected["id"], usuario, doc, payload)
        st.success("Documento atualizado.")
        st.rerun()


def page_rescisoes() -> None:
    st.title("Rescisões")
    colaboradores = [c for c in get_colaboradores() if c.get("status") == "ativo"]
    selected = select_colaborador("Colaborador ativo", colaboradores)
    if not selected:
        return
    tipo = st.selectbox("Tipo de desligamento", ["Pedido do colaborador", "Dispensa pela empresa"])
    data_rescisao = st.date_input("Data da rescisão", value=date.today(), format="DD/MM/YYYY")
    ultimo_dia = st.date_input("Último dia trabalhado", value=date.today(), format="DD/MM/YYYY")
    motivo = st.text_area("Motivo")
    observacoes = st.text_area("Observações")
    carta = st.file_uploader("Carta de desligamento")
    comprovante = st.file_uploader("Comprovante de pagamento")
    data_pagamento = st.date_input("Data de pagamento", value=None, format="DD/MM/YYYY")
    valor_pago = st.number_input("Valor pago", min_value=0.0, step=100.0)
    usuario = pin_form("registrar_rescisao", "rescisao")
    if st.button("Registrar rescisão", type="primary"):
        if tipo == "Pedido do colaborador" and not carta:
            st.error("Carta assinada é obrigatória para pedido do colaborador.")
            return
        if not usuario:
            st.error("Informe um PIN válido.")
            return
        carta_path = upload_document(carta, f"rescisoes/{selected['id']}") if carta else None
        comprovante_path = upload_document(comprovante, f"rescisoes/{selected['id']}") if comprovante else None
        status_prazo = calculate_rescisao_status(ultimo_dia, bool(data_pagamento))
        payload = {
            "colaborador_id": selected["id"],
            "tipo_desligamento": tipo,
            "data_rescisao": data_rescisao.isoformat(),
            "ultimo_dia_trabalhado": ultimo_dia.isoformat(),
            "carta_obrigatoria": tipo == "Pedido do colaborador",
            "carta_anexada": bool(carta_path),
            "data_carta_anexada": now_iso() if carta_path else None,
            "rescisao_paga": bool(data_pagamento),
            "data_pagamento": data_pagamento.isoformat() if data_pagamento else None,
            "valor_pago": valor_pago if valor_pago else None,
            "comprovante_pagamento_url": comprovante_path,
            "status_prazo": status_prazo,
            "motivo": motivo,
            "observacoes": observacoes,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        res = sb().table("rescisoes").insert(payload).execute().data[0]
        sb().table("colaboradores").update({"status": "rescindido", "data_rescisao": data_rescisao.isoformat(), "ultimo_dia_trabalhado": ultimo_dia.isoformat(), "updated_at": now_iso()}).eq("id", selected["id"]).execute()
        audit("registrar_rescisao", selected["id"], usuario, selected, res)
        st.success("Rescisão registrada.")
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
    carta_update = st.file_uploader("Anexar carta de rescisão", key="rescisao_carta_update")
    comprovante_update = st.file_uploader("Anexar comprovante de pagamento", key="rescisao_comprovante_update")
    usuario_update = pin_form("confirmar_pagamento_rescisao", "rescisao_update")
    if st.button("Salvar acompanhamento", type="primary"):
        if not usuario_update:
            st.error("Informe um PIN válido.")
            return
        carta_path = upload_document(carta_update, f"rescisoes/{current['colaborador_id']}") if carta_update else None
        comprovante_path = upload_document(comprovante_update, f"rescisoes/{current['colaborador_id']}") if comprovante_update else None
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
            payload["comprovante_pagamento_url"] = comprovante_path
        sb().table("rescisoes").update(payload).eq("id", current["id"]).execute()
        action = "confirmar_pagamento_rescisao" if paga else "confirmar_contabilidade"
        audit(action, current["colaborador_id"], usuario_update, current, payload)
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
    st.title("Vagas")
    vagas = fetch_table("vagas", "tipo_vinculo", False)
    colaboradores = get_colaboradores()
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    for tipo in ["CLT", "Estagiário", "PJ", "8 horas"]:
        occupied = sum(1 for c in ativos if c.get("tipo_vinculo") == tipo)
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
    st.title("Aniversários")
    colaboradores = [c for c in get_colaboradores() if c.get("data_nascimento")]
    rows = []
    for c in colaboradores:
        birth = parse_date(c.get("data_nascimento"))
        rows.append(
            {
                "nome": c["nome_completo"],
                "tipo": c.get("tipo_vinculo"),
                "cargo": c.get("cargo"),
                "data_nascimento": br_date(birth),
                "idade": age(birth),
                "tempo_empresa": company_time(c.get("data_admissao")),
                "mes": birth.month if birth else None,
                "dia": birth.day if birth else None,
            }
        )
    st.dataframe(pd.DataFrame(rows).sort_values(["mes", "dia"]), use_container_width=True, hide_index=True)
    if st.button("Enviar alertas de aniversário de hoje/amanhã"):
        send_birthday_alerts()
        st.success("Rotina de aniversários processada.")


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
    st.title("Relatórios")
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
    if tipo == "Quadro semanal" and st.button("Enviar quadro semanal por e-mail"):
        send_weekly_report(df)
        st.success("Quadro semanal processado.")


def build_report(tipo: str) -> pd.DataFrame:
    colaboradores = get_colaboradores()
    docs = fetch_table("documentos_colaborador", "created_at", True)
    if tipo == "Colaboradores ativos":
        return pd.DataFrame([c for c in colaboradores if c.get("status") == "ativo"])
    if tipo == "Colaboradores inativos/rescindidos":
        return pd.DataFrame([c for c in colaboradores if c.get("status") != "ativo"])
    if tipo == "Documentação pendente":
        rows = []
        for c in colaboradores:
            _, pend = status_documental(c, docs)
            if pend:
                rows.append({"nome": c["nome_completo"], "tipo": c.get("tipo_vinculo"), "pendências": "; ".join(pend)})
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
                    "tipo": c.get("tipo_vinculo"),
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
                "Tipo de vínculo": c.get("tipo_vinculo"),
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
Total CLT: {sum(1 for c in ativos if c.get('tipo_vinculo') == 'CLT')}
Total estagiários: {sum(1 for c in ativos if c.get('tipo_vinculo') == 'Estagiário')}
Total PJ: {sum(1 for c in ativos if c.get('tipo_vinculo') == 'PJ')}
Total 8 horas: {sum(1 for c in ativos if c.get('tipo_vinculo') == '8 horas')}
Total inativos/rescindidos: {sum(1 for c in colaboradores if c.get('status') != 'ativo')}

Tabela:
{df.to_string(index=False)}

Este relatório é enviado automaticamente pelo sistema de controle de funcionários e estagiários.
"""
    email_and_log("quadro_semanal", subject, body, SOCIOS_EMAILS + [SUPERVISOR_EMAIL])
    sb().table("relatorios_semanais_log").insert({"data_referencia": date.today().isoformat(), "enviado": True, "created_at": now_iso()}).execute()


def page_configuracoes() -> None:
    st.title("Configurações")
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
            subject = f"[Rescisão] Contabilidade comunicada? - {nome}"
            body = f"A contabilidade já foi comunicada sobre a rescisão de {nome}?"
            email_and_log("rescisao_contabilidade", subject, body, SOCIOS_EMAILS, [SUPERVISOR_EMAIL])
        elif days >= 8 and not r.get("rescisao_paga"):
            subject = f"[Rescisão] Pagamento pendente - {nome}"
            body = f"A rescisão de {nome} já foi paga? Status atual: {status}."
            email_and_log("rescisao_pagamento", subject, body, SOCIOS_EMAILS, [SUPERVISOR_EMAIL])


def main() -> None:
    css()
    require_login()
    try:
        st.sidebar.image(LOGO_PATH, use_container_width=True)
    except Exception:
        st.sidebar.title("A&M")
    st.sidebar.caption("Assis & Mollerke")
    page = st.sidebar.radio(
        "Menu",
        [
            "Dashboard",
            "Colaboradores",
            "Novo cadastro",
            "Documentação",
            "Rescisões",
            "Vagas",
            "Aniversários",
            "Relatórios",
            "Configurações",
            "Auditoria",
        ],
    )
    update_deadlines_and_alerts()
    pages = {
        "Dashboard": dashboard,
        "Colaboradores": page_colaboradores,
        "Novo cadastro": page_novo_cadastro,
        "Documentação": page_documentacao,
        "Rescisões": page_rescisoes,
        "Vagas": page_vagas,
        "Aniversários": page_aniversarios,
        "Relatórios": page_relatorios,
        "Configurações": page_configuracoes,
        "Auditoria": page_auditoria,
    }
    pages[page]()


if __name__ == "__main__":
    main()
