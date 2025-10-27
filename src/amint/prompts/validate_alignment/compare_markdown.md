# Compare Markdown Content for Semantic Alignment

Compare the following two markdown contents and determine if they are semantically equivalent in terms of pricing information. This task is similar to a metamorphic test, where you need to ensure that the content aligns in meaning, even if the formatting or presentation differs.

## Evaluation Criteria:

Focus on these key aspects:
1. **Plan Information**: Names, prices, billing intervals, and descriptions
2. **Feature Availability**: Which features are included/excluded in each plan
3. **Usage Limits**: Quotas, caps, and restrictions for features
4. **Add-on Pricing**: Additional services, their prices, and availability

## Instructions:

- Ignore formatting differences (spacing, headers, styling, etc.) and minor syntax variations (punctuation, synonyms, etc.).
- Focus on substantive pricing content
- Consider equivalent information presented differently as aligned
- Look for missing plans, features, or pricing details
- Check for incorrect prices, limits, or availability
- If a pricing model applies the plan fee per unit (e.g., $5 per channel), it may be represented either as a plan that includes one (ore more) unit by default with additional units modeled as add-ons (similar to overage costs), or as a base plan with scalable unit pricing. Consider both representations equivalent as long as the meaning is preserved (i.e., users can subscribe to the plan and incrementally increase usage by paying the same unit price).
- Do not be misled by minor differences in wording or formatting that do not change considerably the meaning and semantics of the pricing information.
- If the scraped data is incomplete or missing, consider it as aligned with the generated markdown as long as the scraped data does not contradict the generated markdown.

## Generated Markdown (generated from Pricing2YAML file):
<generated_markdown>
```
{ideal_markdown}
```
</generated_markdown>

## Scraped Markdown (from live website):
<scraped_markdown>
```
{scraped_markdown}
```
</scraped_markdown>

## Response Format:

Return your response as JSON with the following structure:
```json
{{
  "aligned": boolean,
  "differences": [
    "Brief description of key differences if not aligned"
  ],
  "confidence": "number (from 0 to 1, where 1 is high confidence)"
}}
```

If aligned is true, the content is semantically equivalent.
If aligned is false, list the main differences that need to be addressed.

Remember to answer only with the JSON structure and no additional text. Focus on clarity and conciseness in your descriptions.