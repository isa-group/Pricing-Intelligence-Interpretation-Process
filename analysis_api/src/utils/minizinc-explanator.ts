import { ErrorMessage } from 'minizinc';
import { AddOn, Plan, Pricing } from 'pricing4ts';
import { calculateOverriddenValue } from './dzn-exporter/number-utils.js';
import { UsageLimitValueType } from '../types.js'


export function explain(minizincError: any, pricing: Pricing): string {
  const message = (minizincError as ErrorMessage).message;
  
  if (!message) {
    return JSON.stringify(minizincError);
  }
  
  const [errorId, errorMessage] = message.split(':');
  switch (errorId) {
    case 'InvalidUsageLimitValueError':
      return explainUsageLimitWithoutValueError(pricing, errorMessage);
    case 'DeadFeatureError':
      return explainDeadFeatureError(pricing, errorMessage);
    case 'DeadUsageLimitError':
      return explainDeadUsageLimitError(pricing, errorMessage);
    default:
      return message;
  }
}

function explainUsageLimitWithoutValueError(pricing: Pricing, errorMessage: string): string {
  const pricingUsageLimits = pricing.usageLimits!;
  const usageLimitsWithoutValue = [];
  const featuresLinkedToManyUsageLimits = _findFeaturesLinkedToManyUsageLimits(pricing);

  for (const usageLimit of Object.values(pricingUsageLimits)) {
    const plansWithUsageLimitInactive = _plansWithInactiveUsageLimit(
      usageLimit.name,
      usageLimit.linkedFeatures,
      pricing,
      featuresLinkedToManyUsageLimits
    );
    const isUsageLimitInvalid = plansWithUsageLimitInactive.length > 0;

    if (isUsageLimitInvalid) {
      usageLimitsWithoutValue.push(`${usageLimit.name} in [${plansWithUsageLimitInactive}]`);
    }
  }

  return (
    `${errorMessage} Found usage limits without value > 0: ` + usageLimitsWithoutValue.join(', ')
  );
}

function explainDeadFeatureError(pricing: Pricing, errorMessage: string): string {
  const pricingFeatures = Object.keys(pricing.features);
  const deadFeatures = [];

  for (const feature of pricingFeatures) {
    let isFeatureDead = !(
      _isFeatureInAnyPlan(feature, pricing.plans) || _isFeatureInAnyAddOn(feature, pricing.addOns)
    );

    if (isFeatureDead) {
      deadFeatures.push(feature);
    }
  }

  return `${errorMessage} Found dead features: ` + deadFeatures.join(', ');
}

function explainDeadUsageLimitError(pricing: Pricing, errorMessage: string): string {
  const pricingUsageLimits = Object.keys(pricing.usageLimits!);
  const deadUsageLimits = [];

  for (const usageLimit of pricingUsageLimits) {
    let isUsageLimitDead = !(
      _isUsageLimitInAnyPlan(usageLimit, pricing.plans) ||
      _isUsageLimitInAnyAddOn(
        usageLimit,
        pricing.usageLimits![usageLimit].valueType,
        pricing.addOns
      )
    );

    if (isUsageLimitDead) {
      deadUsageLimits.push(usageLimit);
    }
  }

  return `${errorMessage} Found dead usage limits: ` + deadUsageLimits.join(', ');
}

function _isFeatureInAnyPlan(feature: string, plans: Record<string, Plan> | undefined): boolean {
  if (plans) {
    for (const plan of Object.values(plans)) {
      if (plan.features[feature].value || plan.features[feature].defaultValue) {
        return true;
      }
    }
  }

  return false;
}

function _isUsageLimitInAnyPlan(
  usageLimit: string,
  plans: Record<string, Plan> | undefined
): boolean {
  if (plans) {
    for (const plan of Object.values(plans)) {
      if (calculateOverriddenValue(plan.usageLimits![usageLimit]) > 0) {
        return true;
      }
    }
  }

  return false;
}

function _isFeatureInAnyAddOn(feature: string, addOns: Record<string, AddOn> | undefined): boolean {
  if (addOns) {
    for (const addOn of Object.values(addOns)) {
      if (addOn.features?.[feature]?.value) {
        return true;
      }
    }
  }

  return false;
}

function _isUsageLimitInAnyAddOn(
  usageLimit: string,
  usageLimitValueType: UsageLimitValueType,
  addOns: Record<string, AddOn> | undefined
): boolean {
  if (addOns) {
    for (const addOn of Object.values(addOns)) {
      // If the usage limit has a value in the add-on, or extend the plan's value, it is considered active
      if (
        (addOn.usageLimits?.[usageLimit] &&
          calculateOverriddenValue({
            ...addOn.usageLimits?.[usageLimit]!,
            valueType: usageLimitValueType,
          }) > 0) ||
        (addOn.usageLimitsExtensions?.[usageLimit] &&
          calculateOverriddenValue({
            ...addOn.usageLimitsExtensions?.[usageLimit]!,
            valueType: usageLimitValueType,
          }) > 0)
      ) {
        return true;
      }
    }
  }

  return false;
}

function _plansWithInactiveUsageLimit(
  usageLimit: string,
  linkedFeatures: string[] | undefined,
  pricing: Pricing,
  featuresLinkedToManyUsageLimits: string[]
): string[] {
  const plansWithInactiveUsageLimit: string[] = [];

  if (pricing.plans && linkedFeatures && linkedFeatures.length > 0) {
    for (const plan of Object.values(pricing.plans)) {
      const planFeatures = plan.features;
      let isPlanWithLinkedFeatureActive = false;

      // If no feature linked to the limit is active in the plan, an inactive usage limit is not invalid, so there is no need to perform the evaluation
      for (const feature of Object.values(planFeatures)) {
        if (linkedFeatures.includes(feature.name)) {
          if (
            !featuresLinkedToManyUsageLimits.includes(feature.name) &&
            (feature.value || feature.defaultValue)
          ) {
            isPlanWithLinkedFeatureActive = true;
            break;
          } else if (featuresLinkedToManyUsageLimits.includes(feature.name)) {
            const usageLimitsLinkedToFeature = Object.values(pricing.usageLimits!).map(u =>
              u.linkedFeatures?.includes(feature.name)
            );

            if (
              usageLimitsLinkedToFeature.some(
                u => calculateOverriddenValue(plan.usageLimits![usageLimit]) > 0
              )
            ) {
              isPlanWithLinkedFeatureActive = true;
              break;
            }
          }
        }
      }

      if (!isPlanWithLinkedFeatureActive) {
        continue;
      }

      const overridenValue = calculateOverriddenValue(plan.usageLimits![usageLimit]);

      if (overridenValue === 0) {
        plansWithInactiveUsageLimit.push(plan.name);
      }
    }
  }

  return plansWithInactiveUsageLimit;
}

function _findFeaturesLinkedToManyUsageLimits(pricing: Pricing) {
  const pricingUsageLimits = pricing.usageLimits!;

  const linkedFeaturesCounter: Record<string, number> = {};

  for (const usageLimit of Object.values(pricingUsageLimits)) {
    const linkedFeatures = usageLimit.linkedFeatures;

    if (linkedFeatures) {
      for (const feature of linkedFeatures) {
        if (!linkedFeaturesCounter[feature]) {
          linkedFeaturesCounter[feature] = 0;
        }
        linkedFeaturesCounter[feature] += 1;
      }
    }
  }

  return Object.entries(linkedFeaturesCounter)
    .filter(([_, count]) => count > 1)
    .map(([feature]) => feature);
}
