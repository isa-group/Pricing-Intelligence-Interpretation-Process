import { Pricing } from 'pricing4ts';
import { DZNKeywords, Chunk } from './index.js';
import { EOL } from 'os';
import { FilterCriteria } from '../../types.js';
import {
  calculateAddOnAvailableForMatrix,
  calculateAddOnsDependsOnOExcludesMatrix,
  calculateAddOnsFeaturesMatrix,
  calculateAddOnsUsageLimitsExtensionsMatrix,
  calculateAddOnsUsageLimitsMatrix,
  getAddOnNames,
  getAddOnPrices,
} from '../helpers/add-ons.js';
import { AddOn, Plan, UsageLimit } from 'pricing4ts';
import {
  calculatePlanFeaturesMatrix,
  calculatePlanUsageLimitsMatrix,
  getPlanPrices,
  getPlanNames,
} from '../helpers/plans.js';
import { getFeatureNames, getNumberOfFeatures } from '../helpers/features.js';
import {
  calculateLinkedFeaturesMatrix,
  getNumberOfUsageLimits,
  getUsageLimitNames,
} from '../helpers/usage-limits.js';
import { formatMatrixToString, generateChunk, generateChunkBlock } from './string-utils.js';
import { UNLIMITED_VALUE } from './number-utils.js';

export function pricing2DZN(pricing: Pricing): string {
  const numFeatures = getNumberOfFeatures(pricing.features);
  const numUsageLimits = getNumberOfUsageLimits(pricing.usageLimits);
  const numPlans = pricing.plans ? Object.keys(pricing.plans).length : 0;
  const numAddOns = pricing.addOns ? Object.keys(pricing.addOns).length : 0;

  const variableChunks: Chunk[] = [
    {
      left: DZNKeywords.NumberOfFeatures,
      value: JSON.stringify(numFeatures),
    },
    {
      left: DZNKeywords.NumberOfUsageLimits,
      value: JSON.stringify(numUsageLimits),
    },
    { left: DZNKeywords.NumberOfPlans, value: JSON.stringify(numPlans) },
    { left: DZNKeywords.NumberOfAddOns, value: JSON.stringify(numAddOns) },
  ];

  const variablesBlock = generateChunkBlock(variableChunks);

  const featureNames = getFeatureNames(pricing.features);
  const usageLimitNames = getUsageLimitNames(pricing.usageLimits);
  const planNames = getPlanNames(pricing.plans);
  const addOnNames = getAddOnNames(pricing.addOns);

  const namesChunks: Chunk[] = [
    { left: DZNKeywords.Features, value: JSON.stringify(featureNames) },
    {
      left: DZNKeywords.UsageLimits,
      value: JSON.stringify(usageLimitNames),
    },
    { left: DZNKeywords.Plans, value: JSON.stringify(planNames) },
    { left: DZNKeywords.AddOns, value: JSON.stringify(addOnNames) },
  ];

  const namesBlock = generateChunkBlock(namesChunks);

  const pricesChunk = generatePricesChunk(pricing.plans, pricing.addOns);
  const booleanUsageLimitsChunk = generateBooleanUsageLimitsChunk(pricing.usageLimits);
  const planChunks = generatePlanChunks(pricing.usageLimits || {}, pricing.plans);

  const linkedFeatures = generateLinkedFeaturesMatrix(pricing);
  const addOnsChunks = generateAddOnsChunks(pricing);
  return [variablesBlock, namesBlock, pricesChunk, booleanUsageLimitsChunk, linkedFeatures, planChunks, addOnsChunks].join(
    EOL
  );
}

