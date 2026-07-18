export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        {/* two temporal rings + a pin: "what was true, and when" */}
        <circle cx="12" cy="12" r="9" stroke="var(--brand)" strokeWidth="1.6" opacity="0.35" />
        <path
          d="M12 3a9 9 0 0 1 0 18"
          stroke="var(--brand)"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <circle cx="12" cy="12" r="2.4" fill="var(--brand)" />
        <path d="M12 12V7" stroke="var(--brand-3)" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      <span className="text-[15px] font-semibold tracking-tight">Agent Memry</span>
    </span>
  );
}
