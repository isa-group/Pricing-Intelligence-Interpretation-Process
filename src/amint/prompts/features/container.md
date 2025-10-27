# Features Container Identification

For the website that contains the pricing of the SaaS '{saas_name}', identify the containers that hold the features and usage limits. Return the response strictly as a JSON object in the following format:

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

## Guidelines
- Each entry in 'selectors' must represent a CSS selector pointing to an element containing the features and usage elements.
- Each entry in 'elements' must contain:
  - 'tag': the HTML tag of the element (e.g., 'div', 'section').
  - 'attributes': a mapping of attributes and their values that uniquely identify the element.
- If a CSS selector already identifies a target HTML fragment, you do not need to include an element with the same target.
- If a **comparison table** is present, prefer it over any other structure. In that case, you may not include any other structure.
- Elements should only be used when CSS selectos does not capture the whole data we need to extract.
- If no features and usage limits are found, return:
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