import { Feature, Pricing, UsageLimit } from 'pricing4ts';
import { CspSolution } from '../../types';

export const UNLIMITED_VALUE = 100000000;

export function isUsagelimit(item: Feature | UsageLimit) {
  const usageLimitTypes = ['non_renewable', 'renewable', 'time_driven', 'response_driven'];

  return usageLimitTypes.includes(item.type.toLowerCase());
}

export function calculateOverriddenRow(items: Record<string, Feature | UsageLimit>): number[] {
  const values = [];

  for (const item of Object.values(items)) {
    values.push(calculateOverriddenValue(item));
  }

  return values;
}

export function calculateOverriddenValue(item: Feature | UsageLimit): number {
  const defaultValue = 0;
  let value;

  if (item.valueType === 'NUMERIC' && item.value !== undefined && item.value !== null) {
    value = (item.value as number) > UNLIMITED_VALUE ? UNLIMITED_VALUE : (item.value as number);
  } else if (item.valueType === 'NUMERIC' && item.defaultValue !== undefined && item.defaultValue !== null) {
    value =
      (item.defaultValue as number) > UNLIMITED_VALUE
        ? UNLIMITED_VALUE
        : (item.defaultValue as number);
  } else if (item.valueType === 'BOOLEAN' && item.value !== undefined && item.value !== null) {
    value = item.value ? 1 : 0;
  } else if (
    item.valueType === 'BOOLEAN' &&
    item.defaultValue !== undefined &&
    item.defaultValue !== null
  ) {
    value = item.defaultValue ? 1 : 0;
  } else if (item.valueType === 'TEXT' && item.value) {
    value = item.value.toString().length > 0 ? 1 : 0;
  } else if (item.valueType === 'TEXT' && item.defaultValue) {
    value = item.defaultValue.toString().length > 0 ? 1 : 0;
  } else {
    value = defaultValue;
  }

  return value;
}

export function valueToNumber(value?: string | number | boolean | string[]): number {
  switch (typeof value) {
    case 'boolean':
      return value ? 1 : 0;
    case 'number':
      return value === Infinity ? UNLIMITED_VALUE : value;
    case 'object':
    case 'string':
      return 1;
    case 'undefined':
      return 0;
  }
}

export function parseCurrency(isoCode: string): string {
  const currencyMap: Record<string, string> = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    JPY: '¥',
    CNY: '¥',
    INR: '₹',
    RUB: '₽',
    AUD: 'A$',
    CAD: 'C$',
    CHF: 'CHF',
  };

  return currencyMap[isoCode] || isoCode;
}

export function calculateMinizincSubscriptionCost(pricingData: Pricing, optimal: CspSolution): number | string {
    let subscriptionCost: number = 0; 
    if (pricingData.plans) {
        let planPrice = pricingData.plans[Object.keys(pricingData.plans)[optimal.selected_plan - 1]].price;
        if (typeof planPrice !== 'number') {
            return 'Subscription cost includes non-numeric plan price, cannot calculate total cost. Please check the pricing data or contact sales.';
        } else {
            subscriptionCost += Number(planPrice) ?? 0;
        }
    }
    if (pricingData.addOns) {
        let hasStringPrice = false;
        const addOnKeys = Object.keys(pricingData.addOns);
        subscriptionCost += addOnKeys.reduce((total, key, index) => {
            if (optimal.selected_addons[index] === 1) {
                const addon = pricingData.addOns ? pricingData.addOns[key] : undefined;
                if (addon && typeof addon.price === 'string') {
                  hasStringPrice = true;
                }
                return total + (addon && typeof addon.price === 'number' ? addon.price : 0);
            }
            return total;
        }, 0);

        if (hasStringPrice) {
            return 'Subscription cost includes add-ons with non-numeric prices, cannot calculate total cost. Please check the pricing data or contact sales.';
        }

    }
    return subscriptionCost;
}

export function calculateChocoSubscriptionCost(pricingData: Pricing, subscription: { plan: string; addOns: string[], features: string[], usageLimits: object[] }): number | string {
    let subscriptionCost: number = 0; 
    if (pricingData.plans) {
        let planPrice = pricingData.plans[subscription.plan].price;
        if (typeof planPrice !== 'number') {
            return 'Subscription cost includes non-numeric plan price, cannot calculate total cost. Please check the pricing data or contact sales.';
        } else {
            subscriptionCost += Number(planPrice) ?? 0;
        }
    }
    if (subscription.addOns) {
        subscriptionCost += subscription.addOns.reduce((total, key, index) => {
            const addon = pricingData.addOns ? pricingData.addOns[key] : undefined;
            return total + (addon && typeof addon.price === 'number' ? addon.price : 0);
        }, 0);

        let hasStringPrice = false;
        subscription.addOns.forEach(addon => {
            if (pricingData.addOns && typeof pricingData.addOns[addon].price === 'string') {
                hasStringPrice = true;
            }
        });

        if (hasStringPrice) {
            return 'Subscription cost includes add-ons with non-numeric prices, cannot calculate total cost. Please check the pricing data or contact sales.';
        }

    }
    return subscriptionCost;
}