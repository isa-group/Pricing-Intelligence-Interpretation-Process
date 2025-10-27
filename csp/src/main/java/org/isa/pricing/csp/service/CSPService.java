package org.isa.pricing.csp.service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiConsumer;

import org.chocosolver.solver.ICause;
import org.chocosolver.solver.Model;
import org.chocosolver.solver.Solution;
import org.chocosolver.solver.Solver;
import org.chocosolver.solver.constraints.Constraint;
import org.chocosolver.solver.constraints.Propagator;
import org.chocosolver.solver.exception.ContradictionException;
import org.chocosolver.solver.explanations.Explanation;
import org.chocosolver.solver.explanations.ExplanationEngine;
import org.chocosolver.solver.search.strategy.decision.Decision;
import org.chocosolver.solver.variables.BoolVar;
import org.chocosolver.solver.variables.IntVar;
import org.chocosolver.util.tools.ArrayUtils;
import org.isa.pricing.csp.output.CSPOutput;
import org.isa.pricing.csp.output.ConfigurationSpace;
import org.isa.pricing.csp.output.MessageType;
import org.isa.pricing.csp.output.Subscription;
import org.isa.pricing.csp.output.SubscriptionItem;
import org.isa.pricing.csp.parser.Yaml2CSP;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import io.github.isagroup.models.PricingManager;
import io.github.isagroup.models.ValueType;

@Service
public class CSPService {

    // A large integer bound to cap prices/limits in the model
    private static final int BIGINT = 1000;

    // A scale factor for usage limits (to convert to integer)
    private static final int USAGE_LIMIT_SCALE = 1000;

    /**
     * Main entry point to solve the CSP problem.
     * 
     * @param file the YAML file provided by the user containing the iPricing.
     * @return CSPOutput containing solution details or errors.
     */
    public CSPOutput solveCSP(MultipartFile file) {
        // 1) Prepare model, output, constants
        var wrapper = initializeModelAndOutput();

        // 2) Retrieve input (PricingManager, etc.)
        Map<String, Object> pricingMap = Yaml2CSP.retrievePricingFromYaml(file);
        if (!pricingMap.containsKey("pricingManager")) {
            // If we cannot read a valid PricingManager, return the errors
            return (CSPOutput) pricingMap.get("errors");
        }
        PricingManager pricingManager = (PricingManager) pricingMap.get("pricingManager");

        // 3) Prepare lists and matrices from pricingManager
        fillListsAndMatrices(pricingManager, wrapper);

        // 4) Convert prices from double (currency) to int cents
        convertPricesToCents(wrapper);

        // 5) Define Choco integer variables (plan, add-ons, final cost, etc.)
        defineChocoVariables(wrapper);

        // 6) Validate basic data correctness (pure data checks)
        if (!validateDataIntegrity(wrapper, pricingManager)) {
            // If errors exist, return output immediately
            return wrapper.output;
        }

        // 7) Constrain existence of at least one plan/add-on
        if (!addPlanOrAddOnExistenceConstraint(wrapper)) {
            // If errors exist, return output immediately
            return wrapper.output;
        }

        // 8) Add further domain constraints for add-ons, dependencies, excludes, etc.
        if (!addAdditionalModelConstraints(wrapper)) {
            // If errors exist, return output immediately
            return wrapper.output;
        }

        // 9) Encode plan and add-on costs into the model
        encodePlanAndAddOnCosts(wrapper);

        // 10) Solve the model and return the final result
        solveModel(wrapper, pricingManager);

        return wrapper.output;
    }

    /**
     * Step 1) Initialize Choco model and prepare CSPOutput & constants.
     *
     * @return a Wrapper object holding the model, output, and key constants.
     */
    private ModelWrapper initializeModelAndOutput() {
        // We can rename these bounds or store them in class-level constants
        final int MAX_PRICE_BOUND = 100_000;           // Replacement for BIGINT
        final int CENTS_SCALE = 100;                   // For converting currency
        final int UNLIMITED = 100_000_000 - 1;         // Very large for unlimited usage

        Model model = new Model("iPricing Validation");
        CSPOutput output = new CSPOutput();
        output.setMessageType(MessageType.VALIDATION_ERROR);

        // Wrap these into a helper object
        ModelWrapper wrapper = new ModelWrapper();
        wrapper.model = model;
        wrapper.output = output;
        wrapper.MAX_PRICE_BOUND = MAX_PRICE_BOUND;
        wrapper.CENTS_SCALE = CENTS_SCALE;
        wrapper.UNLIMITED = UNLIMITED;

        return wrapper;
    }

    /**
     * Step 3) Fill the model wrapper with lists and matrices read from the PricingManager.
     */
    private void fillListsAndMatrices(PricingManager pricingManager, ModelWrapper wrapper) {
        // Prepare main lists
        wrapper.features = featuresList(pricingManager);
        wrapper.usageLimits = usageLimitsList(pricingManager);
        wrapper.plans = plansList(pricingManager);
        wrapper.addOns = addOnsList(pricingManager);

        // Prepare price lists
        wrapper.plansPrices = plansPricesList(pricingManager);
        wrapper.addOnsPrices = addOnsPricesList(pricingManager);

        wrapper.stringValuesMap = new HashMap<>();

        // Prepare binary/numeric matrices
        wrapper.linkedFeatures = linkedFeaturesMatrix(pricingManager);
        wrapper.plansFeatures = plansFeaturesMatrix(pricingManager, wrapper);
        wrapper.plansUsageLimits = plansUsageLimitsMatrix(pricingManager, wrapper);
        wrapper.addOnsFeatures = addOnsFeaturesMatrix(pricingManager, wrapper);
        wrapper.addOnsUsageLimits = addOnsUsageLimitsMatrix(pricingManager, wrapper);
        wrapper.addOnsUsageLimitsExtension = addOnsUsageLimitsExtensionMatrix(pricingManager, wrapper);
        wrapper.addOnsAvailableFor = addOnsAvailableForMatrix(pricingManager);
        wrapper.addOnsDependsOn = addOnsDependsOnMatrix(pricingManager);
        wrapper.addOnsExcludes = addOnsExcludesMatrix(pricingManager);

        // Collect these variables into the output for debugging
        Map<String, Object> variables = new HashMap<>();
        variables.put("pricingManager", pricingManager);
        variables.put("features", wrapper.features);
        variables.put("usageLimits", wrapper.usageLimits);
        variables.put("plans", wrapper.plans);
        variables.put("addOns", wrapper.addOns);
        variables.put("plansPrices", wrapper.plansPrices);
        variables.put("addOnsPrices", wrapper.addOnsPrices);
        variables.put("linkedFeatures", wrapper.linkedFeatures);
        variables.put("plansFeatures", wrapper.plansFeatures);
        variables.put("plansUsageLimits", wrapper.plansUsageLimits);
        variables.put("addOnsFeatures", wrapper.addOnsFeatures);
        variables.put("addOnsUsageLimits", wrapper.addOnsUsageLimits);
        variables.put("addOnsUsageLimitsExtension", wrapper.addOnsUsageLimitsExtension);
        variables.put("addOnsAvailableFor", wrapper.addOnsAvailableFor);
        variables.put("addOnsDependsOn", wrapper.addOnsDependsOn);
        variables.put("addOnsExcludes", wrapper.addOnsExcludes);

        wrapper.output.setVariables(variables);
    }

    /**
     * Step 4) Convert plan and add-on prices from double to int (cents).
     */
    private void convertPricesToCents(ModelWrapper wrapper) {
        wrapper.planPriceCents = new int[wrapper.plans.size()];
        for (int i = 0; i < wrapper.plans.size(); i++) {
            double dblPrice = wrapper.plansPrices.get(i);
            wrapper.planPriceCents[i] = (int) Math.round(dblPrice * wrapper.CENTS_SCALE);
        }

        wrapper.addOnPriceCents = new int[wrapper.addOns.size()];
        for (int i = 0; i < wrapper.addOns.size(); i++) {
            double dblPrice = wrapper.addOnsPrices.get(i);
            wrapper.addOnPriceCents[i] = (int) Math.round(dblPrice * wrapper.CENTS_SCALE);
        }
    }

    /**
     * Step 5) Define all IntVar variables in the Choco model (selected plan, add-ons, costs).
     */
    private void defineChocoVariables(ModelWrapper wrapper) {
        Model model = wrapper.model;

        // If no plans, force selectedPlan = 0 (just a placeholder)
        if (wrapper.plans.isEmpty()) {
            wrapper.selectedPlan = model.intVar("selectedPlan", 0, 0);
        } else {
            wrapper.selectedPlan = model.intVar("selectedPlan", 0, wrapper.plans.size() - 1);
        }

        // One binary variable per add-on
        wrapper.selectedAddOns = model.intVarArray("selectedAddOns", wrapper.addOns.size(), 0, 1);

        // The final subscription cost
        wrapper.subscriptionCost = model.intVar("subscriptionCost", 0, wrapper.UNLIMITED);

        // Plan price chosen
        wrapper.planPriceVar = model.intVar("planPrice", 0, wrapper.MAX_PRICE_BOUND * wrapper.CENTS_SCALE);

        // One variable for each add-on cost
        wrapper.addOnCostVars = model.intVarArray("addOnCost", wrapper.addOns.size(), 
                                                  0, wrapper.MAX_PRICE_BOUND * wrapper.CENTS_SCALE);
    }

