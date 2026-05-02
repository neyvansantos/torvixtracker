"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { FormEvent, useState } from "react";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!isSupabaseConfigured) {
      setError("Supabase não está configurado.");
      return;
    }

    if (!email) {
      setError("O e-mail é obrigatório.");
      return;
    }

    setLoading(true);
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    setLoading(false);

    if (resetError) {
      setError("Não foi possível enviar o e-mail de recuperação.");
      return;
    }

    setMessage("E-mail de recuperação enviado. Verifique sua caixa de entrada.");
  }

  return (
    <main className="relative overflow-hidden">
      <AuthBackground />
      <section className="mx-auto flex min-h-[calc(100svh-4rem)] max-w-6xl items-center justify-center px-5 py-20 sm:px-8">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_90px_rgba(0,0,0,0.28)]">
          <p className="mb-4 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Recuperação
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Recuperar senha</h1>
          <p className="mt-3 leading-7 text-muted">
            Insira seu e-mail para receber instruções de recuperação.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
            <div className="block">
              <label className="text-sm font-semibold text-white" htmlFor="email">
                E-mail
              </label>
              <input
                className="mt-2 h-12 w-full rounded-md border border-border bg-black/35 px-4 text-white outline-none transition placeholder:text-muted/60 focus:border-primary"
                id="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="seuemail@exemplo.com"
                type="email"
                value={email}
              />
            </div>

            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            {message ? <p className="text-sm text-primary">{message}</p> : null}

            <button
              className="inline-flex h-12 w-full items-center justify-center rounded-md bg-primary px-6 text-base font-bold text-[#001014] transition hover:-translate-y-0.5 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
              type="submit"
            >
              {loading ? "Enviando..." : "Enviar instruções"}
            </button>
          </form>

          <p className="mt-6 text-sm text-muted">
            Lembrou a senha?{" "}
            <Link className="font-semibold text-primary hover:text-white" href="/login">
              Voltar para o login
            </Link>
          </p>
        </div>
      </section>
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
