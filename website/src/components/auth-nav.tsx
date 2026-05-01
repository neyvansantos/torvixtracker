"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(isSupabaseConfigured);

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
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return <div className="hidden h-10 w-28 rounded-md bg-white/5 md:block" />;
  }

  if (user) {
    return (
      <div className="flex items-center gap-2">
        <Link
          className="hidden h-10 items-center justify-center rounded-md border border-primary/35 px-4 text-sm font-bold text-white transition hover:bg-primary-soft sm:inline-flex"
          href="/dashboard"
        >
          Painel
        </Link>
        <button
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-bold text-[#001014] shadow-[0_0_28px_rgba(0,229,255,0.22)] transition hover:bg-white"
          onClick={handleLogout}
          type="button"
        >
          Sair
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Link
        className="hidden h-10 items-center justify-center rounded-md border border-primary/35 px-4 text-sm font-bold text-white transition hover:bg-primary-soft sm:inline-flex"
        href="/login"
      >
        Entrar
      </Link>
      <Link
        className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-bold text-[#001014] shadow-[0_0_28px_rgba(0,229,255,0.22)] transition hover:bg-white"
        href="/register"
      >
        Criar conta
      </Link>
    </div>
  );
}