    /**
     * Step 6) Perform data-integrity checks (pure data validations).
     * 
     * @return false if any validation fails and an error is set, true otherwise.
     */
    private boolean validateDataIntegrity(ModelWrapper wrapper, PricingManager pricingManager) {
        // Helper to ensure a matrix only has {0,1}
        final BiConsumer<Model, List<List<Integer>>> ensureBinaryMatrix = (m, matrix) -> {
            for (List<Integer> row : matrix) {
                for (Integer cell : row) {
                    if (cell != 0 && cell != 1) {
                        wrapper.output.setErrors(
                            Collections.singletonList("Matrix must contain only binary values (0 or 1)!"));
                        return;
                    }
                }
            }
        };

        // 6.1) Basic plan checks
        if (!wrapper.plans.isEmpty()) {
            if (wrapper.plansFeatures.isEmpty()) {
                wrapper.output.setErrors(Collections.singletonList("The plans must have features!"));
                return false;
            }
            if (wrapper.output.getErrors() != null) {
                return false;
            }
            // Check dimension and that each plan has at least 1 feature
            for (List<Double> row : wrapper.plansFeatures) {
                if (row.size() != wrapper.features.size()) {
                    String planName = wrapper.plans.get(wrapper.plansFeatures.indexOf(row));
                    wrapper.output.setErrors(Collections.singletonList(
                        "Each plan must have all features! Plan: " + planName + " has incorrect number of features."));
                    return false;
                }
                if (!row.stream().anyMatch(value -> value != 0.0)) {
                    String planName = wrapper.plans.get(wrapper.plansFeatures.indexOf(row));
                    wrapper.output.setErrors(Collections.singletonList(
                        "Each plan must have at least one feature enabled! Plan: " + planName + " has none."));
                    return false;
                }
            }
        }

        // 6.2) Add-ons data checks
        if (!wrapper.addOns.isEmpty()) {
            // If addOn arrays are all empty, fail
            if (wrapper.addOnsFeatures.isEmpty() && wrapper.addOnsUsageLimits.isEmpty() 
                && wrapper.addOnsUsageLimitsExtension.isEmpty()) {
                wrapper.output.setErrors(
                    Collections.singletonList("The add-ons must have features or usage limits!"));
                return false;
            }
            if (wrapper.output.getErrors() != null) {
                return false;
            }
            // Ensure each add-on has correct dimension
            for (int i = 0; i < wrapper.addOns.size(); i++) {
                if (wrapper.addOnsFeatures.get(i).size() != wrapper.features.size()) {
                    wrapper.output.setErrors(Collections.singletonList(
                        "Add-on '" + wrapper.addOns.get(i) + "' must have exactly "
                        + wrapper.features.size() + " features."));
                    return false;
                }
                if (!wrapper.addOnsUsageLimits.isEmpty() && wrapper.addOnsUsageLimits.get(i).size() != wrapper.usageLimits.size()) {
                    wrapper.output.setErrors(Collections.singletonList(
                        "Add-on '" + wrapper.addOns.get(i) + "' must have exactly "
                        + wrapper.usageLimits.size() + " usage limits."));
                    return false;
                }
                if (!wrapper.addOnsUsageLimits.isEmpty() && wrapper.addOnsUsageLimitsExtension.get(i).size() != wrapper.usageLimits.size()) {
                    wrapper.output.setErrors(Collections.singletonList(
                        "Add-on '" + wrapper.addOns.get(i) + "' must have exactly "
                        + wrapper.usageLimits.size() + " usage limit extensions."));
                    return false;
                }
            }

            // Check addOnsAvailableFor, addOnsDependsOn, addOnsExcludes
            if (wrapper.addOnsAvailableFor.isEmpty()) {
                wrapper.output.setErrors(Collections.singletonList("The add-ons must have availability variable!"));
                return false;
            }
            if (wrapper.addOnsAvailableFor.size() != wrapper.addOns.size()) {
                wrapper.output.setErrors(Collections.singletonList("Each add-on must have availability variable!"));
                return false;
            }
            for (List<Integer> row : wrapper.addOnsAvailableFor) {
                if (row.size() != wrapper.plans.size()) {
                    wrapper.output.setErrors(Collections.singletonList("Each add-on must have availability variable!"));
                    return false;
                }
            }

            if (wrapper.addOnsDependsOn.isEmpty()) {
                wrapper.output.setErrors(Collections.singletonList("The add-ons must have dependencies variable!"));
                return false;
            }
            if (wrapper.addOnsDependsOn.size() != wrapper.addOns.size()) {
                wrapper.output.setErrors(Collections.singletonList("Each add-on must have dependencies variable!"));
                return false;
            }
            for (List<Integer> row : wrapper.addOnsDependsOn) {
                if (row.size() != wrapper.addOns.size()) {
                    wrapper.output.setErrors(Collections.singletonList("Each add-on must have dependencies!"));
                    return false;
                }
            }

            if (wrapper.addOnsExcludes.isEmpty()) {
                wrapper.output.setErrors(Collections.singletonList("The add-ons must have exclusions variable!"));
                return false;
            }
            if (wrapper.addOnsExcludes.size() != wrapper.addOns.size()) {
                wrapper.output.setErrors(Collections.singletonList("Each add-on must have exclusions variable!"));
                return false;
            }
            for (List<Integer> row : wrapper.addOnsExcludes) {
                if (row.size() != wrapper.addOns.size()) {
                    wrapper.output.setErrors(Collections.singletonList("Each add-on must have exclusions variable!"));
                    return false;
                }
            }

            // Ensure the three addOn matrices are binary
            ensureBinaryMatrix.accept(wrapper.model, wrapper.addOnsAvailableFor);
            if (wrapper.output.getErrors() != null) {
                return false;
            }
            ensureBinaryMatrix.accept(wrapper.model, wrapper.addOnsDependsOn);
            if (wrapper.output.getErrors() != null) {
                return false;
            }
            ensureBinaryMatrix.accept(wrapper.model, wrapper.addOnsExcludes);
            if (wrapper.output.getErrors() != null) {
                return false;
            }
        }

        // 6.3) linkedFeatures checks
        if (!wrapper.linkedFeatures.isEmpty()) {
            ensureBinaryMatrix.accept(wrapper.model, wrapper.linkedFeatures);
            if (wrapper.output.getErrors() != null) {
                return false;
            }
            if ((wrapper.usageLimits.isEmpty() || wrapper.features.isEmpty())) {
                wrapper.output.setErrors(Collections.singletonList(
                    "Usage limits and features must be defined if linked features are used!"));
                return false;
            }
        }

        // 6.4) plansUsageLimits checks
        if (!wrapper.plansUsageLimits.isEmpty()) {
            for (List<Double> row : wrapper.plansUsageLimits) {
                if (row.size() != wrapper.usageLimits.size()) {
                    String planName = wrapper.plans.get(wrapper.plansUsageLimits.indexOf(row));
                    wrapper.output.setErrors(Collections.singletonList(
                        "Each plan must have all usage limits! Plan: " + planName 
                        + " has incorrect usage limit dimension."));
                    return false;
                }
                // Each usage limit >= 0
                // for (Double limit : row) {
                //     if (limit < 0) {
                //         wrapper.output.setErrors(
                //             Collections.singletonList("Usage limits must be >= 0!"));
                //         return false;
                //     }
                // }
                // For each plan p and usage limit u, create a constant variable and enforce it is non-negative.
                for (int p = 0; p < wrapper.plans.size(); p++) {
                    for (int u = 0; u < wrapper.usageLimits.size(); u++) {
                        // Scale the usage limit value as needed.
                        int usageLimitValue = (int) (wrapper.plansUsageLimits.get(p).get(u) * USAGE_LIMIT_SCALE);
                        // Create a constant variable representing this usage limit.
                        IntVar usageLimitVar = wrapper.model.intVar(
                            "usageLimit_plan" + p + "_" + wrapper.usageLimits.get(u), usageLimitValue, usageLimitValue
                        );
                        // Post a constraint ensuring the usage limit is >= 0.
                        Constraint nonNegativeConstraint = wrapper.model.arithm(usageLimitVar, ">=", 0);
                        nonNegativeConstraint.setName("Usage limit " + wrapper.usageLimits.get(u) + " must be always non-negative for plan " + wrapper.plans.get(p));
                        nonNegativeConstraint.post();
                    }
                }
            }
        }

        // 6.5) If usage limit > 0 but a feature is linked, that feature must be in the plan
        // if (!wrapper.plans.isEmpty() && !wrapper.usageLimits.isEmpty() && !wrapper.linkedFeatures.isEmpty()) {
        //     for (int p = 0; p < wrapper.plans.size(); p++) {
        //         for (int u = 0; u < wrapper.usageLimits.size(); u++) {
        //             int usageLimitValue = (int) (wrapper.plansUsageLimits.get(p).get(u)*USAGE_LIMIT_SCALE);
        //             if (usageLimitValue <= 0) {
        //                 continue;
        //             }
        //             String error = null;
        //             boolean foundLinkedFeature = false;
        //             for (int f = 0; f < wrapper.features.size(); f++) {
        //                 boolean isFeatureLinked = (wrapper.linkedFeatures.get(u).get(f) == 1);
        //                 boolean planHasFeature = (wrapper.plansFeatures.get(p).get(f) == 1);

        //                 if (isFeatureLinked && !planHasFeature) {
        //                     error = "Plan '" + wrapper.plans.get(p) + "' must have the feature '" 
        //                         + wrapper.features.get(f) + "' enabled because it has a positive usage limit ('" 
        //                         + wrapper.usageLimits.get(u) + "') linked to that feature. " 
        //                         + "Otherwise, the usage limit for this plan must be set to 0.";
        //                 } else if (isFeatureLinked && planHasFeature) {
        //                     foundLinkedFeature = true;
        //                     break;
        //                 }
        //             }
        //             if (error != null && !foundLinkedFeature) {
        //                 wrapper.output.setErrors(Collections.singletonList(error));
        //                 return false;
        //             }
        //         }
        //     }
        // }
        if (!wrapper.plans.isEmpty() && !wrapper.usageLimits.isEmpty() && !wrapper.linkedFeatures.isEmpty()) {
            for (int p = 0; p < wrapper.plans.size(); p++) {
                for (int u = 0; u < wrapper.usageLimits.size(); u++) {
                    // Scale the usage limit value as in your original code.
                    int usageLimitValue = (int) (wrapper.plansUsageLimits.get(p).get(u) * USAGE_LIMIT_SCALE);
                    if (usageLimitValue <= 0) {
                        continue;
                    }
                    if (pricingManager.getUsageLimits().get(wrapper.usageLimits.get(u)).getValueType() == ValueType.BOOLEAN) {
                        continue;
                    }
                    // Collect indices of features that are linked to this usage limit.
                    List<Integer> linkedFeatureIndices = new ArrayList<>();
                    for (int f = 0; f < wrapper.features.size(); f++) {
                        if (wrapper.linkedFeatures.get(u).get(f) == 1) {
                            linkedFeatureIndices.add(f);
                        }
                    }
                    if (!linkedFeatureIndices.isEmpty()) {
                        // Compute the sum of the plan's features over the linked features.
                        int sumLinkedFeatures = 0;
                        for (Integer f : linkedFeatureIndices) {
                            sumLinkedFeatures += wrapper.plansFeatures.get(p).get(f);
                        }
                        // Post a constraint stating that at least one linked feature must be active.
                        // Here we create an integer variable holding the constant value of the sum.
                        // If sumLinkedFeatures is 0, this constraint will fail.
                        Constraint linkedFeatureConstraint = wrapper.model.arithm(
                            wrapper.model.intVar(sumLinkedFeatures), ">", 0
                        );
                        linkedFeatureConstraint.setName("Linked feature constraint: For plan '" 
                            + wrapper.plans.get(p) + "' and usage limit '" + wrapper.usageLimits.get(u)
                            + "', at least one linked feature must be enabled.");
                        linkedFeatureConstraint.post();
                    }
                }
            }
        }
        

        // //6.6) If feature f==1 for plan p and is linked to a set of usage limits U, then at least 1 u from U must be > 0 for plan p
        // for (int p = 0; p < wrapper.plans.size(); p++) {
        //     for (int f = 0; f < wrapper.features.size(); f++) {
        //         // Check if feature f is active in plan p
        //         if (wrapper.plansFeatures.get(p).get(f) == 1) {
        //             boolean foundGoodUsageLimit = false;
        //             boolean foundBadUsageLimit = false;
        //             List<String> badUsageLimits = new ArrayList<>();
        //             for (int u = 0; u < wrapper.usageLimits.size(); u++) {
        //                 boolean isLinkedFeature = wrapper.linkedFeatures.get(u).get(f) == 1;
        //                 double usageValue = wrapper.plansUsageLimits.get(p).get(u);
        //                 // Check if usage limit u is linked to the feature f
        //                 if (isLinkedFeature) {
        //                     // Check if usage limit u is > 0 for plan p
        //                     if (usageValue > 0) {
        //                         foundGoodUsageLimit = true;
        //                         break;
        //                     } else {
        //                         foundBadUsageLimit = true;
        //                         badUsageLimits.add(wrapper.usageLimits.get(u));
        //                     }
        //                 }
        //             }
        //             // If no good usage limit found, but a bad one exists, report an error
        //             if (!foundGoodUsageLimit && foundBadUsageLimit) {
        //                 wrapper.output.setErrors(Collections.singletonList(
        //                     "Plan '" + wrapper.plans.get(p) + "' has the feature '" + wrapper.features.get(f) + "' active, " +
        //                     "but it is also a linked feature with " + badUsageLimits.size() + " usage " + 
        //                     (badUsageLimits.size() == 1 ? "limit " + badUsageLimits.get(0) :
        //                     "limits, and at least one of them (" + badUsageLimits + ") ") + 
        //                     "must have a positive value (> 0) for this plan. Otherwise, the feature should be disabled for the plan ('" + 
        //                     wrapper.plans.get(p) + "')."
        //                 ));
        //                 return false;
        //             }
        //         }
        //     }
        // }

        // 6.6) Check if a feature is unreachable (value 0 for every plan and add-on) using Choco
        for (int f = 0; f < wrapper.features.size(); f++) {
            List<IntVar> featureValues = new ArrayList<>();
            
            // For each plan, create a constant variable for the feature value.
            for (int p = 0; p < wrapper.plans.size(); p++) {
                // Assume that wrapper.plansFeatures.get(p).get(f) is 0.0 or nonzero (e.g., 1.0)
                int val = (int) Math.round(wrapper.plansFeatures.get(p).get(f));
                // Create a constant IntVar for this plan's feature.
                featureValues.add(wrapper.model.intVar("plan_" + p + "_feature_" + f, val, val));
            }
            
            // For each add-on, create a constant variable for the feature value.
            for (int a = 0; a < wrapper.addOns.size(); a++) {
                int val = (int) Math.round(wrapper.addOnsFeatures.get(a).get(f));
                featureValues.add(wrapper.model.intVar("addon_" + a + "_feature_" + f, val, val));
            }
            
            // Sum all the constant feature values.
            IntVar featureSum = wrapper.model.intVar("feature_" + f + "_sum", 0, wrapper.UNLIMITED);
            wrapper.model.sum(featureValues.toArray(new IntVar[0]), "=", featureSum).post();
            
            // Post a constraint: featureSum must be greater than 0.
            // If the feature is unreachable, featureSum will be 0 and propagation will fail.
            Constraint unreacheableFeature = wrapper.model.arithm(featureSum, ">", 0);
            unreacheableFeature.setName("Feature '" + wrapper.features.get(f)
            + "' is unreachable. For a NUMERIC feature, at least one plan or add-on must provide a positive value. "
            + "For a TEXT feature, at least one plan or add-on must specify a non-empty value. "
            + "For a BOOLEAN feature, at least one plan or add-on must set it to true.");
            unreacheableFeature.post();
        }

        // 6.7) Check if a usage limit is unreachable (value 0 for every plan and add-on) using Choco
        for (int u = 0; u < wrapper.usageLimits.size(); u++) {
            List<IntVar> usageValues = new ArrayList<>();
            
            // For each plan, create a constant variable for the usage limit value.
            for (int p = 0; p < wrapper.plans.size(); p++) {
                int val = (int) Math.round(wrapper.plansUsageLimits.get(p).get(u));
                usageValues.add(wrapper.model.intVar("plan_" + p + "_usageLimit_" + u, val, val));
            }
            
            // For each add-on, create a constant variable for the usage limit value.
            for (int a = 0; a < wrapper.addOns.size(); a++) {
                int val = (int) Math.round(wrapper.addOnsUsageLimits.get(a).get(u));
                usageValues.add(wrapper.model.intVar("addon_" + a + "_usageLimit_" + u, val, val));
            }

            //For each add-on, create a constant variable for the usage limit extension value.
            for (int a = 0; a < wrapper.addOns.size(); a++) {
                int val = (int) Math.round(wrapper.addOnsUsageLimitsExtension.get(a).get(u));
                usageValues.add(wrapper.model.intVar("addon_" + a + "_usageLimitExtension_" + u, val, val));
            }
            
            // Sum all the constant usage limit values.
            IntVar usageSum = wrapper.model.intVar("usageLimit_" + u + "_sum", 0, wrapper.UNLIMITED);
            wrapper.model.sum(usageValues.toArray(new IntVar[0]), "=", usageSum).post();
            
            // Post a constraint: usageSum must be greater than 0.
            Constraint unreachableUsage = wrapper.model.arithm(usageSum, ">", 0);
            unreachableUsage.setName("Usage Limit '" + wrapper.usageLimits.get(u)
                + "' is unreachable. For a NUMERIC usage limit, at least one plan or add-on must provide a positive value. "
                + "For a TEXT usage limit, at least one plan or add-on must specify a non-empty value. "
                + "For a BOOLEAN usage limit, at least one plan or add-on must set it to true.");
            unreachableUsage.post();
        }

        //6.8) If feature f==1 for plan p and is linked to a set of usage limits U, then at least 1 u from U must be > 0 for plan p
        if (!wrapper.plans.isEmpty() && !wrapper.usageLimits.isEmpty() && !wrapper.linkedFeatures.isEmpty()) {
            for (int p = 0; p < wrapper.plans.size(); p++) {
                for (int f = 0; f < wrapper.features.size(); f++) {
                    // Only consider active features in plan p.
                    if (wrapper.plansFeatures.get(p).get(f) == 1) {
                        List<Constraint> linkedUsageConstraints = new ArrayList<>();
                        // For each usage limit u that is linked to feature f...
                        for (int u = 0; u < wrapper.usageLimits.size(); u++) {
                            if (wrapper.linkedFeatures.get(u).get(f) == 1) {
                                // Scale the usage limit value.
                                int usageLimitValue = (int) (wrapper.plansUsageLimits.get(p).get(u) * USAGE_LIMIT_SCALE);
                                // Create a constant variable for this usage limit.
                                IntVar usageLimitVar = wrapper.model.intVar("usage_limit_plan" + p + "_ul" + u, usageLimitValue, usageLimitValue);
                                // Create a constraint that requires the usage limit to be > 0.
                                Constraint usagePositive = wrapper.model.arithm(usageLimitVar, ">", 0);
                                linkedUsageConstraints.add(usagePositive);
                            }
                        }
                        // If there is at least one usage limit linked to feature f...
                        if (!linkedUsageConstraints.isEmpty()) {
                            // Post a disjunction: at least one of the linked usage limits must be > 0.
                            Constraint atLeastOneUsagePositive = wrapper.model.or(linkedUsageConstraints.toArray(new Constraint[0]));
                            atLeastOneUsagePositive.setName("For plan '" + wrapper.plans.get(p)
                                + "', feature '" + wrapper.features.get(f)
                                + "' requires at least one linked usage limit (i.e. an usage limit with '"
                                + wrapper.features.get(f) + "' as linkedFeature) for plan '" + wrapper.plans.get(p) + "' to be > 0. Otherwise, the feature '" + wrapper.features.get(f) + "' should be disabled for this plan.");
                            atLeastOneUsagePositive.post();
                        }
                    }
                }
            }
        }
        
        return true;
    }

