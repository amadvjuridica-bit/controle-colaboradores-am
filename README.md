# Controle de Colaboradores - Assis & Mollerke

Aplicativo Streamlit para controle interno de funcionários CLT, estagiários, PJ, vínculos de 8 horas, documentação, rescisões, vagas, aniversários, relatórios, auditoria por PIN e alertas por e-mail.

## Estrutura

- `app.py`: aplicativo Streamlit completo.
- `supabase/schema.sql`: criação das tabelas, índices, modelos de documentos, bucket privado e vagas iniciais.
- `supabase/seed_initial.sql`: importação inicial filtrada da planilha enviada.
- `scripts/import_initial_xlsx.py`: importador para reprocessar a planilha original.
- `scripts/run_daily_jobs.py`: rotina diária de e-mails para servidor, cron ou GitHub Actions.
- `.streamlit/secrets.toml.example`: modelo de secrets sem senhas reais.
- `assets/logo.png`: logo da empresa.

## Deploy no Supabase

1. Crie um projeto no Supabase.
2. Abra `SQL Editor`.
3. Execute `supabase/schema.sql`.
4. Execute `supabase/seed_initial.sql`.
5. Em `Storage`, confirme que o bucket privado `documentos` existe.
6. Em `Project Settings > API`, copie `Project URL` e `service_role key`.

## Usuários e PIN

O sistema usa uma senha principal do app e PIN individual para ações críticas.

1. Configure `APP_PASSWORD` e `PIN_SALT` nos secrets.
2. Rode o app.
3. Acesse `Configurações`.
4. Digite o PIN desejado para cada usuário e copie o hash.
5. Insira os usuários na tabela `usuarios`.

Exemplo:

```sql
insert into public.usuarios (nome, perfil, pin_hash) values
('Matheus Assis', 'Sócio administrador', 'HASH_GERADO_NO_APP'),
('Luigi Mollerke', 'Sócio', 'HASH_GERADO_NO_APP'),
('Luís Eduardo', 'Supervisor', 'HASH_GERADO_NO_APP');
```

Nunca salve PIN em texto puro.

## Secrets do Streamlit

Crie `.streamlit/secrets.toml` localmente ou configure os mesmos campos no Streamlit Cloud:

```toml
APP_PASSWORD = "senha-principal"
PIN_SALT = "salt-longo-aleatorio"
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "service-role-key"
SUPABASE_STORAGE_BUCKET = "documentos"
SMTP_HOST = "mail.amcob.com.br"
SMTP_PORT = 465
SMTP_USER = "am@amcob.com.br"
SMTP_PASS = "senha-smtp"
SMTP_FROM = "am@amcob.com.br"
SMTP_FROM_NAME = "Assis & Mollerke"
SMTP_CC = "am@amcob.com.br"
DEFAULT_TO = "amadvjuridica@gmail.com"
```

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Rotinas automáticas 24h

O Streamlit Cloud mantém o app online, mas não é um agendador garantido para tarefas em horário fixo. Para alertas diários e relatório semanal, rode:

```bash
python scripts/run_daily_jobs.py
```

Agende esse comando em um servidor 24h, cron, GitHub Actions ou serviço equivalente, com as variáveis de ambiente do Supabase e SMTP configuradas.

## Importação inicial

O seed já contém apenas os registros solicitados:

- Funcionários ativos: Carlos, Daniel e Nicoli/Nicole.
- Funcionários desligados da aba Funcionários não são importados.
- Estagiários ativos: Lívia, Juliana, Ana Clara, Rithielly e Darlan.

Para reimportar a planilha:

```bash
set INITIAL_XLSX_PATH=C:\Users\User\OneDrive\ASSIS E MOLLERKE\ESTAGIÁRIOS E FUNCIONÁRIOS\INFORMAÇÕES_ESTAGIÁRIOS_FUNCIONARIOS.xlsx
python scripts/import_initial_xlsx.py
```

Campos vazios são importados, mantidos editáveis e marcados como cadastro incompleto.
