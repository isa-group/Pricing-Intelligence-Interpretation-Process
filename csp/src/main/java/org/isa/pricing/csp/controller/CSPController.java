package org.isa.pricing.csp.controller;

import org.isa.pricing.csp.output.CSPOutput;
import org.isa.pricing.csp.output.MessageType;
import org.isa.pricing.csp.service.CSPService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.bind.annotation.RequestParam;


@RestController
public class CSPController {

    private final CSPService cspService;

    public CSPController(CSPService cspService) {
        this.cspService = cspService;
    }

    /**
     * POST endpoint to solve CSP from an uploaded YAML file.
     * 
     * Usage: 
     *   curl -v -F file=@/path/to/yourfile.yml http(s)://your-host/validate
     * 
     * @param file the YAML file provided by the client
     * @return CSPOutput with solver results or errors
     */
    @PostMapping("/validate")
    public ResponseEntity<CSPOutput> solveCSP(@RequestParam("file") MultipartFile file) {
        CSPOutput output = cspService.solveCSP(file);
        if (output.getMessageType() == MessageType.SUCCESS) {
            return ResponseEntity.ok(output);
        } else {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(output);
        }
    }
}
