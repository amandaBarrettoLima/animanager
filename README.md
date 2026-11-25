# AniManager — Ração sob controle

Flask + SQLite no back-end e HTML/CSS/JS (ES Modules, sem build) no front-end,
organizados em camadas MVC.

## Como rodar
    python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python run.py                                          # http://localhost:5000
    python -m unittest discover -s tests -t .              # 107 testes do back-end

O banco `database/animanager.db` é criado a partir de `database/schema.sql` + `database/seed.sql`
na primeira execução. Variáveis: `SECRET_KEY` (obrigatória em produção), `DATABASE_PATH`, `SEED_DEMO=0`.

Usuários de teste (senha `senha123`): `admin@animanager.org` (todos os abrigos),
`esperanca@animanager.com` (Esperança), `patinhas@animanager.org` (Patinhas).

## Estrutura
```
run.py / config.py          entrada e configuração
database/                   schema.sql (tabelas, CHECKs, índices, view de saldo) e seed.sql
app/
  __init__.py               Application Factory
  container.py              Composition Root (injeção de dependência)
  controllers/              C  → só HTTP: lê request, chama o serviço, devolve resposta
  services/                 regras de negócio (única camada que "decide")
  repositories/             acesso a dados (todo SQL mora aqui)
  models/                   M  → entidades imutáveis (dataclasses)
  views/json_views.py       V  → como cada entidade é exposta na API
  listeners/                observers (auditoria)
  core/                     banco, exceções, eventos, relógio, validadores, segurança
static/
  index.html, css/
  js/models/                M  → falam com a API
  js/views/                 V  → só geram HTML (sem lógica, sem fetch)
  js/controllers/           C  → eventos, orquestram model + view
  (Sprint 3: telas Início, Histórico e Perfis; diálogo de remoção de abrigo)
  js/core/                  http-client, router, dispatcher, helpers
tests/test_api.py
```
Fluxo: `Controller → Service → Repository → SQLite`. Dependências só apontam para baixo;
controllers nunca escrevem SQL e repositories nunca conhecem HTTP.

## Padrões GoF e princípios aplicados
| Padrão | Onde | Para quê |
|---|---|---|
| Factory Method | `create_app`, `TipoMovimentacaoFactory`, `AccessPolicyFactory` | criar a app / a estratégia certa |
| Singleton | `core/database.py::Database`, `js/core/http-client.js` | ponto único de config do banco e de acesso à API |
| Strategy | `access_policy.py` (Administrador/Responsável), `movimentacao_strategies.py` (Entrada/Saída) | trocar regra sem `if` espalhado |
| Observer | `core/events.py` + `AuditoriaListener`; `js/core/event-emitter.js` | auditoria desacoplada; front reage à sessão expirada |
| Decorator | `@login_required` | exigir sessão sem tocar no controller |
| Template Method | `repositories/base.py`, `js/controllers/pagina-controller.js` | esqueleto comum, detalhes nas subclasses |
| Unit of Work | `Database.transaction()` | "checa saldo + grava" atômico (`BEGIN IMMEDIATE`) |
| Repository, DTO/Presenter | `repositories/`, `views/json_views.py` | isolar dados; nunca vazar `senha_hash` |
| Front Controller | `js/controllers/app-controller.js` | rota, guarda de acesso e render num só lugar |

SOLID: **S** cada camada/classe com uma função; **O** novo tipo de movimentação ou perfil = nova classe;
**L** estratégias intercambiáveis; **I** interfaces pequenas; **D** serviços recebem dependências pelo
construtor (`container.py`), o que permite trocar o relógio nos testes.

## Visual (tema “Pet Shop”)
Inspirado em landing pages de pet shop em *design plano*: fundo creme, laranja/amarelo quentes, azul-marinho nos títulos,
cantos bem arredondados, botões “gordinhos” (com borda inferior), banner no topo de cada tela e um cachorro e um gato
desenhados em SVG (`static/js/views/ilustracoes.js`, sem imagens externas nem direitos autorais).
* **Paleta:** só variáveis no início de `static/css/styles.css` (`--brand` laranja, `--sun` amarelo, `--navy`, `--bg`...).
  Há versão escura automática (`prefers-color-scheme: dark`).
