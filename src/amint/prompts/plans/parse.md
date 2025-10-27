# Plans Data Parsing

You are given the following markdown content extracted from the SaaS '{saas_name}' HTML pricing page:
========================================
{markdown}
========================================

Return a JSON object with the following structure:

```json
{
  "config": {
    "billing": {
      // This object shows discount multipliers for each billing period.
      // For example:
      //   "monthly": 1,
      //   "annual": 0.8,
      //   "biannual": 0.75
    },
    "variables": {
      // Any variables used in SpEL expressions (e.g., specialDiscount) go here.
      // Leave this empty if no variables are needed.
    },
    "currency": "<ISO Currency Code>"
  },
  "plans": [
    {
      "name": "<plan name>",
      "description": "<description>",
      "price": <plan base price or SpEL or 'Contact Sales'>,
      "unit": "<string representing how it's measured>"
    }
    ... more plans ...
  ]
}
```

## Important Notes
- Return ONLY valid JSON (no extra text or explanations).
- 'billing' values are used as multipliers to reflect discounts to the prices.
- 'variables' can be any key-value pairs used in SpEL. It's empty if no variable is needed.
- 'price' can be a number, 'Contact Sales', or a SpEL expression that could contain variables (e.g., '#specialDiscount * 100').
- 'currency' must follow ISO currency codes (e.g. 'USD', 'EUR').
- 'unit' is a string describing how each plan subscription is measured (e.g. 'user', 'account', 'post'). It should not refer to the billing period.
- If a plan is free, the price should be 0.
- Do not repeat any plan_name in the 'plans' array.
- Do not confuse it with an add-on, which is similar to a plan but offers extra capabilities and can be subscribed to multiple times or just once, even if a plan has already been chosen.
- If no plans can be identified, return the same JSON structure with an empty 'plans' array and an empty 'config' object. 