import { Pricing } from 'pricing4ts';
import PricingCSP from '../models/minizinc/minizinc.js';
import { generateFilterDZN, pricing2DZN } from '../utils/dzn-exporter/pricing-dzn-exporter.js';
import { PricingOperation } from '../models/minizinc/minizinc.js';
import { ErrorMessage } from 'minizinc';
import { CspSolution, FilterCriteria } from '../types.js';
import { explain } from '../utils/minizinc-explanator.js';
import { getPlanPrices } from '../utils/helpers/plans.js';
import { getAddOnPrices } from '../utils/helpers/add-ons.js';
import { calculateMinizincSubscriptionCost, parseCurrency, UNLIMITED_VALUE } from '../utils/dzn-exporter/number-utils.js';

export interface MinizincOperationResult {
  configurationSpaceResult?: any;
  minSubscriptionPriceResult?: any;
  maxSubscriptionPriceResult?: any;
}

export default class MinizincService {

  private readonly pricing: Pricing;

  constructor(pricing: Pricing) {
    this.pricing = pricing;
  }

  async runPricingOperation(pricingOperation: PricingOperation) {
    const dznPricing = pricing2DZN(this.pricing);
    const model = new PricingCSP();
    return model.runPricingOperation(pricingOperation, dznPricing);
  }

  convertPricingToDZN(): string {
    return pricing2DZN(this.pricing);
  }

  convertPricingToDZNWithFilters(filters: FilterCriteria): string {
    const dznPricing = this.convertPricingToDZN();
    return dznPricing + '\n' + generateFilterDZN(this.pricing, filters);
  }

  async getFilteredConfigurationSpace(filters: FilterCriteria) {
    const dznPricing = this.convertPricingToDZNWithFilters(filters);

    try {
      const configurationSpace = [];
      const result = await this._getFilteredConfigurationSpace(dznPricing);
      const allSolutions: CspSolution[] = result.allSolutions!;

      for (const solution of allSolutions) {
        const subscriptionCost = calculateMinizincSubscriptionCost(this.pricing, solution);
        const solutionResult = { subscription: {
                plan: Object.keys(this.pricing.plans ?? {})[solution.selected_plan - 1],
                addOns: this.pricing.addOns
                    ? solution.selected_addons.map((addonIndex: number) =>
                        addonIndex === 1
                            ? Object.keys(this.pricing.addOns ?? {})[addonIndex - 1]
                            : null
                    ).filter((addon: string | null) => addon !== null)
                    : [],
                features: solution.subscription_features.map((featureIndex: number, index: number) =>
                    featureIndex === 1 ? Object.keys(this.pricing.features)[index] : null
                ).filter((feature: string | null) => feature !== null),
                usageLimits: solution.subscription_usage_limits.map((usageLimitIndex: number, index: number) =>
                    usageLimitIndex > 0
                        ? { [Object.keys(this.pricing.usageLimits ?? {})[index]]: usageLimitIndex >= UNLIMITED_VALUE ? 'Infinity' : usageLimitIndex }
                        : null
                ).filter((usageLimit: object | null) => usageLimit !== null),
                },
            cost: typeof subscriptionCost === 'number' ? `${subscriptionCost} ${parseCurrency(this.pricing.currency)}` : subscriptionCost
        };
        configurationSpace.push(solutionResult);
      }

      return configurationSpace;

    } catch (e) {
      throw new Error((e as ErrorMessage).message);
    }
  }

  async getOptimalSubscription(filters: FilterCriteria, to_be_minimized: boolean): Promise<{ subscription: any; cost: string }> {
    const dznPricing = this.convertPricingToDZNWithFilters(filters);
    try {
      const result = await this._getOptimalSubscription(dznPricing, to_be_minimized);
      if (!result.solution || !result.solution.output || !result.solution.output.json) {
        throw new Error('No solution found for the given filters.');
      }
      const solution: CspSolution = result.solution.output.json as CspSolution;

      if (!solution) {
        throw new Error('No valid subscription found with the current filters.');
      }
      const subscriptionCost = calculateMinizincSubscriptionCost(this.pricing, solution);
      const solutionResult = { subscription: {
            plan: Object.keys(this.pricing.plans ?? {})[solution.selected_plan - 1],
            addOns: this.pricing.addOns
                ? solution.selected_addons.map((addonIndex: number) =>
                    addonIndex === 1
                        ? Object.keys(this.pricing.addOns ?? {})[addonIndex - 1]
                        : null
                ).filter((addon: string | null) => addon !== null)
                : [],
            features: solution.subscription_features.map((featureIndex: number, index: number) =>
                featureIndex === 1 ? Object.keys(this.pricing.features)[index] : null
            ).filter((feature: string | null) => feature !== null),
            usageLimits: solution.subscription_usage_limits.map((usageLimitIndex: number, index: number) =>
                usageLimitIndex > 0
                    ? { [Object.keys(this.pricing.usageLimits ?? {})[index]]: usageLimitIndex }
                    : null
            ).filter((usageLimit: object | null) => usageLimit !== null),
            },
        cost: typeof subscriptionCost === 'number' ? `${subscriptionCost} ${parseCurrency(this.pricing.currency)}` : subscriptionCost
      };
      return solutionResult;
    } catch (e) {
      throw new Error((e as ErrorMessage).message || 'An error occurred while getting the optimal subscription.');
    }
  }

