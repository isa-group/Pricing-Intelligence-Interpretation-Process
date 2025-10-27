# Add-ons Container Identification

For the website that contains the pricing of the SaaS '{saas_name}', identify the containers that hold the add-ons. Return the response strictly as a JSON object in the following format:

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

## Definition
An **add-on** is an optional feature or service that can be purchased separately from the main product.  
It typically enhances the base functionality of a plan or provides extended capabilities such as overage costs, premium modules, or additional user accounts.  
Moreover, any extension of an existing feature or usage limit is also considered an add-on.

## Guidelines
- Each entry in 'selectors' must represent a CSS selector pointing to an element containing the add-ons or containers with relevant information indicating the possibility of adding new features and usage limits or just adding some extra usage to the existing ones.
- Each entry in 'elements' must contain:
  - 'tag': the HTML tag of the element (e.g., 'div', 'section').
  - 'attributes': a mapping of attributes and their values that uniquely identify the element.
- If a CSS selector already identifies a target HTML fragment, you do not need to include an element with the same target.
- Elements should only be used when CSS selectors do not capture the whole data we need to extract.
- If no add-ons are found, return:
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