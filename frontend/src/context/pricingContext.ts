import { createContext } from "react";
import { PricingContextItem } from "../types";

export const PricingContext = createContext<PricingContextItem[] | null>(null)