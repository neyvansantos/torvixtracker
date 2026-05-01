// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import Link from "next/link";
import { PRICE_FULL, PRICE_TEXT, PRODUCT_NAME } from "@/config/product";

const problems = [
  "Hardware de eye tracking dedicado costuma ser caro.",
  "Configuracoes de rastreamento podem ser limitadas ou pouco flexiveis.",
  "Jogadores de simulador querem mais imersão, controle e liberdade na câmera.",
];

const solutions = [
  "Rastreamento de cabeça por webcam",
  "Rastreamento do olhar",
  "Visão estendida",
  "Curvas de sensibilidade",
  "Filtro de movimento",
  "Saída compatível com TrackIR",
];

const proPlan = [
  "Visão estendida",
  "Rastreamento do olhar",
  "Curvas de sensibilidade",
  "Filtro de movimento",
  "Perfis personalizados",
  "Atualizações",
];

const faqs = [
  {
    question: "Precisa de Tobii?",
    answer:
      "Não. O Torvix Tracker foi pensado para usar webcam comum como entrada de rastreamento.",
  },
  {
    question: "Precisa de OpenTrack?",
    answer:
      "Não obrigatoriamente. A proposta é entregar saída compatível com TrackIR e fluxos usados em simuladores.",
  },
  {
    question: "Funciona no ETS2?",
    answer:
      "Sim. O foco inicial do produto é Euro Truck Simulator 2 com controle de câmera mais imersivo.",
  },
  {
    question: "Funciona no ATS?",
    answer:
      "Sim. American Truck Simulator faz parte do alvo principal do site e da configuração do app.",
  },
  {
    question: "Precisa de webcam?",
    answer:
      "Sim. A webcam é usada para capturar rosto, cabeça e olhar durante o rastreamento.",
  },
];