* **Fontes:** Fredoka (títulos/botões) e Nunito (texto), via Google Fonts; sem internet cai para a fonte arredondada do sistema.
* **Telas:** login em duas colunas com ilustração · banner por página (`cabecalho()` em `views/componentes.js`) ·
  tela Início com atalhos e cartões de estoque · menu em “pílulas” com rolagem horizontal no celular · diálogos com fundo desfocado.
* Respeita `prefers-reduced-motion` e mantém foco visível para navegação por teclado.

## Regras de negócio e segurança
* Permissão sempre validada no servidor (`AccessPolicy`): responsável só vê/altera o próprio abrigo (403 nos demais).
  Funções **administrativas** (criar/remover abrigo, gerir perfis) → `Acesso restrito a administradores`.
* Saldo = entradas − saídas − consumos (view `vw_saldo_abrigo`); saída/consumo não pode exceder o saldo.
* Um consumo por abrigo por dia (também garantido por `UNIQUE(abrigo_id, dia)` no banco).
* Correção de consumo após 24 h exige justificativa.
* **Nomes únicos:** só pode existir **1 abrigo com um dado nome** no sistema, e **1 animal com um dado nome em cada
  abrigo** — animais de abrigos diferentes podem ter o mesmo nome. A comparação ignora maiúsculas/minúsculas, acentos
  de caixa (`Ç`/`ç`) e espaços extras (`"Abrigo  X "` = `"abrigo x"`). Violação → HTTP 409. A regra vale na aplicação
  (dentro da transação) **e** no banco (`UNIQUE(nome_chave)` e `UNIQUE(abrigo_id, nome_chave)`).
* **Remoção de abrigo (US-07):** só administrador. Bloqueada se houver animais ou usuários responsáveis vinculados;
  caso contrário remove o abrigo **e o histórico de estoque/consumo dele** (registrado na auditoria).
* **Estoque mínimo (US-16):** campo `estoque_minimo` (kg, ≥ 0) por abrigo; 0 desliga o alerta.
* **Alerta de estoque baixo (US-17):** saldo **abaixo** do mínimo (igual ao mínimo não alerta). A cada consumo, correção ou
  saída a resposta traz `alerta` e, se o saldo *cruzou* o mínimo, grava o evento `estoque.baixo` (Observer). A tela
  inicial lista os abrigos em alerta dentro do escopo do usuário.
* **Perfis (US-03):** Administrador ou Responsável de abrigo; ninguém altera o **próprio** perfil. Vale na hora, inclusive
  para sessões já abertas.
* **Minha conta:** qualquer usuário (administrador ou responsável de abrigo) troca o próprio e-mail e/ou senha, informando a
  **senha atual**. Senha nova: 6 a 128 caracteres, sem espaço nas pontas. E-mail: formato válido e único no sistema (409 se já existir).
* **Acesso de outros usuários (admin):** na tela **Perfis → Editar acesso** o administrador troca o e-mail e define uma nova
  senha (digitada ou **temporária gerada**: 10 caracteres, sem `0/O/1/l/I`). Para si mesmo, usa “Minha conta”.
* **Senhas não podem ser “visualizadas”:** são guardadas só como hash scrypt (exigência da Definition of Done: “nunca em
  texto puro”), então nem o administrador consegue ler uma senha já gravada. O que o sistema faz é **exibir a senha uma única vez**,
  no momento em que o administrador a define ou gera (com 👁️ para ver/ocultar e botão Copiar), para repassá-la ao usuário.
  Se for esquecida, define-se outra. A auditoria registra *quem* trocou *o quê*, nunca a senha.
