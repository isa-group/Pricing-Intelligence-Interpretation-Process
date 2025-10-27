In this case, we have one addon, `foo`, which requires a nonexistent addon, `bar`, to be purchased first.

We can model this in `Pricing2Yaml` by placing the key of the nonexistent addon `bar` inside the optional list field `dependsOn` of the addon `foo`.