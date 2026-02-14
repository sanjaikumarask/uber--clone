#!/bin/bash

echo "🚀 Deploying Uber Clone with Nginx..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Stop existing containers
echo -e "${YELLOW}1. Stopping existing containers...${NC}"
docker-compose down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 2: Build all services
echo -e "${YELLOW}2. Building all services...${NC}"
docker-compose build
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Build complete${NC}"
echo ""

# Step 3: Start all services
echo -e "${YELLOW}3. Starting all services...${NC}"
docker-compose up -d
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start services!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Step 4: Wait for backend to be ready
echo -e "${YELLOW}4. Waiting for backend to be ready...${NC}"
sleep 10
echo -e "${GREEN}✅ Backend ready${NC}"
echo ""

# Step 5: Collect static files
echo -e "${YELLOW}5. Collecting Django static files...${NC}"
docker exec uber_backend python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to collect static files!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Static files collected${NC}"
echo ""

# Step 6: Run migrations
echo -e "${YELLOW}6. Running database migrations...${NC}"
docker exec uber_backend python manage.py migrate --noinput
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Migrations failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Migrations complete${NC}"
echo ""

# Step 7: Test Nginx configuration
echo -e "${YELLOW}7. Testing Nginx configuration...${NC}"
docker exec uber_nginx nginx -t
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Nginx configuration invalid!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Nginx configuration valid${NC}"
echo ""

# Step 8: Check all services
echo -e "${YELLOW}8. Checking service status...${NC}"
docker-compose ps
echo ""

# Step 9: Test health endpoint
echo -e "${YELLOW}9. Testing health endpoint...${NC}"
sleep 2
HEALTH=$(curl -s http://localhost/health)
if [ "$HEALTH" == "healthy" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed!${NC}"
    echo "Response: $HEALTH"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Access your applications:"
echo ""
echo "  Rider Web:       http://localhost/"
echo "  Admin Dashboard: http://localhost/admin-dashboard"
echo "  Django Admin:    http://localhost/admin"
echo "  API:             http://localhost/api/"
echo "  Health Check:    http://localhost/health"
echo ""
echo "🔍 Useful commands:"
echo ""
echo "  View logs:       docker-compose logs -f"
echo "  Stop all:        docker-compose down"
echo "  Restart Nginx:   docker restart uber_nginx"
echo "  Check status:    docker-compose ps"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
