import request from 'supertest';
import { createApp } from '../src/app';
import { Application } from 'express';
import { describe, it, beforeEach, expect } from '@jest/globals';

describe('New Pricing API Endpoints (OpenAPI v2.0.0)', () => {
    let app: Application;

    beforeEach(() => {
        app = createApp();
    });

    describe('POST /pricing/summary', () => {
        it('should return pricing summary for valid YAML', async () => {
            const validYaml = `
plans:
  - name: BASIC
    price: 0
    features: [f1, f2]
  - name: PRO
    price: 50
    features: [f1, f2, f3, f4]
addOns:
  - name: XTRA
    price: 10
    availableFor: [BASIC, PRO]
            `;

            const response = await request(app)
                .post('/pricing/summary')
                .send({ pricingYamlContent: validYaml })
                .expect(200);

            expect(response.body).toHaveProperty('numberOfUniqueFeatures', 4);
            expect(response.body).toHaveProperty('numberOfPlans', 2);
            expect(response.body).toHaveProperty('numberOfAddOns', 1);
            expect(response.body).toHaveProperty('minPlanPrice', 0);
            expect(response.body).toHaveProperty('maxPlanPrice', 50);
        });

        it('should return 400 for missing pricingYamlContent', async () => {
            const response = await request(app)
                .post('/pricing/summary')
                .send({})
                .expect(400);

            expect(response.body).toHaveProperty('error');
            expect(response.body.error).toContain('pricingYamlContent is required');
        });

        it('should return 400 for invalid YAML syntax', async () => {
            const invalidYaml = `
plans:
  - name: BASIC
    price: [invalid yaml syntax
            `;

            const response = await request(app)
                .post('/pricing/summary')
                .send({ pricingYamlContent: invalidYaml })
                .expect(400);

            expect(response.body).toHaveProperty('error');
            expect(response.body.error).toContain('Invalid YAML syntax');
        });

        it('should return 422 for invalid pricing data structure', async () => {
            const invalidStructure = `
invalidField: value
            `;

            const response = await request(app)
                .post('/pricing/summary')
                .send({ pricingYamlContent: invalidStructure })
                .expect(422);

            expect(response.body).toHaveProperty('error');
            expect(response.body.error).toContain('Invalid pricing data structure');
        });
    });

    describe('POST /pricing/analysis', () => {
        it('should create analysis job for valid request', async () => {
            const validRequest = {
                pricingYamlContent: `
plans:
  - name: BASIC
    price: 0
    features: [f1, f2]
addOns: []
                `,
                operation: 'validate',
                solver: 'minizinc'
            };

            const response = await request(app)
                .post('/pricing/analysis')
                .send(validRequest)
                .expect(202);

            expect(response.body).toHaveProperty('jobId');
            expect(response.body).toHaveProperty('status', 'PENDING');
            expect(response.body).toHaveProperty('submittedAt');
            expect(response.body.jobId).toMatch(/^job-/);
        });

        it('should return 400 for missing required fields', async () => {
            const invalidRequest = {
                pricingYamlContent: 'plans: []',
                // missing operation and solver
            };

            const response = await request(app)
                .post('/pricing/analysis')
                .send(invalidRequest)
                .expect(400);

            expect(response.body).toHaveProperty('error');
            expect(response.body.error).toContain('Missing required fields');
        });

        it('should validate validate-subscription operation payload', async () => {
            const requestWithInvalidPayload = {
                pricingYamlContent: `
plans:
  - name: PRO
    price: 50
    features: [f1, f2]
addOns: []
                `,
                operation: 'validate-subscription',
                solver: 'ortools',
                jobPayload: {
                    plan: 'NONEXISTENT_PLAN'
                }
            };

            const response = await request(app)
                .post('/pricing/analysis')
                .send(requestWithInvalidPayload)
                .expect(400);

            expect(response.body).toHaveProperty('error');
            expect(response.body.error).toContain('not found in pricing configuration');
        });
    });

    describe('GET /pricing/analysis/:jobId', () => {
        it('should return 404 for non-existent job', async () => {
            const response = await request(app)
                .get('/pricing/analysis/non-existent-job')
                .expect(404);

            expect(response.body).toHaveProperty('error', 'Job not found');
        });

        it('should return job status for existing job', async () => {
            // First create a job
            const createResponse = await request(app)
                .post('/pricing/analysis')
                .send({
                    pricingYamlContent: 'plans:\n  - name: BASIC\n    price: 0\n    features: [f1]',
                    operation: 'validate',
                    solver: 'minizinc'
                });

            const jobId = createResponse.body.jobId;

            // Then get its status
            const statusResponse = await request(app)
                .get(`/pricing/analysis/${jobId}`)
                .expect(200);

            expect(statusResponse.body).toHaveProperty('jobId', jobId);
            expect(statusResponse.body).toHaveProperty('status');
            expect(statusResponse.body).toHaveProperty('submittedAt');
            expect(['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']).toContain(statusResponse.body.status);
        });
    });
});
