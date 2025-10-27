# Analysis API - Pricing Configuration Analysis Service

The Analysis API is a specialized service built with Node.js and TypeScript that implements advanced pricing configuration analysis capabilities using constraint programming (Constraint Satisfaction Problem - CSP) with MiniZinc.

## 🎯 Main Features

### 🧮 Advanced CSP Engine
- **Constraint resolution**: Uses MiniZinc to solve complex constraint satisfaction problems
- **Multiple solvers**: Compatible with Choco and Minizinc
- **Exhaustive analysis**: Complete enumeration of configuration spaces
- **Optimization**: Search for optimal configurations according to specific criteria

### 📊 Analysis Capabilities
- **Specification validation**: Verification of iPricing YAML file coherence
- **Pricing summaries**: Automatic generation of statistics and metrics
- **Configuration spaces**: Calculation of all possible combinations
- **Smart filtering**: Search for configurations that meet specific criteria
- **Cost analysis**: Price calculation for specific configurations

### 🔧 Robust Architecture
- **RESTful API**: Well-documented endpoints following OpenAPI 3.0
- **Asynchronous operations**: Handling long jobs through background jobs
- **Strict validation**: Input and output validation with TypeScript schemas
- **Error handling**: Robust error treatment and detailed logging

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Analysis API                            │
├─────────────────────────────────────────────────────────────┤
│  Express.js + TypeScript                                   │
│  ├─ REST Endpoints                                          │
│  ├─ Validation middleware                                   │
│  ├─ Multer for file upload                                  │
│  └─ CORS and error handling                                 │
├─────────────────────────────────────────────────────────────┤
│  Business Services                                         │
│  ├─ MinizincService                                         │
│  ├─ JobManager                                              │
│  ├─ PricingValidator                                        │
│  └─ AnalyticsProcessor                                      │
├─────────────────────────────────────────────────────────────┤
│  MiniZinc Engine                                           │
│  ├─ CSP models in .mzn                                      │
│  ├─ YAML → DZN conversion                                   │
│  ├─ Solver execution                                        │
│  └─ Result post-processing                                  │
├─────────────────────────────────────────────────────────────┤
│  Storage                                                   │
│  ├─ Temporary YAML files                                    │
│  ├─ Jobs in progress                                        │
│  ├─ Analysis results                                        │
│  └─ Operation logs                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Installation and Configuration

### Local Development

```bash
# 1. Navigate to directory
cd analysis_api

# 2. Install dependencies
npm install

# 3. Configure environment variables
export NODE_ENV=development
export PORT=3000
export CHOCO_API=http://localhost:8000
export LOG_LEVEL=INFO

# 4. Run in development mode
npm run dev

# 5. Build for production
npm run build
npm start
```

### Using Docker

```bash
# Build image
docker build -t analysis-api .

# Run container
docker run -p 3000:3000 \
  -e NODE_ENV=production \
  -e CHOCO_API=http://choco-api:8000 \
  analysis-api
```

## 📋 API Endpoints

### Pricing Summary

**POST** `/api/v1/pricing/summary`

Gets a statistical summary of a pricing specification.

```bash
curl -X POST "http://localhost:3000/api/v1/pricing/summary" \
  -F "pricingFile=@my-pricing.yaml"
```

**Example response**:
```json
{
  "numberOfPlans": 3,
  "numberOfFeatures": 15,
  "numberOfAddOns": 5,
  "minPlanPrice": 10.0,
  "maxPlanPrice": 100.0,
  ... // Other statistical fields
}
```

### Configuration Analysis

**POST** `/api/v1/pricing/analysis`

Starts an asynchronous analysis job for a pricing specification.

```bash
curl -X POST "http://localhost:3000/api/v1/pricing/analysis" \
  -F "pricingFile=@my-pricing.yaml" \
  -F "operation=optimal" \
  -F "solver=minizinc" \
  -F "objective=minimize" \
  -F "filters={\"maxPrice\": 50, \"requiredFeatures\": [\"usuarios\"]}"
```

**Parameters**:
- `operation`: Type of analysis (`validate`, `optimal`, `subscriptions`, `filter`)
- `solver`: CSP solver to use (`minizinc`, `choco`)
- `objective`: Optimization objective (`minimize`, `maximize`)
- `filters`: Filtering criteria in JSON format

**Response**:
```json
{
  "jobId": "job_12345",
  "status": "PENDING"
}
```

### Job Status

**GET** `/api/v1/pricing/analysis/{jobId}`

Gets the status and results of an analysis job.

```bash
curl "http://localhost:3000/api/v1/pricing/analysis/job_12345"
```

**Possible responses**:

**In progress**:
```json
{
  "jobId": "job_12345",
  "status": "RUNNING"
}
```

**Completed**:
```json
{
  "jobId": "job_12345",
  "status": "COMPLETED",
  "results": {
    ... // Analysis results
  }
}
```

## 🔧 Available Analysis Types

### 1. Validation (`validate`)

Verifies the mathematical and logical coherence of a pricing specification.

**Checks performed**:
- Price consistency between plans
- Feature coherence between plans
- Add-on dependency validation
- Detection of impossible configurations

### 2. Optimal Configurations (`optimal`)

Finds the best configurations according to specific criteria.

**Optimization criteria**:
- Minimize/maximize total cost
- Maximize obtained features
- Optimize price-quality ratio
- Minimize number of necessary add-ons

### 3. Subscription Space (`subscriptions`)

Enumerates all possible and valid configurations.

**Information provided**:
- Complete list of configurations
- Cost of each configuration
- Included features
- Applicable add-ons

### 4. Filtering (`filter`)

Searches for configurations that meet specific criteria.

**Available filters**:
```typescript
interface FilterCriteria {
  maxPrice?: number;                        // Maximum price
  minPrice?: number;                        // Minimum price
  features?: string[];                      // Required features
  usageLimits?: Record<string, number>[];   // Usage limits per feature
}
```

### Health Checks

```bash
# Check service status
curl http://localhost:3000/health

# Expected response
{
  "status": "UP",
  "timestamp": "2024-01-15T10:30:00Z",
}
```

## 🔧 Advanced Configuration

### Environment Variables

```bash
# Basic configuration
NODE_ENV=production                    # Runtime environment
PORT=3000                             # Server port
LOG_LEVEL=info                        # Logging level

# External services
CHOCO_API=http://choco-api:8000       # Choco API URL
```


## 📚 Additional Resources

### API Documentation

- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc
- **OpenAPI Spec**: http://localhost:3000/api-docs/json

### Troubleshooting

Common problems and solutions:

1. **Insufficient memory**: Increase `NODE_OPTIONS="--max-old-space-size=X"` with desired memory size (in MB)
2. **Invalid YAML file**: Verify with validation endpoint

