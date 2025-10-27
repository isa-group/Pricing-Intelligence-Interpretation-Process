import { calculateOverriddenValue, valueToNumber } from '../dzn-exporter/number-utils.js';
import { AddOn, Feature, UsageLimit } from "pricing4ts";

export function getAddOnNames(addOns?: Record<string, AddOn>): string[] {
  if (!addOns) {
    return [];
  }

  return Object.values(addOns).map(addOn => addOn.name);
}

export function getAddOnPrices(addOns?: Record<string, AddOn>): number[] {
  const prices: number[] = [];
  if (!addOns) {
    return prices;
  }

  for (const addOn of Object.values(addOns)) {
    const price = addOn.price;
    if (typeof price === 'number') {
      prices.push(price);
    } else if (typeof price === 'string') {
      prices.push(100);
    }
  }

  return prices;
}

export function calculateAddOnsFeaturesMatrix(features: Record<string, Feature>, addOns: Record<string, AddOn>): number[][] {
  const matrix = [];
  for (const addOn of Object.values(addOns)) {
    const addOnFeatures = addOn.features;
    
    if (!addOnFeatures) {
      matrix.push(new Array(Object.values(features).length).fill(0));
      continue;
    }
    const row = [];
    for (const feature of Object.values(features)) {
      let value = 0;
      const overriddenValue = addOnFeatures[feature.name] ? calculateOverriddenValue({...addOnFeatures[feature.name], valueType: feature.valueType}) : undefined;
      if (overriddenValue) {
        value = 1;
      }
      row.push(value);
    }
  
    matrix.push(row);
  }
  return matrix;
}

export function calculateAddOnsUsageLimitsMatrix(
  usageLimits: Record<string, UsageLimit>,
  addOns: Record<string, AddOn>
): number[][] {
  const matrix: number[][] = [];

  if (Object.keys(usageLimits).length === 0) {
    return matrix;
  }
  for (const addOn of Object.values(addOns)) {
    const addOnUsageLimits = addOn.usageLimits || {};
    const numberOfOverriddenAddOns = Object.keys(addOnUsageLimits).length;
    if (numberOfOverriddenAddOns === 0) {
      matrix.push(new Array(Object.keys(usageLimits).length).fill(0));
      continue;
    }
    const row = [];
    for (const usageLimit of Object.values(usageLimits)) {
      const value = addOnUsageLimits[usageLimit.name] ? calculateOverriddenValue({...addOnUsageLimits[usageLimit.name], valueType: usageLimit.valueType}) : 0;
      row.push(value);
    }

    matrix.push(row);
  }
  return matrix;
}

export function calculateAddOnsUsageLimitsExtensionsMatrix(
  usageLimits: Record<string, UsageLimit>,
  addOns: Record<string, AddOn>
): number[][] {
  const matrix: number[][] = [];

  if (Object.keys(usageLimits).length === 0) {
    return matrix;
  }
  for (const addOn of Object.values(addOns)) {
    const addOnUsageLimits = addOn.usageLimitsExtensions || {};
    const numberOfOverriddenAddOns = Object.keys(addOnUsageLimits).length;
    if (numberOfOverriddenAddOns === 0) {
      matrix.push(new Array(Object.keys(usageLimits).length).fill(0));
      continue;
    }
    const row = [];
    for (const usageLimit of Object.values(usageLimits)) {
      const value = addOnUsageLimits[usageLimit.name]
        ? valueToNumber(addOnUsageLimits[usageLimit.name].value)
        : 0;
      row.push(value);
    }
  
    matrix.push(row);
  }
  return matrix;
}

export function calculateAddOnAvailableForMatrix(
  planNames: string[],
  addOns?: Record<string, AddOn>
): number[][] {
  const matrix: number[][] = [];

  if (!addOns || planNames.length === 0) {
    return matrix;
  }

  for (const addOn of Object.values(addOns)) {
    const row = [];
    for (const planName of planNames) {
      const value = addOn.availableFor.includes(planName) ? 1 : 0;
      row.push(value);
    }
    matrix.push(row);
  }
  return matrix;
}

export function calculateAddOnsDependsOnOExcludesMatrix(addOns?: Record<string, AddOn>, field: "dependsOn" | "excludes" = "dependsOn"): number[][] {
  const matrix: number[][] = [];

  if (!addOns) {
    return matrix;
  }

  for (const addOn of Object.values(addOns)) {
    const selectedField = field === "dependsOn" ? addOn.dependsOn : addOn.excludes;
    const row = [];
    if (!selectedField) {
      row.push(new Array(Object.values(addOns).length).fill(0));
      continue;
    }
    for (const innerAddOn of Object.values(addOns)) {
      const value = selectedField.includes(innerAddOn.name) ? 1 : 0;
      row.push(value);
    }
    matrix.push(row);
  }
  return matrix;
}
