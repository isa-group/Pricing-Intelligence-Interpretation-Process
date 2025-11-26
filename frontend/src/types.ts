export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  metadata?: {
    plan?: Record<string, unknown>;
    result?: Record<string, unknown>;
  };
}

export type Kinds = "url" | "yaml";
export type Origins = "user" | "detected" | "preset" | "agent";

export type PricingContextItem =
  | (BaseContextItemInput & { id: string })
  | (SphereContextItemInput & { id: string });

export type ContextInputType = BaseContextItemInput | SphereContextItemInput;

export interface BaseContextItemInput {
  kind: Kinds;
  uploaded: boolean
  label: string;
  value: string;
  origin?: Origins;
}

export interface SphereContextItemInput {
  kind: "yaml";
  label: string;
  value: string;
  origin: "sphere";
  owner: string;
  collection: string | null;
  pricingName: string;
  version: string
  yamlPath: string;
}

export interface PromptPreset {
  id: string;
  label: string;
  description: string;
  question: string;
  context: BaseContextItemInput[];
}
