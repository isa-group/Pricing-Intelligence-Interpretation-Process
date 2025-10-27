include "../validation/valid-subscription.mzn";

% ----------------------
% ----- INPUT DATA -----
% ----------------------

float: min_price;
float: max_price;
array[FEATURES] of int: requested_features; % The position i indicates wether the feature i must be in the subscription.
array[USAGE_LIMITS] of int: requested_usage_limits; % The position i indicates wether the usage limit i must be in the subscription.

% ----------------------
% ----- CONSTRAINTS -----
% ----------------------

% Check the format of the datafile
constraint assert(forall(i in FEATURES)(
  requested_features[i] in {0, 1}
), "Invalid datafile. All requested_features values must be 0 or 1, indicating whether the feature i must be included within the subscription or not");

% All features and usage limits must be satisfied by the subscription
constraint forall(i in FEATURES)(
  subscription_features[i] >= requested_features[i]
);

constraint 
  if num_usage_limits > 0
    then forall(i in USAGE_LIMITS)(
      subscription_usage_limits[i] >= requested_usage_limits[i]
    )
  endif;

% The price of the subscription cannot exceed max_price, and must surpass min_price
constraint subscription_cost_cents >= min_price;
constraint subscription_cost_cents <= max_price;