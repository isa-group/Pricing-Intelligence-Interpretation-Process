# Dockerfile for Analysis API
FROM node:21.1-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -g 1001 nodejs && \
    useradd -r -u 1001 -g nodejs -s /bin/bash -m analysis

# Install curl and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        unzip && \
    rm -rf /var/lib/apt/lists/*

# Install minizinc
RUN apt-get update && \
    apt-get install -y --no-install-recommends minizinc && \
    rm -rf /var/lib/apt/lists/*

# Use a shared Corepack cache for root and analysis
ENV COREPACK_HOME=/opt/corepack

# Enable and activate pnpm 9
RUN mkdir -p "${COREPACK_HOME}" && \
    corepack enable && \
    corepack prepare pnpm@9.15.9 --activate && \
    pnpm --version

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies, including dev dependencies for building
RUN pnpm install --frozen-lockfile

# Copy source code
COPY src/ ./src/
COPY tsconfig.json ./

# Build TypeScript
RUN pnpm run build

# Remove dev dependencies after build
RUN pnpm prune --prod

# Create necessary directories
RUN mkdir -p /app/logs /app/output /tmp

# Grant ownership to the runtime user
RUN chown -R analysis:nodejs \
        /app \
        /tmp \
        /home/analysis \
        /opt/corepack

# Switch to non-root user
USER analysis

# Verify pnpm with the actual runtime user
RUN cd /tmp && pnpm --version

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s \
    --timeout=10s \
    --start-period=5s \
    --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Start the application
CMD ["pnpm", "start"]