  /**
   * Validate pricing
   */
    async validatePricing() {
        const dznPricing = this.convertPricingToDZN();
        try {
            const result = await this._getConfigurationSpace(dznPricing);
            const allSolutions: CspSolution[] = result.allSolutions!;
            if (allSolutions.length === 0) {
                throw new Error('No valid subscription found with the current pricing configuration.');
            }
        } catch (e) {
            throw new Error((e as ErrorMessage).message || 'An error occurred while validating the pricing.');
        }
    }

  /**
   * Gets the complete configuration space
   */
  async getConfigurationSpace() {
    const dznPricing = this.convertPricingToDZN();

    try {
      const configurationSpace = [];
      const result = await this._getConfigurationSpace(dznPricing);
      const allSolutions: CspSolution[] = result.allSolutions!;

      for (const solution of allSolutions) {
        const subscriptionCost = calculateMinizincSubscriptionCost(this.pricing, solution);
        const solutionResult = { subscription: {
                plan: Object.keys(this.pricing.plans ?? {})[solution.selected_plan - 1],
                addOns: this.pricing.addOns
                    ? solution.selected_addons.map((addonIndex: number) =>
                        addonIndex === 1
                            ? Object.keys(this.pricing.addOns ?? {})[addonIndex - 1]
                            : null
                    ).filter((addon: string | null) => addon !== null)
                    : [],
                features: solution.subscription_features.map((featureIndex: number, index: number) =>
                    featureIndex === 1 ? Object.keys(this.pricing.features)[index] : null
                ).filter((feature: string | null) => feature !== null),
                usageLimits: solution.subscription_usage_limits.map((usageLimitIndex: number, index: number) =>
                    usageLimitIndex > 0
                        ? { [Object.keys(this.pricing.usageLimits ?? {})[index]]: usageLimitIndex >= UNLIMITED_VALUE ? 'Infinity' : usageLimitIndex }
                        : null
                ).filter((usageLimit: object | null) => usageLimit !== null),
                },
            cost: typeof subscriptionCost === 'number' ? `${subscriptionCost} ${parseCurrency(this.pricing.currency)}` : subscriptionCost
        };
        configurationSpace.push(solutionResult);
      }

      return configurationSpace;

    } catch (e) {
      throw new Error((e as ErrorMessage).message);
    }
  }

  async runAnalyticsOperations(printDzn: boolean = false): Promise<MinizincOperationResult> {
    const dznPricing = this.convertPricingToDZN();

    if (printDzn) {
      console.log(dznPricing);
    }

    try {
      const [configurationSpaceResult, minSubscriptionPriceResult, maxSubscriptionPriceResult] = await Promise.all([
        this._getConfigurationSpace(dznPricing),
        this._getMinSubscriptionPrice(dznPricing),
        this._getMaxSubscriptionPrice(dznPricing)
      ]);

      return {
        configurationSpaceResult,
        minSubscriptionPriceResult,
        maxSubscriptionPriceResult
      };
    } catch (e) {
      throw new Error(explain(e, this.pricing));
    }
  }

  /**
   * Calculates the price of a specific configuration
   */
  computeConfigurationPrice(minizincSolution: Record<string, any>): number {
    const plansPrices = getPlanPrices(this.pricing.plans);
    const addOnPrices = getAddOnPrices(this.pricing.addOns);

    let configurationPrice = 0;
    
    if (plansPrices.length > 0) {
      configurationPrice += plansPrices[minizincSolution.selected_plan - 1];
    }

    if (addOnPrices.length > 0) {
      for (let i = 0; i < minizincSolution.selected_addons.length; i++) {
        const item = minizincSolution.selected_addons[i];

        if (item === 1) {
          configurationPrice += addOnPrices[i];
        }
      }
    }

    return configurationPrice;
  }

  private async _getConfigurationSpace(dznPricing: string) {
    const model = new PricingCSP();
    return model.runPricingOperation(PricingOperation.CONFIGURATION_SPACE, dznPricing);
  }

  private async _getMinSubscriptionPrice(dznPricing: string) {
    const model = new PricingCSP();
    return model.runPricingOperation(PricingOperation.CHEAPEST_SUBSCRIPTION, dznPricing);
  }

  private async _getMaxSubscriptionPrice(dznPricing: string) {
    const model = new PricingCSP();
    return model.runPricingOperation(PricingOperation.MOST_EXPENSIVE_SUBSCRIPTION, dznPricing);
  }

  private async _getFilteredConfigurationSpace(dznPricing: string) {
    const model = new PricingCSP();
    return model.runPricingOperation(PricingOperation.CONFIGURATION_SPACE_FILTER, dznPricing);
  }

  private async _getOptimalSubscription(dznPricing: string, to_be_minimized: boolean) {
    const model = new PricingCSP();
    return model.runPricingOperation(
      to_be_minimized ? PricingOperation.CHEAPEST_FILTER : PricingOperation.MOST_EXPENSIVE_FILTER,
      dznPricing
    );
  }
}
