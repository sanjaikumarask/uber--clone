# 🗺️ How to Draw Polyline on Google Maps - Simple Guide

## What is a Polyline?

A **polyline** is a line drawn on a map connecting multiple GPS coordinates. Think of it as "connect the dots" on a map - you give it a series of points, and it draws a line through them.

**Use Cases:**
- Show route from Point A to Point B
- Display driver's path in real-time
- Visualize completed journey

---

## 📚 Table of Contents

1. [Method 1: Manual Polyline (Simple)](#method-1-manual-polyline-simple)
2. [Method 2: Google Directions API (Automatic)](#method-2-google-directions-api-automatic)
3. [Method 3: Encoded Polyline (Efficient)](#method-3-encoded-polyline-efficient)
4. [Complete Working Example](#complete-working-example)

---

## Method 1: Manual Polyline (Simple)

### Step 1: Define Your Points

```javascript
// Array of GPS coordinates
const routePoints = [
  { lat: 13.0827, lng: 80.2707 },  // Point 1: Pickup
  { lat: 13.0825, lng: 80.2705 },  // Point 2
  { lat: 13.0820, lng: 80.2700 },  // Point 3
  { lat: 13.0815, lng: 80.2695 },  // Point 4
  { lat: 13.0810, lng: 80.2690 },  // Point 5: Dropoff
];
```

### Step 2: Create Polyline

**React with @react-google-maps/api:**

```tsx
import { GoogleMap, Polyline } from '@react-google-maps/api';

function MyMap() {
  const routePoints = [
    { lat: 13.0827, lng: 80.2707 },
    { lat: 13.0825, lng: 80.2705 },
    { lat: 13.0820, lng: 80.2700 },
    { lat: 13.0810, lng: 80.2690 },
  ];

  return (
    <GoogleMap
      center={{ lat: 13.0827, lng: 80.2707 }}
      zoom={14}
    >
      <Polyline
        path={routePoints}
        options={{
          strokeColor: '#2563eb',    // Blue color
          strokeOpacity: 1.0,         // Fully opaque
          strokeWeight: 6,            // Line thickness
        }}
      />
    </GoogleMap>
  );
}
```

**Vanilla JavaScript:**

```javascript
// After map is loaded
const polyline = new google.maps.Polyline({
  path: routePoints,
  strokeColor: '#2563eb',
  strokeOpacity: 1.0,
  strokeWeight: 6,
  map: map  // Your map instance
});
```

### Result:
✅ A blue line connecting all your points!

---

## Method 2: Google Directions API (Automatic)

This method automatically calculates the best route between two points.

### Step 1: Backend - Get Route from Google

**Python (Django):**

```python
import requests

def get_route_from_google(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng):
    """
    Get optimal route from Google Directions API
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    
    params = {
        "origin": f"{pickup_lat},{pickup_lng}",
        "destination": f"{dropoff_lat},{dropoff_lng}",
        "mode": "driving",
        "key": "YOUR_GOOGLE_MAPS_API_KEY"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        route = data["routes"][0]
        
        # Extract encoded polyline
        encoded_polyline = route["overview_polyline"]["points"]
        
        # Extract distance and duration
        leg = route["legs"][0]
        distance_km = leg["distance"]["value"] / 1000
        duration_min = leg["duration"]["value"] / 60
        
        return {
            "polyline": encoded_polyline,
            "distance_km": distance_km,
            "duration_min": duration_min
        }
    else:
        raise Exception(f"Google API Error: {data['status']}")

# Usage
route = get_route_from_google(13.0827, 80.2707, 13.0569, 80.2425)
print(route)
# Output: {
#   "polyline": "a~l~Fjk~uOnqC_c@{~@_dB...",
#   "distance_km": 4.2,
#   "duration_min": 12
# }
```

**Node.js:**

```javascript
const axios = require('axios');

async function getRouteFromGoogle(pickupLat, pickupLng, dropoffLat, dropoffLng) {
  const url = 'https://maps.googleapis.com/maps/api/directions/json';
  
  const params = {
    origin: `${pickupLat},${pickupLng}`,
    destination: `${dropoffLat},${dropoffLng}`,
    mode: 'driving',
    key: 'YOUR_GOOGLE_MAPS_API_KEY'
  };
  
  const response = await axios.get(url, { params });
  const data = response.data;
  
  if (data.status === 'OK') {
    const route = data.routes[0];
    const leg = route.legs[0];
    
    return {
      polyline: route.overview_polyline.points,
      distance_km: leg.distance.value / 1000,
      duration_min: leg.duration.value / 60
    };
  } else {
    throw new Error(`Google API Error: ${data.status}`);
  }
}

// Usage
const route = await getRouteFromGoogle(13.0827, 80.2707, 13.0569, 80.2425);
console.log(route);
```

### Step 2: Frontend - Decode and Draw

```tsx
import { useMemo } from 'react';
import { GoogleMap, Polyline } from '@react-google-maps/api';

function MapWithRoute() {
  // This comes from your backend
  const encodedPolyline = "a~l~Fjk~uOnqC_c@{~@_dB...";
  
  // Decode the polyline
  const decodedPath = useMemo(() => {
    if (!encodedPolyline || !window.google) return [];
    
    try {
      return google.maps.geometry.encoding.decodePath(encodedPolyline);
    } catch (error) {
      console.error('Failed to decode polyline:', error);
      return [];
    }
  }, [encodedPolyline]);
  
  return (
    <GoogleMap
      center={{ lat: 13.0827, lng: 80.2707 }}
      zoom={14}
    >
      <Polyline
        path={decodedPath}
        options={{
          strokeColor: '#2563eb',
          strokeOpacity: 1.0,
          strokeWeight: 6,
        }}
      />
    </GoogleMap>
  );
}
```

### Result:
✅ Google calculates the optimal route and you draw it!

---

## Method 3: Encoded Polyline (Efficient)

### What is an Encoded Polyline?

Instead of sending hundreds of coordinates:
```json
[
  {lat: 13.0827, lng: 80.2707},
  {lat: 13.0826, lng: 80.2706},
  {lat: 13.0825, lng: 80.2705},
  ... (100 more points)
]
```

You send a compressed string:
```
"a~l~Fjk~uOnqC_c@{~@_dB..."
```

**Benefits:**
- 90% smaller data transfer
- Faster loading
- Less bandwidth

### How to Use:

**1. Get encoded polyline from Google (backend)**
```python
# Already shown in Method 2
route = get_route_from_google(pickup, dropoff)
encoded = route["polyline"]  # "a~l~Fjk~uOnqC..."
```

**2. Store in database**
```python
ride = Ride.objects.create(
    pickup_lat=13.0827,
    pickup_lng=80.2707,
    drop_lat=13.0569,
    drop_lng=80.2425,
    planned_route_polyline=encoded  # Store the string
)
```

**3. Send to frontend via API/WebSocket**
```python
# API Response
{
    "ride_id": 123,
    "polyline": "a~l~Fjk~uOnqC_c@{~@_dB...",
    "pickup": {"lat": 13.0827, "lng": 80.2707},
    "dropoff": {"lat": 13.0569, "lng": 80.2425}
}
```

**4. Decode and draw in frontend**
```tsx
const path = google.maps.geometry.encoding.decodePath(encodedPolyline);

<Polyline path={path} options={{...}} />
```

---

## Complete Working Example

### Full React Component

```tsx
import { useState, useEffect, useMemo } from 'react';
import { GoogleMap, useJsApiLoader, Polyline, Marker } from '@react-google-maps/api';

const libraries = ['geometry'];

function UberMap() {
  // Load Google Maps
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: 'YOUR_API_KEY',
    libraries: libraries
  });

  // State
  const [encodedPolyline, setEncodedPolyline] = useState('');
  const [pickup, setPickup] = useState({ lat: 13.0827, lng: 80.2707 });
  const [dropoff, setDropoff] = useState({ lat: 13.0569, lng: 80.2425 });

  // Fetch route from backend
  useEffect(() => {
    fetch('/api/rides/get-route/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pickup_lat: pickup.lat,
        pickup_lng: pickup.lng,
        drop_lat: dropoff.lat,
        drop_lng: dropoff.lng
      })
    })
      .then(res => res.json())
      .then(data => {
        setEncodedPolyline(data.polyline);
      })
      .catch(console.error);
  }, [pickup, dropoff]);

  // Decode polyline
  const decodedPath = useMemo(() => {
    if (!isLoaded || !encodedPolyline || !window.google) return [];
    
    try {
      return google.maps.geometry.encoding.decodePath(encodedPolyline);
    } catch (error) {
      console.error('Decode error:', error);
      return [];
    }
  }, [isLoaded, encodedPolyline]);

  if (!isLoaded) return <div>Loading map...</div>;

  return (
    <GoogleMap
      center={pickup}
      zoom={13}
      mapContainerStyle={{ width: '100%', height: '600px' }}
    >
      {/* Pickup Marker */}
      <Marker
        position={pickup}
        label="A"
        icon={{
          url: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
        }}
      />

      {/* Dropoff Marker */}
      <Marker
        position={dropoff}
        label="B"
        icon={{
          url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
        }}
      />

      {/* Route Polyline */}
      {decodedPath.length > 0 && (
        <Polyline
          path={decodedPath}
          options={{
            strokeColor: '#2563eb',
            strokeOpacity: 1.0,
            strokeWeight: 6,
            geodesic: true
          }}
        />
      )}
    </GoogleMap>
  );
}

export default UberMap;
```

### Backend API Endpoint

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests

@csrf_exempt
def get_route(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        pickup_lat = data['pickup_lat']
        pickup_lng = data['pickup_lng']
        drop_lat = data['drop_lat']
        drop_lng = data['drop_lng']
        
        # Call Google Directions API
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{pickup_lat},{pickup_lng}",
            "destination": f"{drop_lat},{drop_lng}",
            "mode": "driving",
            "key": "YOUR_GOOGLE_MAPS_API_KEY"
        }
        
        response = requests.get(url, params=params)
        google_data = response.json()
        
        if google_data["status"] == "OK":
            route = google_data["routes"][0]
            leg = route["legs"][0]
            
            return JsonResponse({
                "polyline": route["overview_polyline"]["points"],
                "distance_km": leg["distance"]["value"] / 1000,
                "duration_min": leg["duration"]["value"] / 60
            })
        else:
            return JsonResponse({"error": "Route not found"}, status=400)
```

---

## 🎨 Customization Options

### Different Colors

```tsx
<Polyline
  path={path}
  options={{
    strokeColor: '#10b981',  // Green
    strokeColor: '#f59e0b',  // Orange
    strokeColor: '#8b5cf6',  // Purple
    strokeColor: '#ef4444',  // Red
  }}
/>
```

### Dashed Line

```tsx
<Polyline
  path={path}
  options={{
    strokeColor: '#2563eb',
    strokeOpacity: 0,
    icons: [{
      icon: {
        path: 'M 0,-1 0,1',
        strokeOpacity: 1,
        scale: 4
      },
      offset: '0',
      repeat: '20px'
    }]
  }}
/>
```

### Animated Line

```tsx
<Polyline
  path={path}
  options={{
    strokeColor: '#2563eb',
    strokeWeight: 6,
    icons: [{
      icon: {
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
      },
      offset: '100%',
      repeat: '100px'
    }]
  }}
/>
```

### Dual Polyline (Uber Style)

```tsx
{/* Grey background - full route */}
<Polyline
  path={fullPath}
  options={{
    strokeColor: '#e5e7eb',
    strokeOpacity: 0.8,
    strokeWeight: 6,
    zIndex: 1
  }}
/>

{/* Blue foreground - completed route */}
<Polyline
  path={completedPath}
  options={{
    strokeColor: '#2563eb',
    strokeOpacity: 1.0,
    strokeWeight: 6,
    zIndex: 2
  }}
/>
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Polyline Not Showing

**Problem:** Map loads but no line appears

**Solutions:**
```tsx
// ✅ Make sure path has at least 2 points
if (path.length < 2) {
  console.error('Need at least 2 points for polyline');
}

// ✅ Check if Google Maps is loaded
if (!window.google) {
  console.error('Google Maps not loaded yet');
}

// ✅ Verify coordinates are valid
path.forEach(point => {
  if (point.lat < -90 || point.lat > 90) {
    console.error('Invalid latitude:', point.lat);
  }
  if (point.lng < -180 || point.lng > 180) {
    console.error('Invalid longitude:', point.lng);
  }
});
```

### Issue 2: Encoded Polyline Decode Error

**Problem:** `decodePath()` throws error

**Solution:**
```tsx
const decodedPath = useMemo(() => {
  if (!encodedPolyline || !window.google?.maps?.geometry) {
    return [];
  }
  
  try {
    return google.maps.geometry.encoding.decodePath(encodedPolyline);
  } catch (error) {
    console.error('Decode failed:', error);
    console.log('Polyline string:', encodedPolyline);
    return [];
  }
}, [encodedPolyline]);
```

### Issue 3: Polyline Appears Jagged

**Problem:** Line doesn't follow roads smoothly

**Solution:**
```tsx
<Polyline
  path={path}
  options={{
    strokeColor: '#2563eb',
    strokeWeight: 6,
    geodesic: true  // ← Add this for smooth curves
  }}
/>
```

---

## 📊 Performance Tips

### 1. Simplify Long Polylines

If you have 1000+ points, simplify them:

```javascript
function simplifyPath(path, tolerance = 0.0001) {
  // Use Douglas-Peucker algorithm
  // Or just take every Nth point
  return path.filter((_, index) => index % 5 === 0);
}

const simplifiedPath = simplifyPath(decodedPath);
```

### 2. Use Encoded Polylines

Always prefer encoded polylines over raw coordinates:

```
❌ Bad: Send 500 coordinate objects (50 KB)
✅ Good: Send 1 encoded string (5 KB)
```

### 3. Memoize Decoded Path

```tsx
const decodedPath = useMemo(() => {
  return google.maps.geometry.encoding.decodePath(encodedPolyline);
}, [encodedPolyline]);  // Only recompute when polyline changes
```

---

## 🎯 Quick Reference

### Minimal Example (Copy-Paste Ready)

```tsx
import { GoogleMap, Polyline } from '@react-google-maps/api';

function QuickPolyline() {
  const path = [
    { lat: 13.0827, lng: 80.2707 },
    { lat: 13.0569, lng: 80.2425 }
  ];

  return (
    <GoogleMap center={path[0]} zoom={13}>
      <Polyline
        path={path}
        options={{
          strokeColor: '#2563eb',
          strokeWeight: 6
        }}
      />
    </GoogleMap>
  );
}
```

### API Call Example

```bash
# Get route from Google
curl "https://maps.googleapis.com/maps/api/directions/json?origin=13.0827,80.2707&destination=13.0569,80.2425&mode=driving&key=YOUR_KEY"
```

---

## ✅ Summary

**3 Ways to Draw Polylines:**

1. **Manual** - Define points yourself
   - Simple, full control
   - Good for: Custom paths, testing

2. **Google Directions API** - Let Google calculate route
   - Automatic, follows roads
   - Good for: Real navigation, production

3. **Encoded Polyline** - Compressed format
   - Efficient, fast
   - Good for: Large datasets, mobile apps

**Choose based on your needs:**
- Testing/Demo → Manual
- Production App → Google Directions API + Encoded Polyline
- Real-time Updates → Encoded Polyline with WebSocket

---

## 🚀 Next Steps

1. Get a Google Maps API key
2. Try the "Complete Working Example" above
3. Customize colors and styles
4. Add markers for pickup/dropoff
5. Implement real-time updates

**Your polyline is now ready!** 🎉
