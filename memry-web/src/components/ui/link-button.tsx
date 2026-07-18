import Link from "next/link";
import type { VariantProps } from "class-variance-authority";
import { buttonVariants } from "./button";
import { cn } from "@/lib/utils";

type Variants = VariantProps<typeof buttonVariants>;

export function LinkButton({
  href,
  external = false,
  variant,
  size,
  className,
  children,
}: {
  href: string;
  external?: boolean;
  className?: string;
  children: React.ReactNode;
} & Variants) {
  const cls = cn(buttonVariants({ variant, size }), className);
  if (external) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={cls}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {children}
    </Link>
  );
}
