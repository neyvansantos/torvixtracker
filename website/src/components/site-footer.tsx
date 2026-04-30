// Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
import Image from "next/image";
import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="bg-[#030507]">
      <div className="mx-auto flex max-w-6xl flex-col gap-5 px-5 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div className="flex items-center gap-3">
          <Image
            alt=""
            className="h-8 w-auto"
            height={980}
            src="/torvix-logo.png"
            width={544}
          />
          <span>© 2026 Neyvan Santos. Todos os direitos reservados.</span>
        </div>
        <div className="flex flex-wrap gap-4">
          <Link className="hover:text-primary" href="/pricing">
            Preços
          </Link>
          <Link className="hover:text-primary" href="/faq">
            FAQ
          </Link>
        </div>
      </div>
    </footer>
  );
}
