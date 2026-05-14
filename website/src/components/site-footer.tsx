// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.
import Image from "next/image";
import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="bg-[#030507]">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-5 px-4 py-8 text-center text-sm text-muted sm:flex-row sm:justify-between sm:px-6 sm:text-left lg:px-8">
        <div className="flex max-w-xs flex-col items-center gap-3 sm:max-w-none sm:flex-row">
          <Image
            alt="Logo Torvix Tracker"
            className="h-8 w-auto"
            height={980}
            src="/torvix-logo.png"
            width={544}
          />
          <span>© 2026 Torvix Tracker. Todos os direitos reservados.</span>
        </div>
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2">
          <Link className="hover:text-primary" href="/pricing">
            Preços
          </Link>
          <Link className="hover:text-primary" href="/faq">
            FAQ
          </Link>
          <Link className="hover:text-primary" href="/privacidade">
            Privacidade
          </Link>
          <Link className="hover:text-primary" href="/termos">
            Termos
          </Link>
        </div>
      </div>
    </footer>
  );
}
