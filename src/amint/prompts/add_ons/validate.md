# Add-ons Data Validation

You are provided with a JSON object containing add-on data extracted from the SaaS '{saas_name}' pricing page:
========================================
```json
{json}
```
========================================

Your task is to validate and clean this data according to the following rules:

## 1. Configuration Object
- Must contain exactly these keys:
    - 'billing': object mapping billing periods to multipliers (e.g., monthly: 1, annual: 0.8)
    - 'variables': object with SpEL variable definitions
    - 'currency': string (valid ISO currency code)
- If any key is missing or invalid, remove it

## 2. Add-On Objects
Each add-on must have:
- Required fields:
    - 'name': string (unique)
    - 'description': string
    - 'price': number, 'Contact Sales', or valid SpEL expression
    - 'unit': string
    - 'features': object with feature names as keys and boolean values
    - 'usageLimits': array of limit objects
    - 'availableForPlans': array of plan names
- Optional fields:
    - 'dependsOnAddOns': array of add-on names
    - 'excludeAddOns': array of add-on names

Rules for add-ons:
- Must have at least one feature or usage limit
- Price must be a number, 'Contact Sales', or valid SpEL expression
- Unit must not include billing period
- Features must be boolean values
- Usage limits must have:
    - 'limitValueType': string (e.g., 'NUMERIC')
    - 'limitValue': number
    - 'limitUnit': string
    - 'extendPreviousOne': boolean
- Available plans must exist in the plans list
- Dependencies must reference existing add-ons
- Exclusions must reference existing add-ons

## 3. Feature Objects
Each feature must have:
- Required fields:
    - 'name': string (unique)
    - 'description': string
    - 'tag': string
    - 'valueType': string (e.g., 'BOOLEAN', 'NUMERIC')
    - 'type': string (e.g., 'FEATURE', 'USAGE_LIMIT')
- Optional fields:
    - 'plans': object mapping plan names to values
    - 'usageLimit': object with limit details

Rules for features:
- Must have at least one plan if type is 'FEATURE'
- Must have usage limit if type is 'USAGE_LIMIT'
- Value type must match the type of value provided
- Tag must be one of: 'FEATURE', 'USAGE_LIMIT', 'ADD_ON'

## 4. Validation Process
- Remove any add-ons that don't meet the requirements
- Remove any features that don't meet the requirements
- Clean up any invalid references in dependencies or exclusions
- Ensure all required fields are present and valid
- Remove any duplicate names
- Ensure all references to plans and add-ons are valid

## 5. Output Format
Return a strictly valid JSON object with exactly three keys:
- 'config': validated configuration object
- 'features': array of validated feature objects
- 'add-ons': array of validated add-on objects

If the input is invalid or empty, return an object with 'config': null, 'features': [], and 'add-ons': [].
Return ONLY the JSON object. 