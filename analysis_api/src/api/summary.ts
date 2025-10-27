import { Request, Response } from 'express';
import { PricingSummaryResponse } from '../types.js';
import { Pricing } from 'pricing4ts';
import { retrievePricingFromPath } from 'pricing4ts/server';
import { randomUUID } from 'crypto';
import * as fs from 'fs';
import { getPlanPrices } from '../utils/helpers/plans.js';

/**
 * POST /pricing/summary
 * Get a summary of key pricing metrics from uploaded YAML file
 */
export const getPricingSummary = (req: Request, res: Response) => {
    try {
        // Check if file was uploaded
        const file = (req as any).file;
        if (!file) {
            return res.status(400).json({ 
                error: 'Pricing YAML file is required. Please upload a file.' 
            });
        }

        // Parse YAML content from uploaded file
        let pricingData: Pricing;
        const pricingYamlContent = file.buffer.toString('utf8');
        
        // Store pricingYamlContent in a file yaml format
        // Generate a temporary file path
        const pricingUUID = `pricing-${randomUUID()}`;
        const tempFilePath = `/tmp/${pricingUUID}.yaml`;
        fs.writeFileSync(tempFilePath, pricingYamlContent);
        try {
            pricingData = retrievePricingFromPath(tempFilePath);
        } catch (yamlError) {
            fs.unlink(tempFilePath, (err) => {
                if (err) {
                    console.error(`Failed to delete temporary file ${tempFilePath}:`, err);
                }
            });

            return res.status(400).json({ 
                error: 'Invalid YAML syntax',
                details: yamlError instanceof Error ? yamlError.message : 'Unknown YAML parsing error'
            });
        }

        // Calculate metrics
        const plans = pricingData.plans || {};
        const addOns = pricingData.addOns || {};

        // Get all unique features across all plans
        const allFeatures = pricingData.features ? new Set(Object.keys(pricingData.features)) : new Set();

        // Get price statistics
        const planPrices = getPlanPrices(pricingData.plans);
        const minPlanPrice = Math.min(...planPrices);
        const maxPlanPrice = Math.max(...planPrices);

        // Example metrics (replace with your actual logic for each metric)
        const numberOfFeatures = allFeatures.size;
        const numberOfPlans = Object.values(plans).length;
        const numberOfFreePlans = Object.values(plans).filter((plan: any) => plan.price === 0).length;
        const numberOfPaidPlans = numberOfPlans - numberOfFreePlans;
        const numberOfAddOns = Object.values(addOns).length;

        // Placeholder logic for other metrics (set to 0 or implement as needed)
        const numberOfInformationFeatures = Object.values(pricingData.features).filter(f => f.type === "INFORMATION").length;
        const numberOfIntegrationFeatures = Object.values(pricingData.features).filter(f => f.type === "INTEGRATION").length;
        const numberOfIntegrationApiFeatures = Object.values(pricingData.features).filter(f => f.integrationType === "API").length;
        const numberOfIntegrationExtensionFeatures = Object.values(pricingData.features).filter(f => f.integrationType === "EXTENSION").length;
        const numberOfIntegrationIdentityProviderFeatures = Object.values(pricingData.features).filter(f => f.integrationType === "IDENTITY_PROVIDER").length;
        const numberOfIntegrationWebSaaSFeatures = Object.values(pricingData.features).filter(f => f.integrationType === "WEB_SAAS").length;
        const numberOfIntegrationMarketplaceFeatures = Object.values(pricingData.features).filter(f => f.integrationType === "MARKETPLACE").length;
        const numberOfIntegrationExternalDeviceFeatures = Object.values(pricingData.features).filter(f => f.integrationType === "EXTERNAL_DEVICE").length;
        const numberOfDomainFeatures = Object.values(pricingData.features).filter(f => f.type === "DOMAIN").length;
        const numberOfAutomationFeatures = Object.values(pricingData.features).filter(f => f.type === "AUTOMATION").length;
        const numberOfBotAutomationFeatures = Object.values(pricingData.features).filter(f => f.automationType === "BOT").length;
        const numberOfFilteringAutomationFeatures = Object.values(pricingData.features).filter(f => f.automationType === "FILTERING").length;
        const numberOfTrackingAutomationFeatures = Object.values(pricingData.features).filter(f => f.automationType === "TRACKING").length;
        const numberOfTaskAutomationFeatures = Object.values(pricingData.features).filter(f => f.automationType === "TASK_AUTOMATION").length;
        const numberOfManagementFeatures = Object.values(pricingData.features).filter(f => f.type === "MANAGEMENT").length;
        const numberOfGuaranteeFeatures = Object.values(pricingData.features).filter(f => f.type === "GUARANTEE").length;
        const numberOfSupportFeatures = Object.values(pricingData.features).filter(f => f.type === "SUPPORT").length;
        const numberOfPaymentFeatures = Object.values(pricingData.features).filter(f => f.type === "PAYMENT").length;
        const numberOfUsageLimits = pricingData.usageLimits ? Object.values(pricingData.usageLimits).length : 0;
        const numberOfRenewableUsageLimits = pricingData.usageLimits ? Object.values(pricingData.usageLimits).filter(ul => ul.type === "RENEWABLE").length : 0;
        const numberOfNonRenewableUsageLimits = pricingData.usageLimits ? Object.values(pricingData.usageLimits).filter(ul => ul.type === "NON_RENEWABLE").length : 0;

        const numberOfReplacementAddons = Object.values(addOns).filter((addOn: any) =>
            addOn.usageLimitsExtensions && typeof addOn.usageLimitsExtensions === 'object' && Object.keys(addOn.usageLimitsExtensions).length === 0
        ).length;

        const numberOfExtensionAddons = numberOfAddOns - numberOfReplacementAddons;

        const summary: PricingSummaryResponse = {
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
            minSubscriptionPrice: parseFloat(minPlanPrice.toFixed(2)),
            maxSubscriptionPrice: parseFloat(maxPlanPrice.toFixed(2)),
        };

        res.status(200).json(summary);

    } catch (error) {
        console.error('Error in getPricingSummary:', error);
        res.status(500).json({ 
            error: 'Internal server error during summary generation',
            details: error instanceof Error ? error.message : 'Unknown error'
        });
    }
};
