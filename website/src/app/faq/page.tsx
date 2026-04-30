// Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
const faqs = [
  {
    question: "Preciso de Tobii Eye Tracker?",
    answer:
      "Não. O Torvix Tracker funciona com uma webcam comum e não exige hardware dedicado.",
  },
  {
    question: "Preciso de OpenTrack?",
    answer:
      "Não. O Torvix Tracker envia os dados de rastreamento diretamente ao jogo usando saída compatível com TrackIR.",
  },
  {
    question: "Funciona com Euro Truck Simulator 2?",
    answer: "Sim. O Torvix Tracker é compatível com ETS2.",
  },
  {
    question: "Funciona com American Truck Simulator?",
    answer: "Sim. ATS é totalmente suportado.",
  },
  {
    question: "Preciso de uma webcam muito boa?",
    answer:
      "Uma webcam básica funciona, mas câmeras melhores entregam rastreamento mais suave.",
  },
  {
    question: "É difícil configurar?",
    answer:
      "Não. O aplicativo foi pensado para ser simples, com calibração fácil e ajustes flexíveis.",
  },
  {
    question: "Tem rastreamento de cabeça?",
    answer: "Sim. O rastreamento completo de cabeça é suportado.",
  },
  {
    question: "Tem rastreamento dos olhos?",
    answer:
      "O Torvix Tracker inclui rastreamento simulado do olhar para uma experiência mais imersiva.",
  },
  {
    question: "Vai receber atualizações?",
    answer:
      "Sim. A versão Pro receberá atualizações e melhorias futuras.",
  },
];

export default function FaqPage() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.16)_0%,rgba(0,72,82,0.08)_24%,rgba(5,8,10,0.02)_58%,rgba(0,229,255,0.08)_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-20 -z-10 h-[560px] w-[960px] -translate-x-1/2 rounded-full bg-primary/12 blur-3xl" />

      <section className="mx-auto max-w-4xl px-5 py-20 sm:px-8">
        <div className="text-center">
          <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            FAQ
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
            Perguntas frequentes
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-muted">
            Tudo que você precisa saber antes de usar o Torvix Tracker.
          </p>
        </div>

        <div className="mt-12 space-y-4">
          {faqs.map((faq, index) => (
            <details
              className="group rounded-2xl border border-border bg-surface p-5 shadow-[0_20px_80px_rgba(0,0,0,0.16)] transition hover:border-primary/45 open:border-primary/45 open:bg-surface-strong"
              key={faq.question}
              open={index === 0}
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-5 text-left text-base font-semibold text-white marker:hidden sm:text-lg">
                <span>{faq.question}</span>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary-soft text-xl leading-none text-primary transition group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-4 max-w-3xl leading-8 text-muted">{faq.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </main>
  );
}
