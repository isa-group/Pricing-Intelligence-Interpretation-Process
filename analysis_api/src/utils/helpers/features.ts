import { Feature } from "pricing4ts";

export function getNumberOfFeatures(features: Record<string, Feature>) {
  return Object.keys(features).length;
}

export function getFeatureNames(features: Record<string, Feature>) {
  return Object.values(features).map(feature => feature.name);
}

export function isIntegrationType(string: string): boolean{
  return (
    string === 'API' ||
    string === 'EXTENSION' ||
    string === 'IDENTITY_PROVIDER' ||
    string === 'WEB_SAAS' ||
    string === 'MARKETPLACE' ||
    string === 'EXTERNAL_DEVICE'
  );
}

export function isAutomationType(string: string): boolean{
  return (
    string === 'BOT' ||
    string === 'FILTERING' ||
    string === 'TRACKING' ||
    string === 'TASK_AUTOMATION'
  );
}

export function isPaymentType(string: string): boolean{
  return (
    string === 'CARD' ||
    string === 'GATEWAY' ||
    string === 'INVOICE' ||
    string === 'ACH' ||
    string === 'WIRE_TRANSFER' ||
    string === 'OTHER'
  );
}
