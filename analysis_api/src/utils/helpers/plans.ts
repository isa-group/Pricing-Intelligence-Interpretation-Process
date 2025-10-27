import { calculateOverriddenRow } from "../dzn-exporter/number-utils.js";
import { Plan, UsageLimit } from "pricing4ts";

export function getPlanNames(plans?: Record<string, Plan>): string[] {
  if (!plans) {
    return [];
  }

  return Object.values(plans).map(plan => plan.name);
}

export function getPlanPrices(plans?: Record<string, Plan>): number[] {
  const prices: number[] = [];
  if (!plans) {
    return prices;
  }

  const planKeys = Object.keys(plans);
  
  for (let i = 0; i < planKeys.length; i++) {
    const price = plans[planKeys[i]].price;
    if (typeof price === 'number') {
      prices.push(price);
    } else if (typeof price === 'string') {
      prices.push(10 * prices[i - 1]);
    }
  }

  return prices;
}

export function calculatePlanFeaturesMatrix(plans: Record<string, Plan>): number[][] {
  const matrix = [];
  for (let plan in plans) {
    const planFeatures = plans[plan].features;
    const row: number[] = calculateOverriddenRow(planFeatures);
    matrix.push(row);
  }
  return matrix;
}

export function calculatePlanUsageLimitsMatrix(
  usageLimits: Record<string, UsageLimit>,
  plans: Record<string, Plan>
): number[][] {
  const matrix: number[][] = [];

  if (Object.keys(usageLimits).length === 0) {
    return matrix;
  }

  for (let plan in plans) {
    const usageLimits = plans[plan].usageLimits;
    if (!usageLimits) {
      continue;
    }
    const row: number[] = calculateOverriddenRow(usageLimits);
    matrix.push(row);
  }
  return matrix;
}
