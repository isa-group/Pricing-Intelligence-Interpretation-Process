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

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for building)
RUN npm ci && npm cache clean --force

# Copy source code
COPY src/ ./src/
COPY tsconfig.json ./

# Build TypeScript
# RUN NODE_OPTIONS="--max-old-space-size=8192" npm run build
RUN npm run build

# Remove dev dependencies after build
RUN npm prune --production

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
CMD ["npm", "start"]
