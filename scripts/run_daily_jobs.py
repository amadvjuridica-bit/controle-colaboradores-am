from __future__ import annotations

import os
import re
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage

from dateutil.relativedelta import relativedelta
from supabase import create_client


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SMTP_HOST = os.getenv("SMTP_HOST", "mail.amcob.com.br")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Assis & Mollerke")

SOCIOS = ["am@amcob.com.br", "amadvjuridica@gmail.com"]
SUPERVISOR = "comercial@amcob.com.br"

CARGA_HORARIA_RE = re.compile(r"^Carga horária CLT:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def normalize_tipo_vinculo(value):
    return "CLT" if value == "8 horas" else value


def carga_horaria_from_colaborador(colaborador):
    if colaborador.get("tipo_vinculo") == "8 horas":
        return "8 horas"
    explicit = colaborador.get("carga_horaria")
    if explicit:
        return str(explicit)
    match = CARGA_HORARIA_RE.search(colaborador.get("observacoes") or "")
    return match.group(1).strip() if match else ""


def colaborador_tipo_label(colaborador):
    tipo = normalize_tipo_vinculo(colaborador.get("tipo_vinculo"))
    carga = carga_horaria_from_colaborador(colaborador)
    if tipo == "CLT" and carga:
        return f"CLT ({carga})"
    return tipo or ""

def send_email(subject: str, body: str, to: list[str], cc: list[str] | None = None) -> bool:
    cc = cc or []
    if not SMTP_USER or not SMTP_PASS or not SMTP_FROM:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    msg["Reply-To"] = SMTP_FROM
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(body)
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    return True


def parse_date(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value)).date()


def age(birth, ref):
    return relativedelta(ref, birth).years


def company_time(start, ref):
    if not start:
        return ""
    delta = relativedelta(ref, start)
    if delta.years and delta.months:
        return f"{delta.years} anos e {delta.months} meses"
    if delta.years:
        return f"{delta.years} anos"
    return f"{delta.months} meses"


def log_email(sb, tipo, subject, body, to, cc, sent):
    sb.table("alertas_email").insert(
        {
            "tipo": tipo,
            "assunto": subject,
            "destinatarios": to,
            "cc": cc,
            "corpo": body,
            "enviado": sent,
        }
    ).execute()


def birthday_alerts(sb, colaboradores):
    today = date.today()
    for label, target in [("amanhã", today + timedelta(days=1)), ("hoje", today)]:
        for c in colaboradores:
            birth = parse_date(c.get("data_nascimento"))
            if not birth or (birth.month, birth.day) != (target.month, target.day):
                continue
            log_exists = sb.table("aniversarios_log").select("id").eq("colaborador_id", c["id"]).eq("tipo_alerta", label).eq("data_referencia", target.isoformat()).execute().data
            if log_exists:
                continue
            subject = f"[Aniversário {label}] Assis & Mollerke - {c['nome_completo']}"
            body = f"""Olá,

{('Amanhã é' if label == 'amanhã' else 'Hoje é')} aniversário de {c['nome_completo']}.

Dados:
Nome: {c['nome_completo']}
Tipo de vínculo: {colaborador_tipo_label(c)}
Cargo: {c.get('cargo', '')}
Data de nascimento: {birth:%d/%m/%Y}
Idade: {age(birth, target)}
Tempo de empresa: {company_time(parse_date(c.get('data_admissao')), today)}

Mensagem automática do sistema de controle de colaboradores.
"""
            sent = send_email(subject, body, SOCIOS + [SUPERVISOR])
            log_email(sb, "aniversario", subject, body, SOCIOS + [SUPERVISOR], [], sent)
            sb.table("aniversarios_log").insert({"colaborador_id": c["id"], "tipo_alerta": label, "data_referencia": target.isoformat(), "enviado": sent}).execute()