    /**
     * Step 7) Add constraint: must pick at least one plan or one add-on (if they exist).
     */
    private boolean addPlanOrAddOnExistenceConstraint(ModelWrapper wrapper) {
        Model model = wrapper.model;
        // If both plans and add-ons exist
        if (!wrapper.plans.isEmpty() && !wrapper.addOns.isEmpty()) {
            model.or(
                model.arithm(wrapper.selectedPlan, ">=", 0),
                model.sum(wrapper.selectedAddOns, ">", 0)
            ).post();
        } else if (wrapper.plans.isEmpty() && !wrapper.addOns.isEmpty()) {
            // No plans => must pick at least one add-on
            model.sum(wrapper.selectedAddOns, ">", 0).post();
        } else if (!wrapper.plans.isEmpty() && wrapper.addOns.isEmpty()) {
            // No add-ons => must pick at least one plan
            model.arithm(wrapper.selectedPlan, ">=", 0).post();
        } else {
            // If no plans or add-ons exist, there's nothing to choose
            wrapper.output.setErrors(Collections.singletonList("No plans or add-ons to choose from!"));
            return false;
        }
        return true;
    }

    /**
     * Step 8) Add additional constraints regarding add-ons (dependencies, excludes, etc.).
     */
    private boolean addAdditionalModelConstraints(ModelWrapper wrapper) {
        // // 8.1) Each add-on must have at least one (feature / usageLimit / usageLimitExtension)
        // for (int i = 0; i < wrapper.addOns.size(); i++) {
        //     boolean hasFeature = wrapper.addOnsFeatures.get(i).contains(1);
        //     boolean hasUsageLimit = wrapper.addOnsUsageLimits.get(i).stream().anyMatch(v -> v != 0);
        //     boolean hasUsageLimitExt = wrapper.addOnsUsageLimitsExtension.get(i).stream().anyMatch(v -> v != 0);

        //     if (!hasFeature && !hasUsageLimit && !hasUsageLimitExt) {
        //         wrapper.output.setErrors(Collections.singletonList(
        //             "Add-On " + wrapper.addOns.get(i) 
        //             + " must have at least one feature, usage limit, or usage limit extension enabled!"));
        //         return false;
        //     }
        // }

        // // 8.2) Each add-on must be available for at least one plan
        // if (!wrapper.plans.isEmpty() && !wrapper.addOns.isEmpty()) {
        //     for (int i = 0; i < wrapper.addOns.size(); i++) {
        //         if (!wrapper.addOnsAvailableFor.get(i).contains(1)) {
        //             wrapper.output.setErrors(Collections.singletonList(
        //                 "Add-On " + wrapper.addOns.get(i) 
        //                 + " must be available for at least one plan!"));
        //             return false;
        //         }
        //     }
        // }

        // 8.1) Each add-on must have at least one (feature / usageLimit / usageLimitExtension)
        for (int i = 0; i < wrapper.addOns.size(); i++) {
            // Compute constant sums from the input lists:
            int sumFeatures = wrapper.addOnsFeatures.get(i).stream().mapToInt(x -> (int) Math.round(x)).sum();
            int sumUsageLimits =  wrapper.addOnsUsageLimits.isEmpty() ? 0 : wrapper.addOnsUsageLimits.get(i).stream().mapToInt(x -> (int) Math.round(x)).sum();
            int sumUsageLimitsExt = wrapper.addOnsUsageLimitsExtension.isEmpty() ? 0 : wrapper.addOnsUsageLimitsExtension.get(i).stream().mapToInt(x -> (int) Math.round(x)).sum();

            // Create constant IntVars for each sum:
            IntVar featuresSum = wrapper.model.intVar("addon" + i + "_featuresSum", sumFeatures, sumFeatures);
            IntVar usageLimitSum = wrapper.model.intVar("addon" + i + "_usageLimitSum", sumUsageLimits, sumUsageLimits);
            IntVar usageLimitExtSum = wrapper.model.intVar("addon" + i + "_usageLimitExtSum", sumUsageLimitsExt, sumUsageLimitsExt);

            // Create three constraints: each asserts that a sum is > 0.
            Constraint featureActive = wrapper.model.arithm(featuresSum, ">", 0);
            Constraint usageLimitActive = wrapper.model.arithm(usageLimitSum, ">", 0);
            Constraint usageLimitExtActive = wrapper.model.arithm(usageLimitExtSum, ">", 0);

            // At least one of these must be true:
            Constraint atLeastOneEnabled = wrapper.model.or(featureActive, usageLimitActive, usageLimitExtActive);
            atLeastOneEnabled.setName("Add-On '" + wrapper.addOns.get(i) 
                + "' must have at least one feature, usage limit, or usage limit extension enabled");
            atLeastOneEnabled.post();
        }

        // 8.2) Each add-on must be available for at least one plan
        if (!wrapper.plans.isEmpty() && !wrapper.addOns.isEmpty()) {
            for (int i = 0; i < wrapper.addOns.size(); i++) {
                // Compute the sum of the availability flags for this add-on.
                int sumAvailable = wrapper.addOnsAvailableFor.get(i).stream().mapToInt(x -> x).sum();

                // Wrap as a constant variable.
                IntVar availableSum = wrapper.model.intVar("addon" + i + "_availableSum", sumAvailable, sumAvailable);

                // Post the constraint that the sum must be greater than 0.
                Constraint availableForPlan = wrapper.model.arithm(availableSum, ">", 0);
                availableForPlan.setName("Add-On '" + wrapper.addOns.get(i) + "' must be available for at least one plan");
                availableForPlan.post();
            }
        }


        // // 8.3) No two plans should be exactly the same
        // for (int i = 0; i < wrapper.plans.size(); i++) {
        //     for (int j = i + 1; j < wrapper.plans.size(); j++) {
        //         if (wrapper.plansFeatures.get(i).equals(wrapper.plansFeatures.get(j)) 
        //             && wrapper.plansUsageLimits.get(i).equals(wrapper.plansUsageLimits.get(j))) {
        //             wrapper.output.setErrors(Collections.singletonList(
        //                 "Plan " + wrapper.plans.get(i) + " and plan " + wrapper.plans.get(j) 
        //                 + " are exactly the same!"));
        //             return false;
        //         }
        //     }
        // }

        // // 8.4) No two add-ons should be exactly the same
        // for (int i = 0; i < wrapper.addOns.size(); i++) {
        //     for (int j = i + 1; j < wrapper.addOns.size(); j++) {
        //         if (wrapper.addOnsFeatures.get(i).equals(wrapper.addOnsFeatures.get(j))
        //             && wrapper.addOnsUsageLimits.get(i).equals(wrapper.addOnsUsageLimits.get(j))
        //             && wrapper.addOnsUsageLimitsExtension.get(i).equals(wrapper.addOnsUsageLimitsExtension.get(j))
        //             && wrapper.addOnsAvailableFor.get(i).equals(wrapper.addOnsAvailableFor.get(j))
        //             && wrapper.addOnsDependsOn.get(i).equals(wrapper.addOnsDependsOn.get(j))
        //             && wrapper.addOnsExcludes.get(i).equals(wrapper.addOnsExcludes.get(j))) {
        //             wrapper.output.setErrors(Collections.singletonList(
        //                 "Add-On " + wrapper.addOns.get(i) + " and Add-On " + wrapper.addOns.get(j) 
        //                 + " are exactly the same!"));
        //             return false;
        //         }
        //     }
        // }

        // 8.3) No two plans should be exactly the same
        if (wrapper.plans.size() > 1) {
            addNoDuplicatePlansConstraint(wrapper);
        }
        
        // 8.4) No two add-ons should be exactly the same
        if (wrapper.addOns.size() > 1) {
            addNoDuplicateAddOnsConstraint(wrapper);
        }
        

        // 8.5) All selected add-ons must be available for the selected plan
        for (int i = 0; i < wrapper.addOns.size(); i++) {
            wrapper.model.ifThen(
                wrapper.model.arithm(wrapper.selectedAddOns[i], "=", 1),
                wrapper.model.element(
                    wrapper.model.intVar(1),
                    wrapper.addOnsAvailableFor.get(i).stream().mapToInt(Integer::intValue).toArray(),
                    wrapper.selectedPlan
                )
            );
        }

        // 8.6) If add-on A depends on add-on B, then B must be selected
        for (int i = 0; i < wrapper.addOns.size(); i++) {
            for (int j = 0; j < wrapper.addOns.size(); j++) {
                if (i != j && wrapper.addOnsDependsOn.get(i).get(j) == 1) {
                    wrapper.model.ifThen(
                        wrapper.model.arithm(wrapper.selectedAddOns[i], "=", 1),
                        wrapper.model.arithm(wrapper.selectedAddOns[j], "=", 1)
                    );
                }
            }
        }

        // 8.7) If add-on A excludes add-on B, they cannot both be selected
        for (int i = 0; i < wrapper.addOns.size(); i++) {
            for (int j = 0; j < wrapper.addOns.size(); j++) {
                if (i != j &&wrapper.addOnsExcludes.get(i).get(j) == 1) {
                    wrapper.model.ifThen(
                        wrapper.model.arithm(wrapper.selectedAddOns[i], "=", 1),
                        wrapper.model.arithm(wrapper.selectedAddOns[j], "=", 0)
                    );
                }
            }
        }

        return true;
    }

