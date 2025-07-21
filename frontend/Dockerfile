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

# Debug after COPY: Check what was copied
RUN echo "=== After COPY . . ===" && \
    echo "=== Root directory ===" && \
    ls -la && \
    echo "=== Looking for src ===" && \
    find . -type d -name "src" 2>/dev/null | head -10 || echo "No src found" && \
    echo "=== All directories ===" && \
    find . -type d -maxdepth 2 | sort

# Set build-time environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Verify src directory exists before build
RUN test -d src || (echo "ERROR: src directory not found!" && exit 1)

# Build the Next.js application with verbose output
RUN npm run build || \
    (echo "=== Build Failed ===" && \
     echo "=== Current directory ===" && \
     pwd && \
     echo "=== tsconfig.json ===" && \
     cat tsconfig.json && \
     echo "=== Checking problematic file ===" && \
     cat src/components/markdown/markdown-editor-container.tsx | head -20 && \
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