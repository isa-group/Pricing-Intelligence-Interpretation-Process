import { Request, Response } from 'express';
import { 
    JobCreationResponse, 
    GetJobDetailsResponse,
    JobStatusEnum,
    FilterCriteria,
} from '../types.js';
import MinizincService from '../services/minizinc.service.js';
import { Pricing } from 'pricing4ts';
import { retrievePricingFromPath } from 'pricing4ts/server';
import * as fs from 'fs';
import { randomUUID } from 'crypto';
import axios from 'axios';
import { calculateChocoSubscriptionCost, parseCurrency } from '../utils/dzn-exporter/number-utils.js';

// In-memory storage for jobs (replace with database in production)
const jobs: { [jobId: string]: any } = {};

/**
 * POST /pricing/analysis
 * Create a new pricing analysis job with uploaded YAML file
 */
export const createPricingAnalysisJob = (req: Request, res: Response) => {
    try {
        // Check if file was uploaded
        const file = (req as any).file;
        if (!file) {
            return res.status(400).json({ 
                error: 'Pricing YAML file is required. Please upload a file.' 
            });
        }

        // Extract form data from request body
        const { operation, solver, filters, objective } = req.body;

        // Validate required fields
        if (!operation || !solver) {
            return res.status(400).json({ 
                error: 'Missing required fields: operation and solver are required' 
            });
        }

        // Parse and validate YAML content from uploaded file
        let pricingData: Pricing = {
            saasName: '',
            syntaxVersion: '',
            version: '',
            createdAt: new Date(),
            currency: '',
            variables: {},
            features: {}
        };
        const pricingYamlContent = file.buffer.toString('utf8');
        
        // Store pricingYamlContent in a file yaml format
        // Generate a temporary file path
        const pricingUUID = `pricing-${randomUUID()}`;
        const tempFilePath = `/tmp/${pricingUUID}.yaml`;
        fs.writeFileSync(tempFilePath, pricingYamlContent);
        try {
            pricingData = retrievePricingFromPath(tempFilePath);
        } catch (yamlError) {
            if (solver !== 'choco' && operation !== 'validate') {
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
        }

        // Clean up temporary file after parsing
        fs.unlink(tempFilePath, (err) => {
            if (err) {
                console.error(`Failed to delete temporary file ${tempFilePath}:`, err);
            }
        });

        // Create job
        const jobId = `job-${randomUUID()}`;
        const submittedAt = new Date().toISOString();

        // Parse filters if provided
        let parsedFilters: FilterCriteria | undefined;
        if (filters) {
            try {
                parsedFilters = JSON.parse(filters);
            } catch (filterError) {
                return res.status(400).json({
                    error: 'Invalid filters format. Must be valid JSON.'
                });
            }
        }

        // if ((operation === 'optimal' || operation === 'filter') && !parsedFilters) {
        //     return res.status(400).json({
        //         error: 'Filters are required for optimal and filter operations'
        //     });
        // }

        jobs[jobId] = {
            // Store only metadata, not the full YAML content
            operation,
            solver,
            filters: parsedFilters,
            objective,
            status: 'PENDING' as JobStatusEnum,
            submittedAt
        };

        processJobAsync(jobId, pricingData, pricingYamlContent);

        const response: JobCreationResponse = {
            jobId,
            status: 'PENDING',
            submittedAt
        };

        res.status(202).json(response);

    } catch (error) {
        console.error('Error in createPricingAnalysisJob:', error);
        res.status(500).json({ 
            error: 'Internal server error during job submission',
            details: error instanceof Error ? error.message : 'Unknown error'
        });
    }
};

/**
 * GET /pricing/analysis/{jobId}
 * Get pricing analysis job status or result
 */
export const getPricingAnalysisJobStatusOrResult = (req: Request, res: Response) => {
    try {
        const { jobId } = req.params;
        const job = jobs[jobId];

        if (!job) {
            return res.status(404).json({ 
                error: 'Job not found' 
            });
        }

        const response: GetJobDetailsResponse = {
            jobId,
            status: job.status,
            submittedAt: job.submittedAt
        };

        // Add status-specific fields
        if (job.status === 'RUNNING' || job.status === 'COMPLETED' || job.status === 'FAILED') {
            (response as any).startedAt = job.startedAt;
        }

        if (job.status === 'COMPLETED') {
            (response as any).completedAt = job.completedAt;
            (response as any).result = job.result;
        }

        if (job.status === 'FAILED') {
            (response as any).failedAt = job.failedAt;
            (response as any).error = job.error;
        }

        res.status(200).json(response);

    } catch (error) {
        console.error('Error in getPricingAnalysisJobStatusOrResult:', error);
        res.status(500).json({ 
            error: 'Internal server error',
            details: error instanceof Error ? error.message : 'Unknown error'
        });
    }
};

/**
 * Process async job with real MinizincService operations
 */
const processJobAsync = async (jobId: string, pricingData: Pricing, pricingYamlContent: string) => {
    const job = jobs[jobId];
    if (!job) return;

    // Start job processing
    if (jobs[jobId] && jobs[jobId].status === 'PENDING') {
        jobs[jobId].status = 'RUNNING';
        jobs[jobId].startedAt = new Date().toISOString();
        
        try {
            const minizincService = new MinizincService(pricingData);
            let result: any;

            switch (job.operation) {
                case 'validate':
                    if (job.solver === 'minizinc') {
                        result = await _minizincValidate(minizincService, result);
                    } else if (job.solver === 'choco') {
                        result = await _chocoValidate(pricingYamlContent, result);
                    } else {
                        result = { error: 'Unsupported solver specified!' };
                    }
                    break;
                    
                case 'optimal':
                    if (job.solver === 'minizinc') {
                        const to_be_minimized = job.objective === 'minimize' ? true : false;
                        result = await _minizincOptimal(minizincService, job.filters, to_be_minimized, result);
                    } else if (job.solver === 'choco') {
                        result = { error: 'Choco solver is not implemented yet' };
                    } else {
                        result = { error: 'Unsupported solver specified!' };
                    }
                    break;
                    
                case 'subscriptions':
                    if (job.solver === 'minizinc') {
                        result = await _minizincSubscriptions(minizincService, result);
                    } else if (job.solver === 'choco') {
                        result = await _chocoSubscriptions(pricingData, pricingYamlContent, result);
                    } else {
                        result = { error: 'Unsupported solver specified!' };
                    }
                    break;
                    
                case 'filter':
                    if (job.solver === 'minizinc') {
                        result = await _minizincFilter(minizincService, job.filters, result);
                    } else if (job.solver === 'choco') {
                        result = { error: 'Choco solver is not implemented yet' };
                    } else {
                        result = { error: 'Unsupported solver specified!' };
                    }
                    break;
                    
                default:
                    result = { message: 'Unsupported operation!' };
            }

            // Mark job as completed
            if (jobs[jobId] && jobs[jobId].status === 'RUNNING') {
                jobs[jobId].status = 'COMPLETED';
                jobs[jobId].completedAt = new Date().toISOString();
                jobs[jobId].result = result;
            }

        } catch (error) {
            // Mark job as failed
            if (jobs[jobId] && jobs[jobId].status === 'RUNNING') {
                jobs[jobId].status = 'FAILED';
                jobs[jobId].failedAt = new Date().toISOString();
                jobs[jobId].error = {
                    message: error instanceof Error ? error.message : 'Unknown error occurred',
                    details: error instanceof Error ? error.stack : undefined
                };
            }
        }
    }
};

async function _minizincSubscriptions(minizincService: MinizincService, result: any) {
    try {
        const configSpace = await minizincService.getConfigurationSpace();
        result = {
            subscriptions: configSpace,
            cardinality: configSpace.length
        };
    } catch (error) {
        result = { subscriptions: [], cardinality: 0, error: error instanceof Error ? error.message : String(error)};
    }
    return result;
}

async function _minizincValidate(minizincService: MinizincService, result: any) {
    try {
        await minizincService.validatePricing();
        result = { valid: true };
    } catch (error) {
        result = {
            valid: false,
            error: error instanceof Error ? error.message : String(error)
        };
    }
    return result;
}
async function _minizincOptimal(minizincService: MinizincService, filters: FilterCriteria, to_be_minimized: boolean, result: any): Promise<any> {
    try {
        const optimal = await minizincService.getOptimalSubscription(filters, to_be_minimized);
        result = { optimal };
    } catch (error) {
        result = {
            error: error instanceof Error ? error.message : String(error)
        };
    }
    return result;
}

async function _minizincFilter(minizincService: MinizincService, filters: FilterCriteria, result: any): Promise<any> {
    try {
        const configSpace = await minizincService.getFilteredConfigurationSpace(filters);
        result = {
            subscriptions: configSpace,
            cardinality: configSpace.length
        };
    } catch (error) {
        result = {
            error: error instanceof Error ? error.message : String(error)
        };
    }
    return result;
}

async function _chocoValidate(pricingYamlContent: string, result: any): Promise<any> {
    const endpoint = process.env.CHOCO_API || 'http://localhost:8080';

    // File upload as multipart/form-data using axios
    const FormData = (await import('form-data')).default;
    const formData = new FormData();
    let uuid = randomUUID();
    fs.writeFileSync(`/tmp/${uuid}.yaml`, pricingYamlContent);
    formData.append('file', Buffer.from(pricingYamlContent), `${uuid}.yaml`);

    try {
        const response = await axios.post(`${endpoint}/validate`, formData, {
            headers: formData.getHeaders(),
        });
        if (response.data && response.data.messageType === 'SUCCESS') {
            result = { valid: true };
        } else {
            result = { valid: false, error: response.data?.errors || 'Unknown error' };
        }
    } catch (error: any) {
        // console.error('Choco validate error:', error);
        result = { valid: false, error: error?.response?.data?.errors || error?.message || 'Unknown error' };
    }

    fs.unlinkSync(`/tmp/${uuid}.yaml`);

    return result;
}

async function _chocoSubscriptions(pricingData: Pricing, pricingYamlContent: string, result: any): Promise<any> {
    const endpoint = process.env.CHOCO_API || 'http://localhost:8080';

    // File upload as multipart/form-data using axios
    const FormData = (await import('form-data')).default;
    const formData = new FormData();
    let uuid = randomUUID();
    fs.writeFileSync(`/tmp/${uuid}.yaml`, pricingYamlContent);
    formData.append('file', Buffer.from(pricingYamlContent), `${uuid}.yaml`);

    try {
        const response = await axios.post(`${endpoint}/validate`, formData, {
            headers: formData.getHeaders(),
        });
        if (response.data && response.data.messageType === 'SUCCESS') {
            result = { subscriptions: parseConfigurationSpacePrice(response.data.configurationSpace, pricingData), cardinality: response.data.configurationSpace.cardinality || 0 };
        } else {
            result = { subscriptions: [], error: response.data?.errors || 'Unknown error' };
        }
    } catch (error: any) {
        result = { subscriptions: [], error: error?.message || 'Unknown error' };
    }

    fs.unlinkSync(`/tmp/${uuid}.yaml`);

    return result;
}

function parseConfigurationSpacePrice(configurationSpace: { subscriptions: any[]; cardinality: number }, pricingData: Pricing): any[] {
    return configurationSpace.subscriptions.map((config: { subscription: {plan: string, addOns: string[], features: string[], usageLimits: object[]}; cost: any; }) => {
        const { cost, subscription } = config;
        let newCost = calculateChocoSubscriptionCost(pricingData, subscription);
        if (typeof newCost === 'number') {
            newCost = `${newCost} ${parseCurrency(pricingData.currency)}`;
        }
        return {
            ...subscription,
            cost: newCost
        };
    });
}