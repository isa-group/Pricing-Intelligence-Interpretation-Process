import { PricingContextItem } from "../src/types";
import {
  diffPricingContextWithDetectedUrls,
  extractPricingUrls,
} from "../src/utils";

describe("Utils test suite", () => {
  it("Given prompt text should extract urls", () => {
    const text =
      "Extract from https://example.org and http://example.org both pricings.";
    const urls = extractPricingUrls(text);
    expect(urls).toHaveLength(2);
    expect(urls).toMatchObject(["https://example.org/", "http://example.org/"]);
  });

  it("Given pricing context and detected url should diff", () => {
    const pricingContext: PricingContextItem[] = [
      {
        id: "807ea299-9cf1-43c0-bc07-62ac9f97e8a3",
        kind: "url",
        value: "https://example.org",
        label: "https://example.org",
        transform: "not-started",
        url: "https://example.org",
        origin: "user",
      },
      {
        id: "d23d8252-e3e0-428a-8768-c1b8846e04e1",
        kind: "yaml",
        value: "saasName: test\n",
        label: "test-pricing.yaml",
        origin: "user",
      },
    ];
    const detectedUrls: string[] = [
      "https://example.org",
      "https://github/pricing",
    ];
    const newUrls = diffPricingContextWithDetectedUrls(
      pricingContext,
      detectedUrls
    );

    expect(newUrls).toHaveLength(1);
    expect(newUrls).toContain("https://github/pricing")
  });
});
