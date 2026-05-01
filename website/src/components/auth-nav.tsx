"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

type AuthNavProps = {
  mode?: "header" | "menu";
  onNavigate?: () => void;
};

export function AuthNav({ mode = "header", onNavigate }: AuthNavProps) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(isSupabaseConfigured);
  const isMenu = mode === "menu";

  useEffect(() => {
    if (!isSupabaseConfigured) {
      return;
    }

    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  async function handleLogout() {
    await supabase.auth.signOut();
    setUser(null);
    onNavigate?.();
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return (
      <div
        className={
          isMenu
            ? "h-10 w-full rounded-md bg-white/5"
            : "hidden h-10 w-28 rounded-md bg-white/5 md:block"
        }
      />
    );
  }

  if (user) {
    return (
      <div className={isMenu ? "flex flex-col gap-2" : "flex items-center gap-2"}>
        <Link
          className={
            isMenu
              ? "inline-flex h-11 w-full items-center justify-center rounded-md border border-primary/35 px-4 text-sm font-bold text-white transition hover:bg-primary-soft"
              : "hidden h-10 items-center justify-center rounded-md border border-primary/35 px-4 text-sm font-bold text-white transition hover:bg-primary-soft sm:inline-flex"
          }
          href="/dashboard"
          onClick={onNavigate}
        >
          Painel
        </Link>
        <button
          className={
            isMenu
              ? "inline-flex h-11 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-bold text-[#001014] shadow-[0_0_28px_rgba(0,229,255,0.22)] transition hover:bg-white"
              : "inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-bold text-[#001014] shadow-[0_0_28px_rgba(0,229,255,0.22)] transition hover:bg-white"
          }
          onClick={handleLogout}
          type="button"
        >
          Sair
        </button>
      </div>
    );
  }

  return (
    <div className={isMenu ? "flex flex-col gap-2" : "flex items-center gap-2"}>
      <Link
        className={
          isMenu
            ? "inline-flex h-11 w-full items-center justify-center rounded-md border border-primary/35 px-4 text-sm font-bold text-white transition hover:bg-primary-soft"
            : "hidden h-10 items-center justify-center rounded-md border border-primary/35 px-4 text-sm font-bold text-white transition hover:bg-primary-soft sm:inline-flex"
        }
        href="/login"
        onClick={onNavigate}
      >
        Entrar
      </Link>
      <Link
        className={
          isMenu
            ? "inline-flex h-11 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-bold text-[#001014] shadow-[0_0_28px_rgba(0,229,255,0.22)] transition hover:bg-white"
            : "inline-flex h-10 items-center justify-center rounded-md bg-primary px-3 text-sm font-bold text-[#001014] shadow-[0_0_28px_rgba(0,229,255,0.22)] transition hover:bg-white sm:px-4"
        }
        href="/register"
        onClick={onNavigate}
      >
        Criar conta
      </Link>
    </div>
  );
}
