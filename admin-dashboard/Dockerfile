# ===== Build stage =====
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ===== Production stage =====
FROM nginx:1.25-alpine

# 👇 IMPORTANT: copy to /usr/share/nginx/admin
COPY --from=builder /app/dist /usr/share/nginx/admin

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
