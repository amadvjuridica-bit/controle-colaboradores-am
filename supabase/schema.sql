create extension if not exists "pgcrypto";

create table if not exists public.usuarios (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  perfil text not null,
  pin_hash text not null,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.colaboradores (
  id uuid primary key default gen_random_uuid(),
  nome_completo text not null,
  cpf text not null,
  rg text,
  data_nascimento date,
  cidade_nascimento text,
  estado_nascimento text,
  telefone text,
  email text not null,
  endereco text,
  cep text,
  cargo text,
  tipo_vinculo text not null,
  status text not null default 'ativo' check (status in ('ativo', 'inativo', 'rescindido')),
  data_admissao date,
  data_rescisao date,
  ultimo_dia_trabalhado date,
  banco text,
  agencia text,
  conta text,
  tipo_conta text,
  pix text,
  tipo_pix text,
  titular_conta text,
  cpf_titular text,
  observacoes text,
  cadastro_incompleto boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.documentos_modelo (
  id uuid primary key default gen_random_uuid(),
  tipo_vinculo text not null,
  documento text not null,
  obrigatorio boolean not null default true,
  prazo_dias integer,
  destaque boolean not null default false,
  created_at timestamptz not null default now(),
  unique (tipo_vinculo, documento)
);

create table if not exists public.documentos_colaborador (
  id uuid primary key default gen_random_uuid(),
  colaborador_id uuid not null references public.colaboradores(id),
  documento text not null,
  recebido boolean not null default false,
  data_recebimento date,
  arquivo_url text,
  observacoes text,
  status text not null default 'pendente' check (status in ('pendente', 'recebido', 'em atraso')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (colaborador_id, documento)
);

create table if not exists public.rescisoes (
  id uuid primary key default gen_random_uuid(),
  colaborador_id uuid not null references public.colaboradores(id),
  tipo_desligamento text not null,
  data_rescisao date not null,
  ultimo_dia_trabalhado date not null,
  carta_obrigatoria boolean not null default false,
  carta_anexada boolean not null default false,
  data_carta_anexada timestamptz,
  contabilidade_comunicada boolean not null default false,
  data_comunicacao_contabilidade date,
  rescisao_paga boolean not null default false,
  data_pagamento date,
  valor_pago numeric(12,2),
  comprovante_pagamento_url text,
  status_prazo text not null default 'em aberto',
  motivo text,
  observacoes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.vagas (
  id uuid primary key default gen_random_uuid(),
  tipo_vinculo text not null unique,
  quantidade_total integer not null default 0,
  quantidade_ocupada integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.historico_acoes (
  id uuid primary key default gen_random_uuid(),
  usuario_id uuid references public.usuarios(id),
  usuario_nome text,
  acao text not null,
  colaborador_id uuid references public.colaboradores(id),
  antes jsonb,
  depois jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.alertas_email (
  id uuid primary key default gen_random_uuid(),
  tipo text not null,
  assunto text not null,
  destinatarios jsonb not null default '[]'::jsonb,
  cc jsonb not null default '[]'::jsonb,
  corpo text,
  enviado boolean not null default false,
  erro text,
  created_at timestamptz not null default now()
);

create table if not exists public.configuracoes_email (
  id uuid primary key default gen_random_uuid(),
  chave text not null unique,
  valor text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.aniversarios_log (
  id uuid primary key default gen_random_uuid(),
  colaborador_id uuid references public.colaboradores(id),
  tipo_alerta text not null,
  data_referencia date not null,
  enviado boolean not null default false,
  created_at timestamptz not null default now(),
  unique (colaborador_id, tipo_alerta, data_referencia)
);

create table if not exists public.relatorios_semanais_log (
  id uuid primary key default gen_random_uuid(),
  data_referencia date not null unique,
  enviado boolean not null default false,
  created_at timestamptz not null default now()
);

create unique index if not exists idx_colaboradores_cpf_unique on public.colaboradores(cpf);
create index if not exists idx_colaboradores_status on public.colaboradores(status);
create index if not exists idx_colaboradores_tipo on public.colaboradores(tipo_vinculo);
create index if not exists idx_documentos_colaborador on public.documentos_colaborador(colaborador_id);
create index if not exists idx_rescisoes_colaborador on public.rescisoes(colaborador_id);
create index if not exists idx_historico_colaborador on public.historico_acoes(colaborador_id);

insert into storage.buckets (id, name, public)
values ('documentos', 'documentos', false)
on conflict (id) do nothing;

insert into public.documentos_modelo (tipo_vinculo, documento, prazo_dias, destaque) values
('Estagiário', 'Contrato de estágio', 7, true),
('Estagiário', 'RG', null, false),
('Estagiário', 'CPF', null, false),
('Estagiário', 'Comprovante de residência', null, false),
('Estagiário', 'Declaração de matrícula', null, false),
('CLT', 'RG', null, false),
('CLT', 'CPF', null, false),
('CLT', 'Comprovante de endereço', null, false),
('CLT', 'Exame admissional', null, true),
('CLT', 'PIS/PASEP', null, false),
('CLT', 'Certidão de nascimento/casamento', null, false),
('CLT', 'Título de eleitor', null, false),
('CLT', 'Certificado de reservista', null, false),
('CLT', 'Comprovante de escolaridade', null, false)
on conflict (tipo_vinculo, documento) do nothing;

insert into public.vagas (tipo_vinculo, quantidade_total, quantidade_ocupada) values
('CLT', 3, 3),
('Estagiário', 5, 5),
('PJ', 0, 0)
on conflict (tipo_vinculo) do nothing;