export default function Home() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.15)_0%,rgba(0,72,82,0.10)_12%,rgba(5,8,10,0.02)_28%,rgba(0,229,255,0.08)_45%,rgba(5,8,10,0.02)_62%,rgba(0,112,128,0.10)_82%,rgba(5,8,10,0.04)_100%)]" />
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[560px] bg-[radial-gradient(circle_at_top,rgba(0,229,255,0.24),rgba(0,70,78,0.10)_42%,rgba(5,8,10,0)_74%)]" />
      <div className="pointer-events-none absolute left-1/2 top-[980px] -z-10 h-[560px] w-[900px] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute left-1/2 top-[2140px] -z-10 h-[620px] w-[980px] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />

      <section className="mx-auto grid min-h-[calc(100svh-4rem)] max-w-6xl items-center gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary shadow-[0_0_34px_rgba(0,229,255,0.12)]">
            Rastreamento de cabeça e olhar por webcam para ETS2/ATS
          </p>
          <h1 className="max-w-4xl text-5xl font-bold tracking-tight text-white sm:text-7xl">
            Transforme sua webcam em um rastreador profissional
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted sm:text-xl">
            Sem hardware caro. Funciona com ETS2 e ATS.
          </p>
          <div className="mt-7">
            <p className="text-2xl font-black text-primary">
              🔥 Acesso antecipado – {PRICE_TEXT}
            </p>
            <p className="mt-2 text-sm font-semibold text-white">
              {PRICE_FULL}. Sem mensalidade.
            </p>
            <ul className="mt-4 grid gap-2 text-sm text-muted sm:grid-cols-3">
              <li>✔ Pagamento único</li>
              <li>✔ Sem mensalidade</li>
              <li>✔ Acesso imediato após compra</li>
            </ul>
          </div>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link
              className="inline-flex h-12 items-center justify-center rounded-md bg-primary px-6 text-base font-bold text-[#001014] shadow-[0_0_34px_rgba(0,229,255,0.26)] transition hover:-translate-y-0.5 hover:bg-white"
              href="/checkout"
            >
              Comprar por {PRICE_TEXT}
            </Link>
            <Link
              className="inline-flex h-12 items-center justify-center rounded-md border border-primary/35 bg-white/[0.03] px-6 text-base font-bold text-white transition hover:-translate-y-0.5 hover:border-primary hover:bg-primary-soft"
              href="/login"
            >
              Entrar
            </Link>
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-6 rounded-[2rem] bg-primary/10 blur-3xl" />
          <div className="relative rounded-2xl bg-surface/80 p-4 shadow-2xl ring-1 ring-white/5 backdrop-blur">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div>
                <p className="text-sm font-semibold text-white">Status do rastreamento</p>
                <p className="mt-1 text-xs text-muted">Perfil ETS2 ativo</p>
              </div>
              <span className="rounded-md bg-primary-soft px-3 py-1 text-xs font-bold text-primary">
                ATIVO
              </span>
            </div>
            <div className="mt-4 aspect-video rounded-xl bg-[linear-gradient(135deg,rgba(0,229,255,0.14),rgba(255,255,255,0.03))] p-5 ring-1 ring-primary/15">
              <div className="flex h-full flex-col justify-between rounded-lg border border-white/10 bg-black/35 p-5">
                <div className="grid grid-cols-3 gap-3 text-center text-xs text-muted">
                  <span>Yaw +12</span>
                  <span>Pitch -4</span>
                  <span>Roll +2</span>
                </div>
                <div className="mx-auto h-28 w-28 rounded-full border border-primary/80 shadow-[0_0_42px_rgba(0,229,255,0.28)]" />
                <div className="grid gap-2">
                  {["Cabeça", "Olhar", "Saída TrackIR"].map((item) => (
                    <div
                      className="h-2 rounded-full bg-primary/70"
                      key={item}
                      title={item}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-black/25">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-primary">
              Problema
            </p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Imersao em simuladores ainda costuma custar caro.
            </h2>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {problems.map((problem) => (
              <article
                className="rounded-2xl border border-border bg-surface p-6 transition hover:-translate-y-1 hover:border-primary/50"
                key={problem}
              >
                <div className="mb-5 h-2 w-14 rounded-full bg-primary" />
                <p className="leading-7 text-muted">{problem}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-primary">
            Solucao
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Recursos pensados para ETS2, ATS e simuladores.
          </h2>
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {solutions.map((solution) => (
            <article
              className="rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_80px_rgba(0,0,0,0.18)] transition hover:-translate-y-1 hover:border-primary/50 hover:bg-surface-strong"
              key={solution}
            >
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-primary-soft text-lg font-black text-primary">
                +
              </div>
              <h3 className="text-lg font-semibold text-white">{solution}</h3>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-[#020405]">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.18em] text-primary">
                Em acao
              </p>
              <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Veja o Torvix Tracker em acao.
              </h2>
              <p className="mt-5 leading-8 text-muted">
                Esta area esta preparada para receber um video ou GIF mostrando
                o app funcionando com webcam, rastreamento e saída para o simulador.
              </p>
            </div>
            <div className="rounded-2xl border border-primary/25 bg-[linear-gradient(135deg,rgba(0,229,255,0.12),rgba(255,255,255,0.035))] p-4 shadow-[0_0_60px_rgba(0,229,255,0.10)]">
              <div className="flex aspect-video items-center justify-center rounded-xl border border-white/10 bg-black/55 text-center">
                <p className="text-lg font-semibold text-primary">
                  Vídeo em breve
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-primary">
            Planos
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Versao completa paga desde o primeiro acesso.
          </h2>
        </div>
        <div className="mt-10 grid gap-5 lg:grid-cols-1">
          <PlanCard
            cta={`Comprar por ${PRICE_TEXT}`}
            featured
            href="/checkout"
            items={proPlan}
            name={`${PRODUCT_NAME} Pro`}
            price={PRICE_TEXT}
          />
        </div>
      </section>

      <section className="border-t border-border bg-black/30">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-primary">
              FAQ
            </p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Duvidas rapidas antes de comprar.
            </h2>
          </div>
          <div className="mt-10 grid gap-4 lg:grid-cols-2">
            {faqs.map((faq) => (
              <article
                className="rounded-2xl border border-border bg-surface p-6"
                key={faq.question}
              >
                <h3 className="font-semibold text-white">{faq.question}</h3>
                <p className="mt-3 leading-7 text-muted">{faq.answer}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function PlanCard({
  cta,
  featured = false,
  href,
  items,
  name,
  price,
}: {
  cta: string;
  featured?: boolean;
  href: string;
  items: string[];
  name: string;
  price: string;
}) {
  return (
    <article
      className={`rounded-2xl border p-6 transition hover:-translate-y-1 ${
        featured
          ? "border-primary/50 bg-primary-soft shadow-[0_0_70px_rgba(0,229,255,0.13)]"
          : "border-border bg-surface"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-2xl font-bold text-white">{name}</h3>
          <p className="mt-2 text-muted">{price}</p>
        </div>
        {featured ? (
          <span className="rounded-md bg-primary px-3 py-1 text-xs font-bold text-[#001014]">
            Melhor escolha
          </span>
        ) : null}
      </div>
      <ul className="mt-8 space-y-3">
        {items.map((item) => (
          <li className="flex gap-3 text-muted" key={item}>
            <span className="mt-2 h-2 w-2 rounded-full bg-primary" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <Link
        className={`mt-8 inline-flex h-12 w-full items-center justify-center rounded-md text-base font-bold transition ${
          featured
            ? "bg-primary text-[#001014] hover:bg-white"
            : "border border-primary/35 text-white hover:bg-primary-soft"
        }`}
        href={href}
      >
        {cta}
      </Link>
    </article>
  );
}
