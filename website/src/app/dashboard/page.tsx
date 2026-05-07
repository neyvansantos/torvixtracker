"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { redirect, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import {
  PRICE_FULL,
  PRICE_TEXT,
  PRODUCT_NAME,
} from "@/config/product";
import { getCurrentUser, getUserProfile, type UserProfile } from "@/lib/auth";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [loadingDownloadLinks, setLoadingDownloadLinks] = useState(false);
  const [downloadError, setDownloadError] = useState("");
  const [downloadLinks, setDownloadLinks] = useState<{
    installer?: string;
    name?: string;
  } | null>(null);
  const [loginRedirect, setLoginRedirect] = useState<string | null>(
    isSupabaseConfigured
      ? null
      : "/login?message=Configure o Supabase antes de acessar o painel.",
  );
  const hasPro = profile?.has_pro === true;
  const plan = profile?.plan || (hasPro ? "pro" : "free");

  const requestDownloadLinks = useCallback(async (accessToken?: string) => {
    setDownloadError("");
    setLoadingDownloadLinks(true);

    const token =
      accessToken ||
      (
        await supabase.auth.getSession()
      ).data.session?.access_token;

    if (!token) {
      setLoadingDownloadLinks(false);
      router.push("/login");
      return;
    }

    const response = await fetch("/api/download/torvix", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    setLoadingDownloadLinks(false);

    if (!response.ok) {
      const data = (await response.json().catch(() => null)) as
        | { error?: string }
        | null;
      setDownloadError(data?.error || "Não foi possível baixar o instalador.");
      return;
    }

    const data = (await response.json()) as {
      download_name?: string;
      download_url?: string;
    };

    if (!data.download_url) {
      setDownloadError("Link do instalador não encontrado.");
      return;
    }

    setDownloadLinks({
      installer: data.download_url,
      name: data.download_name,
    });
  }, [router]);

  const refreshProfile = useCallback(async (currentUserId = user?.id) => {
    if (!currentUserId) {
      return;
    }

    setCheckingPayment(true);
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      await fetch("/api/checkout/sync-payment", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      }).catch(() => null);
    }

    const userProfile = await getUserProfile(currentUserId);
    setCheckingPayment(false);

    if (userProfile) {
      setProfile(userProfile);

      if (userProfile.has_pro === true) {
        await requestDownloadLinks(session?.access_token);
      }
    }
  }, [requestDownloadLinks, user?.id]);

  useEffect(() => {
    let isMounted = true;

    if (!isSupabaseConfigured) {
      return;
    }

    async function loadDashboard() {
      const currentUser = await getCurrentUser();

      if (!currentUser) {
        setLoginRedirect("/login");
        return;
      }

      const userProfile = await getUserProfile(currentUser.id);

      if (!isMounted) {
        return;
      }

      setUser(currentUser);
      setProfile(userProfile ?? { plan: "free", has_pro: false });
      setLoading(false);

      if (userProfile?.has_pro === true) {
        await requestDownloadLinks();
      }
    }

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, [requestDownloadLinks, router]);

  useEffect(() => {
    if (!user?.id || profile?.has_pro === true) {
      return;
    }

    let attempts = 0;
    const maxAttempts = 12;
    const interval = window.setInterval(async () => {
      attempts += 1;
      await refreshProfile(user.id);

      if (attempts >= maxAttempts) {
        window.clearInterval(interval);
      }
    }, 5000);

    return () => {
      window.clearInterval(interval);
    };
  }, [user?.id, profile?.has_pro, refreshProfile]);

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }


  if (loginRedirect) {
    redirect(loginRedirect);
  }

  if (loading) {
    return (
      <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-5 text-muted">
        Carregando...
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-5 text-muted">
        Carregando...
      </main>
    );
  }

  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.16)_0%,rgba(0,72,82,0.08)_26%,rgba(5,8,10,0.02)_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-20 -z-10 h-[560px] w-[960px] -translate-x-1/2 rounded-full bg-primary/12 blur-3xl" />

      <section className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-5 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
              Painel
            </p>
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Sua conta {PRODUCT_NAME}
            </h1>
            <p className="mt-5 text-lg leading-8 text-muted">{user?.email}</p>
          </div>
          <button
            className="inline-flex h-12 items-center justify-center rounded-md border border-primary/35 px-6 text-base font-bold text-white transition hover:bg-primary-soft"
            onClick={handleLogout}
            type="button"
          >
            Sair
          </button>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="text-2xl font-bold text-white">Status da conta</h2>
            <div className="mt-6 grid gap-3">
              <StatusRow label="Plano" value={plan === "pro" ? "Pro" : "Sem Pro"} />
              <StatusRow label="Acesso" value={hasPro ? "Pro ativado" : "Acesso bloqueado"} />
            </div>
          </div>
          <div className="rounded-2xl border border-primary/35 bg-primary-soft p-6">
            <h2 className="text-2xl font-bold text-white">
              {hasPro ? "Pro ativado" : "Acesso bloqueado"}
            </h2>
            <p className="mt-4 leading-7 text-muted">
              {hasPro
                ? "Seu acesso Pro está ativo. O instalador está disponível para esta conta."
                : "Compre o Torvix Tracker para liberar o instalador"}
            </p>
            {!hasPro ? (
              <div className="mt-6 rounded-xl border border-primary/30 bg-black/20 p-4">
                <p className="text-xl font-black text-primary">
                  🔥 Acesso antecipado – {PRICE_TEXT}
                </p>
                <p className="mt-2 text-sm font-semibold text-white">
                  {PRICE_FULL}. Sem mensalidade.
                </p>
                <ul className="mt-4 grid gap-2 text-sm text-muted">
                  <li>✔ Pagamento único</li>
                  <li>✔ Sem mensalidade</li>
                  <li>✔ Acesso imediato após compra</li>
                </ul>
                <button
                  className="mt-5 inline-flex h-11 w-full items-center justify-center rounded-md border border-primary/35 px-5 font-bold text-white transition hover:bg-primary-soft disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={checkingPayment}
                  onClick={() => refreshProfile()}
                  type="button"
                >
                  {checkingPayment ? "Verificando..." : "Verificar pagamento"}
                </button>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-5 grid gap-5 md:grid-cols-1">
          <article className="rounded-2xl border border-border bg-surface p-6 opacity-85">
            <h2 className="text-2xl font-bold text-white">
              {hasPro ? "Baixar" : "Compra necessária"}
            </h2>
            <p className="mt-3 leading-7 text-muted">
              {hasPro
                ? "Baixe o instalador completo do Torvix Tracker."
                : "Compre o Torvix Tracker para liberar o instalador"}
            </p>
            {hasPro ? (
              <div className="mt-8">
                <a
                  className="inline-flex min-h-12 w-full items-center justify-center rounded-md bg-primary px-6 py-3 text-center text-base font-bold text-[#001014] transition hover:bg-white aria-disabled:pointer-events-none aria-disabled:opacity-60"
                  aria-disabled={!downloadLinks?.installer || loadingDownloadLinks}
                  download
                  href={downloadLinks?.installer || undefined}
                >
                  {loadingDownloadLinks
                    ? "Preparando link..."
                    : downloadLinks?.name || "Torvix Tracker Setup"}
                </a>
              </div>
            ) : (
              <Link
                className="mt-8 inline-flex h-12 w-full items-center justify-center rounded-md border border-primary/35 px-6 text-base font-bold text-white transition hover:bg-primary-soft"
                href="/checkout"
              >
                Comprar por {PRICE_TEXT}
              </Link>
            )}
            {downloadError ? (
              <p className="mt-4 text-sm text-red-300">{downloadError}</p>
            ) : null}
          </article>
        </div>
      </section>
    </main>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-border bg-black/25 p-4">
      <span className="text-muted">{label}</span>
      <span className="font-bold text-primary">{value}</span>
    </div>
  );
}