* **Sessões:** ao trocar a senha (por si ou pelo admin) as outras sessões daquele usuário são encerradas; quem trocou continua logado.
* Senhas com hash (scrypt), sessão de 24 h, cookie HttpOnly/SameSite, JSON obrigatório (barra CSRF por `<form>`),
  SQL 100 % parametrizado, escape de HTML no front, trilha de auditoria na tabela `auditoria`.

## Banco de dados e migração
`database/schema.sql` cria um banco novo já na versão 2 (`PRAGMA user_version`). Se você já tem um `animanager.db` das
Sprints 1–2, **nada a fazer**: ao iniciar, `app/core/migrations.py` adiciona as colunas novas sem perder dados e
**renomeia nomes repetidos** que já existissem (o mais novo vira `"Nome (2)"`, `"Nome (3)"`…), registrando um aviso no log.

## Endpoints
`POST /api/auth/login` · `POST /api/auth/logout` · `GET /api/auth/me`

| Recurso | Rotas |
|---|---|
| Abrigos | `GET /api/abrigos` · `POST /api/abrigos` (admin) · `PUT /api/abrigos/<id>` · `DELETE /api/abrigos/<id>` (admin) |
| Animais | `GET /api/animais[?abrigo_id=]` · `POST /api/animais` |
| Estoque | `GET /api/movimentacoes` · `POST /api/movimentacoes` · `GET /api/estoque/saldos` · `GET /api/estoque/alertas` |
| Consumo | `GET /api/consumos` · `POST /api/consumos` · `PUT /api/consumos/<id>` |
| Histórico | `GET /api/historico/consumos?inicio=AAAA-MM-DD&fim=AAAA-MM-DD&abrigo_id=&pagina=1&tamanho=10` |
| Perfis (admin) | `GET /api/usuarios` · `PUT /api/usuarios/<id>/perfil` `{"perfil": "administrador"\|"responsavel", "abrigo_id": 1}` |
| Minha conta | `PUT /api/conta` `{"email"?, "nova_senha"?, "senha_atual"}` |
| Acesso de outros (admin) | `PUT /api/usuarios/<id>/credenciais` `{"email"?, "nova_senha"? \| "gerar_senha": true}` → devolve `senha_temporaria` (só quando gerada; `Cache-Control: no-store`) |

`POST /api/consumos`, `PUT /api/consumos/<id>` e `POST /api/movimentacoes` devolvem também `"alerta"`
(`{abrigo_id, abrigo_nome, saldo, estoque_minimo}` ou `null`). O histórico devolve
`{itens, pagina, tamanho, total, total_paginas, total_kg}` (tamanho: 1–100).

## Rastreabilidade — Sprint 3 (documento de Scrum → código → teste)
| História | Implementação | Testes (`tests/test_sprint3.py`) |
|---|---|---|
| US-07 Remover abrigo | `AbrigoService.remover`, `DELETE /api/abrigos/<id>`, diálogo de confirmação | `TestRemoverAbrigo` (cenário “Remoção de abrigo com animais”) |
| US-15 Histórico por período | `ConsumoService.historico`, `HistoricoController`, tela **Histórico** | `TestHistorico` |
| US-16 Nível mínimo | `abrigos.estoque_minimo`, campo no formulário de abrigo | `TestEstoqueMinimoEAlerta` |
| US-17 Alerta de estoque baixo | `EstoqueService.alertas/verificar_nivel_minimo`, tela **Início** | cenário “Estoque cruza o limiar” |
| US-03 Atribuir perfil | `UsuarioService`, tela **Perfis** | `TestPerfis` |
| US-04 Restringir funções administrativas | `AccessPolicy.exigir_administrador`, menu e rota protegidos | cenário “Perfil restrito tenta acessar área administrativa” |
| Minha conta / acesso (ajuste) | `UsuarioService.alterar_conta/alterar_credenciais`, telas **Minha conta** e **Perfis → Editar acesso** | `tests/test_acesso.py` |
| Nomes únicos (ajuste) | `nome_chave` + índices únicos + checagem transacional | `TestNomesUnicos`, `TestMigracao` |
