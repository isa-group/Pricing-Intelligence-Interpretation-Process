# Features Data Parsing

You are given the following markdown content extracted from the SaaS '{saas_name}' HTML pricing page:
========================================
{markdown}
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
       * if integrationType=WEB_SAAS => 'pricingUrls' is also required and it would represent a list of pricing urls that should point towards the target of the web SaaS integration
   - If type=PAYMENT, the 'valueType' must be TEXT and the value (value:
  - CARD
  - INVOICE) and defaultValue (e.g. defaultValue:
  - CARD) must be a list of valid payment methods (CARD, GATEWAY, INVOICE, ACH, WIRE_TRANSFER, OTHER).
6) 'plans': required
 // A mapping of plan names to their availability or usage of the feature. For example:
 // {
 //   'Free': false,
 //   'Pro': true
 //   'Plus': true
 // }
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

## Feature type guidelines
- AUTOMATION:
  Automates tasks within the system or tracks thresholds/events to notify users when they are exceeded.
  This may include bot or AI-driven features (e.g., generative text, predictions).
  Requires an "automationType" field in {BOT, FILTERING, TRACKING, TASK_AUTOMATION}.
- DOMAIN:
  Provides core, domain-specific functionality. These features introduce new operations or exclusive services
  directly tied to the system's primary domain. It's the most common feature type.
- GUARANTEE:
  Represents technical or service commitments (e.g., compliance, SLAs) made by the SaaS provider.
  Requires a "docUrl" field linking to relevant documentation (e.g., security or compliance pages).
- INFORMATION:
  Exposes, visualizes, or provides additional data and insights.
  For example, analytics dashboards or logs that help users understand usage or system events.
- INTEGRATION:
  Allows the SaaS to interact with external services or provides an API so other services can integrate
  functionality here. Requires an "integrationType" field in {API, EXTENSION, IDENTITY_PROVIDER, WEB_SAAS, MARKETPLACE, EXTERNAL_DEVICE}.
  - If "integrationType" = "WEB_SAAS", also requires a "pricingUrls" field (list of URLs).
- MANAGEMENT:
  Provides administrative or organizational functionality, typically used by team leaders or system administrators
  to configure accounts, impose rules, or oversee projects.
- PAYMENT:
  Specifies payment methods, conditions, or possibilities within the SaaS.
  The "value" (valueType must be TEXT) might be a sequence of valid payment methods
  {CARD, GATEWAY, INVOICE, ACH, WIRE_TRANSFER, OTHER}.
- SUPPORT:
  Details the support level or services provided (e.g., help desk, priority queue, enterprise-level support).
  May define the granularity or tier of assistance available to the user.

## Usage limit type guidelines
- NON_RENEWABLE: A static limit that remains throughout the subscription (e.g. '5 total private projects').
Once the user reaches the limit, it cannot reset until the subscription renews or changes. 
- RENEWABLE: The limit automatically resets after a set period (day, week, month, etc.).
For example: '100 pull requests per month' that resets monthly.
- RESPONSE_DRIVEN: The limit is consumed based on how much computational work or resources the SaaS uses per request.
For instance, 'flowCredits' might be a currency-like token that decreases in proportion to request complexity.
- TIME_DRIVEN: The limit is consumed based on usage duration (e.g., compute minutes, streaming hours).
Commonly combined with NON_RENEWABLE in certain contexts (e.g., '10 CPU hours total' until subscription ends).

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
- The plan names you use in 'plans' must be taken from the following list: {plans}.
- Some HTML pricing pages may list the same feature multiple times across different sections. Include each **unique feature** only once in the output, even if it appears repeatedly in the markdown.
- If a **comparison table** is present, prioritize it over all other structures and extract features exclusively from it. Ignore repeated or redundant features outside the table.

## Example feature object
```json
{
  "name": "Example Automation Feature",
  "description": "Automatically track a certain metric and notify the user if thresholds are exceeded.",
  "tag": "Automation",
  "valueType": "BOOLEAN",
  "type": "AUTOMATION",
  "automationType": "TRACKING",
  "plans": {
      "Example Plan Basic": false,
      "Example Plan Pro": true
  },
  "limit": {
      "name": "Example Usage Limit",
      "description": "This usage limit resets every month. It restricts how many requests can be tracked.",
      "type": "RENEWABLE",
      "valueType": "NUMERIC",
      "unit": "requests/month",
      "linkedFeatures": ["Example Automation Feature"],
      "plans": {
          "Example Plan Basic": {
              "limitValue": 10,
              "limitUnit": "requests/month"
          },
          "Example Plan Pro": {
              "limitValue": 1000,
              "limitUnit": "requests/month"
          }
      }
  }
}
```

Return ONLY a valid JSON array of such objects. If no features or usage limits exist, return []. 