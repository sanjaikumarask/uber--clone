#!/usr/bin/env python3
"""
FIX: Google Maps API Key Issue

Problem: Current API key has referer restrictions that block server-side requests
Solution: Instructions to fix the API key in Google Cloud Console
"""

print("""
🔧 GOOGLE MAPS API KEY FIX REQUIRED
=====================================

PROBLEM FOUND:
--------------
Your Google Maps API key has "HTTP referer restrictions" which blocks server-side requests.

Error: "REQUEST_DENIED - API keys with referer restrictions cannot be used with this API"

SOLUTION (Choose ONE):
----------------------

OPTION 1: Remove Referer Restrictions (Quick Fix)
--------------------------------------------------
1. Go to: https://console.cloud.google.com/apis/credentials
2. Find your API key: AIzaSyD5******************************
3. Click "Edit"
4. Under "Application restrictions":
   - Change from "HTTP referers" to "None"
5. Click "Save"
6. Wait 1-2 minutes for changes to propagate
7. Restart backend: docker compose restart backend

⚠️  WARNING: This makes the key less secure. Anyone can use it.


OPTION 2: Create Separate API Key (Recommended)
------------------------------------------------
1. Go to: https://console.cloud.google.com/apis/credentials
2. Click "CREATE CREDENTIALS" → "API key"
3. Name it: "Uber Clone - Server Side"
4. Under "Application restrictions":
   - Select "IP addresses"
   - Add your server IP (or leave as "None" for development)
5. Under "API restrictions":
   - Select "Restrict key"
   - Enable: "Directions API", "Maps JavaScript API", "Geocoding API"
6. Click "Save"
7. Copy the new API key
8. Update docker-compose.yml:
   
   backend:
     environment:
       - GOOGLE_MAPS_API_KEY=YOUR_NEW_SERVER_KEY_HERE
   
9. Restart: docker compose down && docker compose up -d


OPTION 3: Use Two Different Keys (Most Secure)
-----------------------------------------------
1. Keep current key for frontend (with referer restrictions)
2. Create new key for backend (with IP restrictions)
3. Update configuration:

   # Frontend (.env)
   VITE_GOOGLE_MAPS_API_KEY=AIzaSyD5******************************

   # Backend (docker-compose.yml)
   GOOGLE_MAPS_API_KEY=YOUR_NEW_SERVER_KEY_HERE


CURRENT STATUS:
---------------
✅ API key is set in backend
❌ API key has referer restrictions (blocks server-side calls)
❌ Polylines are NOT being generated
✅ Fallback mode is working (using Haversine calculation)


AFTER FIX:
----------
✅ Backend will call Google Directions API successfully
✅ Polylines will be generated and stored in database
✅ Grey route lines will appear on rider map
✅ Blue completed lines will grow as driver moves


VERIFY FIX WORKED:
------------------
1. Create a new ride
2. Check backend logs:
   docker logs uber_backend --tail 20
   
3. Look for:
   ✅ "✅ Google Maps Route Calculated"
   ❌ "⚠️ Google Maps Error: REQUEST_DENIED"

4. Check database:
   docker exec -it uber_backend python manage.py shell -c "from apps.rides.models import Ride; r = Ride.objects.last(); print('Polyline:', r.planned_route_polyline[:50] if r.planned_route_polyline else 'EMPTY')"
   
   Should show: "Polyline: a~l~Fjk~uOnqC_c@{~@_dB..."
   NOT: "Polyline: EMPTY"

""")
