"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
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

    if (!email || !password || !confirmPassword) {
      setError("E-mail, senha e confirmação são obrigatórios.");
      return;
    }

    if (password.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    if (password !== confirmPassword) {
      setError("As senhas não conferem.");
      return;
    }

    setLoading(true);
    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName || null,
        },
      },
    });
    setLoading(false);

    if (signUpError) {
      setError("Não foi possível criar a conta. Verifique os dados e tente novamente.");
      return;
    }

    setMessage("Conta criada. Verifique seu email se a confirmação estiver ativa.");
    router.push("/login?message=Conta criada. Você já pode entrar.");
  }

  return (
    <main className="relative overflow-hidden">
      <AuthBackground />
      <section className="mx-auto flex min-h-[calc(100svh-4rem)] max-w-6xl items-center justify-center px-5 py-20 sm:px-8">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_90px_rgba(0,0,0,0.28)]">
          <p className="mb-4 inline-flex rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm font-semibold text-primary">
            Conta
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Criar conta
          </h1>
          <p className="mt-3 leading-7 text-muted">
            Crie sua conta do Torvix Tracker para acessar a versão Pro.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="text-sm font-semibold text-white">Nome opcional</span>
              <input
                className="mt-2 h-12 w-full rounded-md border border-border bg-black/35 px-4 text-white outline-none transition placeholder:text-muted/60 focus:border-primary"
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Seu nome"
                type="text"
                value={fullName}
              />
            </label>
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
                placeholder="Mínimo 6 caracteres"
                type="password"
                value={password}
              />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-white">Confirmar senha</span>
              <input
                className="mt-2 h-12 w-full rounded-md border border-border bg-black/35 px-4 text-white outline-none transition placeholder:text-muted/60 focus:border-primary"
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Repita a senha"
                type="password"
                value={confirmPassword}
              />
            </label>

            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            {message ? <p className="text-sm text-primary">{message}</p> : null}

            <button
              className="inline-flex h-12 w-full items-center justify-center rounded-md bg-primary px-6 text-base font-bold text-[#001014] transition hover:-translate-y-0.5 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
              type="submit"
            >
              {loading ? "Criando..." : "Criar conta"}
            </button>
          </form>

          <p className="mt-6 text-sm text-muted">
            Já tem conta?{" "}
            <Link className="font-semibold text-primary hover:text-white" href="/login">
              Entrar
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
