export const site = {
  name: "Cogniflow",
  tagline: "The auditable, self-hostable belief ledger for agents.",
  repo: "https://github.com/Nagendhra-web/cogniflow",
  nav: [
    { href: "/playground", label: "Playground" },
    { href: "/plugins", label: "Plugins" },
    { href: "/benchmark", label: "Benchmark" },
    { href: "/use-cases", label: "Use cases" },
    { href: "/docs", label: "Docs" },
  ],
} as const;

export const chartColors = {
  brand: "#4fe3c4",   // Cogniflow (aqua-mint)
  brand2: "#8b7cff",  // violet
  plain: "#8b95c9",   // the "other" system - lavender-slate, distinct from brand mint
  win: "#56d39a",
  warn: "#f2c14e",
  miss: "#6b77a8",
  danger: "#ff6b8a",
  grid: "#2a3366",
  text: "#9aa6d6",
} as const;
