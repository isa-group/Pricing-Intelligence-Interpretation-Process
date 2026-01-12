# Dockerfile for Analysis API
FROM node:21.1-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -g 1001 nodejs && \
    useradd -r -u 1001 -g nodejs -s /bin/bash -m analysis

# Install curl and build dependencies
RUN apt-get update && apt-get install -y curl wget unzip

# Install minizinc
RUN apt-get update && apt-get install -y minizinc && apt-get clean

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files (pnpm)
COPY package.json pnpm-lock.yaml ./

# Install dependencies (including dev dependencies for building)
RUN pnpm install --frozen-lockfile

# Copy source code
COPY src/ ./src/
COPY tsconfig.json ./

# Build TypeScript
RUN pnpm run build

# Remove dev dependencies after build
RUN pnpm prune --prod

# Create necessary directories
RUN mkdir -p /tmp && \
    mkdir -p ./logs && \
    mkdir -p ./output

# Change ownership to non-root user
RUN chown -R analysis:nodejs /app && \
    chown -R analysis:nodejs /tmp && \
    chown -R analysis:nodejs /home/analysis

# Switch to non-root user
USER analysis

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Start the application
CMD ["pnpm", "start"]
