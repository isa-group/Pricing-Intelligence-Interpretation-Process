include "./valid-pricing.mzn";

% C4: A subscription cannot be empty

constraint sum(f in FEATURES)(subscription_features[f]) > 0;

% C5: All the features included within the subscription must correspond to a combination of one plan and 0..n add-ons or zero plans and 1..n add-ons.

constraint forall(f in FEATURES)(
      if num_addons > 0 
        then
          features_included_in_selected_addons[f] = max(a in ADDONS)(selected_addons[a] * addons_features[a, f])
        else
          features_included_in_selected_addons[f] = 0
      endif
);

constraint
  if num_usage_limits > 0
    then forall(u in USAGE_LIMITS)(
      if num_addons > 0 
        then
          usage_limits_included_in_selected_addons[u] = 
              max(a in ADDONS)(if selected_addons[a] = 1 then addons_usage_limits[a, u] else 0 endif)
              +
              sum(a in ADDONS)(if selected_addons[a] = 1 then addons_usage_limits_extensions[a, u] else 0 endif)
        else
          usage_limits_included_in_selected_addons[u] = 0
      endif
    )
  endif;

constraint forall(f in FEATURES)(
  subscription_features[f] = (if num_plans > 0 then plans_features[selected_plan, f] == 1 else false endif \/ features_included_in_selected_addons[f] == 1)
);

constraint
  if num_usage_limits > 0
    then forall(u in USAGE_LIMITS)(
      subscription_usage_limits[u] = if num_plans > 0 then plans_usage_limits[selected_plan, u] else false endif + usage_limits_included_in_selected_addons[u]
    )
  endif;

% C6: All selected add_ons must be available for the selected plan

constraint
  if num_addons > 0 /\ num_plans > 0 
    then forall(i in ADDONS)(
      if selected_addons[i] == 1 
        then addons_available_for[i, selected_plan] == 1 
      endif
    )
  endif;

% C7: The subscription must included all dependent addons

constraint
  if num_addons > 0
    then forall(i in ADDONS, j in ADDONS)(
      if addons_depends_on[i, j] == 1 then selected_addons[i] == 1 -> selected_addons[j] == 1 endif
    )
  endif;

% C8: The subscription must not include any excluded addons
constraint
  if num_addons > 0
    then forall(i in ADDONS, j in ADDONS)(
      if addons_excludes[i, j] == 1 then selected_addons[i] == 1 -> selected_addons[j] == 0 endif
    )
  endif;