# Features Data Validation

You are given the following JSON array of feature and usage limits objects extracted from a SaaS pricing page:
========================================
```json
{features_json}
```
========================================

Return a **strictly valid JSON array** describing each feature. Each feature object must follow:

## Feature-level rules
1) 'name': string
2) 'description': string
3) 'tag': string (optional; it containts the name of the group where that feature belongs as some SaaS providers group their features in small groups, making the pricing easier to recall.)
4) 'valueType': one of {BOOLEAN, TEXT} (required)
5) 'type': one of {AUTOMATION, DOMAIN, GUARANTEE, INFORMATION, INTEGRATION, MANAGEMENT, PAYMENT, SUPPORT} (required)
   - if type=AUTOMATION => 'automationType' is required in {BOT, FILTERING, TRACKING, TASK_AUTOMATION}
   - if type=GUARANTEE => 'docUrl' is required (string URL)
   - if type=INTEGRATION => 'integrationType' is required in {API, EXTENSION, IDENTITY_PROVIDER, WEB_SAAS, MARKETPLACE, EXTERNAL_DEVICE}
       * if integrationType=WEB_SAAS => 'pricingUrls' is also required and it would represent a list of pricing urls that sould point towards the target of the web SaaS integration
   - If type=PAYMENT, the 'valueType' must be TEXT and the value (value:
-CARD
-INVOICE) and defaultValue (e.g. defaultValue:
-CARD) must be a list of valid payment methods (CARD, GATEWAY, INVOICE, ACH, WIRE_TRANSFER, OTHER).
6) 'plans': required
 # A mapping of plan names to their availability or usage of the feature. For example:
 # {
 #   'Free': false,
 #   'Pro': true
 #   'Plus': true
 # }
7) The previous attribute must include every plan from the list of plans: {plans}. You must also consider the following when giving a value for the feature in each plan:
   - if valueType=BOOLEAN => bool (true/false)
   - if valueType=TEXT => either a string OR, if the feature's 'type' is PAYMENT,
     a list of valid payment methods: {CARD, GATEWAY, INVOICE, ACH, WIRE_TRANSFER, OTHER}

## Usage limit rules (inside 'limit' object or 'limit': null)
1) 'limit': {
     'name': string (It is a good habit to name usage limits including part of the feature name (e.g. Your Feature) and a noun (e.g. Limit, Uses, Cap...) that fits well that is linked, for example 'Your Feature Limit'),
     'description': string,
     'type': one of {NON_RENEWABLE, RENEWABLE, RESPONSE_DRIVEN, TIME_DRIVEN},
     'valueType': one of {NUMERIC, TEXT},
     'unit': string (e.g. 'user/account', 'minute/month'),
     'linkedFeatures': array of strings (each usage limit must be linked to at least the feature in which it is defined),
      'plans': { // A mapping of plan names to their limit overrides
       // For example (for a NUMERIC valueType):
       //   'Free': null,
       //   'Pro': { 'limitValue': 100, 'limitUnit': 'requests/month' }
       //   'Plus': { 'limitValue': .inf, 'limitUnit': 'requests/month' }
       // }
   } or null

## Important Considerations
- If an usage limit cannot be linked to any existing feature, create a new BOOLEAN feature so that the limit has at least one valid reference.
- If a feature has a NUMERIC usage limit, the feature must have a BOOLEAN value type.
- If you want to model something that seems like a NUMERIC feature, you must model it as a BOOLEAN feature with a NUMERIC usage limit.
- If you want to model something that seems like a TEXT feature but that state a temporal/date limit, you must model it as a BOOLEAN feature with a NUMERIC usage limit.
- You must try to model as many features as possible with a BOOLEAN valueType whereas usage limits should have a NUMERIC valueType.
- If you want to indicate that a feature is not available in a plan, set the plan value to false if valueType is BOOLEAN, "" as empty string for TEXT valueType.
- If a value is Infinity, Unlimited, etc. use '.inf' as the value.
- Do not consider any prices or billing (cycles) information in this task.
- If you want to indicate that a usage limit is not present in a plan, set the plan value to "" if valueType is TEXT or 0 if valueType is NUMERIC (do not use negative numbers, 0 is the lowest value you must use for a NUMERIC valueType).
- If a feature include the 'pricingUrls' field, the list must include at least one URL pointing towards the target of the web SaaS integration.
- You should pay extra attention to NUMERIC features and try if possible to model them as BOOLEAN and linked them to a new NUMERIC usage limit.

Your task is to validate the JSON array and update any feature objects that do not conform to the schema described above. If no changes are needed, simply return the original JSON array. Return ONLY the valid JSON array without any additional text. 