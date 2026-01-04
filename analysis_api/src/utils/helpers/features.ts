import { Feature } from "pricing4ts";

export function getNumberOfFeatures(features: Record<string, Feature>) {
  return Object.keys(features).length;
}

export function getFeatureNames(features: Record<string, Feature>) {
  return Object.values(features).map(feature => feature.name);
}

export function getDefaultFeatureValues(features: Record<string, Feature>, featuresNames: string[]) {
  return featuresNames.map(name => {
    const feature = features[name];

    if (feature.valueType === 'BOOLEAN') {
      return feature.defaultValue ? 1 : 0;
    }else if (feature.valueType === 'NUMERIC') {
      return feature.defaultValue as number;
    }else if (feature.valueType === 'TEXT') {
      return 1;
    }else{
      throw new Error(`Unsupported feature value type: ${feature.valueType}`);
    }
  });
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
