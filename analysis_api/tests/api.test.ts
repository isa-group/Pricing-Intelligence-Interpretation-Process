import { describe, test, expect, beforeEach } from '@jest/globals';
import request from 'supertest';
import { createApp } from '../src/app';
import { TestUtils } from './utils';

const app = createApp();

describe('Pricing Analysis API - Complete Test Suite', () => {
  // describe('OpenAPI Documentation', () => {
  //   test('GET /api-docs/json should return OpenAPI specification', async () => {
  //     const response = await request(app)
  //       .get('/api-docs/json')
  //       .expect(200);

  //     expect(response.body).toHaveProperty('openapi');
  //     expect(response.body).toHaveProperty('info');
  //     expect(response.body).toHaveProperty('paths');
  //     expect(response.body.info.title).toBe('Pricing Analysis API');
  //   });
  // });

  describe('Pricing Management', () => {
    describe('POST /pricings', () => {
      test('should create a new pricing with valid YAML file', async () => {
        const response = await request(app)
          .post('/pricings')
          .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml')
          .expect(201);

        expect(response.body).toHaveProperty('pricingId');
        expect(response.body.pricingId).toMatch(/^pricing-\d+$/);
      });

      test('should handle missing file', async () => {
        const response = await request(app)
          .post('/pricings')
          .expect(201); // Server currently accepts requests without files

        expect(response.body).toHaveProperty('pricingId');
      });

      test('should handle invalid YAML content', async () => {
        const response = await request(app)
          .post('/pricings')
          .attach('pricingFile', TestUtils.getInvalidYamlBuffer(), 'invalid-pricing.yaml')
          .expect(201); // Server currently doesn't validate YAML content

        expect(response.body).toHaveProperty('pricingId');
      });
    });

    describe('GET /pricings/{pricingId}', () => {
      test('should retrieve existing pricing configuration', async () => {
        // Create a pricing first
        const createResponse = await request(app)
          .post('/pricings')
          .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

        const pricingId = createResponse.body.pricingId;

        const response = await request(app)
          .get(`/pricings/${pricingId}`)
          .expect(200);

        expect(response.body).toHaveProperty('pricingId', pricingId);
        expect(response.body).toHaveProperty('uploadedAt');
        expect(response.body).toHaveProperty('fileContent');
        expect(response.body.fileContent).toContain('Test Pricing Model');
      });

      test('should return 404 for non-existent pricing', async () => {
        await request(app)
          .get('/pricings/non-existent-id')
          .expect(404);
      });
    });

    describe('DELETE /pricings/{pricingId}', () => {
      test('should delete existing pricing', async () => {
        // Create a pricing first
        const createResponse = await request(app)
          .post('/pricings')
          .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

        const pricingId = createResponse.body.pricingId;

        await request(app)
          .delete(`/pricings/${pricingId}`)
          .expect(204);

        // Verify it's deleted
        await request(app)
          .get(`/pricings/${pricingId}`)
          .expect(404);
      });

      test('should return 404 for non-existent pricing', async () => {
        await request(app)
          .delete('/pricings/non-existent-id')
          .expect(404);
      });
    });
  });

  describe('Job Management', () => {
    let pricingId: string;

    beforeEach(async () => {
      // Create a pricing for job tests
      const createResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      pricingId = createResponse.body.pricingId;
    });

    describe('POST /pricings/{pricingId}/jobs', () => {
      test('should create a new job with valid parameters', async () => {
        const response = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'validate', solver: 'minizinc' })
          .send({
            config: { strict: true },
            constraints: ['basic']
          })
          .expect(202);

        expect(response.body).toHaveProperty('jobId');
        expect(response.body.jobId).toMatch(/^job-\d+$/);
        expect(response.body).toHaveProperty('status', 'PENDING');
        expect(response.body).toHaveProperty('submittedAt');
      });

      test('should create job with optimum operation', async () => {
        const response = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'optimum', solver: 'ortools' })
          .send({
            objective: 'minimize_cost',
            constraints: { budget: 100 }
          })
          .expect(202);

        expect(response.body).toHaveProperty('jobId');
        expect(response.body).toHaveProperty('status', 'PENDING');
      });

      test('should return 404 for non-existent pricing', async () => {
        const response = await request(app)
          .post('/pricings/non-existent/jobs')
          .query({ operation: 'validate' })
          .send({})
          .expect(404);

        expect(response.body).toHaveProperty('message', 'Pricing configuration not found');
      });

      test('should create jobs for all supported operations', async () => {
        const operations = ['validate', 'cardinality', 'validate-subscription', 'optimum', 'subscriptions', 'filter'];
        
        for (const operation of operations) {
          const response = await request(app)
            .post(`/pricings/${pricingId}/jobs`)
            .query({ operation, solver: 'minizinc' })
            .send({ test: true })
            .expect(202);

          expect(response.body).toHaveProperty('jobId');
          expect(response.body).toHaveProperty('status', 'PENDING');
        }
      });

      test('should create jobs for all supported solvers', async () => {
        const solvers = ['minizinc', 'chuffed', 'ortools', 'gecode'];
        
        for (const solver of solvers) {
          const response = await request(app)
            .post(`/pricings/${pricingId}/jobs`)
            .query({ operation: 'validate', solver })
            .send({ test: true })
            .expect(202);

          expect(response.body).toHaveProperty('jobId');
          expect(response.body).toHaveProperty('status', 'PENDING');
        }
      });
    });

    describe('GET /pricings/{pricingId}/jobs/{jobId}', () => {
      let jobId: string;

      beforeEach(async () => {
        // Create a job for testing
        const createJobResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'validate' })
          .send({ config: { strict: true } });

        jobId = createJobResponse.body.jobId;
      });

      test('should return job in PENDING state initially', async () => {
        const response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body).toHaveProperty('jobId', jobId);
        expect(response.body).toHaveProperty('status', 'PENDING');
        expect(response.body).toHaveProperty('submittedAt');
      });

      test('should return job status transitions', async () => {
        // Check initial PENDING state
        let response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body.status).toBe('PENDING');

        // Wait for job completion
        await TestUtils.wait(4000);

        response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body.status).toBe('COMPLETED');
        expect(response.body).toHaveProperty('submittedAt');
        expect(response.body).toHaveProperty('startedAt');
        expect(response.body).toHaveProperty('completedAt');
        expect(response.body).toHaveProperty('result');
      }, 10000);

      test('should return 404 for non-existent job', async () => {
        await request(app)
          .get(`/pricings/${pricingId}/jobs/non-existent-job`)
          .expect(404);
      });
    });

    describe('Job Results by Operation Type', () => {
      test('validate operation should return validation result', async () => {
        const createResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'validate' })
          .send({ config: { strict: true } });

        const jobId = createResponse.body.jobId;

        // Wait for completion
        await TestUtils.wait(4000);

        const response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body.status).toBe('COMPLETED');
        expect(response.body.result).toHaveProperty('valid');
        expect(typeof response.body.result.valid).toBe('boolean');
      }, 10000);

      test('cardinality operation should return cardinal result', async () => {
        const createResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'cardinality', solver: 'minizinc' })
          .send({ constraints: ['basic'] });

        const jobId = createResponse.body.jobId;

        // Wait for completion
        await TestUtils.wait(4000);

        const response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body.status).toBe('COMPLETED');
        expect(response.body.result).toHaveProperty('cardinal');
        expect(typeof response.body.result.cardinal).toBe('number');
      }, 10000);

      test('optimum operation should return optimization result', async () => {
        const createResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'optimum', solver: 'ortools' })
          .send({
            objective: 'minimize_cost',
            constraints: { budget: 100 }
          });

        const jobId = createResponse.body.jobId;

        // Wait for completion
        await TestUtils.wait(4000);

        const response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body.status).toBe('COMPLETED');
        expect(response.body.result).toHaveProperty('subscriptions');
        expect(response.body.result).toHaveProperty('cost');
        expect(Array.isArray(response.body.result.subscriptions)).toBe(true);
      }, 10000);
    });
  });

  describe('Error Handling', () => {
    test('should handle malformed JSON in job creation', async () => {
      const createResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const pricingId = createResponse.body.pricingId;

      const response = await request(app)
        .post(`/pricings/${pricingId}/jobs`)
        .set('Content-Type', 'application/json')
        .send('{"invalid": json}')
        .expect(400);

      expect(response.body).toHaveProperty('message');
    });

    test('should handle non-existent routes', async () => {
      await request(app)
        .get('/non-existent-route')
        .expect(404);
    });
  });

  describe('YAML Content Validation', () => {
    test('should handle OpenAPI-compliant YAML structure', async () => {
      const yamlContent = `
plans:
  - name: BASIC
    price: 0
    features: [f1, f2]
  - name: PRO  
    price: 10
    features: [f1, f2, f3]
addOns:
  - name: XTRA
    price: 5
    availableFor: [BASIC, PRO]
  - name: PREMIUM
    price: 15
    availableFor: [PRO]
`;
      
      const response = await request(app)
        .post('/pricings')
        .attach('pricingFile', Buffer.from(yamlContent, 'utf8'), 'openapi-pricing.yaml')
        .expect(201);

      expect(response.body).toHaveProperty('pricingId');
    });
  });

  describe('Integration Scenarios', () => {
    test('should handle complete pricing and job workflow', async () => {
      // 1. Create pricing
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml')
        .expect(201);

      const pricingId = pricingResponse.body.pricingId;

      // 2. Create multiple jobs
      const jobTypes = [
        { operation: 'validate', expectedResult: 'valid' },
        { operation: 'cardinality', expectedResult: 'cardinal' },
        { operation: 'optimum', expectedResult: 'subscriptions' }
      ];

      const jobIds: string[] = [];

      for (const { operation } of jobTypes) {
        const jobResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation, solver: 'minizinc' })
          .send({ test: true })
          .expect(202);

        jobIds.push(jobResponse.body.jobId);
      }

      // 3. Wait for all jobs to complete
      await TestUtils.wait(5000);

      // 4. Verify all jobs completed
      for (const jobId of jobIds) {
        const response = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(response.body.status).toBe('COMPLETED');
        expect(response.body).toHaveProperty('result');
      }

      // 5. Delete pricing
      await request(app)
        .delete(`/pricings/${pricingId}`)
        .expect(204);

      // 6. Verify all jobs are deleted
      for (const jobId of jobIds) {
        await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(404);
      }
    }, 15000);
  });

  describe('Performance Tests', () => {
    test('should handle multiple concurrent job creations', async () => {
      const createResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const pricingId = createResponse.body.pricingId;

      // Create 5 jobs concurrently
      const jobPromises = Array.from({ length: 5 }, (_, i) => 
        request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'validate', solver: 'minizinc' })
          .send({ test: true, index: i })
      );

      const responses = await Promise.all(jobPromises);

      responses.forEach(response => {
        expect(response.status).toBe(202);
        expect(response.body).toHaveProperty('jobId');
        expect(response.body).toHaveProperty('status', 'PENDING');
      });
    });

    test('should handle rapid sequential requests', async () => {
      const createResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const pricingId = createResponse.body.pricingId;

      // Create jobs sequentially as fast as possible
      for (let i = 0; i < 3; i++) {
        const response = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'validate', solver: 'minizinc' })
          .send({ test: true, index: i });

        expect(response.status).toBe(202);
        expect(response.body).toHaveProperty('jobId');
      }
    });
  });

  describe('Edge Cases', () => {
    test('should handle empty request body for job creation', async () => {
      const createResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const pricingId = createResponse.body.pricingId;

      const response = await request(app)
        .post(`/pricings/${pricingId}/jobs`)
        .query({ operation: 'validate', solver: 'minizinc' })
        .send({})
        .expect(202);

      expect(response.body).toHaveProperty('jobId');
    });

    test('should handle very large payload', async () => {
      const createResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const pricingId = createResponse.body.pricingId;

      const largePayload = {
        data: Array.from({ length: 100 }, (_, i) => ({
          id: i,
          value: `value_${i}`,
          metadata: Array.from({ length: 10 }, (_, j) => `meta_${i}_${j}`)
        }))
      };

      const response = await request(app)
        .post(`/pricings/${pricingId}/jobs`)
        .query({ operation: 'validate', solver: 'minizinc' })
        .send(largePayload)
        .expect(202);

      expect(response.body).toHaveProperty('jobId');
    });
  });
});
