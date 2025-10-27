% ----------------------
% ----- INPUT DATA -----
% ----------------------

int: unlimited = 1000000000;

int: num_features;
int: num_usage_limits;
int: num_plans;
int: num_addons;

array[1..num_features] of string: features;
array[1..num_usage_limits] of string: usage_limits;
array[1..num_plans] of string: plans;
array[1..num_addons] of string: addons;

set of int: FEATURES = index_set(features);
set of int: USAGE_LIMITS = index_set(usage_limits);
set of int: PLANS = index_set(plans);
set of int: ADDONS = index_set(addons);


array[PLANS] of int: plans_prices_cent; % The position i indicates the price of a plan.
array[ADDONS] of int: addons_prices_cent; % The position i indicates the price of an add-on.
array[USAGE_LIMITS] of int: boolean_usage_limits; % The position i indicates wether the usage limit i is a boolean usage limit or not.

array[PLANS, FEATURES] of int: plans_features; % The position (i,j) indicates wether the plan i includes the feature j
array[PLANS, USAGE_LIMITS] of float: plans_usage_limits; % The position (i,j) indicates the value of the usage limit j in the plan i.

array[USAGE_LIMITS, FEATURES] of int: linked_features; % The position (i,j) indicates wether the usageLimit i is linked to the feature j

array[ADDONS, FEATURES] of int: addons_features; % The position (i,j) indicates wether the add-on i includes the feature j
array[ADDONS, USAGE_LIMITS] of float: addons_usage_limits; % The position (i,j) indicates the value of the usage limit j in the add-on i.
array[ADDONS, USAGE_LIMITS] of float: addons_usage_limits_extensions; % The position (i,j) indicates the extension of the limit imposed by the usage limit j in the subscription when contracting the add-on i.
array[ADDONS, PLANS] of int: addons_available_for; % The position (i,j) indicates whether the add-on i is available for the plan j
array[ADDONS, ADDONS] of int: addons_depends_on; % The position (i,j) indicates whether the add-on i depends on the addon j, which means they have to be in the same subscription
array[ADDONS, ADDONS] of int: addons_excludes; % The position (i,j) indicates whether the add-on i excludes the addon j, which means they cannot be in the same subscription

% ---------------------
% ----- VARIABLES -----
% ---------------------

array[FEATURES] of var 0..1: subscription_features;
array[USAGE_LIMITS] of var 0.0..unlimited: subscription_usage_limits;

var int: selected_plan;

array[ADDONS] of var 0..1: selected_addons;
array[FEATURES] of var 0..1: features_included_in_selected_addons;
array[USAGE_LIMITS] of var 0.0..unlimited: usage_limits_included_in_selected_addons;

var int: subscription_cost_cents;
var int: plan_subscription_cost_cents;
var int: addons_subscription_cost_cents;

% -----------------------
% ----- CONSTRAINTS -----
% -----------------------

% ----- Pricing consistency criteria -----

% C1: plans_features and linked_features values must be 0 or 1. plans_usage_limits values must be positive

constraint
  if num_plans > 0 
    then assert(forall(i in PLANS, j in FEATURES)(
      plans_features[i,j] in {0, 1}
    ), "Invalid datafile. All plans_features values must be 0 or 1, indicating whether a feature j is included in the plan i or not")
  endif;

constraint 
  if num_usage_limits > 0 
    then assert(forall(i in USAGE_LIMITS, j in FEATURES)(
      linked_features[i,j] in {0, 1}
    ), "Invalid datafile. All linked_features values must be 0 or 1, indicating whether a feature j is linked to an usage_limit i or not")
  endif;

constraint 
  if num_plans > 0 /\ num_usage_limits > 0 
    then assert(forall(i in PLANS, j in USAGE_LIMITS)(
      plans_usage_limits[i,j] >= -1
    ), "Invalid datafile. All usage limits values must be greater or equal to -1, with -1 indicating a false BOOLEAN usage limit.")
  endif;

constraint
  if num_plans > 0 
    then selected_plan in PLANS
    else selected_plan = 0
  endif;

constraint if num_plans > 0 then plan_subscription_cost_cents = plans_prices_cent[selected_plan] else plan_subscription_cost_cents = 0 endif;
constraint if num_addons > 0 then addons_subscription_cost_cents = sum(a in ADDONS)(selected_addons[a] * addons_prices_cent[a]) else addons_subscription_cost_cents = 0 endif;

constraint subscription_cost_cents = plan_subscription_cost_cents + addons_subscription_cost_cents;

constraint subscription_cost_cents >= 0;
