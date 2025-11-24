export function extractPricingUrls(text: string): string[] {
  const matches = text.match(/https?:\/\/[^\s)]+/gi) ?? [];
  const urls: string[] = [];

  matches.forEach((raw) => {
    const candidate = raw.replace(/[),.;]+$/, "");
    try {
      const url = new URL(candidate);
      if (!urls.includes(url.href)) {
        urls.push(url.href);
      }
    } catch (error) {
      console.warn("Detected invalid pricing URL candidate", candidate, error);
    }
  });

  return urls;
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

export function extractHttpReferences(payload: unknown): string[] {
  const results = new Set<string>();
  const visited = new Set<unknown>();

  const visit = (value: unknown) => {
    if (value === null || value === undefined) {
      return;
    }
    if (typeof value === "string") {
      if (isHttpUrl(value)) {
        results.add(value);
      }
      return;
    }
    if (typeof value !== "object") {
      return;
    }
    if (visited.has(value)) {
      return;
    }
    visited.add(value);

    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }

    Object.values(value).forEach(visit);
  };

  visit(payload);
  return Array.from(results);
}