function generatePricesChunk(plans?: Record<string, Plan>, addOns?: Record<string, AddOn>): string {
  const plansPrices = getPlanPrices(plans);
  const plansPricesCent = plansPrices.map(price => {
    return Number(Number(price * 100).toFixed(0)); // Convert to cents
  });

  if (plans && Object.keys(plans).length !== 0 && plansPricesCent.every(p => p === null)) {
    throw new Error(`Either prices are not defined for all plans, or they are not numbers. Current parsed prices: ${plansPrices}`);
  }
  const addOnPrices = getAddOnPrices(addOns);
  const addOnPricesCent = addOnPrices.map(price => {
    return Number(Number(price * 100).toFixed(0)); // Convert to cents
  });

  const pricesChunks: Chunk[] = [
    {
      left: DZNKeywords.PlansPrices,
      value: JSON.stringify(plansPricesCent),
    },
    {
      left: DZNKeywords.AddOnsPrices,
      value: JSON.stringify(addOnPricesCent),
    },
  ];

  return generateChunkBlock(pricesChunks);
}

function generateBooleanUsageLimitsChunk(usageLimits?: Record<string, UsageLimit> | undefined): string {
  
  if (!usageLimits){
    return '';
  }
  
  const booleanUsageLimits = Object.values(usageLimits).map(ul => ul.valueType === 'BOOLEAN' ? 1 : 0);

  const booleanUsageLimitsChunks: Chunk[] = [
    {
      left: DZNKeywords.BooleanUsageLimits,
      value: JSON.stringify(booleanUsageLimits),
    },
  ];

  return generateChunkBlock(booleanUsageLimitsChunks);
}

function generatePlanChunks(usageLimits: Record<string, UsageLimit>, plans?: Record<string, Plan>): string {
  if (!plans){
    return '';
  }
  
  const planNames = Object.values(plans).map(plan => plan.name);
  const planFeaturesMatrix = calculatePlanFeaturesMatrix(plans);
  const planUsageLimitsMatrix = calculatePlanUsageLimitsMatrix(usageLimits, plans);

  const addOnChunks: Chunk[] = [
    {
      left: DZNKeywords.PlansFeatures,
      row: DZNKeywords.Plans,
      col: DZNKeywords.Features,
      value: formatMatrixToString(planNames, planFeaturesMatrix),
    },
    {
      left: DZNKeywords.PlansUsageLimits,
      row: DZNKeywords.Plans,
      col: DZNKeywords.UsageLimits,
      value: formatMatrixToString(planNames, planUsageLimitsMatrix),
    },
  ];

  return generateChunkBlock(addOnChunks);
}

function generateAddOnsChunks(pricing: Pricing): string {
  if (!pricing.addOns) {
    return '';
  }

  if (!pricing.usageLimits) {
    return '';
  }

  const addOnNames = getAddOnNames(pricing.addOns);
  const planNames = getPlanNames(pricing.plans);

  const addOnsFeatureMatrix = calculateAddOnsFeaturesMatrix(pricing.features, pricing.addOns);
  const addOnsUsageLimitsMatrix = calculateAddOnsUsageLimitsMatrix(
    pricing.usageLimits,
    pricing.addOns
  );
  const addOnsUsageLimitsExtensionsMatrix = calculateAddOnsUsageLimitsExtensionsMatrix(
    pricing.usageLimits,
    pricing.addOns
  );
  const addOnsAvailableForMatrix = calculateAddOnAvailableForMatrix(planNames, pricing.addOns);
  const addOnsDependsOnMatrix = calculateAddOnsDependsOnOExcludesMatrix(pricing.addOns);
  const addOnsExcludesOnMatrix = calculateAddOnsDependsOnOExcludesMatrix(pricing.addOns, "excludes");

  const addOnChunks: Chunk[] = [
    {
      left: DZNKeywords.AddOnsFeatures,
      row: DZNKeywords.AddOns,
      col: DZNKeywords.Features,
      value: formatMatrixToString(addOnNames, addOnsFeatureMatrix),
    },
    {
      left: DZNKeywords.AddOnsUsageLimits,
      row: DZNKeywords.AddOns,
      col: DZNKeywords.UsageLimits,
      value: formatMatrixToString(addOnNames, addOnsUsageLimitsMatrix),
    },
    {
      left: DZNKeywords.AddOnsUsageLimitsExtensions,
      row: DZNKeywords.AddOns,
      col: DZNKeywords.UsageLimits,
      value: formatMatrixToString(addOnNames, addOnsUsageLimitsExtensionsMatrix),
    },
    {
      left: DZNKeywords.AddOnsAvailableFor,
      row: DZNKeywords.AddOns,
      col: DZNKeywords.Plans,
      value: formatMatrixToString(addOnNames, addOnsAvailableForMatrix),
    },
    {
      left: DZNKeywords.AddOnsDependsOn,
      row: DZNKeywords.AddOns,
      col: DZNKeywords.AddOns,
      value: formatMatrixToString(addOnNames, addOnsDependsOnMatrix),
    },
    {
      left: DZNKeywords.AddOnsExcludes,
      row: DZNKeywords.AddOns,
      col: DZNKeywords.AddOns,
      value: formatMatrixToString(addOnNames, addOnsExcludesOnMatrix),
    },
  ];

  return generateChunkBlock(addOnChunks);
}

