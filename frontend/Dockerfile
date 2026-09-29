# Frontend Dockerfile — multi-stage: Node builds, nginx serves.
# Final image contains no Node, no node_modules, no source.

# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

# Cache-friendly COPY order: package files before source
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit; else npm install --no-audit; fi

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine AS runtime

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Non-root user (nginx runs as nginx user by default in alpine)
# Adjust permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

# Exec-form CMD
CMD ["nginx", "-g", "daemon off;"]