    /**
     * Step 8.3: No two plans should be exactly the same.
     */
    private void addNoDuplicatePlansConstraint(ModelWrapper wrapper) {
        Model model = wrapper.model;
        int numPlans = wrapper.plans.size();

        for (int i = 0; i < numPlans; i++) {
            for (int j = i + 1; j < numPlans; j++) {
                // Boolean variable indicating if plans i and j are different
                BoolVar[] featureDifferences = new BoolVar[wrapper.features.size()];
                BoolVar[] usageLimitDifferences = new BoolVar[wrapper.usageLimits.size()];

                // Create difference constraints for features
                for (int k = 0; k < wrapper.features.size(); k++) {
                    featureDifferences[k] = model.boolVar("feature_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar((int) (wrapper.plansFeatures.get(i).get(k)*USAGE_LIMIT_SCALE)), "!=", model.intVar((int) (wrapper.plansFeatures.get(j).get(k)*USAGE_LIMIT_SCALE)))
                        .reifyWith(featureDifferences[k]);
                }

                // Create difference constraints for usage limits
                for (int k = 0; k < wrapper.usageLimits.size(); k++) {
                    usageLimitDifferences[k] = model.boolVar("usage_limit_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar((int) (wrapper.plansUsageLimits.get(i).get(k)*USAGE_LIMIT_SCALE)), 
                                "!=", 
                                (int)(wrapper.plansUsageLimits.get(j).get(k)*USAGE_LIMIT_SCALE))
                        .reifyWith(usageLimitDifferences[k]);
                }

                // Ensure at least one difference exists
                Constraint duplicates = model.or(ArrayUtils.append(featureDifferences, usageLimitDifferences));
                duplicates.setName("Plan " + wrapper.plans.get(i) + " and plan " + wrapper.plans.get(j) + " are exactly the same!");
                duplicates.post();
            }
        }
    }

    /**
     * Step 8.4: No two add-ons should be exactly the same.
     */
    private void addNoDuplicateAddOnsConstraint(ModelWrapper wrapper) {
        Model model = wrapper.model;
        int numAddOns = wrapper.addOns.size();

        for (int i = 0; i < numAddOns; i++) {
            for (int j = i + 1; j < numAddOns; j++) {
                // Boolean variables for checking differences
                BoolVar[] featureDifferences = new BoolVar[wrapper.features.size()];
                BoolVar[] usageLimitDifferences = new BoolVar[wrapper.usageLimits.size()];
                BoolVar[] usageLimitExtensionDifferences = new BoolVar[wrapper.usageLimits.size()];
                BoolVar[] availabilityDifferences = new BoolVar[wrapper.plans.size()];
                BoolVar[] dependencyDifferences = new BoolVar[wrapper.addOns.size()];
                BoolVar[] exclusionDifferences = new BoolVar[wrapper.addOns.size()];

                // Features
                for (int k = 0; k < wrapper.features.size(); k++) {
                    featureDifferences[k] = model.boolVar("addon_feature_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar((int)(wrapper.addOnsFeatures.get(i).get(k)*USAGE_LIMIT_SCALE)), "!=", (int)(wrapper.addOnsFeatures.get(j).get(k)*USAGE_LIMIT_SCALE))
                        .reifyWith(featureDifferences[k]);
                }

                // Usage Limits
                for (int k = 0; k < wrapper.usageLimits.size(); k++) {
                    usageLimitDifferences[k] = model.boolVar("addon_usage_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar((int)(wrapper.addOnsUsageLimits.get(i).get(k)*USAGE_LIMIT_SCALE)), 
                                "!=", 
                                model.intVar((int)(wrapper.addOnsUsageLimits.get(j).get(k)*USAGE_LIMIT_SCALE)))
                        .reifyWith(usageLimitDifferences[k]);
                }

                // Usage Limit Extensions
                for (int k = 0; k < wrapper.usageLimits.size(); k++) {
                    usageLimitExtensionDifferences[k] = model.boolVar("addon_usage_ext_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar((int) (wrapper.addOnsUsageLimitsExtension.get(i).get(k)*USAGE_LIMIT_SCALE)), 
                                "!=", 
                                model.intVar((int) (wrapper.addOnsUsageLimitsExtension.get(j).get(k)*USAGE_LIMIT_SCALE)))
                        .reifyWith(usageLimitExtensionDifferences[k]);
                }

                // Availability for plans
                for (int k = 0; k < wrapper.plans.size(); k++) {
                    availabilityDifferences[k] = model.boolVar("addon_avail_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar(wrapper.addOnsAvailableFor.get(i).get(k)), "!=", wrapper.addOnsAvailableFor.get(j).get(k))
                        .reifyWith(availabilityDifferences[k]);
                }

                // Dependencies
                for (int k = 0; k < wrapper.addOns.size(); k++) {
                    dependencyDifferences[k] = model.boolVar("addon_depends_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar(wrapper.addOnsDependsOn.get(i).get(k)), "!=", wrapper.addOnsDependsOn.get(j).get(k))
                        .reifyWith(dependencyDifferences[k]);
                }

                // Exclusions
                for (int k = 0; k < wrapper.addOns.size(); k++) {
                    exclusionDifferences[k] = model.boolVar("addon_exclude_diff_" + i + "_" + j + "_" + k);
                    model.arithm(model.intVar(wrapper.addOnsExcludes.get(i).get(k)), "!=", wrapper.addOnsExcludes.get(j).get(k))
                        .reifyWith(exclusionDifferences[k]);
                }

                // Ensure at least one difference exists
                Constraint duplicates = model.or(ArrayUtils.append(featureDifferences, usageLimitDifferences, 
                                        usageLimitExtensionDifferences, availabilityDifferences, 
                                        dependencyDifferences, exclusionDifferences));
                duplicates.setName("Add-On " + wrapper.addOns.get(i) + " and Add-On " + wrapper.addOns.get(j) + " are exactly the same!");
                duplicates.post();
            }
        }
    }


    /**
     * Step 9) Encode plan and add-on costs in the model, e.g. element constraints and cost summations.
     */
    private void encodePlanAndAddOnCosts(ModelWrapper wrapper) {
        Model model = wrapper.model;

        // 9.1) Plan cost = planPriceCents[selectedPlan]
        if (!wrapper.plans.isEmpty()) {
            model.element(wrapper.planPriceVar, wrapper.planPriceCents, wrapper.selectedPlan).post();
        } else {
            // If no plans exist, planPriceVar = 0
            model.arithm(wrapper.planPriceVar, "=", 0).post();
        }

        // 9.2) Each add-on cost = selectedAddOns[a] * addOnPriceCents[a]
        for (int a = 0; a < wrapper.addOns.size(); a++) {
            model.scalar(
                new IntVar[]{ wrapper.selectedAddOns[a] },
                new int[]   { wrapper.addOnPriceCents[a] },
                "=",
                wrapper.addOnCostVars[a]
            ).post();
        }

        // 9.3) Sum of add-ons costs
        IntVar totalAddOnsCost = model.intVar("totalAddOnsCost", 0, wrapper.UNLIMITED);
        model.sum(wrapper.addOnCostVars, "=", totalAddOnsCost).post();

        // 9.4) subscriptionCost = planPriceVar + totalAddOnsCost
        model.arithm(wrapper.subscriptionCost, "=", wrapper.planPriceVar, "+", totalAddOnsCost).post();
    }

    /**
     * Step 10) Solve the model and populate output with either the number of solutions or explanation if unsat.
     */
    private void solveModel(ModelWrapper wrapper, PricingManager pricingManager) {
        Solver solver = wrapper.model.getSolver();
        ExplanationEngine explEngine = new ExplanationEngine(wrapper.model, false, true);

        try {
            solver.propagate();
            List<Solution> allSolutions = solver.findAllSolutions();
            Set<SubscriptionItem> subscriptionItems = new HashSet<>();
            Set<Integer> reachableAddOns = new HashSet<>();
            Set<Integer> reachablePlans = new HashSet<>();
            
            for (Solution sol : allSolutions) {
                SubscriptionItem subscriptionItem = new SubscriptionItem();
                Subscription subscription = new Subscription();
                
                // Set plan
                if (!wrapper.plans.isEmpty()) {
                    int selectedPlanIndex = sol.getIntVal(wrapper.selectedPlan);
                    subscription.setPlan(wrapper.plans.get(selectedPlanIndex));
                    reachablePlans.add(selectedPlanIndex);
                }
                
                // Set add-ons
                List<String> selectedAddOnsList = new ArrayList<>();
                for(int i = 0; i < wrapper.selectedAddOns.length; i++) {
                    int addOn = sol.getIntVal(wrapper.selectedAddOns[i]);
                    if (addOn == 1) {
                        selectedAddOnsList.add(wrapper.addOns.get(i));
                        reachableAddOns.add(i);
                    }
                }
                subscription.setAddOns(selectedAddOnsList);
                
                // Set features - extract from solution based on plan and add-ons
                List<String> activeFeatures = new ArrayList<>();
                if (!wrapper.plans.isEmpty()) {
                    int planIndex = sol.getIntVal(wrapper.selectedPlan);
                    // Add features from selected plan
                    for (int f = 0; f < wrapper.features.size(); f++) {
                        if (wrapper.plansFeatures.get(planIndex).get(f) == 1.0) {
                            activeFeatures.add(wrapper.features.get(f));
                        }
                    }
                }
                // Add features from selected add-ons
                for(int i = 0; i < wrapper.selectedAddOns.length; i++) {
                    int addOn = sol.getIntVal(wrapper.selectedAddOns[i]);
                    if (addOn == 1) {
                        for (int f = 0; f < wrapper.features.size(); f++) {
                            if (wrapper.addOnsFeatures.get(i).get(f) == 1.0 && !activeFeatures.contains(wrapper.features.get(f))) {
                                activeFeatures.add(wrapper.features.get(f));
                            }
                        }
                    }
                }
                subscription.setFeatures(activeFeatures);
                
                // Set usage limits - extract from solution based on plan and add-ons
                List<Map<String, Double>> activeUsageLimits = new ArrayList<>();
                if (!wrapper.plans.isEmpty()) {
                    int planIndex = sol.getIntVal(wrapper.selectedPlan);
                    // Add usage limits from selected plan
                    for (int u = 0; u < wrapper.usageLimits.size(); u++) {
                        if (wrapper.plansUsageLimits.get(planIndex).get(u) > 0.0) {
                            String key = wrapper.usageLimits.get(u); 
                            Map<String, Double> activeUsageLimitMap = new HashMap<>();
                            activeUsageLimitMap.put(
                                key,
                                (Double) pricingManager.getPlans().values().stream()
                                    .filter(plan -> plan.getName().equals(wrapper.plans.get(planIndex)))
                                    .findFirst()
                                    .map(plan -> plan.getUsageLimits().values().stream()
                                        .filter(ul -> ul.getName().equals(key))
                                        .findFirst()
                                        .map(ul -> ul.getValue() != null ? Double.parseDouble(ul.getValue().toString()) : Double.parseDouble(ul.getDefaultValue().toString()))
                                        .orElse(null))
                                    .orElse(null)
                            );
                            if (activeUsageLimitMap.get(key) != null && activeUsageLimitMap.get(key) > 0.0) {
                                activeUsageLimits.add(activeUsageLimitMap);
                            }
                        }
                    }
                }

                // Add usage limits from selected add-ons
                for(int i = 0; i < wrapper.selectedAddOns.length; i++) {
                    final int addOnIndex = i;
                    int addOn = sol.getIntVal(wrapper.selectedAddOns[addOnIndex]);
                    if (addOn == 1) {
                        for (int u = 0; u < wrapper.usageLimits.size(); u++) {
                            if (wrapper.addOnsUsageLimits.get(addOnIndex).get(u) > 0.0) {
                                String key = wrapper.usageLimits.get(u);
                                Map<String, Double> activeUsageLimitMap = new HashMap<>();
                                activeUsageLimitMap.put(key, (double) pricingManager.getAddOns().values().stream()
                                    .filter(a -> a.getName().equals(wrapper.addOns.get(addOnIndex)))
                                    .findFirst()
                                    .map(a -> a.getUsageLimits().values().stream()
                                        .filter(ul -> ul.getName().equals(key))
                                        .findFirst()
                                        .map(ul -> ul.getValue() != null ? Double.parseDouble(ul.getValue().toString()) : Double.parseDouble(ul.getDefaultValue().toString()))
                                        .orElse(null))
                                    .orElse(null));
                                if (activeUsageLimitMap.get(key) != null && activeUsageLimitMap.get(key) > 0.0) {
                                    if (activeUsageLimits.stream().anyMatch(map -> map.keySet().equals(activeUsageLimitMap.keySet()))) {
                                        activeUsageLimits.removeIf(map -> map.keySet().equals(activeUsageLimitMap.keySet()));
                                    }
                                    activeUsageLimits.add(activeUsageLimitMap);
                                }
                            }
                            if (wrapper.addOnsUsageLimitsExtension.get(addOnIndex).get(u) > 0.0) {
                                String key = wrapper.usageLimits.get(u);
                                if (activeUsageLimits.stream().anyMatch(map -> map.containsKey(key))) {
                                    // If the usage limit is already present, update its value
                                    activeUsageLimits.stream()
                                        .filter(map -> map.containsKey(key))
                                        .forEach(map -> map.put(key, map.get(key) + pricingManager.getAddOns().values().stream()
                                            .filter(a -> a.getName().equals(wrapper.addOns.get(addOnIndex)))
                                            .findFirst()
                                            .map(a -> a.getUsageLimitsExtensions().get(key) != null ? Double.parseDouble(a.getUsageLimitsExtensions().get(key).getValue().toString()) : Double.parseDouble(a.getUsageLimits().get(key).getDefaultValue().toString()))
                                            .orElse(0.0)));
                                } else {
                                    // Otherwise, add a new entry
                                    Map<String, Double> activeUsageLimitMap = new HashMap<>();
                                    activeUsageLimitMap.put(key, pricingManager.getAddOns().values().stream()
                                        .filter(a -> a.getName().equals(wrapper.addOns.get(addOnIndex)))
                                        .findFirst()
                                        .map(a -> a.getUsageLimitsExtensions().get(key) != null ? Double.parseDouble(a.getUsageLimitsExtensions().get(key).getValue().toString()) : Double.parseDouble(a.getUsageLimits().get(key).getDefaultValue().toString()))
                                        .orElse(0.0));
                                    if (activeUsageLimitMap.get(key) != null && activeUsageLimitMap.get(key) > 0.0) {
                                        activeUsageLimits.add(activeUsageLimitMap);
                                    }
                                }
                            }
                        }
                    }
                }
                subscription.setUsageLimits(activeUsageLimits);

                // Set cost
                String cost = String.valueOf(sol.getIntVal(wrapper.subscriptionCost));
                subscriptionItem.setCost(cost);
                subscriptionItem.setSubscription(subscription);
                
                subscriptionItems.add(subscriptionItem);
            }
            
            int configurationSpace = subscriptionItems.size();
            ConfigurationSpace cs = new ConfigurationSpace();
            cs.setSubscriptions(subscriptionItems);
            wrapper.output.setConfigurationSpace(cs);
            wrapper.output.setModel(wrapper.model.toString());

            // Check if all add-ons are reachable
            List<String> unreachableAddOnsOrPlans = new ArrayList<>();
            for (int i = 0; i < wrapper.plans.size(); i++) {
                if(!reachablePlans.contains(i)){
                    unreachableAddOnsOrPlans.add("Plan '" + wrapper.plans.get(i) + "' is unreachable. It must be available for at least one configuration.");
                }
            }

            for (int i = 0; i < wrapper.selectedAddOns.length; i++) {
                if(!reachableAddOns.contains(i)){
                    unreachableAddOnsOrPlans.add("Add-On '" + wrapper.addOns.get(i) + "' is unreachable. It must be available for at least one configuration.");
                }
            }

            if (!unreachableAddOnsOrPlans.isEmpty()) {
                wrapper.output.setErrors(unreachableAddOnsOrPlans);
                wrapper.output.setMessageType(MessageType.UNSAT_ERROR);
            } else{  
                if (configurationSpace == 0) {
                    wrapper.output.setErrors(Collections.singletonList(
                        "Something went wrong, no valid configuration found. Please, check your iPricing carefully! A pricing must always provide one valid configuration to establish a subscription."));
                    wrapper.output.setMessageType(MessageType.UNSAT_ERROR);
                } else {
                    wrapper.output.setMessageType(MessageType.SUCCESS);
                }
            }
        } catch (ContradictionException e) {
            Explanation explanation = explEngine.explain(e);
            wrapper.output.setModel(wrapper.model.toString());
            wrapper.output.setMessageType(MessageType.UNSAT_ERROR);

            List<String> errors = new ArrayList<>();

            Set<String> uniqueConstraintNames = new HashSet<>();
            Set<String> uniqueDecisionNames = new HashSet<>();

            // Iterate over each element in the explanation.
            // Explanation is a set containing decisions and propagators.
            for (ICause cause : explanation.getCauses()) {
                if (cause instanceof Propagator) {
                    Propagator<?> propagator = (Propagator<?>) cause;
                    // Retrieve the associated constraint, if any.
                    Constraint constraint = propagator.getConstraint();
                    if (constraint != null) {
                        String name = constraint.getName();
                        if (name == null || name.isEmpty()) {
                            name = constraint.toString();
                        }
                        uniqueConstraintNames.add(name);
                    }
                } else if (cause instanceof Decision<?> decision) {
                    String name = decision.toString();
                    uniqueDecisionNames.add(name);
                }
            }
            
            // Add each unique constraint name to the errors list.
            for (String name : uniqueConstraintNames) {
                errors.add("Unsat constraint: " + name);
            }

            // Add each unique decision name to the errors list.
            for (String name : uniqueDecisionNames) {
                errors.add("Unsat decision: " + name);
            }
        
            
            wrapper.output.setErrors(errors);
        }

        // Clean up the model
        wrapper.model.getSolver().reset();
        wrapper.model = null;
    }

    // -------------------------------------------------------------------------
    // Below are the original list/matrix-building methods unchanged (apart from
    // potential minor code style improvements). They are used by fillListsAndMatrices().
    // -------------------------------------------------------------------------

    private List<String> featuresList(PricingManager pricingManager) {
        List<String> features = new ArrayList<>();
        if (pricingManager.getFeatures() == null) {
            return features;
        }
        for (var feature : pricingManager.getFeatures().values()) {
            features.add(feature.getName());
        }
        return features;
    }

    private List<String> usageLimitsList(PricingManager pricingManager) {
        List<String> usageLimits = new ArrayList<>();
        if (pricingManager.getUsageLimits() == null) {
            return usageLimits;
        }
        for (var usageLimit : pricingManager.getUsageLimits().values()) {
            usageLimits.add(usageLimit.getName());
        }
        return usageLimits;
    }

    private List<String> plansList(PricingManager pricingManager) {
        List<String> plans = new ArrayList<>();
        if (pricingManager.getPlans() == null) {
            return plans;
        }
        for (var plan : pricingManager.getPlans().values()) {
            plans.add(plan.getName());
        }
        return plans;
    }

    private List<String> addOnsList(PricingManager pricingManager) {
        List<String> addOns = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOns;
        }
        for (var addOn : pricingManager.getAddOns().values()) {
            addOns.add(addOn.getName());
        }
        return addOns;
    }

    private List<Double> plansPricesList(PricingManager pricingManager) {
        List<Double> plansPrices = new ArrayList<>();
        if (pricingManager.getPlans() == null) {
            return plansPrices;
        }
        for (var plan : pricingManager.getPlans().values()) {
            try {
                double p = Double.parseDouble(plan.getPrice().toString());
                plansPrices.add((p > BIGINT) ? (double) BIGINT : p);
            } catch (NumberFormatException e) {
                plansPrices.add((double) BIGINT);
            }
        }
        return plansPrices;
    }

    private List<Double> addOnsPricesList(PricingManager pricingManager) {
        List<Double> addOnsPrices = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsPrices;
        }
        for (var addOn : pricingManager.getAddOns().values()) {
            try {
                double p = Double.parseDouble(addOn.getPrice().toString());
                addOnsPrices.add((p > BIGINT) ? (double) BIGINT : p);
            } catch (NumberFormatException e) {
                addOnsPrices.add((double) BIGINT);
            }
        }
        return addOnsPrices;
    }

    private List<List<Integer>> linkedFeaturesMatrix(PricingManager pricingManager) {
        List<List<Integer>> linkedFeatures = new ArrayList<>();
        if (pricingManager.getUsageLimits() == null) {
            return linkedFeatures;
        }
        for (var usageLimit : pricingManager.getUsageLimits().values()) {
            List<Integer> row = new ArrayList<>();
            for (var feature : pricingManager.getFeatures().values()) {
                row.add(usageLimit.getLinkedFeatures() != null 
                        && usageLimit.getLinkedFeatures().contains(feature.getName()) ? 1 : 0);
            }
            linkedFeatures.add(row);
        }
        return linkedFeatures;
    }

    private List<List<Double>> plansFeaturesMatrix(PricingManager pricingManager, ModelWrapper wrapper) {
        List<List<Double>> plansFeatures = new ArrayList<>();
        if (pricingManager.getPlans() == null) {
            return plansFeatures;
        }
        for (var plan : pricingManager.getPlans().values()) {
            List<Double> row = new ArrayList<>();
            for (var feature : pricingManager.getFeatures().values()) {
                if (plan.getFeatures() != null && plan.getFeatures().get(feature.getName()) != null) {
                    // Evaluate plan features
                    if (plan.getFeatures().get(feature.getName()).getValue() == null) {
                        row.add(parseValue(plan.getFeatures().get(feature.getName()).getDefaultValue(), wrapper));
                    } else {
                        row.add(parseValue(plan.getFeatures().get(feature.getName()).getValue(), wrapper));
                    }
                } else {
                    row.add(0.0);
                }
            }
            plansFeatures.add(row);
        }
        return plansFeatures;
    }

    private List<List<Double>> plansUsageLimitsMatrix(PricingManager pricingManager, ModelWrapper wrapper) {
        List<List<Double>> plansUsageLimits = new ArrayList<>();
        if (pricingManager.getPlans() == null) {
            return plansUsageLimits;
        }

        if (pricingManager.getUsageLimits() == null) {
            return plansUsageLimits;
        }

        for (var plan : pricingManager.getPlans().values()) {
            List<Double> row = new ArrayList<>();
            for (var usageLimit : pricingManager.getUsageLimits().values()) {
                double usageLimitValue;
                boolean isBoolean = usageLimit.getValueType() == ValueType.BOOLEAN;
                if (plan.getUsageLimits() != null && plan.getUsageLimits().get(usageLimit.getName()) != null) {
                    if (plan.getUsageLimits().get(usageLimit.getName()).getValue() == null) {
                        usageLimitValue = parseValue(
                            plan.getUsageLimits().get(usageLimit.getName()).getDefaultValue(), wrapper);
                    } else {
                        usageLimitValue = parseValue(
                            plan.getUsageLimits().get(usageLimit.getName()).getValue(), wrapper);
                    }
                    if (isBoolean && usageLimitValue == 0.0) {
                        usageLimitValue = 2.0;
                    }
                    if (Double.isInfinite(usageLimitValue) || usageLimitValue > wrapper.MAX_PRICE_BOUND){
                        usageLimitValue = wrapper.MAX_PRICE_BOUND;
                    }
                } else {
                    usageLimitValue = 0.0;
                }
                row.add(usageLimitValue);
            }
            plansUsageLimits.add(row);
        }
        return plansUsageLimits;
    }

    private List<List<Double>> addOnsFeaturesMatrix(PricingManager pricingManager, ModelWrapper wrapper) {
        List<List<Double>> addOnsFeatures = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsFeatures;
        }
        for (var addOn : pricingManager.getAddOns().values()) {
            List<Double> row = new ArrayList<>();
            for (var feature : pricingManager.getFeatures().values()) {
                if (addOn.getFeatures() != null && addOn.getFeatures().get(feature.getName()) != null) {
                    if (addOn.getFeatures().get(feature.getName()).getValue() == null) {
                        row.add(parseValue(addOn.getFeatures().get(feature.getName()).getDefaultValue(), wrapper));
                    } else {
                        row.add(parseValue(addOn.getFeatures().get(feature.getName()).getValue(), wrapper));
                    }
                } else {
                    row.add(0.0);
                }
            }
            addOnsFeatures.add(row);
        }
        return addOnsFeatures;
    }

    private List<List<Double>> addOnsUsageLimitsMatrix(PricingManager pricingManager, ModelWrapper wrapper) {
        List<List<Double>> addOnsUsageLimits = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsUsageLimits;
        }

        if (pricingManager.getUsageLimits() == null) {
            return addOnsUsageLimits;
        }

        for (var addOn : pricingManager.getAddOns().values()) {
            List<Double> row = new ArrayList<>();
            for (var usageLimit : pricingManager.getUsageLimits().values()) {
                boolean isBoolean = usageLimit.getValueType() == ValueType.BOOLEAN;
                double val = 0.0;
                if (addOn.getUsageLimits() != null && addOn.getUsageLimits().get(usageLimit.getName()) != null) {
                    if (addOn.getUsageLimits().get(usageLimit.getName()).getValue() == null) {
                        val = parseValue(
                            addOn.getUsageLimits().get(usageLimit.getName()).getDefaultValue(), wrapper);
                    } else {
                        val = parseValue(
                            addOn.getUsageLimits().get(usageLimit.getName()).getValue(), wrapper);
                    }
                }
                if (isBoolean && val == 0.0) {
                    val = 2.0;
                }
                row.add(val);
            }
            addOnsUsageLimits.add(row);
        }
        return addOnsUsageLimits;
    }

