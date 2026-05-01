"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import Link from "next/link";
import { useState } from "react";
import { AuthNav } from "@/components/auth-nav";

type MobileMenuProps = {
  navigation: Array<{
    href: string;
    label: string;
  }>;
};

export function MobileMenu({ navigation }: MobileMenuProps) {
  const [open, setOpen] = useState(false);

  function closeMenu() {
    setOpen(false);
  }

  return (
    <div className="md:hidden">
      <button
        aria-expanded={open}
        aria-label={open ? "Fechar menu" : "Abrir menu"}
        className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-primary/35 text-white transition hover:bg-primary-soft"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span className="flex w-4 flex-col gap-1.5">
          <span
            className={`h-0.5 rounded-full bg-current transition ${
              open ? "translate-y-2 rotate-45" : ""
            }`}
          />
          <span
            className={`h-0.5 rounded-full bg-current transition ${
              open ? "opacity-0" : ""
            }`}
          />
          <span
            className={`h-0.5 rounded-full bg-current transition ${
              open ? "-translate-y-2 -rotate-45" : ""
            }`}
          />
        </span>
      </button>

      {open ? (
        <div className="absolute left-4 right-4 top-[calc(100%+0.75rem)] rounded-md border border-border bg-[#05090d] p-4 shadow-[0_18px_55px_rgba(0,0,0,0.45)]">
          <div className="flex flex-col gap-1 text-sm font-semibold text-muted">
            {navigation.map((item) => (
              <Link
                className="rounded-md px-3 py-3 transition hover:bg-primary-soft hover:text-primary"
                href={item.href}
                key={item.href}
                onClick={closeMenu}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="mt-4 border-t border-border pt-4">
            <AuthNav mode="menu" onNavigate={closeMenu} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
