"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, Star, X } from "lucide-react";
import { site } from "@/lib/site";
import { Logo } from "./logo";
import { cn } from "@/lib/utils";

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Link href="/" className="shrink-0" aria-label="Agent Memry home">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {site.nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={site.repo}
            target="_blank"
            rel="noreferrer"
            className="hidden items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent/50 sm:inline-flex"
          >
            <Star className="size-4" /> Star
          </a>
          <Link
            href="/playground"
            className="hidden rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 sm:inline-block"
          >
            Open playground
          </Link>
          <button
            className="inline-flex size-9 items-center justify-center rounded-md border border-border md:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border/70 bg-background/95 px-5 py-3 md:hidden">
          <nav className="flex flex-col gap-1">
            {site.nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/playground"
              onClick={() => setOpen(false)}
              className="mt-1 rounded-md bg-primary px-3 py-2 text-center text-sm font-semibold text-primary-foreground"
            >
              Open playground
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
