# Development vs Production URLs

## **Current Setup:**

You have **TWO environments** running:

### **1. Development (What You Should Use)**
```
Rider Web: http://localhost:5173 Use this!
Admin Dashboard: http://localhost:5174 Use this!
Backend API: http://localhost:8000/api/
```

**Features:**
- Hot reload (instant updates)
- Better error messages
- Source maps for debugging
- Faster iteration

### **2. Production (Nginx)**
```
Rider Web: http://localhost/ Old build
Admin Dashboard: http://localhost/admin-dashboard Not configured
Backend API: http://localhost/api/ Works
Django Admin: http://localhost/admin/ Works
```

**Features:**
- Optimized build
- Gzip compression
- Production-ready
- Needs manual rebuild

---

## **Why You're Seeing Errors:**

### **Error 1: JavaScript Error on `http://localhost/`**
```
Uncaught Error at index-jF3o4qcm.js
```

**Cause:** Old build from Feb 11 with Google Maps API key issue

**Solution:** Either:
1. Use dev server: `http://localhost:5173` 
2. Rebuild: `./deploy-frontend.sh`

### **Error 2: 404 on `/admin-dashboard`**
**Cause:** Admin dashboard not built/deployed to Nginx

**Solution:** Use dev server: `http://localhost:5174` 

---

## **Recommended Workflow:**

### **For Development (Daily Work):**
```bash
# Terminal 1: Backend
docker compose up

# Terminal 2: Rider Web
cd frontend/rider-web
npm run dev
# Access at: http://localhost:5173

# Terminal 3: Admin Dashboard
cd admin-dashboard
npm run dev
# Access at: http://localhost:5174
```

### **For Production Testing:**
```bash
# Build and deploy to Nginx
./deploy-frontend.sh

# Access at: http://localhost/
```

---

## **Quick Reference:**

|Task|URL|Notes|
|------|-----|-------|
|**Develop Rider App**|`http://localhost:5173`|Hot reload, debugging|
|**Develop Admin**|`http://localhost:5174`|Hot reload, debugging|
|**Test API**|`http://localhost:8000/api/`|Direct backend access|
|**Django Admin**|`http://localhost/admin/`|Always works|
|**Production Test**|`http://localhost/`|After `./deploy-frontend.sh`|

---

## **Fix Current Issues:**

### **Option 1: Just Use Dev Servers (Easiest)**
```bash
# Already running!
http://localhost:5173 ← Rider
http://localhost:5174 ← Admin
```

### **Option 2: Update Nginx Build**
```bash
./deploy-frontend.sh
```

This will:
1. Build rider web app
2. Copy to Nginx
3. Restart Nginx
4. Make `http://localhost/` work

---

## **Why Two Setups?**

### **Development (Port 5173/5174):**
- Fast iteration
- Instant updates
- Better debugging
- **Use this 99% of the time!**

### **Production (Port 80):**
- Optimized code
- Smaller files
- Gzip compression
- **Use for final testing before deployment**

---

## **Summary:**

**Your apps ARE working!** Just use the dev servers:

```
Rider: http://localhost:5173
Admin: http://localhost:5174
API: http://localhost:8000/api/
```

The Nginx errors are because you're trying to use the production build, which is outdated. For development, **always use the dev servers** (ports 5173/5174).

---

## **When to Use Each:**

|Scenario|Use|
|----------|-----|
|Writing code|Dev servers (5173/5174)|
|Testing features|Dev servers (5173/5174)|
|Debugging|Dev servers (5173/5174)|
|Final testing|Nginx (port 80) after rebuild|
|Deployment|Nginx (port 80)|

**Bottom line: Keep using `http://localhost:5173` for development!** 
