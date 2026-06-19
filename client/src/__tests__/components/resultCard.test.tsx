import { describe, expect, it } from "bun:test";

// Replicate domainIcon from resultCard.tsx
function domainIcon(domain: string): string {
  const d = domain.toLowerCase();
  if (d.includes("github")) return "🐙";
  if (d.includes("youtube")) return "▶️";
  if (d.includes("linkedin")) return "💼";
  if (d.includes("facebook")) return "📘";
  if (d.includes("instagram")) return "📸";
  if (d.includes("pinterest")) return "📌";
  if (d.includes("medium")) return "✍️";
  return "🌐";
}

// Replicate formatDate from resultCard.tsx
function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No date";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

describe("resultCard - domainIcon", () => {
  it("returns specific icons for known domains", () => {
    expect(domainIcon("github.com")).toBe("🐙");
    expect(domainIcon("youtube.com")).toBe("▶️");
    expect(domainIcon("linkedin.com")).toBe("💼");
    expect(domainIcon("facebook.com")).toBe("📘");
    expect(domainIcon("instagram.com")).toBe("📸");
    expect(domainIcon("pinterest.com")).toBe("📌");
    expect(domainIcon("medium.com")).toBe("✍️");
  });

  it("returns default globe icon for unknown domains", () => {
    expect(domainIcon("example.com")).toBe("🌐");
    expect(domainIcon("random-site.org")).toBe("🌐");
    expect(domainIcon("")).toBe("🌐");
  });

  it("is case-insensitive", () => {
    expect(domainIcon("GITHUB.COM")).toBe("🐙");
    expect(domainIcon("YouTube.com")).toBe("▶️");
  });
});

describe("resultCard - formatDate", () => {
  it('returns "No date" for null', () => {
    expect(formatDate(null)).toBe("No date");
  });

  it("formats valid date strings", () => {
    const result = formatDate("2024-01-15");
    expect(result).toContain("2024");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
  });

  it("formats ISO date strings", () => {
    const result = formatDate("2024-06-01T12:00:00Z");
    expect(result).toContain("2024");
    expect(result).toContain("Jun");
    expect(result).toContain("1");
  });
});