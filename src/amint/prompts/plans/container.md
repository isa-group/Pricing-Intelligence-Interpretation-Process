# Plans Container Identification

For the website that contains the pricing of the SaaS '{saas_name}', identify the containers that hold the pricing plans. Return the response strictly as a JSON object in the following format:

```json
{
    "selectors": ["<CSS selector 1>", "<CSS selector 2>", ...],
    "elements": [
        {"tag": "<HTML tag>,
         "attributes": {"attr1": "value1", "attr2": "value2"}
        },
    ]
}
```

Do not include any explanation or additional text outside the JSON object.

A plan is a subscription tier that a customer can choose, such as 'Basic', 'Pro', 'Enterprise', etc. Do not confuse it with an add-on, which is similar to a plan but offers extra capabilities and can be subscribed to multiple times (or just once), even if a plan has already been chosen.

## Guidelines
- Each entry in 'selectors' must represent a CSS selector pointing to an element containing the pricing plans.
- Each entry in 'elements' must contain:
  - 'tag': the HTML tag of the element (e.g., 'div', 'section').
  - 'attributes': a mapping of attributes and their values that uniquely identify the element.
- If a CSS selector already identifies a target HTML fragment, you do not need to include an element with the same target.
- Elements should only be used when CSS selectos does not capture the whole data we need to extract.
- If no pricing plans are found, return:
```json
{
    "selectors": []
    "elements": []
}
```

The HTML content of the page is:
```html
{html}
``` 