    private List<List<Double>> addOnsUsageLimitsExtensionMatrix(PricingManager pricingManager, ModelWrapper wrapper) {
        List<List<Double>> addOnsUsageLimitsExtension = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsUsageLimitsExtension;
        }

        if (pricingManager.getUsageLimits() == null) {
            return addOnsUsageLimitsExtension;
        }

        for (var addOn : pricingManager.getAddOns().values()) {
            List<Double> row = new ArrayList<>();
            for (var usageLimit : pricingManager.getUsageLimits().values()) {
                boolean isBoolean = usageLimit.getValueType() == ValueType.BOOLEAN;
                double val = 0.0;
                if (addOn.getUsageLimitsExtensions() != null 
                    && addOn.getUsageLimitsExtensions().get(usageLimit.getName()) != null) {
                    if (addOn.getUsageLimitsExtensions().get(usageLimit.getName()).getValue() == null) {
                        val = parseValue(
                            addOn.getUsageLimitsExtensions().get(usageLimit.getName()).getDefaultValue(), wrapper);
                    } else {
                        val = parseValue(
                            addOn.getUsageLimitsExtensions().get(usageLimit.getName()).getValue(), wrapper);
                    }
                }
                if (isBoolean && val == 0.0) {
                    val = 2.0;
                }
                row.add(val);
            }
            addOnsUsageLimitsExtension.add(row);
        }
        return addOnsUsageLimitsExtension;
    }

    private List<List<Integer>> addOnsAvailableForMatrix(PricingManager pricingManager) {
        List<List<Integer>> addOnsAvailableFor = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsAvailableFor;
        }
        for (var addOn : pricingManager.getAddOns().values()) {
            List<Integer> row = new ArrayList<>();
            for (var plan : pricingManager.getPlans().values()) {
                row.add(addOn.getAvailableFor() != null && addOn.getAvailableFor().contains(plan.getName()) ? 1 : 0);
            }
            addOnsAvailableFor.add(row);
        }
        return addOnsAvailableFor;
    }

    private List<List<Integer>> addOnsDependsOnMatrix(PricingManager pricingManager) {
        List<List<Integer>> addOnsDependsOn = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsDependsOn;
        }
        for (var addOn : pricingManager.getAddOns().values()) {
            List<Integer> row = new ArrayList<>();
            for (var addOn2 : pricingManager.getAddOns().values()) {
                row.add(addOn.getDependsOn() != null && addOn.getDependsOn().contains(addOn2.getName()) ? 1 : 0);
            }
            addOnsDependsOn.add(row);
        }
        return addOnsDependsOn;
    }

    private List<List<Integer>> addOnsExcludesMatrix(PricingManager pricingManager) {
        List<List<Integer>> addOnsExcludes = new ArrayList<>();
        if (pricingManager.getAddOns() == null) {
            return addOnsExcludes;
        }
        for (var addOn : pricingManager.getAddOns().values()) {
            List<Integer> row = new ArrayList<>();
            for (var addOn2 : pricingManager.getAddOns().values()) {
                row.add(addOn.getExcludes() != null && addOn.getExcludes().contains(addOn2.getName()) ? 1 : 0);
            }
            addOnsExcludes.add(row);
        }
        return addOnsExcludes;
    }

    // Helper method to convert a value to a boolean
    private boolean toBoolean(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof String strValue) {
            return !strValue.isEmpty();
        }
        if (value instanceof Number number) {
            return number.doubleValue() > 0;
        }
        if (value instanceof Boolean boolValue) {
            return boolValue;
        }
        return true; // Consider all other types as true
    }

    private Double parseValue(Object value, ModelWrapper wrapper) {
        if (value == null) {
            return 0.0;
        }

        if (value instanceof Number number) {
            if (number.doubleValue() <= 0) {
                return 0.0;
            }
            if (number.doubleValue() >= wrapper.MAX_PRICE_BOUND) {
                return (double) wrapper.MAX_PRICE_BOUND/USAGE_LIMIT_SCALE;
            }
            if ((int) (number.doubleValue() * USAGE_LIMIT_SCALE) == 0  || Math.round(number.doubleValue()) == 0) {
                return 1.0;
            }
            return number.doubleValue();
        }

        if (value instanceof Boolean boolValue) {
            return Boolean.TRUE.equals(boolValue) ? 1.0 : 0.0; 
        }

        if (value instanceof String strValue) {
            return strValue.isEmpty() ? 0.0 : stringToNumber(strValue, wrapper);
        }

        String defaultValue = value.toString(); // Review this to check how it works for PAYMENT Features (specially how to dissable them when there is no payment for a plan)

        return defaultValue.isEmpty() ? 0.0 : stringToNumber(defaultValue, wrapper);
    }

    private Double stringToNumber(String value, ModelWrapper wrapper) {
        if (wrapper.stringValuesMap.containsKey(value)) {
            return wrapper.stringValuesMap.get(value);
        } else {
            Double number = (double) wrapper.stringValuesMap.keySet().size() + 1;
            wrapper.stringValuesMap.put(value, number);
            return number;
        }
    }

    // -------------------------------------------------------------------------
    // A small Wrapper class to hold all relevant model objects and data
    // -------------------------------------------------------------------------
    private static class ModelWrapper {
        Model model;
        CSPOutput output;

        // Constants
        int MAX_PRICE_BOUND;
        int CENTS_SCALE;
        int UNLIMITED;

        Map<String, Double> stringValuesMap;

        // Lists
        List<String> features;
        List<String> usageLimits;
        List<String> plans;
        List<String> addOns;

        List<Double> plansPrices;
        List<Double> addOnsPrices;

        // Matrices
        List<List<Integer>> linkedFeatures;
        List<List<Double>> plansFeatures;
        List<List<Double>> plansUsageLimits;
        List<List<Double>> addOnsFeatures;
        List<List<Double>> addOnsUsageLimits;
        List<List<Double>> addOnsUsageLimitsExtension;
        List<List<Integer>> addOnsAvailableFor;
        List<List<Integer>> addOnsDependsOn;
        List<List<Integer>> addOnsExcludes;

        // Price arrays
        int[] planPriceCents;
        int[] addOnPriceCents;

        // Choco variables
        IntVar selectedPlan;
        IntVar[] selectedAddOns;
        IntVar subscriptionCost;
        IntVar planPriceVar;
        IntVar[] addOnCostVars;
    }
}
