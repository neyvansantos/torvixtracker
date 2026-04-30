"use client";

import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { useEffect, useState } from "react";
import { PRICE_FULL, PRICE_TEXT, PRODUCT_NAME } from "@/config/product";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

type PixCheckout = {
  payment_id: string;
  status: string;
  qr_code: string | null;
  qr_code_base64: string | null;
  ticket_url: string | null;
  already_pro?: boolean;
};

export default function CheckoutPage() {
  const [loadingUser, setLoadingUser] = useState(isSupabaseConfigured);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loadingPix, setLoadingPix] = useState(false);
  const [pix, setPix] = useState<PixCheckout | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isSupabaseConfigured) {
      return;
    }

    supabase.auth.getUser().then(({ data }) => {
      setIsLoggedIn(Boolean(data.user));
      setLoadingUser(false);
    });
  }, []);

  async function handleCreatePix() {
    setError("");
    setLoadingPix(true);

    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      setLoadingPix(false);
      redirect("/login");
    }

    const response = await fetch("/api/checkout/create-pix", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
    });
    const data = (await response.json()) as PixCheckout & { error?: string };

    setLoadingPix(false);

    if (!response.ok) {
      setError(data.error || "Não foi possível gerar o PIX.");
      return;
    }

    setPix(data);
  }

  if (loadingUser) {
    return (
      <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-5 text-muted">
        Carregando...
      </main>
    );
  }

  if (!isLoggedIn) {
    redirect("/login");
  }

  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.16)_0%,rgba(0,72,82,0.08)_26%,rgba(5,8,10,0.02)_100%)]" />
      <section className="mx-auto max-w-4xl px-5 py-20 sm:px-8">
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_90px_rgba(0,0,0,0.26)]">
          <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Checkout PIX
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-white">
            Comprar {PRODUCT_NAME} Pro
          </h1>
          <p className="mt-4 text-2xl font-black text-primary">{PRICE_TEXT}</p>
          <p className="mt-2 leading-7 text-muted">
            {PRICE_FULL}. Sem mensalidade.
          </p>
          <ul className="mt-6 grid gap-2 text-sm text-muted sm:grid-cols-3">
            <li>✔ Pagamento único</li>
            <li>✔ Sem mensalidade</li>
            <li>✔ Acesso imediato após compra</li>
          </ul>

          <button
            className="mt-8 inline-flex h-12 w-full items-center justify-center rounded-md bg-primary px-6 text-base font-bold text-[#001014] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loadingPix}
            onClick={handleCreatePix}
            type="button"
          >
            {loadingPix ? "Gerando PIX..." : "Gerar PIX"}
          </button>

          {error ? <p className="mt-5 text-sm text-red-300">{error}</p> : null}

          {pix?.already_pro ? (
            <div className="mt-8 rounded-xl border border-primary/30 bg-primary-soft p-5">
              <h2 className="text-xl font-bold text-white">Pro já ativado</h2>
              <p className="mt-3 leading-7 text-muted">
                Sua conta já possui acesso Pro.
              </p>
              <Link
                className="mt-5 inline-flex h-11 items-center justify-center rounded-md bg-primary px-5 font-bold text-[#001014] transition hover:bg-white"
                href="/dashboard"
              >
                Ir para o painel
              </Link>
            </div>
          ) : null}

          {pix && !pix.already_pro ? (
            <div className="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
              {pix.qr_code_base64 ? (
                <div className="rounded-xl border border-border bg-white p-4">
                  <Image
                    alt="QR Code PIX do Mercado Pago"
                    className="mx-auto h-auto w-full max-w-72"
                    height={288}
                    src={`data:image/png;base64,${pix.qr_code_base64}`}
                    unoptimized
                    width={288}
                  />
                </div>
              ) : null}

              <div>
                <h2 className="text-xl font-bold text-white">PIX copia e cola</h2>
                <textarea
                  className="mt-4 min-h-36 w-full rounded-md border border-border bg-black/35 p-4 text-sm text-white outline-none"
                  readOnly
                  value={pix.qr_code || ""}
                />
                {pix.ticket_url ? (
                  <a
                    className="mt-4 inline-flex h-11 items-center justify-center rounded-md border border-primary/35 px-5 font-bold text-white transition hover:bg-primary-soft"
                    href={pix.ticket_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Abrir instruções do Mercado Pago
                  </a>
                ) : null}
                <p className="mt-5 leading-7 text-muted">
                  Após o pagamento ser aprovado, seu acesso Pro será liberado
                  automaticamente.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
