In this case, we have two plans: `BASIC` and `PRO`, along with two addons: `addonA` and `addonB`.

Addon `A` can only be purchased if you subscribe to the `BASIC` plan
(`availableFor: ["BASIC"]`) and to addon `B` (`dependsOn: ["B"]`).
However, addon `B` can only be purchased if you subscribe to the `PRO` plan (`availableFor: ["PRO"]`).

Since it is only possible to subscribe to one plan at a time, this creates an inconsistency.