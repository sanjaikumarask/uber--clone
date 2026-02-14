# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:1.25-alpine

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# The actual nginx.conf is mounted from docker-compose
# This container just provides the built files

EXPOSE 80

CMD ["echo", "Build complete - files ready in /usr/share/nginx/html"]
