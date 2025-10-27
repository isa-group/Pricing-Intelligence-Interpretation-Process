package org.isa.pricing.csp.parser;

import java.io.IOException;
import java.io.InputStream;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.isa.pricing.csp.output.CSPOutput;
import org.isa.pricing.csp.output.MessageType;
import org.isa.pricing.csp.service.CSPService;
import org.springframework.web.multipart.MultipartFile;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.error.YAMLException;

import io.github.isagroup.exceptions.CloneFeatureException;
import io.github.isagroup.exceptions.CloneUsageLimitException;
import io.github.isagroup.exceptions.FeatureNotFoundException;
import io.github.isagroup.exceptions.FilepathException;
import io.github.isagroup.exceptions.InvalidAutomationTypeException;
import io.github.isagroup.exceptions.InvalidDefaultValueException;
import io.github.isagroup.exceptions.InvalidIntegrationTypeException;
import io.github.isagroup.exceptions.InvalidLinkedFeatureException;
import io.github.isagroup.exceptions.InvalidPlanException;
import io.github.isagroup.exceptions.InvalidValueTypeException;
import io.github.isagroup.exceptions.PricingParsingException;
import io.github.isagroup.exceptions.PricingPlanEvaluationException;
import io.github.isagroup.exceptions.SerializerException;
import io.github.isagroup.exceptions.UpdateException;
import io.github.isagroup.exceptions.VersionException;
import io.github.isagroup.models.PricingManager;
import io.github.isagroup.services.parsing.PricingManagerParser;
import io.github.isagroup.services.updaters.YamlUpdater;

public class Yaml2CSP {
    /**
     * Private constructor to hide the implicit public one.
     */
    private Yaml2CSP() {
        // Prevents instantiation
    }

    /**
     * Step 2) Reads the given MultipartFile as YAML, updates it, and attempts to parse into a PricingManager.
     *
     * @param file the uploaded YAML file
     * @return a Map containing either:
     *     - "pricingManager": the parsed object, if successful
     *     - "errors": a CSPOutput with error messages if something went wrong
     */
    public static Map<String, Object> retrievePricingFromYaml(MultipartFile file) {
        Yaml yaml = new Yaml();
        Map<String, Object> result = new HashMap<>();
        CSPOutput cspOutput = new CSPOutput();

        try (InputStream is = file.getInputStream()) {
            // 1) Load the YAML content into a Map
            Map<String, Object> configFile = yaml.load(is);

            // 2) Perform any expansions or conversions on the YAML
            YamlUpdater.update(configFile);

            // 3) Parse into your domain model
            PricingManager pricingManager = PricingManagerParser.parseMapToPricingManager(configFile);
            result.put("pricingManager", pricingManager);
        } catch (IOException e) {
            cspOutput.setErrors(Collections.singletonList(
                "FilePathError: Either the file path is invalid or the file does not exist."));
            cspOutput.setMessageType(MessageType.FILE_ERROR);
        } catch (FilepathException e) {
            cspOutput.setErrors(Collections.singletonList("FilepathException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.FILE_ERROR);
        } catch (YAMLException | UpdateException e){
            cspOutput.setErrors(Collections.singletonList("YAMLError: The YAML file is not in the correct format."));
            cspOutput.setMessageType(MessageType.YAML_ERROR);
        } catch (PricingParsingException e) {
            cspOutput.setErrors(Collections.singletonList("PricingParsingException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (PricingPlanEvaluationException e) {
            cspOutput.setErrors(Collections.singletonList("PricingPlanEvaluationException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (InvalidPlanException e) {
            cspOutput.setErrors(Collections.singletonList("InvalidPlanException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (CloneFeatureException e) {
            cspOutput.setErrors(Collections.singletonList("CloneFeatureException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (CloneUsageLimitException e) {
            cspOutput.setErrors(Collections.singletonList("CloneUsageLimitException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (FeatureNotFoundException e) {
            cspOutput.setErrors(Collections.singletonList("FeatureNotFoundException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (InvalidAutomationTypeException e) {
            cspOutput.setErrors(Collections.singletonList("InvalidAutomationTypeException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (InvalidDefaultValueException e) {
            cspOutput.setErrors(Collections.singletonList("InvalidDefaultValueException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (InvalidIntegrationTypeException e) {
            cspOutput.setErrors(Collections.singletonList("InvalidIntegrationTypeException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (InvalidLinkedFeatureException e) {
            cspOutput.setErrors(Collections.singletonList("InvalidLinkedFeatureException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (InvalidValueTypeException e) {
            cspOutput.setErrors(Collections.singletonList("InvalidValueTypeException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (VersionException e) {
            cspOutput.setErrors(Collections.singletonList("VersionException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (IllegalArgumentException e) {
            cspOutput.setErrors(Collections.singletonList("IllegalArgumentException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        } catch (SerializerException e) {
            cspOutput.setErrors(Collections.singletonList("SerializerException: " + e.getMessage()));
            cspOutput.setMessageType(MessageType.PARSER_ERROR);
        }

        // If an error occurred, put cspOutput in "errors"
        // Otherwise, "pricingManager" should already be in the map.
        result.put("errors", cspOutput);
        return result;
    }

    /**
     * Helper method to get the Path object of a YAML file in the resource folder.
    */
    private static Path getYamlPath(String receivedYamlPath) throws URISyntaxException {
        return Paths.get(CSPService.class.getClassLoader().getResource(receivedYamlPath).toURI());
    }
}