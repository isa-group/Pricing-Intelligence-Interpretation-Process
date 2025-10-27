# A-MINT: Automated Modeling of iPricings from Natural Text

[![License](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

A-MINT is an advanced artificial intelligence platform that automates the extraction, analysis, and transformation of SaaS pricing information from natural web pages into structured specifications in iPricing YAML format. The system combines advanced web scraping techniques, natural language processing (NLP), and analysis with constraint satisfaction problem (CSP) algorithms to offer a complete pricing management and intelligence solution.

## 🎯 Main Features

### 🤖 Intelligent AI Processing
- **Automated extraction**: Conversion of pricing pages in natural language to structured iPricing YAML specifications
- **Multiple AI providers**: Compatible with OpenAI, Gemini, Azure OpenAI and other OpenAI-compatible providers
- **Intelligent validation**: Automatic verification and correction of iPricing specifications
- **Semantic alignment**: Validation that generated specifications maintain coherence with original content

### 🔍 Advanced Pricing Analysis
- **CSP Engine (Constraint Satisfaction Problem)**: Mathematical analysis of pricing configurations using MiniZinc/Choco
- **Configuration space**: Complete enumeration of all possible combinations of plans and add-ons
- **Subscription optimization**: Identification of optimal configurations according to specific criteria
- **Smart filtering**: Search for configurations that meet specific requirements

### 🌐 Microservices Architecture
- **A-MINT API**: Main pricing transformation engine
- **Analysis API**: Specialized service for configuration analysis and validation
- **Web Frontend**: Modern and responsive user interface
- **Choco API**: Complementary CSP validation service

### 📊 Economic Analysis Capabilities
- **LLM cost analysis**: Detailed tracking of costs by model, tokens and operation
- **Preprocessing metrics**: Efficiency analysis in HTML reduction
- **Automated reports**: Generation of economic reports in Markdown and HTML
- **Visualizations**: Trend charts, distributions and key metrics

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        A-MINT ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React + Vite)                                       │
│  ├─ Interactive dashboard                                       │
│  ├─ Analysis visualization                                     │
│  └─ Pricing file management                                    │
├─────────────────────────────────────────────────────────────────┤
│  Analysis API (Node.js + TypeScript)                           │
│  ├─ CSP analysis with MiniZinc                                 │
│  ├─ iPricing specification validation                           │
│  ├─ Configuration space calculation                             │
│  └─ Subscription optimization                                  │
├─────────────────────────────────────────────────────────────────┤
│  A-MINT API (Python + FastAPI)                                 │
│  ├─ Web data extraction                                        │
│  ├─ HTML → Markdown → YAML transformation                      │
│  ├─ YAML validation and correction                             │
│  └─ Multiple AI provider integration                           │
├─────────────────────────────────────────────────────────────────┤
│  Choco API (Java + Spring Boot)                                │
│  ├─ Additional CSP specification validation                     │
│  ├─ Complementary constraint analysis                          │
│  └─ Validation support services                                │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Installation and Configuration

### Prerequisites

- **Docker & Docker Compose**: To run all services
- **Python 3.11+**: For local A-MINT engine development
- **Node.js 18+**: For local API and frontend development
- **AI API Keys**: Gemini, OpenAI or other compatible providers

If installing locally, it is recommended to use docker compose. The Makefile allows you to start all systems easily: `make start-api`.

### Environment Variables Configuration

1. **For any provider compatible with the OpenAI API client** (we have used Gemini 2.5 from Google):
```bash
# If you use a single key:
export OPENAI_API_KEY="your-openai-api-key"
# ALTERNATIVE: For automatic rotation of multiple keys:
export OPENAI_API_KEYS="key1,key2,key3"
```
We got our Gemini API key from [Google AI Studio](https://aistudio.google.com/).

2. Alternatively, you can create a `.env` file in the root directory based on the provided `.env.docker.example` file:
```bash
cp .env.docker.example .env
```
Then edit the `.env` file to add your API keys as explained in the previous step. Only the `OPENAI_API_KEY` or `OPENAI_API_KEYS` variable is strictly required.


### Docker Installation (Recommended)

```bash
# 1. Open the repository
cd A-MINT

# 2. Create Docker network
docker network create a-mint-network

# 3. Start all services
docker compose up --build -d

# 4. Verify all services are running
docker compose ps
```

If you want to use the Makefile to manage the services (instead of launching docker commands manually), you can run:

```bash
make start-api
```

### Available Services

Once started, you will have access to:

- **Frontend**: http://localhost:80 - Main web interface
- **A-MINT API**: http://localhost:8001 - Pricing transformation API
- **Analysis API**: http://localhost:8002 - CSP analysis API
- **Choco API**: http://localhost:8000 - Complementary validation API

## 🔧 System Usage

### 1. Pricing Page Transformation

#### Via REST API

```bash
# Start transformation of a URL
curl -X POST "http://localhost:8001/api/v1/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/pricing",
    "model": "gemini-2.5-flash",
    "max_tries": 50,
    "temperature": 0.7
  }'
```

#### Via Makefile (Batch Processing)

```bash
# Transform pricing for specific years
make transform YEARS=2023,2024

# Complete pipeline: transformation, comparison and analysis
make full-pipeline YEARS=2024
```

### 2. Pricing Configuration Analysis

#### Get Pricing Summary

```bash
curl -X POST "http://localhost:8002/api/v1/pricing/summary" \
  -F "pricingFile=@my-pricing-file.yaml"
```

#### Start CSP Analysis

```bash
curl -X POST "http://localhost:8002/api/v1/pricing/analysis" \
  -F "pricingFile=@my-pricing-file.yaml" \
  -F "operation=optimal" \
  -F "solver=minizinc" \
  -F "objective=minimize"
```

## 🧰 Makefile — How it Works & What You Need (RECOMMENDED)

The repository includes a **GNU Make**–based workflow that wraps Docker/Docker Compose so you can run the full A-MINT stack and batch jobs with simple commands like `make start-api` or `make transform`.

### ✅ Requirements to run `make` commands

* **GNU Make** (3.81+).

  * macOS: preinstalled (or `brew install make` as `gmake`).
  * Linux: usually preinstalled (`sudo apt install make` on Debian/Ubuntu).
  * Windows: use **Choco** for installation (`choco install make`); ensure `make` and Docker are available in your shell.
* **Docker** (Engine) and **Docker Compose v2** (the `docker compose` subcommand).

  * Check with: `docker --version` and `docker compose version`.
* **Network & ports available**: the stack uses ports **80**, **8000**, **8001**, **8002** by default.
* **Environment variables**: copy and edit `.env`:

  ```bash
  cp .env.docker.example .env
  # Add your keys (OPENAI_API_KEY, etc.)
  ```
* **Internet access**: containers pull images and call AI providers.

> You do **not** need local Python/Node toolchains to run the stack or scripts via `make`—they’re executed inside containers. Local Python/Node is only required for **developer** workflows outside Docker.

### 🏗️ What the Makefile does under the hood

* **Service lifecycle** (`start-api`, `stop-api`):

  * Creates a shared Docker network: `a-mint-network`.
  * Brings up the stack defined in **root** `docker-compose.yml`:

    * **Frontend** (port 80)
    * **A-MINT API** (port 8001)
    * **Analysis API** (port 8002)
    * **Choco API** (port 8000)
* **Batch jobs** (`transform`, `compare`, `economic-analysis`, `full-pipeline`):

  * Use a separate Compose file at **`scripts/docker-compose.yml`** to run one-off containers with the project’s Python scripts:

    * `scripts/transform_all_pricings.py`
    * `scripts/compare_pricings.py`
    * `scripts/economic_analysis.py`
  * Output is persisted to mounted folders in your repo:

    * `outputData/`, `comparison_results/`, `economic_analysis/`, and logs in `logs/`.

### 📦 Key variables you can override

The Makefile exposes safe knobs you can pass inline:

* `YEARS`: CSV list processed by scripts (default: `2019,2020,2021,2022,2023,2024`)
* `OUTPUT_DIR`: where structured transformation data lands (default: `outputData`)
* `COMPARISON_DIR`: comparison results (default: `comparison_results`)
* `ECONOMIC_DIR`: econ reports (default: `economic_analysis`)
* `LOGS_DIR`: logs directory (default: `logs`)

Examples:

```bash
make transform YEARS=2023,2024
make compare YEARS=2024 OUTPUT_DIR=outData
make economic-analysis LOGS_DIR=runlogs ECONOMIC_DIR=reports
make full-pipeline YEARS=2022,2023,2024
```

### 🧪 Useful tips
> ⚠️ **Warning:** Execution time can vary significantly depending on the number of years, pricing files, and your machine’s performance. In our tests, executing all scripts with just a single pricing as target typically took **5–20 minutes**.

* List commands:

  ```bash
  make help
  ```
* Dry-run (show what would execute without running it):

  ```bash
  make -n transform YEARS=2024
  ```
* Stop all services (some cleanup included):

  ```bash
  make stop-api
  ```
* Clean generated artifacts:

  ```bash
  make clean
  ```
> **Important Note:** After executing the scripts, make sure to check if any orphan containers are left in your Docker environment. You can remove them using `docker container prune -f` to free up resources. Do the same with volumes if needed: `docker volume prune -f` and unused images: `docker image prune -f`.

### 🩺 Troubleshooting

* **`docker: command not found`** → Install Docker and restart your shell.
* **`docker compose: unknown command`** → Install **Compose v2** (or update Docker Desktop).
* **Ports already in use (80/8000/8001/8002)** → Stop other services or change ports in `docker-compose.yml`.
* **`a-mint-network` already exists** → The Makefile ignores this safely; no action needed.
* **Permission errors on mounted folders** → Ensure your user can write to the repo (`chmod -R u+rw .`) or run Docker with a user that can.

---

### 📋 Makefile Commands (recap)

```bash
# Service management
make start-api          # Start all services (Frontend, A-MINT API, Analysis API, Choco API)
make stop-api           # Stop all services and cleanup network

# Data processing
make transform          # Run pricing transformations for YEARS (default range)
make compare            # Compare transformed vs original pricing for YEARS
make economic-analysis  # Build cost/usage reports from logs
make full-pipeline      # transform -> compare -> economic-analysis

# Maintenance
make clean              # Remove outputs: outputData/, comparison_results/, economic_analysis/
make help               # Show available commands
```

This section explains prerequisites, what each target does, where outputs go, and how to customize runs—so new users can run `make` confidently and advanced users can tune variables without touching the Compose files.


## 📊 Data Structure and Specifications

### Feature Types

- **AUTOMATION**: Task automation (BOT, FILTERING, TRACKING, TASK_AUTOMATION)
- **DOMAIN**: Main domain functionalities
- **GUARANTEE**: Technical or service commitments (requires `docUrl`)
- **INFORMATION**: Data and insights exposure
- **INTEGRATION**: External integrations (API, EXTENSION, IDENTITY_PROVIDER, WEB_SAAS, MARKETPLACE, EXTERNAL_DEVICE)
- **MANAGEMENT**: Administrative functionalities
- **PAYMENT**: Payment methods (CARD, GATEWAY, INVOICE, ACH, WIRE_TRANSFER, OTHER)
- **SUPPORT**: Customer support and documentation

### Usage Limit Types

- **NON_RENEWABLE**: One-time limits that don't renew
- **RENEWABLE**: Limits that renew according to billing period

## 📈 Economic Analysis

The system includes advanced economic analysis capabilities to evaluate transformation efficiency and costs:

### Captured Metrics

- **LLM Model Costs**: Detailed analysis of expenses by AI provider
- **Token Usage**: Tracking of input and output tokens per operation
- **Preprocessing Efficiency**: HTML size reduction and cost impact
- **Processing Times**: Performance analysis per operation
- **Success Rates**: Success and failure statistics of transformations

### Generated Reports

```bash
# Execute complete economic analysis
make economic-analysis

# Results are saved in:
economic_analysis/
├── economic_analysis_report.md      # Complete Markdown report
├── economic_analysis_report.html    # HTML version of report
├── cost_breakdown_analysis.png      # Cost breakdown chart
└── processed_*.csv                  # Processed data in CSV
```

### Specification Validation

The system includes automatic validation at multiple levels:

1. **Syntactic Validation**: Valid YAML structure verification
2. **Semantic Validation**: iPricing v2.1 specification conformity
3. **CSP Validation**: Mathematical constraint coherence
4. **Alignment Validation**: Correspondence with original content

## 🔄 Workflows and Pipelines

### Complete Transformation Pipeline

1. **Web Extraction**: Intelligent scraping of pricing pages
2. **HTML Preprocessing**: Content cleaning and optimization
3. **Markdown Conversion**: Structured HTML transformation
4. **Component Extraction**: Identification of plans, features and add-ons
5. **YAML Generation**: Serialization to iPricing format
6. **Validation and Correction**: Automatic verification and corrections
7. **Alignment Analysis**: Semantic correspondence validation

### CSP Analysis Pipeline

1. **Specification Loading**: iPricing YAML file parsing
2. **DZN Conversion**: Transformation to MiniZinc format
3. **CSP Resolution**: Solver execution to obtain solutions
4. **Post-processing**: Result interpretation and formatting
5. **Report Generation**: Creation of detailed reports

## 📂 Project Structure

```
A-MINT/
├── README.md                         # This file
├── LICENSE                          # Project license
├── Makefile                         # Workflow automation
├── docker-compose.yml               # Main Docker configuration
├── requirements.txt                 # Main Python dependencies
├── requirements_visualizations.txt  # Visualization dependencies
├── .env.docker.example              # Environment variables example for Docker compose deployment
├── .env.example                     # Environment variables example for local development
├── .gitignore                       # Git ignore file
├── ICSOC25__Technical_Report.pdf    # Technical report
│
├── src/                            # A-MINT main source code
│   ├── amint/                      # Main package
│   │   ├── api/                    # FastAPI endpoints
│   │   ├── ai/                     # AI clients and configuration
│   │   ├── extractors/             # Data extractors
│   │   ├── models/                 # Data models
│   │   ├── prompts/                # AI prompt templates
│   │   ├── transformers/           # Data transformers
│   │   ├── utils/                  # General utilities
│   │   └── validators/             # Data validators
│   └── Dockerfile                  # Docker image for A-MINT API
│
├── analysis_api/                   # CSP Analysis API
│   ├── src/                        # TypeScript source code
│   │   ├── api/                    # API controllers
│   │   ├── models/                 # MiniZinc models
│   │   ├── services/               # Business logic
│   │   ├── types.ts                # Type definitions
│   │   └── utils/                  # Utilities
│   ├── tests/                      # Test suite (78 test cases)
│   ├── package.json                # Node.js dependencies
│   ├── tsconfig.json               # TypeScript configuration
│   └── Dockerfile                  # Docker image
│
├── frontend/                       # React Web Interface
│   ├── src/                        # React + TypeScript source code
│   │   ├── components/             # Reusable components
│   │   ├── pages/                  # Main pages
│   │   ├── services/               # API clients
│   │   └── utils/                  # Frontend utilities
│   ├── public/                     # Static resources
│   ├── package.json                # React dependencies
│   ├── tailwind.config.js          # Tailwind CSS configuration
│   ├── vite.config.ts              # Vite configuration
│   └── Dockerfile                  # Docker image
│
├── csp/                           # Choco API (Java Spring Boot)
│   ├── src/main/                   # Java source code
│   ├── pom.xml                     # Maven dependencies
│   └── Dockerfile                  # Docker image
│
├── scripts/                       # Batch processing scripts
│   ├── transform_all_pricings.py   # Massive transformation
│   ├── compare_pricings.py         # Result comparison
│   ├── economic_analysis.py        # Economic analysis
│   ├── docker-compose.yml          # Docker for scripts
│   └── Dockerfile                  # Image for scripts
│
├── data/                          # Input data
│   └── pricings/                   # Original pricing files
│
├── output/                        # Generated YAML files
├── outputData/                    # Structured transformation data
├── comparison_results/            # Comparison results
├── economic_analysis/             # Economic analysis reports
└── logs/                         # System logs
    ├── amint_api.log             # A-MINT API logs
    ├── transformation_logs.csv   # Transformation logs
    └── llm_logs.csv              # LLM call logs
```

## ⚠️ Memory Tuning for Large Configuration Spaces

When exploring **very large configuration spaces** (≈ **10k+ combinations**), we found that default container memory settings could cause builds or CSP runs to fail (e.g., out-of-memory or slow GC). For experimentation, we adjusted the Dockerfiles to grant **more heap memory** to Node (during the Analysis API build) and to Java (for the Choco CSP service).

### What we changed (and why)

**Analysis API (`analysis_api/Dockerfile`) — Node heap during build**

* **Uncommented** the high-memory build line and **commented** the default build line:

  ```dockerfile
  # RUN NODE_OPTIONS="--max-old-space-size=8192" npm run build  # ← uncomment this
  RUN npm run build                                             # ← comment this
  ```

  This gives the Node build process up to **~8 GB** of old-space heap, reducing build OOMs when the TypeScript bundle gets heavy or when dependency graphs are large.

**Choco CSP (`csp/Dockerfile`) — Java heap at runtime**

* **Recommended** enabling the Java heap option by **uncommenting**:

  ```dockerfile
  # ENV JAVA_TOOL_OPTIONS="-Xmx8g"  # ← uncomment this (and adjust if needed)
  ```

  This provides the Choco API with **~8 GB** of maximum heap, which helps it handle massive search spaces without crashing or thrashing.

> We did this so that **huge configuration spaces (10k+) could be computed** reliably on our machine. Depending on your hardware and workload, you may also need these changes for better performance.

### When should you enable these?

* You see **build-time OOM** or the Analysis API build stalls/crashes.
* Choco CSP runs terminate with **OutOfMemoryError** or slow to a crawl on large enumerations.
* You’re running **batch pipelines** (e.g., `make full-pipeline`) over many, large pricings.

### How to apply (step-by-step)

1. **Analysis API build memory**

   * Edit `analysis_api/Dockerfile`:

     ```diff
     - # RUN NODE_OPTIONS="--max-old-space-size=8192" npm run build
     - RUN npm run build
     + RUN NODE_OPTIONS="--max-old-space-size=8192" npm run build
     + # RUN npm run build
     ```
2. **Choco CSP runtime memory**

   * Edit `csp/Dockerfile`:

     ```diff
     - # ENV JAVA_TOOL_OPTIONS="-Xmx8g"
     + ENV JAVA_TOOL_OPTIONS="-Xmx8g"
     ```
3. **Rebuild & restart**

   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

### How much memory do I need?

* The above assumes your host can spare **~8 GB** per service at peak.
* On **Docker Desktop (macOS/Windows)**, increase RAM in **Settings → Resources** (we suggest **≥ 12–16 GB** total if you enable both 8g heaps).
* If 8g is too high/low for your machine, tune the values:

  * Node: `--max-old-space-size=4096` (4g), `12288` (12g), etc.
  * Java: `-Xmx4g`, `-Xmx12g`, etc. (optionally add `-Xms2g` to pre-reserve heap).

### Alternatives (if you prefer not to edit Dockerfiles)

You can also inject heap settings via **Compose env** or **build args** (advanced users):

* Node at build time (Compose `build.args` → referenced in Dockerfile).
* Java at runtime (Compose `environment: JAVA_TOOL_OPTIONS=-Xmx8g`).

### Troubleshooting

* **Containers still OOM**: verify host limits (`docker stats`), raise Docker Desktop memory, or reduce parallelism.
* **Slow builds/runs**: more heap ≠ faster; profile first. Consider lowering heap if GC pauses increase.
* **Ports busy / stale images**: `docker compose down`, `docker system prune -f`, then rebuild.

> **TL;DR**: If you’re hitting OOMs or timeouts on very large analyses, **uncomment the 8g lines** shown above and rebuild. It made big spaces (10k+) feasible for us; tuning may still be required based on your machine.


## 🤝 Contributing

### Development Environment Setup

```bash
# 1. Open project
cd A-MINT

# 2. Configure environment variables for development
cp .env.example .env
# Edit .env with your API keys

# 3. Install dependencies for local development
pip install -r requirements.txt
cd analysis_api && npm install && cd ..
cd frontend && npm install && cd ..
cd csp && mvn clean install && cd ..
```

## 📚 Additional Documentation

### Technical Report
A detailed technical report is available in the root directory: [Technical Report](./ICSOC25___Technical_Report.pdf)

### APIs and Specifications

- **A-MINT API**: Swagger UI available at http://localhost:8001/docs
- **Analysis API**: ReDoc at http://localhost:8002/redoc

## 📄 License

This project is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0). See the [LICENSE](LICENSE) file for more details.
