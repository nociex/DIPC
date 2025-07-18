FROM node:18-alpine

# Install build dependencies
RUN apk add --no-cache libc6-compat

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies with verbose logging
RUN npm ci --verbose

# Copy application code
COPY . .

# Display environment and check files
RUN echo "Node version:" && node --version && \
    echo "NPM version:" && npm --version && \
    echo "Files in /app:" && ls -la

# Set environment variable for production build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application with error output
RUN npm run build || (echo "Build failed. Listing files:" && ls -la && exit 1)

# Remove devDependencies after build to reduce image size
RUN npm prune --production

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Change ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]