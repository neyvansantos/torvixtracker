// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Termos de Uso",
  description:
    "Termos de Uso do Torvix Tracker para site, conta, compra, download e uso do aplicativo.",
};

const sections = [
  {
    title: "1. Aceitação dos termos",
    body: [
      "Ao acessar o site, criar uma conta, comprar o plano Pro, baixar ou usar o Torvix Tracker, você concorda com estes Termos de Uso.",
      "Se você não concordar com estes termos, não utilize o site, a área de conta, o checkout ou o aplicativo.",
    ],
  },
  {
    title: "2. Sobre o Torvix Tracker",
    body: [
      "O Torvix Tracker é um aplicativo de rastreamento por webcam voltado para melhorar a experiência em jogos compatíveis, como Euro Truck Simulator 2 e American Truck Simulator.",
      "O funcionamento pode variar conforme webcam, iluminação, desempenho do computador, configurações do sistema, jogo utilizado e perfil de calibração.",
    ],
  },
  {
    title: "3. Conta do usuário",
    body: [
      "Para acessar compras, área de download e recursos Pro, pode ser necessário criar uma conta com e-mail e senha.",
      "Você é responsável por manter suas credenciais em segurança e por todas as ações realizadas na sua conta.",
      "Podemos bloquear ou restringir contas em caso de fraude, abuso, violação destes termos ou tentativa de acesso não autorizado.",
    ],
  },
  {
    title: "4. Compra e acesso Pro",
    body: [
      "O plano Pro é liberado após confirmação do pagamento pelo provedor de pagamento utilizado no checkout.",
      "A liberação pode não ser imediata em caso de atraso, análise, falha de comunicação ou inconsistência no processamento do pagamento.",
      "Preços, ofertas e recursos podem ser alterados futuramente, sem afetar direitos já adquiridos conforme a legislação aplicável.",
    ],
  },
  {
    title: "5. Licença de uso",
    body: [
      "A compra ou download do Torvix Tracker concede uma licença limitada, pessoal, revogável, não exclusiva e intransferível para uso do aplicativo.",
      "Você não recebe propriedade sobre o código, marca, identidade visual, arquivos internos ou demais elementos protegidos do Torvix Tracker.",
    ],
  },
  {
    title: "6. Uso permitido e restrições",
    body: [
      "Você deve usar o Torvix Tracker apenas de forma lícita, respeitando estes termos e as regras dos jogos, plataformas e serviços relacionados.",
      "É proibido revender, sublicenciar, distribuir cópias não autorizadas, tentar burlar mecanismos de acesso, explorar vulnerabilidades, fazer engenharia reversa quando não permitida por lei ou usar o serviço para fraude.",
    ],
  },
  {
    title: "7. Atualizações e disponibilidade",
    body: [
      "Podemos lançar atualizações, melhorias, correções e mudanças de compatibilidade a qualquer momento.",
      "O site, o checkout, o download e determinados recursos podem ficar indisponíveis temporariamente por manutenção, falhas técnicas, provedores externos ou motivos de segurança.",
    ],
  },
  {
    title: "8. Limitação de responsabilidade",
    body: [
      "O Torvix Tracker é fornecido no estado em que se encontra, com esforços razoáveis de qualidade, estabilidade e segurança.",
      "Não garantimos compatibilidade perfeita com todos os computadores, webcams, versões de jogos, mods, softwares externos ou configurações específicas.",
      "Na máxima extensão permitida pela lei, não nos responsabilizamos por perdas indiretas, lucros cessantes, problemas causados por terceiros, uso inadequado, configurações incorretas ou alterações feitas fora do aplicativo oficial.",
    ],
  },
  {
    title: "9. Reembolso e direitos do consumidor",
    body: [
      "Pedidos de reembolso, cancelamento ou suporte comercial serão analisados conforme a legislação aplicável, o método de pagamento utilizado e as condições da compra.",
      "Nada nestes termos limita direitos obrigatórios previstos no Código de Defesa do Consumidor ou em outras normas aplicáveis.",
    ],
  },
  {
    title: "10. Propriedade intelectual",
    body: [
      "Torvix Tracker, seu nome, marca, interface, textos, imagens, arquivos, código e demais materiais pertencem ao Torvix Tracker ou a seus respectivos licenciadores.",
      "Dependências de terceiros, bibliotecas e serviços integrados permanecem sujeitos às suas próprias licenças e termos.",
    ],
  },
  {
    title: "11. Privacidade",
    body: [
      "O tratamento de dados pessoais relacionado ao site, conta, pagamento e download é descrito na Política de Privacidade.",
      "Ao usar o serviço, você também declara ciência da Política de Privacidade disponível no site.",
    ],
  },
  {
    title: "12. Alterações destes termos",
    body: [
      "Podemos atualizar estes Termos de Uso para refletir mudanças no produto, no site, na operação, em provedores externos ou em exigências legais.",
      "A versão mais recente ficará disponível nesta página.",
    ],
  },
];

export default function TermsPage() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.14)_0%,rgba(0,72,82,0.08)_24%,rgba(5,8,10,0.02)_58%,rgba(0,229,255,0.06)_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-20 -z-10 h-[560px] w-[960px] -translate-x-1/2 rounded-full bg-primary/12 blur-3xl" />

      <section className="mx-auto max-w-4xl px-5 py-20 sm:px-8">
        <div>
          <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Termos
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
            Termos de Uso
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-muted">
            Última atualização: 1 de maio de 2026.
          </p>
          <p className="mt-4 max-w-3xl leading-8 text-muted">
            Estes termos definem as regras básicas para uso do site, conta,
            checkout, download e aplicativo Torvix Tracker.
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
          Este documento é informativo e não substitui orientação jurídica
          específica para situações particulares.
        </p>
      </section>
    </main>
  );
}
