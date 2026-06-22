insert into public.colaboradores (
  nome_completo, cpf, rg, data_nascimento, cidade_nascimento, estado_nascimento,
  telefone, email, endereco, cep, cargo, tipo_vinculo, status, data_admissao,
  data_rescisao, ultimo_dia_trabalhado, banco, agencia, conta, tipo_conta, pix,
  tipo_pix, titular_conta, cpf_titular, observacoes, cadastro_incompleto
) values
(
  'CARLOS AUGUSTO BRITTES DOS SANTOS', '035.871.721-37', '1651678', '1991-05-25',
  'Campo Grande', 'MS', '67 8413-2054', '',
  'Registro, 114, Jardim São Conrado, Campo Grande/MS', '79093-536',
  'CLT', 'CLT', 'ativo', '2026-04-06', null, null,
  'Banco Bradesco S.A.', '2202', '10579-1', 'Corrente', '035.871.721-37',
  'CPF', 'CARLOS AUGUSTO BRITTES DOS SANTOS', '035.871.721-37',
  'Importado da aba Funcionários.', true
),
(
  'NICOLI ARROGO ROCHA', '076.663.451-51', '64.852.377-9', '2007-06-18',
  'Campo Grande', 'MS', '18 99787-3307', '',
  'Pepino Giordano, 587, Residencial Oliveira III, Campo Grande/MS', '79091-775',
  'CLT', 'CLT', 'ativo', '2026-04-15', null, null,
  'Nubank', '1', '60800254-3', 'Corrente', '076.663.451-51',
  'CPF', 'NICOLI ARROGO ROCHA', '076.663.451-51',
  'Importado da aba Funcionários. Nome citado pelo cliente como Nicole.', true
),
(
  'DANIEL DEL''OLMO ALVES', '023.722.842-40', '027.722.842-40', '2008-03-27',
  'Campo Grande', 'MS', '67 992259694', '',
  'Rua Eunice Weave, 603, Santo Antônio, Campo Grande/MS', '79100-600',
  'CLT', 'CLT', 'ativo', '2026-05-12', null, null,
  'Banco do Brasil', '485', '1687158', 'CPF', '2372284240',
  'CPF', 'DANIEL DEL''OLMO ALVES', '023.722.842-40',
  'Importado da aba Funcionários.', true
),
(
  'LÍVIA ALVES GRANJA', '055.699.240-78', '2836181', '2005-01-12',
  'Campo Grande', 'MS', '67981214264', 'liviagranja6304@gmail.com',
  'Rua Fernando de Noronha, 118, Vila Sobrinho, BLOCO 1 - AP 301, Campo Grande/MS', '79110-290',
  'Estagiário', 'Estagiário', 'ativo', '2026-04-29', null, null,
  'Nubank', '1', '', 'CPF', '05569924078',
  'CPF', 'LÍVIA ALVES GRANJA', '055.699.240-78',
  'Faculdade: UFMS. Semestre: 1. Turno faculdade: Matutino. Turno escritório: Vespertino. Contrato: superestagios.', true
),
(
  'JULIANA DOS SANTOS MARI', '070.829.501-01', '0939498747', '2006-07-24',
  'Campo Grande', 'MS', '67991595305', 'julianassmari@gmail.com',
  'Rua Ribeirão Limpo, 7, Vila Oeste, Campo Grande/MS', '79116-475',
  'Estagiário', 'Estagiário', 'ativo', '2026-05-11', null, null,
  'Inter', '1', '46196230-6', 'CPF', '07082950101',
  'CPF', 'JULIANA DOS SANTOS MARI', '070.829.501-01',
  'Faculdade: UCDB. Semestre: 1. Turno faculdade: Noturno. Turno escritório: Matutino. Contrato: superestagios.', false
),
(
  'ANA CLARA PRIGOL DA CRUZ', '083.639.061-07', '083.638.061-07', '2004-04-19',
  'Campo Grande', 'MS', '67999264011', 'anaclaraprigoldacruz@gmail.com',
  'Rua Pio Rojas, 348, Monte Castelo, ApK24, Campo Grande/MS', '79010-410',
  'Estagiário', 'Estagiário', 'ativo', '2026-06-10', null, null,
  'Sicredi', '748', '79497-0', 'Telefone', '67999264011',
  'Telefone', 'ANA CLARA PRIGOL DA CRUZ', '083.639.061-07',
  'Faculdade: UCDB. Semestre: 7. Turno faculdade: Noturno. Turno escritório: Vespertino. Contrato: superestagios.', false
),
(
  'RITHIELLY GONÇALVES', '097.941.961-18', '2495508', '2008-05-10',
  'Campo Grande', 'MS', '67996269086', 'rithiellyg08@gmail.com',
  'Ana Pimentel, 56, Tarsila Do Amaral, Campo Grande/MS', '79017-430',
  'Estagiário', 'Estagiário', 'ativo', '2026-06-15', null, null,
  'Banco do Brasil', '0048-5', '181871-6', 'CPF', '09794196118',
  'CPF', 'RITHIELLY GONÇALVES', '097.941.961-18',
  'Faculdade: UNIDERP. Semestre: 1. Turno faculdade: Noturno. Turno escritório: Matutino. Contrato: superestagios.', false
),
(
  'DARLAN CARLOS DE MORAES', '931.387.841-00', '1202916', '1981-08-23',
  'Campo Grande', 'MS', '67993216061', 'darlanmoraes@hotmail.com',
  'Rua Brisas de Zaragoza, 100, Mata do Segredo, Campo Grande/MS', '79014-604',
  'Estagiário', 'Estagiário', 'ativo', '2026-06-15', null, null,
  'Sicredi', '913', '00049069-9', 'E-mail', 'darlanmoraes@hotmail.com',
  'E-mail', 'DARLAN CARLOS DE MORAES', '931.387.841-00',
  'Faculdade: Estácio de Sá. Semestre: 7. Turno faculdade: Matutino. Turno escritório: Vespertino. Contrato: superestagios.', false
)
on conflict (cpf) do update set
  nome_completo = excluded.nome_completo,
  rg = excluded.rg,
  data_nascimento = excluded.data_nascimento,
  telefone = excluded.telefone,
  email = excluded.email,
  endereco = excluded.endereco,
  cep = excluded.cep,
  cargo = excluded.cargo,
  tipo_vinculo = excluded.tipo_vinculo,
  status = excluded.status,
  data_admissao = excluded.data_admissao,
  data_rescisao = excluded.data_rescisao,
  ultimo_dia_trabalhado = excluded.ultimo_dia_trabalhado,
  banco = excluded.banco,
  agencia = excluded.agencia,
  conta = excluded.conta,
  tipo_conta = excluded.tipo_conta,
  pix = excluded.pix,
  tipo_pix = excluded.tipo_pix,
  titular_conta = excluded.titular_conta,
  cpf_titular = excluded.cpf_titular,
  observacoes = excluded.observacoes,
  cadastro_incompleto = excluded.cadastro_incompleto,
  updated_at = now();

insert into public.documentos_colaborador (colaborador_id, documento, recebido, status, observacoes)
select c.id, dm.documento, false,
  case
    when dm.tipo_vinculo = 'Estagiário'
      and dm.documento = 'Contrato de estágio'
      and c.data_admissao + interval '7 days' < current_date
    then 'em atraso'
    else 'pendente'
  end,
  'Checklist criado automaticamente no seed inicial.'
from public.colaboradores c
join public.documentos_modelo dm on dm.tipo_vinculo = c.tipo_vinculo
where c.cpf in (
  '035.871.721-37', '076.663.451-51', '023.722.842-40',
  '055.699.240-78', '070.829.501-01', '083.639.061-07',
  '097.941.961-18', '931.387.841-00'
)
on conflict (colaborador_id, documento) do nothing;
