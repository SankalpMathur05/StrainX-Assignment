"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/requisitions/new", label: "New requisition" },
  { href: "/history", label: "History" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur print:hidden">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 md:px-8">
        <Link href="/" className="flex items-baseline gap-2 font-display text-lg font-bold tracking-tight">
          <span className="inline-block h-3 w-3 -skew-x-12 bg-lavender-ink" aria-hidden="true" />
          StrainX <span className="text-muted">·</span> <span className="font-medium">Quote Compare</span>
        </Link>
        <nav aria-label="Main" className="order-3 w-full md:order-none md:w-auto">
          <ul className="flex gap-1 overflow-x-auto">
            {LINKS.map((link) => {
              const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    aria-current={active ? "page" : undefined}
                    className={`block whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] ${
                      active ? "bg-ink text-bg" : "text-muted hover:text-ink"
                    }`}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
