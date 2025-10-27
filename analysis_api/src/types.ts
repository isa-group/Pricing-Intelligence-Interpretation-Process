import { Feature, UsageLimit } from 'pricing4ts';

export interface CspSolution {
  selected_plan: number;
  selected_addons: number[];
  subscription_features: number[];
  subscription_usage_limits: number[];
  subscription_cost: number;
  features_included_in_selected_addons: number[];
  usage_limits_included_in_selected_addons: number[];
}

export type UsageLimitValueType = UsageLimit['valueType'];
export type FeatureValueType = Feature['valueType'];
export type FeatureType = Feature['type'];
export type UsageLimitType = UsageLimit['type'];

export interface Plan {
  name: string;
  price: number;
  features: string[];
}

export interface AddOn {
  name: string;
  price: number;
  availableFor: string[];
}

export interface PricingInputYaml {
  plans: Plan[];
  addOns?: AddOn[];
}

export interface PricingSummaryRequest {
  // File will be uploaded via multipart/form-data
  // No pricingYamlContent field needed
}

export interface PricingSummaryResponse {
  numberOfFeatures: number;
  numberOfInformationFeatures : number;
  numberOfIntegrationFeatures : number;
  numberOfIntegrationApiFeatures : number;
  numberOfIntegrationExtensionFeatures : number;
  numberOfIntegrationIdentityProviderFeatures : number;
  numberOfIntegrationWebSaaSFeatures : number;
  numberOfIntegrationMarketplaceFeatures : number;
  numberOfIntegrationExternalDeviceFeatures : number;
  numberOfDomainFeatures : number;
  numberOfAutomationFeatures : number;
  numberOfBotAutomationFeatures : number;
  numberOfFilteringAutomationFeatures : number;
  numberOfTrackingAutomationFeatures : number;
  numberOfTaskAutomationFeatures : number;
  numberOfManagementFeatures : number;
  numberOfGuaranteeFeatures : number;
  numberOfSupportFeatures : number;
  numberOfPaymentFeatures : number;
  numberOfUsageLimits : number;
  numberOfRenewableUsageLimits : number;
  numberOfNonRenewableUsageLimits : number;
  numberOfPlans : number;
  numberOfFreePlans : number;
  numberOfPaidPlans : number;
  numberOfAddOns : number;
  numberOfReplacementAddons : number;
  numberOfExtensionAddons : number;
  minSubscriptionPrice : number;
  maxSubscriptionPrice : number;
}

export type JobOperationType = 'validate' | 'optimal' | 'subscriptions' | 'filter';

export interface FilterCriteria {
  minPrice?: number;
  maxPrice?: number;
  features?: string[];
  usageLimits?: Record<string, number>[];
}

export interface AnalysisJobRequest {
  // File will be uploaded via multipart/form-data
  // pricingYamlContent removed - file uploaded separately
  operation: JobOperationType;
  solver: string;
  filters?: FilterCriteria;
  objective?: "minimize" | "maximize";
}

export type JobStatusEnum = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface JobCreationResponse {
  jobId: string;
  status: 'PENDING';
  submittedAt: string;
}

export interface ResultCardinality {
  cardinal: number;
}

export interface ResultValidate {
  valid: boolean;
}

export interface ResultOptimumSubscriptionItem {
  plan: string;
  addOns: string[];
}

export interface ResultOptimum {
  subscriptions: ResultOptimumSubscriptionItem[];
  cost: number;
}

export interface GenericResult {
  [key: string]: any;
}

export type JobResultData = ResultCardinality | ResultValidate | ResultOptimum | GenericResult;

export interface JobBaseResponse {
  jobId: string;
  submittedAt: string;
}

export interface JobPendingResponse extends JobBaseResponse {
  status: 'PENDING';
}

export interface JobRunningResponse extends JobBaseResponse {
  status: 'RUNNING';
  startedAt: string;
}

export interface JobCompletedResponse extends JobBaseResponse {
  status: 'COMPLETED';
  startedAt: string;
  completedAt: string;
  result: JobResultData;
}

export interface JobFailedResponse extends JobBaseResponse {
  status: 'FAILED';
  startedAt?: string;
  failedAt: string;
  error: {
    message: string;
    details?: string;
  };
}

export type GetJobDetailsResponse = JobPendingResponse | JobRunningResponse | JobCompletedResponse | JobFailedResponse;