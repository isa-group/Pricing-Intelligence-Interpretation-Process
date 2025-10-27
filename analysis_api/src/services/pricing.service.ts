import { Pricing } from 'pricing4ts';

export interface PricingAnalytics {
  numberOfFeatures: number;
  numberOfUsageLimits: number;
  numberOfPlans: number;
  numberOfAddOns: number;
  configurationSpaceSize: number;
  minSubscriptionPrice: number;
  maxSubscriptionPrice: number;
}

export interface AnalyticsOptions {
  printDzn: boolean;
}

const defaultAnalyticsOptions: AnalyticsOptions = {
  printDzn: false
}

export default class PricingService {

  private readonly pricing: Pricing;

  constructor(pricing: Pricing) {
    this.pricing = pricing;
  }

  async getAnalytics(analyticsOptions?: AnalyticsOptions) {

    if (!analyticsOptions) {
      analyticsOptions = defaultAnalyticsOptions;
    } else {
      analyticsOptions = {...defaultAnalyticsOptions, ...analyticsOptions};
    }

    try {
      const informationFeatures = Object.values(this.pricing.features).filter(f => f.type === "INFORMATION");
      const integrationFeatures = Object.values(this.pricing.features).filter(f => f.type === "INTEGRATION");
      const domainFeatures = Object.values(this.pricing.features).filter(f => f.type === "DOMAIN");
      const automationFeatures = Object.values(this.pricing.features).filter(f => f.type === "AUTOMATION");
      const managementFeatures = Object.values(this.pricing.features).filter(f => f.type === "MANAGEMENT");
      const guaranteeFeatures = Object.values(this.pricing.features).filter(f => f.type === "GUARANTEE");
      const supportFeatures = Object.values(this.pricing.features).filter(f => f.type === "SUPPORT");
      const paymentFeatures = Object.values(this.pricing.features).filter(f => f.type === "PAYMENT");

      const numberOfFeatures: number = Object.values(this.pricing.features).length;
      const numberOfInformationFeatures: number = informationFeatures.length;
      const numberOfIntegrationFeatures: number = integrationFeatures.length;
      const numberOfIntegrationApiFeatures: number = integrationFeatures.filter(f => f.integrationType === "API").length;
      const numberOfIntegrationExtensionFeatures: number = integrationFeatures.filter(f => f.integrationType === "EXTENSION").length;
      const numberOfIntegrationIdentityProviderFeatures: number = integrationFeatures.filter(f => f.integrationType === "IDENTITY_PROVIDER").length;
      const numberOfIntegrationWebSaaSFeatures: number = integrationFeatures.filter(f => f.integrationType === "WEB_SAAS").length;
      const numberOfIntegrationMarketplaceFeatures: number = integrationFeatures.filter(f => f.integrationType === "MARKETPLACE").length;
      const numberOfIntegrationExternalDeviceFeatures: number = integrationFeatures.filter(f => f.integrationType === "EXTERNAL_DEVICE").length;
      const numberOfDomainFeatures: number = domainFeatures.length;
      const numberOfAutomationFeatures: number = automationFeatures.length;
      const numberOfBotAutomationFeatures: number = automationFeatures.filter(f => f.automationType === "BOT").length;
      const numberOfFilteringAutomationFeatures: number = automationFeatures.filter(f => f.automationType === "FILTERING").length;
      const numberOfTrackingAutomationFeatures: number = automationFeatures.filter(f => f.automationType === "TRACKING").length;
      const numberOfTaskAutomationFeatures: number = automationFeatures.filter(f => f.automationType === "TASK_AUTOMATION").length;
      const numberOfManagementFeatures: number = managementFeatures.length;
      const numberOfGuaranteeFeatures: number = guaranteeFeatures.length;
      const numberOfSupportFeatures: number = supportFeatures.length;
      const numberOfPaymentFeatures: number = paymentFeatures.length;
      const numberOfUsageLimits: number = this.pricing.usageLimits ? Object.values(this.pricing.usageLimits).length : 0;
      const numberOfRenewableUsageLimits: number = this.pricing.usageLimits ? Object.values(this.pricing.usageLimits).filter(ul => ul.type === "RENEWABLE").length : 0;
      const numberOfNonRenewableUsageLimits: number = this.pricing.usageLimits ? Object.values(this.pricing.usageLimits).filter(ul => ul.type === "NON_RENEWABLE").length : 0;
      const numberOfPlans: number = this.pricing.plans ? Object.values(this.pricing.plans).length : 0;
      const numberOfFreePlans: number = this.pricing.plans ? Object.values(this.pricing.plans).filter(p => p.price === 0).length : 0;
      const numberOfPaidPlans: number = this.pricing.plans ? Object.values(this.pricing.plans).filter(p => typeof(p.price) === "number" ? p.price > 0 : true).length : 0;
      const numberOfAddOns: number = this.pricing.addOns ? Object.values(this.pricing.addOns).length : 0;
      const numberOfReplacementAddons: number = this.pricing.addOns ? Object.values(this.pricing.addOns).filter(a => a.features || a.usageLimits).length : 0;
      const numberOfExtensionAddons: number = this.pricing.addOns ? Object.values(this.pricing.addOns).filter(a => a.features || a.usageLimits ? false : a.usageLimitsExtensions).length : 0;

      return {
        numberOfFeatures: numberOfFeatures,
        numberOfInformationFeatures: numberOfInformationFeatures,
        numberOfIntegrationFeatures: numberOfIntegrationFeatures,
        numberOfIntegrationApiFeatures: numberOfIntegrationApiFeatures,
        numberOfIntegrationExtensionFeatures: numberOfIntegrationExtensionFeatures,
        numberOfIntegrationIdentityProviderFeatures: numberOfIntegrationIdentityProviderFeatures,
        numberOfIntegrationWebSaaSFeatures: numberOfIntegrationWebSaaSFeatures,
        numberOfIntegrationMarketplaceFeatures: numberOfIntegrationMarketplaceFeatures,
        numberOfIntegrationExternalDeviceFeatures: numberOfIntegrationExternalDeviceFeatures,
        numberOfDomainFeatures: numberOfDomainFeatures,
        numberOfAutomationFeatures: numberOfAutomationFeatures,
        numberOfBotAutomationFeatures: numberOfBotAutomationFeatures,
        numberOfFilteringAutomationFeatures: numberOfFilteringAutomationFeatures,
        numberOfTrackingAutomationFeatures: numberOfTrackingAutomationFeatures,
        numberOfTaskAutomationFeatures: numberOfTaskAutomationFeatures,
        numberOfManagementFeatures: numberOfManagementFeatures,
        numberOfGuaranteeFeatures: numberOfGuaranteeFeatures,
        numberOfSupportFeatures: numberOfSupportFeatures,
        numberOfPaymentFeatures: numberOfPaymentFeatures,
        numberOfUsageLimits: numberOfUsageLimits,
        numberOfRenewableUsageLimits: numberOfRenewableUsageLimits,
        numberOfNonRenewableUsageLimits: numberOfNonRenewableUsageLimits,
        numberOfPlans: numberOfPlans,
        numberOfFreePlans: numberOfFreePlans,
        numberOfPaidPlans: numberOfPaidPlans,
        numberOfAddOns: numberOfAddOns,
        numberOfReplacementAddons: numberOfReplacementAddons,
        numberOfExtensionAddons: numberOfExtensionAddons,
      };
    } catch (e) {
      if (e instanceof Error) {
        throw new Error(`Error while calculating pricing analytics: ${e.message}`);
      } else {
        throw new Error(`Error while calculating pricing analytics: ${String(e)}`);
      }
    }
  }
}
