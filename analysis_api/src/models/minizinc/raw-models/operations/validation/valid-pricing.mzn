include "../../PricingModel.mzn";

% C1: A pricing cannot be empty

constraint
  assert(num_plans > 0 \/ num_addons > 0, "Invalid datafile. A pricing cannot be empty, there have to be at least one plan or one add-on.");

% C2: All features linked to a usage limit included within a plan are affected by its restriction.

constraint
  if num_plans > 0 /\ num_usage_limits > 0 
    then assert(forall(i in PLANS, j in FEATURES)(
      if sum(k in USAGE_LIMITS)(linked_features[k,j] == 1 /\ plans_features[i,j] == 1) > 0 % If there is at least one usage limit linked to feature j, which is included in plan i
        then sum(k in USAGE_LIMITS)(linked_features[k,j] == 1 /\ (plans_usage_limits[i,k] > 0 \/ boolean_usage_limits[k] == 1)) > 0 % Then, at least one of those usage limits must have a value greater than 0.
      endif
    ), "InvalidUsageLimitValueError: At least one usage limit linked to a feature in a plan must have a value > 0")
  endif;

% C3: If a usage limit has a value > 0 in a plan, at least one of its linked features must be available for such plan.

constraint
  if num_plans > 0 /\ num_usage_limits > 0 
    then assert(forall(i in PLANS, k in USAGE_LIMITS)(
      if plans_usage_limits[i,k] > 0 /\ sum(j in FEATURES)(linked_features[k,j] == 1) > 0% If usage limit k has a value greater than 0 in plan i and is linked to any feature
        then sum(j in FEATURES)(linked_features[k,j] == 1 /\ plans_features[i,j] == 1) > 0 % Then, at least one of its linked features must be available in that plan
      endif
    ), "Invalid datafile. If a usage limit has a value > 0 in a plan, at least one of its linked features must be available for such plan.")
  endif;

% C4: All add-ons must be available for, at least, one plan

constraint
  if num_addons > 0 /\ num_plans > 0
    then assert(forall(i in ADDONS)(
      sum(j in PLANS)(addons_available_for[i,j]) > 0
    ), "Invalid datafile. All add-ons must be available for at least one plan.")
  endif;

% C5: No two plans should be exactly the same

constraint
  if num_plans > 1
    then assert(forall(i, j in PLANS where i < j)(
      exists(k in FEATURES)(
        plans_features[i,k] != plans_features[j,k]
      ) \/
      exists(k in USAGE_LIMITS)(
        plans_usage_limits[i,k] != plans_usage_limits[j,k]
      )
    ), "Invalid datafile. No two plans should be exactly the same.")
  endif;

% C6: No two addons should be exactly the same

constraint
  if num_addons > 1
    then assert(forall(i, j in ADDONS where i < j)(
      exists(k in FEATURES)(
        addons_features[i,k] != addons_features[j,k]
      ) \/
      exists(k in USAGE_LIMITS)(
        addons_usage_limits[i,k] != addons_usage_limits[j,k]
      ) \/
      exists(k in USAGE_LIMITS)(
        addons_usage_limits_extensions[i,k] != addons_usage_limits_extensions[j,k]
      ) \/
      exists(k in PLANS)(
        addons_available_for[i,k] != addons_available_for[j,k]
      ) \/
      exists(k in ADDONS)(
        addons_depends_on[i,k] != addons_depends_on[j,k]
      ) \/
      exists(k in ADDONS)(
        addons_excludes[i,k] != addons_excludes[j,k]
      )
    ), "Invalid datafile. No two addons should be exactly the same.")
  endif;

% C7: There should not be "dead features" within the pricing, i.e., every feature should be included within a plan or an add-on

constraint
  assert(forall(i in FEATURES)(
    sum(j in PLANS)(plans_features[j,i]) + sum(j in ADDONS)(addons_features[j,i]) > 0
  ), "DeadFeatureError: There should not be dead features within the pricing, i.e., every feature should be included within either a plan or an add-on.");

% C8: There should not be "dead usage limits" within the pricing, i.e., every usage limit should be included within a plan or an add-on

constraint
  assert(forall(i in USAGE_LIMITS)(
    sum(j in PLANS)(plans_usage_limits[j,i]) + sum(j in ADDONS)(addons_usage_limits[j,i]) + sum(j in ADDONS)(addons_usage_limits_extensions[j,i]) > 0
  ), "DeadUsageLimitError: There should not be dead usage limits within the pricing, i.e., every usage limit should be included within either a plan or an add-on.");