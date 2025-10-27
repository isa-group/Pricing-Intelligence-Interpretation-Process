# Add-ons Data Parsing

You are given the following markdown content extracted from the SaaS '{saas_name}' HTML pricing page:
========================================
{markdown}
========================================

Your task is to extract and construct add-on objects from this content and update the configuration accordingly.

## Definition
An **add-on** is an optional feature or service that can be purchased separately from the main product.  
It typically enhances the base functionality of a plan or provides extended capabilities such as overage costs, premium modules, or additional user accounts.  
Moreover, any extension of an existing feature or usage limit qualifies as an add-on. Pay special attention to any information suggesting the addition of new features, new usage limits, or increased usage of existing ones.
In some cases, these extended capabilities may be offered at **different prices depending on the selected plan**.  
In such cases, you must model **one distinct add-on per plan** to accurately capture the price variation across plans.

## Instructions

### 1. Configuration Update
- Extend the existing configuration with these keys:
    - 'billing': mapping of billing periods to discount multipliers (e.g., monthly: 1, annual: 0.8).
    - 'variables': key-value pairs for SpEL expressions (e.g., {"#specialDiscount": 0.1}).
    - 'currency': a valid ISO currency code (e.g., 'USD', 'EUR').

### 2. Add-On Object Schema
Each add-on object must include:
- 'name': string (must be unique)
- 'description': string
- 'price': number, 'Contact Sales', or a SpEL expression (e.g., '#specialDiscount * 100')
- 'unit': string (do not include billing period details)
- 'features': object with feature names as keys and boolean values
- 'usageLimits': array of objects, each with a limit name mapping to details:
    - 'limitValueType': string (e.g., 'NUMERIC')
    - 'limitValue': number (it represents the amount for the limit that the add-on provides)
    - 'limitUnit': string (e.g., 'requests/month')
    - 'extendPreviousOne': boolean (in case the limitValue must be added to the original usage limit; for example for representing overage API requests)
- 'availableForPlans': array of plan names (strings)
- 'dependsOnAddOns': array of add-on names (strings)
- 'excludeAddOns': array of add-on names (strings)

An add-on must always have at least one feature or one usage limit.

### 3. Context
- A sample configuration object is provided below:
```json
{
  "config": {
    "billing": {
      "monthly": 1,
      "annual": 0.8,
      "biannual": 0.75
    },
    "variables": { },
    "currency": "<ISO Currency Code>"
  },
  "add-ons": [ ],
  "features": [ ]
}
```

- Already extrated config object: {config}
- Already extracted features: {features}
- Available plans: {plans}

### 4. Output Format
Return a strictly valid JSON object with exactly three keys:
- 'config': updated configuration object. You should only extend the already extracted config object if needed. Despithe this, you must always mantain what it already have in it,
- 'features': a list of new features and limits (do not duplicate already extracted features),
- 'add-ons': a list of add-on objects.

### 5. Example Add-On Object
```json
{
  "name": "Example Add-On",
  "description": "This add-on provides additional functionality for the base product.",
  "price": "#specialDiscount * 100",
  "unit": "user",
  "features": {
      "Example Feature": true,
      "Another Feature": false
  },
  "usageLimits": [
      {
      "Example Limit": {
          "limitValueType": "NUMERIC",
          "limitValue": 10,
          "limitUnit": "requests/month",
          "extendPreviousOne": true
      }
      },
      {
      "Another Limit": {
          "limitValueType": "NUMERIC",
          "limitValue": 1000,
          "limitUnit": "requests/month",
          "extendPreviousOne": false
      }
      }
  ],
  "availableForPlans": [
      "Free",
      "Pro",
      "Enterprise"
  ],
  "dependsOnAddOns": [
      "Another Add-On"
  ],
  "excludeAddOns": [
      "Yet Another Add-On"
  ]
}
```

An add-on must have at least one feature or usage limit linked to it. If no feature or limit already extracted is linked to the add-on, create a new BOOLEAN feature or a NUMERIC limit to link it.
If no add-ons are found, return an object with 'config' (or null), 'features': [] and 'add-ons': [].
Return ONLY the JSON object. 