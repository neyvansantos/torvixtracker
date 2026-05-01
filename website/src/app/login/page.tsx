"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(searchParams.get("message") || "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!isSupabaseConfigured) {
      setError("Supabase não está configurado. Adicione o .env.local primeiro.");
      return;
    }

    if (!email || !password) {
      setError("E-mail e senha são obrigatórios.");
      return;
    }

    setLoading(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);

    if (signInError) {
      setError("Não foi possível entrar. Verifique seu email e senha.");
      return;
    }

    setMessage("Entrada realizada com sucesso. Redirecionando...");
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="relative overflow-hidden">
      <AuthBackground />
      <section className="mx-auto flex min-h-[calc(100svh-4rem)] max-w-6xl items-center justify-center px-5 py-20 sm:px-8">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_90px_rgba(0,0,0,0.28)]">
          <p className="mb-4 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Conta
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Entrar</h1>
          <p className="mt-3 leading-7 text-muted">
            Acesse seu painel do Torvix Tracker.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="text-sm font-semibold text-white">E-mail</span>
              <input
                className="mt-2 h-12 w-full rounded-md border border-border bg-black/35 px-4 text-white outline-none transition placeholder:text-muted/60 focus:border-primary"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="seuemail@exemplo.com"
                type="email"
                value={email}
              />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-white">Senha</span>
              <input
                className="mt-2 h-12 w-full rounded-md border border-border bg-black/35 px-4 text-white outline-none transition placeholder:text-muted/60 focus:border-primary"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Sua senha"
                type="password"
                value={password}
              />
            </label>

            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            {message ? <p className="text-sm text-primary">{message}</p> : null}

            <button
              className="inline-flex h-12 w-full items-center justify-center rounded-md bg-primary px-6 text-base font-bold text-[#001014] transition hover:-translate-y-0.5 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
              type="submit"
            >
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>

          <p className="mt-6 text-sm text-muted">
            Ainda não tem conta?{" "}
            <Link className="font-semibold text-primary hover:text-white" href="/register">
              Criar conta
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}

function LoginFallback() {
  return (
    <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-5 text-muted">
      Carregando login...
    </main>
  );
}

function AuthBackground() {
  return (
    <>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(180deg,rgba(0,229,255,0.16)_0%,rgba(0,72,82,0.08)_28%,rgba(5,8,10,0.02)_100%)]" />
      <div className="pointer-events-none absolute left-1/2 top-20 -z-10 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-primary/12 blur-3xl" />
    </>
  );
}
