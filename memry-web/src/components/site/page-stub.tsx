import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export function PageStub({
  eyebrow,
  title,
  intro,
  planned,
}: {
  eyebrow: string;
  title: string;
  intro: string;
  planned: string[];
}) {
  return (
    <section className="relative overflow-hidden">
      <div className="grid-overlay pointer-events-none absolute inset-0" />
      <div className="relative mx-auto max-w-4xl px-5 py-24 sm:py-28">
        <p className="eyebrow mb-4">{eyebrow}</p>
        <h1 className="text-hero max-w-[20ch]">{title}</h1>
        <p className="text-subhead mt-6 max-w-[60ch]">{intro}</p>

        <div className="mesh-panel mt-10 rounded-xl p-6">
          <div className="mb-3 text-sm font-semibold text-brand">Shipping next</div>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {planned.map((p) => (
              <li key={p} className="flex gap-2">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand" />
                {p}
              </li>
            ))}
          </ul>
        </div>

        <Link
          href="/"
          className="mt-10 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Back home
        </Link>
      </div>
    </section>
  );
}
