// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import Link from "next/link";
import type { Metadata } from "next";
import { PRICE_FULL, PRICE_TEXT, PRODUCT_NAME } from "@/config/product";

export const metadata: Metadata = {
  title: "Planos e Preços",
  description:
    "Confira os planos do Torvix Tracker Pro. Pagamento único, sem mensalidades, acesso imediato.",
};

const proFeatures = [
  "Pagamento único",
  "Acesso completo",
  "Funciona com ETS2 e ATS",
  "Sem mensalidade",
];

export default function PricingPage() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.16)_0%,rgba(0,72,82,0.08)_22%,rgba(5,8,10,0.02)_54%,rgba(0,229,255,0.09)_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-24 -z-10 h-[560px] w-[960px] -translate-x-1/2 rounded-full bg-primary/12 blur-3xl" />

      <section className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Preços
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
            Escolha seu plano {PRODUCT_NAME}
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted">
            {PRICE_FULL}. Acesso completo ao rastreamento por webcam para ETS2
            e ATS.
          </p>
        </div>

        <div className="mt-12 grid gap-5 lg:grid-cols-1">
          <PlanCard
            buttonHref="/checkout"
            buttonText={`Comprar agora por ${PRICE_TEXT}`}
            features={proFeatures}
            highlighted
            name={`${PRODUCT_NAME} Pro`}
            price={PRICE_TEXT}
          />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        <div className="rounded-2xl border border-primary/25 bg-primary-soft p-6 text-center">
          <h2 className="text-2xl font-bold text-white">Acesso Pro</h2>
          <p className="mx-auto mt-4 max-w-3xl leading-8 text-muted">
            {PRICE_FULL}. Sem mensalidade, com acesso completo ao Torvix
            Tracker Pro.
          </p>
        </div>
      </section>
    </main>
  );
}

function PlanCard({
  buttonHref,
  buttonText,
  features,
  highlighted = false,
  name,
  price,
}: {
  buttonHref: string;
  buttonText: string;
  features: string[];
  highlighted?: boolean;
  name: string;
  price: string;
}) {
  return (
    <article
      className={`rounded-2xl border p-6 transition hover:-translate-y-1 ${
        highlighted
          ? "border-primary/55 bg-primary-soft shadow-[0_0_80px_rgba(0,229,255,0.14)]"
          : "border-border bg-surface"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">{name}</h2>
          <p className="mt-3 text-4xl font-black tracking-tight text-white">
            {price}
          </p>
        </div>
        {highlighted ? (
          <span className="rounded-md bg-primary px-3 py-1 text-xs font-bold text-[#001014]">
            Pro
          </span>
        ) : null}
      </div>

      <ul className="mt-8 space-y-3">
        {features.map((feature) => (
          <li className="flex gap-3 text-muted" key={feature}>
            <span className="shrink-0 font-bold text-primary">✔</span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <Link
        className={`mt-8 inline-flex h-12 w-full items-center justify-center rounded-md text-base font-bold transition ${
          highlighted
            ? "bg-primary text-[#001014] hover:bg-white"
            : "border border-primary/35 text-white hover:bg-primary-soft"
        }`}
        href={buttonHref}
      >
        {buttonText}
      </Link>
    </article>
  );
}
