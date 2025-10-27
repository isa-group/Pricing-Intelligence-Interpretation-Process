import { describe, test, expect } from '@jest/globals';
import request from 'supertest';
import { createApp } from '../src/app';
import { TestUtils } from './utils';

const app = createApp();

describe('OpenAPI Integration Tests', () => {
  describe('Complete Workflow Integration', () => {
    test('should handle complete pricing lifecycle with multiple jobs', async () => {
      // 1. Create pricing using buffer instead of file
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml')
        .expect(201);

      const pricingId = pricingResponse.body.pricingId;
      expect(pricingId).toMatch(/^pricing-\d+$/);

      // 2. Verify pricing exists and has correct content
      const getResponse = await request(app)
        .get(`/pricings/${pricingId}`)
        .expect(200);

      expect(getResponse.body.fileContent).toContain('Test Pricing Model');

      // 3. Create multiple jobs of different types
      const jobs: string[] = [];
      
      // Validation job
      const validateJob = await request(app)
        .post(`/pricings/${pricingId}/jobs`)
        .query({ operation: 'validate' })
        .send({ config: { strict: true } })
        .expect(202);
      jobs.push(validateJob.body.jobId);

      // Cardinality job
      const cardinalityJob = await request(app)
        .post(`/pricings/${pricingId}/jobs`)
        .query({ operation: 'cardinality', solver: 'z3' })
        .send({ constraints: ['basic'] })
        .expect(202);
      jobs.push(cardinalityJob.body.jobId);

      // Optimum job
      const optimumJob = await request(app)
        .post(`/pricings/${pricingId}/jobs`)
        .query({ operation: 'optimum', solver: 'cbc' })
        .send({ objective: 'minimize_cost', constraints: { budget: 100 } })
        .expect(202);
      jobs.push(optimumJob.body.jobId);

      // 4. Wait for all jobs to complete
      await TestUtils.wait(5000);

      // 5. Verify all jobs completed successfully
      for (const jobId of jobs) {
        const jobResponse = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);

        expect(jobResponse.body.status).toBe('COMPLETED');
        expect(jobResponse.body).toHaveProperty('result');
      }

      // 6. Delete pricing (should also delete all jobs)
      await request(app)
        .delete(`/pricings/${pricingId}`)
        .expect(204);

      // 7. Verify pricing and jobs are gone
      await request(app)
        .get(`/pricings/${pricingId}`)
        .expect(404);

      for (const jobId of jobs) {
        await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(404);
      }
    }, 15000);

    test('should handle concurrent job creation and monitoring', async () => {
      // Create pricing
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');
      const pricingId = pricingResponse.body.pricingId;

      // Create multiple jobs concurrently
      const jobPromises: Promise<any>[] = [];
      for (let i = 0; i < 5; i++) {
        jobPromises.push(
          request(app)
            .post(`/pricings/${pricingId}/jobs`)
            .query({ operation: 'validate' })
            .send({ config: { strict: true, iteration: i } })
        );
      }

      const jobResponses: any[] = await Promise.all(jobPromises);
      const jobIds: string[] = jobResponses.map(res => res.body.jobId);

      // Verify all jobs were created
      expect(jobIds).toHaveLength(5);
      jobIds.forEach(jobId => {
        expect(jobId).toMatch(/^job-\d+$/);
      });

      // Monitor jobs until completion
      await TestUtils.wait(5000);

      // Verify all completed
      for (const jobId of jobIds) {
        const jobResponse = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobId}`)
          .expect(200);
        expect(jobResponse.body.status).toBe('COMPLETED');
      }
    }, 15000);
  });

  describe('OpenAPI Specification Compliance', () => {
    test('should return proper HTTP status codes for all endpoints', async () => {
      // Test all defined status codes from OpenAPI spec
      
      // 201 for POST /pricings
      await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml')
        .expect(201);

      // 404 for non-existent resources
      await request(app)
        .get('/pricings/non-existent')
        .expect(404);

      await request(app)
        .delete('/pricings/non-existent')
        .expect(404);

      await request(app)
        .post('/pricings/non-existent/jobs')
        .query({ operation: 'validate' })
        .send({})
        .expect(404);

      await request(app)
        .get('/pricings/any/jobs/non-existent')
        .expect(404);

      // 202 for job creation
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');
      
      await request(app)
        .post(`/pricings/${pricingResponse.body.pricingId}/jobs`)
        .query({ operation: 'validate' })
        .send({})
        .expect(202);

      // 204 for successful deletion
      await request(app)
        .delete(`/pricings/${pricingResponse.body.pricingId}`)
        .expect(204);
    });

    test('should handle all operation types defined in OpenAPI spec', async () => {
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');
      const pricingId = pricingResponse.body.pricingId;

      // Test all operation types from the OpenAPI spec
      const operations = [
        { operation: 'validate', expectedResult: 'valid' },
        { operation: 'cardinality', expectedResult: 'cardinal' },
        { operation: 'optimum', expectedResult: 'subscriptions' }
      ];

      for (const { operation, expectedResult } of operations) {
        const jobResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation, solver: 'z3' })
          .send({ test: true })
          .expect(202);

        // Wait for completion
        await TestUtils.wait(4000);

        const resultResponse = await request(app)
          .get(`/pricings/${pricingId}/jobs/${jobResponse.body.jobId}`)
          .expect(200);

        expect(resultResponse.body.status).toBe('COMPLETED');
        expect(resultResponse.body.result).toHaveProperty(expectedResult);
      }
    }, 20000);

    test('should handle all solver types defined in OpenAPI spec', async () => {
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');
      const pricingId = pricingResponse.body.pricingId;

      // Test different solver types
      const solvers = ['z3', 'cbc', 'choco'];

      for (const solver of solvers) {
        const jobResponse = await request(app)
          .post(`/pricings/${pricingId}/jobs`)
          .query({ operation: 'cardinality', solver })
          .send({ constraints: ['basic'] })
          .expect(202);

        expect(jobResponse.body.jobId).toMatch(/^job-\d+$/);
      }
    });
  });

  describe('Error Boundary Testing', () => {
    test('should handle edge cases gracefully', async () => {
      // Test with empty pricing ID
      await request(app)
        .get('/pricings/')
        .expect(404);

      // Test with malformed pricing ID
      await request(app)
        .get('/pricings/invalid-id-format')
        .expect(404);

      // Test job creation without operation parameter
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const jobResponse = await request(app)
        .post(`/pricings/${pricingResponse.body.pricingId}/jobs`)
        .send({})
        .expect(202); // Server accepts without operation

      expect(jobResponse.body.jobId).toMatch(/^job-\d+$/);
    });

    test('should handle large payloads', async () => {
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      // Create job with large payload
      const largePayload = {
        constraints: Array(1000).fill({ type: 'test', value: Math.random() }),
        metadata: 'x'.repeat(10000)
      };

      const jobResponse = await request(app)
        .post(`/pricings/${pricingResponse.body.pricingId}/jobs`)
        .query({ operation: 'validate' })
        .send(largePayload)
        .expect(202);

      expect(jobResponse.body.jobId).toMatch(/^job-\d+$/);
    });
  });

  describe('Performance and Timing Tests', () => {
    test('should handle rapid sequential requests', async () => {
      const startTime = Date.now();
      
      // Create multiple pricings rapidly
      const promises: Promise<any>[] = [];
      for (let i = 0; i < 10; i++) {
        promises.push(
          request(app)
            .post('/pricings')
            .attach('pricingFile', TestUtils.getTestYamlBuffer(), `test-pricing-${i}.yaml`)
        );
      }

      const responses: any[] = await Promise.all(promises);
      const endTime = Date.now();

      // All should succeed
      responses.forEach(response => {
        expect(response.status).toBe(201);
        expect(response.body.pricingId).toMatch(/^pricing-\d+$/);
      });

      // Should complete reasonably quickly
      expect(endTime - startTime).toBeLessThan(5000);
    }, 10000);

    test('should respect job timing constraints', async () => {
      const pricingResponse = await request(app)
        .post('/pricings')
        .attach('pricingFile', TestUtils.getTestYamlBuffer(), 'test-pricing.yaml');

      const jobResponse = await request(app)
        .post(`/pricings/${pricingResponse.body.pricingId}/jobs`)
        .query({ operation: 'validate' })
        .send({});

      const jobId = jobResponse.body.jobId;
      const startTime = Date.now();

      // Job should be PENDING immediately
      const initialStatus = await request(app)
        .get(`/pricings/${pricingResponse.body.pricingId}/jobs/${jobId}`);
      expect(initialStatus.body.status).toBe('PENDING');

      // Wait and check RUNNING state (should happen around 1 second)
      await TestUtils.wait(1200);
      const runningStatus = await request(app)
        .get(`/pricings/${pricingResponse.body.pricingId}/jobs/${jobId}`);
      expect(['RUNNING', 'COMPLETED']).toContain(runningStatus.body.status);

      // Wait and check COMPLETED state (should happen around 3 seconds total)
      await TestUtils.wait(2500);
      const completedStatus = await request(app)
        .get(`/pricings/${pricingResponse.body.pricingId}/jobs/${jobId}`);
      expect(completedStatus.body.status).toBe('COMPLETED');

      const totalTime = Date.now() - startTime;
      expect(totalTime).toBeGreaterThan(2500); // Should take at least 2.5 seconds
      expect(totalTime).toBeLessThan(5000); // But not more than 5 seconds
    }, 10000);
  });
});