function generateLinkedFeaturesMatrix(pricing: Pricing): string {
  if (!pricing.usageLimits) {
    return '';
  }
  const usageLimitsNames = getUsageLimitNames(pricing.usageLimits);
  const featureNames = getFeatureNames(pricing.features);
  const linkedFeaturesMatrix = calculateLinkedFeaturesMatrix(pricing.usageLimits, featureNames);

  return generateChunk({
    left: DZNKeywords.LinkedFeatures,
    row: DZNKeywords.UsageLimits,
    col: DZNKeywords.Features,
    value: formatMatrixToString(usageLimitsNames, linkedFeaturesMatrix),
  });
}

/**
 * Generates DZN string for filter operations based on filter criteria
 * @param pricing - The pricing model containing features and usage limits
 * @param filterCriteria - The filter criteria object from the API request
 * @returns DZN string with filter parameters
 */
export function generateFilterDZN(pricing: Pricing, filterCriteria: FilterCriteria): string {
  const featureNames = getFeatureNames(pricing.features);
  const usageLimitNames = getUsageLimitNames(pricing.usageLimits);
  
  // Generate min_price and max_price
  const minPrice = filterCriteria?.minPrice ?? 0.0;
  const maxPrice = filterCriteria?.maxPrice ?? UNLIMITED_VALUE;
  
  // Generate requested_features array
  // Array where position i indicates whether feature i must be in the subscription (1) or it does not matter (0)
  const requestedFeatures = featureNames.map(featureName => 
    filterCriteria?.features != undefined && filterCriteria.features.length > 0 ? (filterCriteria.features.includes(featureName) ? 1 : 0) : 0
  );
  
  // Generate requested_usage_limits array
  // Array where position i indicates whether usage limit i must have a value bigger than that value when solving the model
  const requestedUsageLimits = usageLimitNames.map(usageLimitName => {
    if (!filterCriteria?.usageLimits || filterCriteria.usageLimits.length === 0) {
      return 0;
    }
    
    // Check if any of the usage limit objects contains this usage limit name
    const hasUsageLimit = filterCriteria.usageLimits.some(ul => 
      Object.prototype.hasOwnProperty.call(ul, usageLimitName)
    );

    return hasUsageLimit ? filterCriteria.usageLimits.find(ul => Object.prototype.hasOwnProperty.call(ul, usageLimitName))?.[usageLimitName] : 0;
  });
  
  const filterChunks: Chunk[] = [
    {
      left: DZNKeywords.MinPrice,
      value: Number(minPrice*100).toFixed(0).toString(),
    },
    {
      left: DZNKeywords.MaxPrice,
      value: Number(maxPrice*100).toFixed(0).toString(),
    },
    {
      left: DZNKeywords.RequestedFeatures,
      value: JSON.stringify(requestedFeatures),
    },
    {
      left: DZNKeywords.RequestedUsageLimits,
      value: JSON.stringify(requestedUsageLimits),
    },
  ];
  
  return generateChunkBlock(filterChunks);
}
