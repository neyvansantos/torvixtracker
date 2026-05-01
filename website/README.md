# Torvix Tracker Website

Site, autenticação, checkout PIX e área de conta do Torvix Tracker, feito com
Next.js, TypeScript, Tailwind CSS, Supabase Auth e Mercado Pago.

## Configuração Local

Instale as dependências:

```bash
npm install
```

Crie o arquivo local de ambiente:

```bash
cp .env.example .env.local
```

Preencha `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_SITE_URL=http://localhost:3000
MERCADO_PAGO_ACCESS_TOKEN=your-mercado-pago-access-token
MERCADO_PAGO_WEBHOOK_SECRET=your-mercado-pago-webhook-secret
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
# opcional: URL publica direta do instalador mais recente
TORVIX_INSTALLER_DOWNLOAD_URL=
```

Nunca coloque `MERCADO_PAGO_ACCESS_TOKEN`, `MERCADO_PAGO_WEBHOOK_SECRET` ou
`SUPABASE_SERVICE_ROLE_KEY` no frontend. Eles são usados apenas nas rotas API
server-side.

Rode localmente:

```bash
npm run dev
```

Abra:

```text
http://localhost:3000
```

## Supabase

1. Crie um projeto no Supabase.
2. Abra Project Settings > API.
3. Copie Project URL para `NEXT_PUBLIC_SUPABASE_URL`.
4. Copie anon public key para `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
5. Copie service role key para `SUPABASE_SERVICE_ROLE_KEY`.
6. Abra Authentication > Providers.
7. Ative o provider Email.

## Tabelas

O dashboard lê `profiles.plan` e `profiles.has_pro`. O download passa pela rota
server-side `POST /api/download/torvix` e só é entregue quando
`profiles.has_pro = true`.

Por padrão, a rota aponta para o asset `latest` do GitHub Releases:

```text
https://github.com/NeyvanSantos/TorvixTracker/releases/latest/download/TorvixTracker_Setup.rar
```

Se o repositório/release for privado, clientes sem acesso ao GitHub receberão
404. Nesse caso, publique o instalador em uma URL acessível e configure
`TORVIX_INSTALLER_DOWNLOAD_URL`.

```sql
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  plan text default 'free',
  has_pro boolean default false,
  created_at timestamp with time zone default now()
);
```

Tabela de compras:

```sql
create table public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  mercado_pago_payment_id text,
  mercado_pago_status text default 'pending',
  amount numeric default 19.99,
  product_name text default 'Torvix Tracker',
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

alter table public.purchases enable row level security;

create policy "User can read own purchases"
on public.purchases
for select
using (auth.uid() = user_id);
```

## Mercado Pago

1. Crie ou acesse sua conta em Mercado Pago Developers.
2. Abra Your integrations.
3. Crie uma aplicação para o Torvix Tracker.
4. Acesse as credenciais da aplicação.
5. Copie o Access Token para `MERCADO_PAGO_ACCESS_TOKEN`.
6. Configure um webhook para pagamentos.

URL local de webhook para testes com ngrok:

```text
https://SEU_SUBDOMINIO.ngrok-free.app/api/webhooks/mercado-pago
```

URL final em produção:

```text
https://SEU_SITE.com/api/webhooks/mercado-pago
```

No painel do Mercado Pago, configure a chave secreta do webhook e copie para:

```env
MERCADO_PAGO_WEBHOOK_SECRET=
```

Para testar localmente com ngrok:

```bash
ngrok http 3000
```

Depois atualize `.env.local`:

```env
NEXT_PUBLIC_SITE_URL=https://SEU_SUBDOMINIO.ngrok-free.app
```

Reinicie o servidor após mudar `.env.local`.

## Fluxo de Compra

1. Usuário cria conta ou entra no site.
2. Usuário acessa `/checkout`.
3. Clica em `Gerar PIX`.
4. O frontend chama `POST /api/checkout/create-pix` com o token Supabase.
5. A rota cria o pagamento PIX no Mercado Pago.
6. A rota salva uma linha em `purchases` com status `pending`.
7. O usuário paga o PIX.
8. Mercado Pago chama `POST /api/webhooks/mercado-pago`.
9. O webhook consulta o pagamento diretamente na API do Mercado Pago.
10. Se `status === "approved"`, o site atualiza:

```text
profiles.has_pro = true
profiles.plan = pro
```

Status `rejected`, `cancelled` ou `expired` apenas atualizam a compra. Eles não
liberam acesso Pro.

## Como Testar

1. Preencha `.env.local` com Supabase, Mercado Pago e service role.
2. Rode `npm run dev`.
3. Entre com um usuário sem Pro.
4. Acesse `/dashboard` e confirme que o acesso está bloqueado.
5. Clique em `Comprar por R$19,99`.
6. Clique em `Gerar PIX`.
7. Pague usando as instruções de teste do Mercado Pago.
8. Aguarde o webhook.
9. No Supabase, abra Table Editor > `profiles`.
10. Confirme se `has_pro` mudou para `true` e `plan` mudou para `pro`.
11. Volte ao dashboard e confirme se o botão `Baixar Torvix Tracker` apareceu.

## Liberação Manual

Enquanto testa, também é possível liberar um usuário manualmente:

1. Abra Supabase.
2. Vá em Table Editor.
3. Abra a tabela `profiles`.
4. Escolha a linha do usuário.
5. Mude `has_pro` para `true`.
6. Mude `plan` para `pro`.
7. Salve a linha.
