# Patch Pricing2YAML File to Match Scraped Content

The generated markdown using the current Pricing2YAML file does not semantically match the scraped markdown from the live website. 

Your task is to update the Pricing2YAML content so that when regenerated, it produces markdown that semantically matches the scraped content and that has addressed the differences identified during the comparison step.

## Pricing2YAML Specification:
The specification addresses how to model it as a YAML file while for this task you will need to handle it as a JSON object that will be parsed to YAML eventually:
<pricing2yaml_specification>
```
{pricing2yaml_specification}
```
</pricing2yaml_specification>

## Current Pricing2YAML Content:
<current_pricing2yaml>
```json
{current_pricing2yaml}
```
</current_pricing2yaml>

## Generated Markdown (from current YAML):
<generated_markdown>
```
{ideal_markdown}
```
</generated_markdown>

## Target Markdown (scraped from website):
<scraped_markdown>
```
{scraped_markdown}
```
</scraped_markdown>

## Differences between Generated and Scraped Markdown:
<differences>
```json
{differences}
```
</differences>

## Instructions:

1. **Identify Mismatches**: Use the differences section to pinpoint the mismatches identified between the generated markdown and the scraped markdown.
2. **Update YAML Structure**: Modify the Pricing2YAML content to address all differences from the differences section, including but not limited to:
   - Correct plan names, prices, and billing intervals
   - Fix feature availability and usage limits
   - Update add-on information
   - Ensure all pricing details match the scraped content
3. **Maintain Specification Compliance**: Ensure the updated content follows the Pricing2YAML specification and structure, preserving the meaning and relationships between plans, features, and add-ons. Take into account that the specification addresses how to model it as a YAML file while for this task you will need to handle it as a JSON object that will be parsed to YAML eventually (after a post-processing step).
4. **Complete Update**: Provide the full updated YAML content as a JSON (similar to the provided one), not just changes

## Response Format:

Return a JSON response with the complete updated Pricing2YAML content and a description of the changes made over the pricing2yaml_content. The response should have the following structure:

```json
{{
  "updated_pricing2yaml": {{
    "saasName": "...",
    "url": "...",
    "plans": [...],
    "features": [...],
    "addOns": {{...}},
    "config": {{...}}
  }},
  "changes_made": [
    "Brief description of each major change made"
  ]
}}
```

The updated_pricing2yaml field should contain the complete, corrected Pricing2YAML structure that will generate markdown semantically matching the scraped content.


Remember to answer only with the JSON structure and no additional text. Focus on clarity and completeness in your updates. You must include all relevant fields and ensure the JSON is valid.