def weekly_report(sb, colaboradores):
    today = date.today()
    if today.weekday() != 0:
        return
    exists = sb.table("relatorios_semanais_log").select("id").eq("data_referencia", today.isoformat()).execute().data
    if exists:
        return
    ativos = [c for c in colaboradores if c.get("status") == "ativo"]
    subject = f"[Quadro semanal de colaboradores] Assis & Mollerke - Semana de {today:%d/%m/%Y}"
    lines = [
        "Bom dia,",
        "",
        "Segue o quadro atualizado de colaboradores da Assis & Mollerke.",
        "",
        "Resumo:",
        f"Total de colaboradores ativos: {len(ativos)}",
        f"Total CLT: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'CLT')}",
        f"Total CLT 6h: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'CLT' and carga_horaria_from_colaborador(c) == '6 horas')}",
        f"Total CLT 8h: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'CLT' and carga_horaria_from_colaborador(c) == '8 horas')}",
        f"Total estagiários: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'Estagiário')}",
        f"Total PJ: {sum(1 for c in ativos if normalize_tipo_vinculo(c.get('tipo_vinculo')) == 'PJ')}",
        f"Total inativos/rescindidos: {sum(1 for c in colaboradores if c.get('status') != 'ativo')}",
        "",
        "Tabela:",
    ]
    for c in colaboradores:
        lines.append(f"{c.get('nome_completo')} | {colaborador_tipo_label(c)} | {c.get('cargo')} | {c.get('status')}")
    lines.extend(["", "Este relatório é enviado automaticamente pelo sistema de controle de funcionários e estagiários."])
    body = "\n".join(lines)
    sent = send_email(subject, body, SOCIOS + [SUPERVISOR])
    log_email(sb, "quadro_semanal", subject, body, SOCIOS + [SUPERVISOR], [], sent)
    sb.table("relatorios_semanais_log").insert({"data_referencia": today.isoformat(), "enviado": sent}).execute()


def resignation_alerts(sb, colaboradores):
    by_id = {c["id"]: c for c in colaboradores}
    rescisoes = sb.table("rescisoes").select("*").execute().data or []
    today = date.today()
    for r in rescisoes:
        if r.get("rescisao_paga"):
            continue
        ultimo = parse_date(r.get("ultimo_dia_trabalhado"))
        if not ultimo:
            continue
        days = (today - ultimo).days + 1
        if days < 1:
            continue
        nome = by_id.get(r.get("colaborador_id"), {}).get("nome_completo", "colaborador")
        if 1 <= days <= 7 and not r.get("contabilidade_comunicada"):
            subject = f"[Rescisão] Comunicar contabilidade - {nome}"
            body = f"A contabilidade já foi comunicada sobre a rescisão de {nome}?"
            sent = send_email(subject, body, SOCIOS, [SUPERVISOR])
            log_email(sb, "rescisao_contabilidade", subject, body, SOCIOS, [SUPERVISOR], sent)
        elif days >= 8:
            subject = f"[Rescisão] Pagamento de rescisão - {nome}"
            body = f"A rescisão de {nome} já foi paga? Prazo contado desde {ultimo:%d/%m/%Y}."
            sent = send_email(subject, body, SOCIOS, [SUPERVISOR])
            log_email(sb, "rescisao_pagamento", subject, body, SOCIOS, [SUPERVISOR], sent)


def document_alerts(sb, colaboradores):
    by_id = {c["id"]: c for c in colaboradores}
    docs = sb.table("documentos_colaborador").select("*").neq("status", "recebido").execute().data or []
    pending_lines = []
    today = date.today()
    for doc in docs:
        colaborador = by_id.get(doc.get("colaborador_id"), {})
        nome = colaborador.get("nome_completo", "Colaborador")
        status = doc.get("status", "pendente")
        admissao = parse_date(colaborador.get("data_admissao"))
        if doc.get("documento") == "Contrato de estágio" and admissao and today > admissao + timedelta(days=7):
            status = "em atraso"
            sb.table("documentos_colaborador").update({"status": status}).eq("id", doc["id"]).execute()
        if doc.get("documento") == "Exame admissional":
            status = "pendente"
        pending_lines.append(f"{nome} | {doc.get('documento')} | {status}")

    if not pending_lines:
        return
    subject = "[Pendências documentais] Assis & Mollerke"
    body = "Pendências documentais atuais:\n\n" + "\n".join(pending_lines)
    sent = send_email(subject, body, [SUPERVISOR], SOCIOS)
    log_email(sb, "documentacao_pendente", subject, body, [SUPERVISOR], SOCIOS, sent)


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    colaboradores = sb.table("colaboradores").select("*").execute().data or []
    birthday_alerts(sb, colaboradores)
    weekly_report(sb, colaboradores)
    resignation_alerts(sb, colaboradores)
    document_alerts(sb, colaboradores)
    print("Rotinas diárias processadas.")


if __name__ == "__main__":
    main()







