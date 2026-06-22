from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
from supabase import create_client


XLSX_PATH = os.getenv("INITIAL_XLSX_PATH", r"C:\Users\User\OneDrive\ASSIS E MOLLERKE\ESTAGIÁRIOS E FUNCIONÁRIOS\INFORMAÇÕES_ESTAGIÁRIOS_FUNCIONARIOS.xlsx")
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

FUNCIONARIOS_PERMITIDOS = {
    "CARLOS AUGUSTO BRITTES DOS SANTOS": "ativo",
    "NICOLI ARROGO ROCHA": "ativo",
    "DANIEL DEL'OLMO ALVES": "ativo",
}


def clean(value):
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value).strip()


def excel_date(value):
    if pd.isna(value) or value in ("", "-"):
        return None
    parsed = pd.to_datetime(value, errors="coerce", origin="1899-12-30", unit="D") if isinstance(value, (int, float)) else pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date().isoformat()


def row_to_colaborador(row, tipo_vinculo, status):
    endereco = ", ".join(
        part
        for part in [
            clean(row.get("Rua")) or clean(row.get("Endereço")),
            clean(row.get("Nº")),
            clean(row.get("Bairro")),
            clean(row.get("Complemento")),
            clean(row.get("Cidade")) or clean(row.get("Cidade ")),
            clean(row.get("Estado")),
        ]
        if part
    )
    email = clean(row.get("E-mail"))
    payload = {
        "nome_completo": clean(row.get("Nome")) or clean(row.get("Nome ")),
        "cpf": clean(row.get("CPF")),
        "rg": clean(row.get("RG")),
        "data_nascimento": excel_date(row.get("Nascimento")),
        "cidade_nascimento": clean(row.get("Cidade")) or clean(row.get("Cidade ")) or "Campo Grande",
        "estado_nascimento": clean(row.get("Estado")) or "MS",
        "telefone": clean(row.get("Telefone")),
        "email": email,
        "endereco": endereco,
        "cep": clean(row.get("CEP")),
        "cargo": "Estagiário" if tipo_vinculo == "Estagiário" else "CLT",
        "tipo_vinculo": tipo_vinculo,
        "status": status,
        "data_admissao": excel_date(row.get("Data Início")),
        "data_rescisao": excel_date(row.get("Rescisão")) if status == "rescindido" else None,
        "ultimo_dia_trabalhado": excel_date(row.get("Rescisão")) if status == "rescindido" else None,
        "banco": clean(row.get("Banco")),
        "agencia": clean(row.get("Agência")),
        "conta": clean(row.get("Conta")),
        "tipo_conta": clean(row.get("Tipo")),
        "pix": clean(row.get("PIX")),
        "tipo_pix": "CPF" if clean(row.get("PIX")) == clean(row.get("CPF")).replace(".", "").replace("-", "") else "",
        "titular_conta": clean(row.get("Nome")) or clean(row.get("Nome ")),
        "cpf_titular": clean(row.get("CPF")),
        "observacoes": f"Importado automaticamente em {datetime.now():%d/%m/%Y %H:%M}.",
    }
    required = ["nome_completo", "cpf", "rg", "data_nascimento", "telefone", "email", "endereco", "cep", "cargo", "data_admissao"]
    payload["cadastro_incompleto"] = any(not payload.get(field) for field in required)
    return payload


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    funcionarios = pd.read_excel(XLSX_PATH, sheet_name="Funcionários")
    estagiarios = pd.read_excel(XLSX_PATH, sheet_name="Estagiários")

    rows = []
    for _, row in funcionarios.iterrows():
        nome = clean(row.get("Nome")) or clean(row.get("Nome "))
        if nome in FUNCIONARIOS_PERMITIDOS:
            rows.append(row_to_colaborador(row, "CLT", FUNCIONARIOS_PERMITIDOS[nome]))

    ativos = estagiarios[estagiarios["Contrato"].astype(str).str.upper().str.strip().eq("ATIVO")]
    for _, row in ativos.iterrows():
        rows.append(row_to_colaborador(row, "Estagiário", "ativo"))

    for payload in rows:
        supabase.table("colaboradores").upsert(payload, on_conflict="cpf").execute()

    print(f"Importados/atualizados {len(rows)} colaboradores.")


if __name__ == "__main__":
    main()
