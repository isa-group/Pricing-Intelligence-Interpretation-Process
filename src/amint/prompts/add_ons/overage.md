# Overage Add-ons Extraction Prompt

You are given the following markdown content extracted from the SaaS '{saas_name}' HTML pricing page:
========================================
{markdown}
========================================

Your task is to identify and construct add-on objects that represent overage costs, i.e. add-ons that enable a customer to extend a usage limit by 1 unit for a price, but which are not explicitly referenced as add-ons. You must start with the already extracted add-ons and add any new overage add-ons that are not present in that list. Do not remove or modify any of the existing add-ons.

## Definition:
An **add-on** is an optional feature or service that can be purchased separately from the main product.  
It typically enhances the base functionality of a plan or provides extended capabilities such as overage costs, premium modules, or additional user accounts.  
Moreover, any extension of an existing feature or usage limit qualifies as an add-on. Pay special attention to any information suggesting the addition of new features, new usage limits, or increased usage of existing ones.
In some cases, these extended capabilities may be offered at **different prices depending on the selected plan**.  
In such cases, you must model **one distinct add-on per plan** to accurately capture the price variation across plans.

## Instructions

### 1. Configuration Update
   - Extend the existing configuration with these keys if needed:
       - 'billing': a mapping of billing periods to discount multipliers (e.g., monthly: 1, annual: 0.8).
       - 'variables': key-value pairs for SpEL expressions (e.g., {"#specialDiscount": 0.1}).
       - 'currency': a valid ISO currency code (e.g., 'USD', 'EUR').

### 2. Add-On Object Schema
   Each add-on object must include:
       - 'name': string (must be unique)
       - 'description': string
       - 'price': number, 'Contact Sales', or a SpEL expression (e.g., '#specialDiscount * 100'). It should be a number (a float or integer) when possible.
       - 'unit': string (do not include billing period details)
       - 'features': an object mapping feature names to boolean values
       - 'usageLimits': an array of objects, each with a limit name mapping to details:
           - 'limitValueType': string (e.g., 'NUMERIC')
           - 'limitValue': number (it represents the amount for the limit that the add-on provides)
           - 'limitUnit': string (e.g., 'requests/month')
           - 'extendPreviousOne': boolean (in case the limitValue must be added to the original usage limit; for example for representing overage API requests)
       - 'availableForPlans': array of plan names (strings)
       - 'dependsOnAddOns': array of add-on names (strings)
       - 'excludeAddOns': array of add-on names (strings)

### 3. Context and Existing Data
   - A sample configuration object is provided below:
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
  "add-ons": [ ...existing add-ons... ],
  "features": [ ...existing features... ]
}

   - Already extracted features and usage limits: 
   ```json
   {features}
   ```
   - Already extracted configuration: 
   ```json
   {config}
   ```
   - Already extracted add-ons: 
   ```json
   {add_ons}
   ```
   - Available plans: 
   ```json
   {plans}
   ```

### 4. Output Format
   Return a strictly valid JSON object with exactly three keys:
       - 'config': the updated configuration object (only extend if necessary while preserving existing keys),
       - 'features': a list of new features and usage limits (do not duplicate already extracted features),
       - 'add-ons': a list of add-on objects that includes both the original add-ons and any newly identified overage add-ons.

### 5. Example Add-On Object
```json
{
    "name": "Overage Extension Add-On",
    "description": "This add-on allows the customer to extend the usage limit by 1 unit for an additional cost.",
    "price": "10",
    "unit": "unit",
    "features": {
        "Extend Usage Limit": true
    },
    "usageLimits": [
        {
            "Overage Limit": {
                "limitValueType": "NUMERIC",
                "limitValue": 1,
                "limitUnit": "unit",
                "extendPreviousOne": true
            }
        }
    ],
    "availableForPlans": [
        "Free",
        "Pro",
        "Enterprise"
    ],
    "dependsOnAddOns": [],
    "excludeAddOns": []
}
```

## IMPORTANT NOTE:
- If you do not have enough information to identify new overage add-ons, return an object with 'config' (or null), 'features': [] and 'add-ons' as the original list.
- Although this is a task that encourages some creativity you cannot invent new add-ons that are not supported by the provided markdown content. In case of doubt, do not create new add-ons.

Return ONLY the JSON object.