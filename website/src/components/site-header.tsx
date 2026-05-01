// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import Image from "next/image";
import Link from "next/link";
import { AuthNav } from "@/components/auth-nav";

const navigation = [
  { href: "/", label: "Início" },
  { href: "/pricing", label: "Preços" },
  { href: "/faq", label: "FAQ" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/82 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link className="flex min-w-0 items-center gap-3" href="/">
          <Image
            alt=""
            className="h-10 w-auto"
            height={980}
            priority
            src="/torvix-icon.png"
            width={544}
          />
          <span className="truncate text-base font-semibold text-white">
            Torvix Tracker
          </span>
        </Link>

        <div className="hidden items-center gap-7 text-sm font-medium text-muted md:flex">
          {navigation.map((item) => (
            <Link
              className="transition-colors hover:text-primary"
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <AuthNav />
      </nav>
    </header>
  );
}
