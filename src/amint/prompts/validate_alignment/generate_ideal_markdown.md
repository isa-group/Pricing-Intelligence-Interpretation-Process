# Generate Ideal Markdown from Pricing2YAML

Based on the following Pricing2YAML specification information and a Pricing2Yaml file, generate an ideal SaaS pricing page in Markdown format for that Pricing2Yaml file.

The generated markdown should include these static sections:

## 1. Plans Section
List each subscription tier with:
- Plan name
- Price and billing interval (you should detailed the different prices for each plan depending on the billing interval chosen; e.g. "$10/mo" or "$100/yr")
- One-sentence description highlighting key benefits (Optional but recommended)

## 2. Comparison Table
Create a markdown table showing all features:
- Use ✔ for included features and ✘ for excluded features
- Include inline usage caps (e.g., "10 projects/mo", "Unlimited users") where applicable
- Organize features by category if possible
- Usage limits with boolean linked features should replace the boolean flags for that features in the table, with their value for each plan

## 3. Add-Ons Section
Create a separate table listing:
- Add-on name
- Description (Optional but recommended)
- Unit price
- Billing period
- Which plans can use this add-on (and if neccessary, if it depends on/excludes other add-ons)
- Features and usage limits included in the add-on if applicable (You can use the same format as the comparison table or describe them in natural language)

This add-ons section may resemble to a fusion of the styles of plans section and comparison table and should only be included if the Pricing2YAML file contains add-ons. If there are no add-ons, it should appear a note indicating that no add-ons are available.

## Pricing2YAML Specification:
<pricing2yaml_specification>
```
{pricing2yaml_specification}
```
</pricing2yaml_specification>

## Pricing2YAML Content:
<pricing2yaml_content>
```json
{pricing2yaml_content}
```
</pricing2yaml_content>

Generate the markdown content without any code blocks or additional formatting. Remember to answer only with the generated markdown content. Make it clean, professional, well-formatted and easy to read:
