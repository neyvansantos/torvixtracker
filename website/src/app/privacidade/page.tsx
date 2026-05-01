// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Política de Privacidade",
  description:
    "Política de Privacidade do Torvix Tracker, com informações sobre dados de conta, pagamento, download e suporte.",
};

const sections = [
  {
    title: "1. Quem somos",
    body: [
      "Esta Política de Privacidade explica como o Torvix Tracker trata dados pessoais no site, na área de conta, no checkout e nos fluxos de download do aplicativo.",
      "O aplicativo desktop Torvix Tracker usa a webcam para rastreamento local no computador do usuário. O site não recebe imagens da webcam nem frames de rastreamento do aplicativo.",
    ],
  },
  {
    title: "2. Dados que podemos coletar",
    body: [
      "Dados de conta: e-mail, senha criptografada pelo provedor de autenticação e nome opcional informado no cadastro.",
      "Dados de compra: identificador do pagamento, status do pagamento, valor, plano adquirido e informações necessárias para liberar o acesso Pro.",
      "Dados técnicos: registros de acesso, endereço IP, navegador, dispositivo, páginas acessadas e eventos necessários para segurança, prevenção de fraude e funcionamento do site.",
      "Dados de suporte: informações que você enviar voluntariamente ao entrar em contato conosco.",
    ],
  },
  {
    title: "3. Como usamos os dados",
    body: [
      "Criar e proteger sua conta.",
      "Processar pagamentos, confirmar compras e liberar acesso ao Torvix Tracker Pro.",
      "Permitir download do instalador para usuários autorizados.",
      "Melhorar segurança, estabilidade, prevenção de fraude e funcionamento do site.",
      "Responder solicitações de suporte e cumprir obrigações legais ou regulatórias.",
    ],
  },
  {
    title: "4. Serviços de terceiros",
    body: [
      "Usamos Supabase para autenticação, sessão de usuário e armazenamento de dados de conta/perfil.",
      "Usamos Mercado Pago para processar pagamentos PIX e confirmar o status da compra.",
      "Usamos Vercel para hospedar o site e disponibilizar as páginas públicas.",
      "Esses provedores podem tratar dados conforme suas próprias políticas, sempre dentro das finalidades necessárias para entregar o serviço.",
    ],
  },
  {
    title: "5. Cookies e armazenamento local",
    body: [
      "O site pode usar cookies técnicos ou armazenamento local para manter sessão de login, autenticação e segurança.",
      "Não usamos essas tecnologias para vender dados pessoais. Caso ferramentas de analytics ou marketing sejam adicionadas no futuro, esta política deverá ser atualizada.",
    ],
  },
  {
    title: "6. Compartilhamento de dados",
    body: [
      "Não vendemos dados pessoais.",
      "Podemos compartilhar dados apenas com provedores necessários ao funcionamento do serviço, como autenticação, hospedagem, pagamento e infraestrutura, ou quando houver obrigação legal.",
    ],
  },
  {
    title: "7. Retenção e segurança",
    body: [
      "Mantemos dados pelo tempo necessário para fornecer o serviço, cumprir obrigações legais, resolver disputas, prevenir fraude e manter registros de compra.",
      "Adotamos medidas razoáveis de segurança, incluindo autenticação por provedor especializado, controle de acesso e uso de variáveis de ambiente para credenciais sensíveis.",
    ],
  },
  {
    title: "8. Direitos do titular",
    body: [
      "Nos termos da LGPD, você pode solicitar confirmação de tratamento, acesso, correção, anonimização, bloqueio, eliminação, portabilidade, informação sobre compartilhamento e revogação de consentimento quando aplicável.",
      "Para exercer seus direitos, entre em contato pelos canais oficiais do Torvix Tracker informando qual solicitação deseja realizar.",
    ],
  },
  {
    title: "9. Alterações nesta política",
    body: [
      "Podemos atualizar esta política para refletir mudanças no produto, no site, nos provedores usados ou em exigências legais.",
      "A versão mais recente ficará disponível nesta página.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.14)_0%,rgba(0,72,82,0.08)_24%,rgba(5,8,10,0.02)_58%,rgba(0,229,255,0.06)_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-20 -z-10 h-[560px] w-[960px] -translate-x-1/2 rounded-full bg-primary/12 blur-3xl" />

      <section className="mx-auto max-w-4xl px-5 py-20 sm:px-8">
        <div>
          <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Privacidade
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
            Política de Privacidade
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-muted">
            Última atualização: 1 de maio de 2026.
          </p>
          <p className="mt-4 max-w-3xl leading-8 text-muted">
            Esta página foi criada para dar transparência sobre como o Torvix
            Tracker trata dados pessoais no site e nos serviços relacionados.
          </p>
        </div>

        <div className="mt-12 space-y-5">
          {sections.map((section) => (
            <section
              className="rounded-2xl border border-border bg-surface p-5 shadow-[0_20px_80px_rgba(0,0,0,0.16)]"
              key={section.title}
            >
              <h2 className="text-xl font-bold text-white">{section.title}</h2>
              <div className="mt-4 space-y-3 leading-8 text-muted">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <p className="mt-10 text-sm leading-7 text-muted">
          Esta política é um documento informativo do produto e não substitui
          orientação jurídica específica.
        </p>
      </section>
    </main>
  );
}
