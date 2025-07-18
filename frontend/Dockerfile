# Build stage
FROM node:18-alpine AS builder

# Install build dependencies
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Set build-time environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Debug: Show environment and installed packages
RUN echo "=== Build Environment ===" && \
    node --version && \
    npm --version && \
    echo "=== Installed packages ===" && \
    npm list --depth=0 || true && \
    echo "=== Directory contents ===" && \
    ls -la

# Build the Next.js application with verbose output
RUN npm run build --verbose || \
    (echo "=== Build Failed ===" && \
     echo "=== Package.json ===" && \
     cat package.json && \
     echo "=== Error details ===" && \
     npm run build 2>&1 | tee /tmp/build.log && \
     cat /tmp/build.log && \
     exit 1)

# Production stage
FROM node:18-alpine AS runner

# Install runtime dependencies
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy built application from builder stage
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Install only production dependencies
RUN npm ci --only=production

# Change ownership to non-root user
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["npm", "start"]