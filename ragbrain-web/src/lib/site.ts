export const site = {
  name: "RAGBrain",
  tagline: "The auditable, self-hostable belief ledger for agents.",
  repo: "https://github.com/Nagendhra-Madishetti/ragbrain",
  nav: [
    { href: "/playground", label: "Playground" },
    { href: "/plugins", label: "Plugins" },
    { href: "/benchmark", label: "Benchmark" },
    { href: "/use-cases", label: "Use cases" },
    { href: "/docs", label: "Docs" },
  ],
} as const;

// Display name for benchmark systems: keep real competitor names; relabel the temporal
// substrate ablation to a category (we don't frame ourselves as built on it).
export function displayName(name: string): string {
  if (name.startsWith("Graphiti")) return "Temporal graph (no as-of)";
  // The benchmark JSONs are frozen measured artifacts captured under the
  // project's former name; map to the current brand at display time only.
  if (name.startsWith("Cogniflow")) return name.replace("Cogniflow", "RAGBrain");
  return name;
}

export const chartColors = {
  brand: "#e4551c", // RAGBrain (warm orange)
  brand2: "#f59e0b", // amber
  plain: "#98a0ae", // the "other" system - neutral gray, distinct from brand orange
  win: "#0e9f6e",
  warn: "#b7791f",
  miss: "#98a0ae",
  danger: "#dc2626",
  grid: "#e8e5df",
  text: "#5c6472",
} as const;
