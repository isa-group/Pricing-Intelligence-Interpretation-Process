import { Model, SolveResult } from 'minizinc';
import { CspSolution } from '../../types';

import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export enum PricingOperation {
  PRICING_MODEL = 'PricingModel.mzn',
  VALID_PRICING = 'valid-pricing.mzn',
  VALID_SUBSCRIPTION = 'valid-subscription.mzn',
  CHEAPEST_SUBSCRIPTION = 'cheapest-subscription.mzn',
  CONFIGURATION_SPACE = 'configuration-space.mzn',
  MOST_EXPENSIVE_SUBSCRIPTION = 'most-expensive-subscription.mzn',
  FILTER = 'filter.mzn',
  CHEAPEST_FILTER = 'cheapest-filter.mzn',
  CONFIGURATION_SPACE_FILTER = 'configuration-space-filter.mzn',
  MOST_EXPENSIVE_FILTER = 'most-expensive-filter.mzn',
}

const modelPaths: {[key in PricingOperation]: string} = {
  [PricingOperation.PRICING_MODEL]: path.join(__dirname, 'raw-models/PricingModel.mzn'),
  [PricingOperation.VALID_PRICING]: path.join(__dirname, 'raw-models/operations/validation/valid-pricing.mzn'),
  [PricingOperation.VALID_SUBSCRIPTION]: path.join(__dirname, 'raw-models/operations/validation/valid-subscription.mzn'),
  [PricingOperation.CHEAPEST_SUBSCRIPTION]: path.join(__dirname, 'raw-models/operations/analysis/cheapest-subscription.mzn'),
  [PricingOperation.CONFIGURATION_SPACE]: path.join(__dirname, 'raw-models/operations/analysis/configuration-space.mzn'),
  [PricingOperation.MOST_EXPENSIVE_SUBSCRIPTION]: path.join(__dirname, 'raw-models/operations/analysis/most-expensive-subscription.mzn'),
  [PricingOperation.FILTER]: path.join(__dirname, 'raw-models/operations/filter/filter.mzn'),
  [PricingOperation.CHEAPEST_FILTER]: path.join(__dirname, 'raw-models/operations/filter/cheapest-filtered-subscription.mzn'),
  [PricingOperation.CONFIGURATION_SPACE_FILTER]: path.join(__dirname, 'raw-models/operations/filter/filtered-configuration-space.mzn'),
  [PricingOperation.MOST_EXPENSIVE_FILTER]: path.join(__dirname, 'raw-models/operations/filter/most-expensive-filtered-subscription.mzn'),
};

export default class PricingCSP {
  private model: Model;
  private pricingData: string;

  constructor() {
    this.model = new Model();

    this.pricingData = '';
  }

  public async runPricingOperation(
    pricingOperation: PricingOperation,
    data: string
  ): Promise<SolveResult & { allSolutions: CspSolution[] | undefined }> {

    this._resetModel();

    if (this.pricingData !== data) {
      this.pricingData = data;
      this.model.addDznString(data);
    }

    const mustExtractAllSolutions = pricingOperation === PricingOperation.CONFIGURATION_SPACE ||
    pricingOperation === PricingOperation.CONFIGURATION_SPACE_FILTER;

    let allSolutions: CspSolution[] | undefined = undefined;

    if (mustExtractAllSolutions){
        allSolutions = [];
      }

    const result = this.model.solve({
      options: {
        solver: 'gecode',
        model: modelPaths[pricingOperation],
        statistics: true,
        'all-solutions':
          pricingOperation === PricingOperation.CONFIGURATION_SPACE ||
          pricingOperation === PricingOperation.CONFIGURATION_SPACE_FILTER,
      },
    });

    result.on('solution', solution => {
      if(mustExtractAllSolutions){
        (allSolutions as CspSolution[]).push(solution.output.json as CspSolution);
      } else {
        // If we are not extracting all solutions, we can just return the first solution
        if (allSolutions === undefined) {
          allSolutions = [solution.output.json as CspSolution];
        }
      }
    });

    return new Promise((resolve, reject) => {
      
      result.on('error', error => {
        reject(error);
      });
      
      Promise.resolve(result).then((result: SolveResult) => {
        resolve({...result, allSolutions: allSolutions });    
      }).catch((error) => {
        reject(error);
      });
    });
  }

  _resetModel() {
    this.model = new Model();
  }
}
