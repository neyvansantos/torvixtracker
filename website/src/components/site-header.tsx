// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import Image from "next/image";
import Link from "next/link";
import { AuthNav } from "@/components/auth-nav";
import { MobileMenu } from "@/components/mobile-menu";

const navigation = [
  { href: "/", label: "Início" },
  { href: "/pricing", label: "Preços" },
  { href: "/faq", label: "FAQ" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/82 backdrop-blur-xl">
      <nav className="relative mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <Link className="flex min-w-0 items-center gap-2 sm:gap-3" href="/">
          <Image
            alt=""
            className="h-8 w-auto sm:h-10"
            height={980}
            priority
            src="/torvix-icon.png"
            width={544}
          />
          <span className="truncate text-sm font-semibold text-white sm:text-base">
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

        <div className="hidden md:block">
          <AuthNav />
        </div>
        <MobileMenu navigation={navigation} />
      </nav>
    </header>
  );
}
