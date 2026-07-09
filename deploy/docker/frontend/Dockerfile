# =============================================================================
# Urban Heat Mitigation Platform - Frontend Dockerfile (Production)
# Multi-stage: build -> nginx serve
# =============================================================================

# Stage 1: Build
FROM node:20-alpine AS builder

ENV NODE_ENV=production \
    NPM_CONFIG_LOGLEVEL=warn

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --only=production && npm cache clean --force

COPY frontend/ .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.25-alpine

ENV NGINX_PORT=80

RUN apk add --no-cache curl && \
    addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    mkdir -p /var/cache/nginx /var/run/nginx && \
    chown -R appuser:appgroup /var/cache/nginx /var/run/nginx

COPY --from=builder /build/dist /usr/share/nginx/html
COPY deploy/docker/frontend/nginx-frontend.conf /etc/nginx/conf.d/default.conf

RUN chown -R appuser:appgroup /usr/share/nginx/html

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

USER appuser
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
