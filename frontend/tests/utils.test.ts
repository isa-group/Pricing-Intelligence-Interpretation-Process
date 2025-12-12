import { extractPricingUrls } from "../src/utils"

describe("Utils test suite", () => {
  it("Given prompt text should extract urls", () => {
    const text = "Extract from https://example.org and http://example.org both pricings."
    const urls = extractPricingUrls(text)
    expect(urls).toHaveLength(2)
    expect(urls).toMatchObject(["https://example.org/", "http://example.org/"])
  });
});
