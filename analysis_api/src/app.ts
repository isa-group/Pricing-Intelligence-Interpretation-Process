import express, { Request, Response, NextFunction } from 'express';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import path from 'path';
import multer from 'multer';
import swaggerUi from 'swagger-ui-express';
import cors from 'cors';

// Import new route handlers
import { getPricingSummary } from './api/summary.js';
import { createPricingAnalysisJob, getPricingAnalysisJobStatusOrResult } from './api/analysis.js';

import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


export function createApp(): express.Application {
const app = express();
  // Set up CORS
  app.use(cors({
    origin: '*', // Allow all origins for simplicity; adjust as needed
  }));

  // Middleware
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Configure multer for file uploads
  const storage = multer.memoryStorage();
  const upload = multer({ storage: storage });

  // Load OpenAPI spec from YAML file for documentation purposes
  const openApiSpecPath = path.join(__dirname, 'openapi.yaml');
  const openApiSpec = yaml.load(fs.readFileSync(openApiSpecPath, 'utf8')) as any;

  // Serve Swagger UI at /api-docs
  app.use('/docs', swaggerUi.serve, swaggerUi.setup(openApiSpec, {
    explorer: true,
    customCss: '.swagger-ui .topbar { display: none }',
    customSiteTitle: 'Pricing Analysis API Documentation'
  }));

//   // Serve raw OpenAPI spec JSON at /api-docs/json
//   app.get('/api-docs/json', (req: Request, res: Response) => {
//       res.json(openApiSpec);
//   });

  // Health check endpoint (both with and without API version prefix for compatibility)
  app.get('/health', (req: Request, res: Response) => {
      res.status(200).json({ status: 'UP'});
  });
  
  app.get('/api/v1/health', (req: Request, res: Response) => {
      res.status(200).json({ status: 'UP'});
  });

  // NEW ENDPOINTS (OpenAPI v2.0.0 aligned)
  
  // POST /api/v1/pricing/summary - Get pricing summary from uploaded YAML file
  app.post('/api/v1/pricing/summary', upload.single('pricingFile'), getPricingSummary);
  
  // POST /api/v1/pricing/analysis - Create analysis job with uploaded YAML file
  app.post('/api/v1/pricing/analysis', upload.single('pricingFile'), createPricingAnalysisJob);
  
  // GET /api/v1/pricing/analysis/{jobId} - Get job status or result
  app.get('/api/v1/pricing/analysis/:jobId', getPricingAnalysisJobStatusOrResult);

  // Error handling middleware
  app.use((err: any, req: Request, res: Response, next: NextFunction) => {
      console.error(err.stack);
      res.status(err.status || 500).json({
          message: err.message || 'Internal server error',
          errors: err.errors
      });
  });

  // 404 handler
  app.use('*', (req: Request, res: Response) => {
      res.status(404).json({ message: 'Route not found' });
  });

  return app;
}
