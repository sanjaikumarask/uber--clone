# 🎯 Polyline Implementation in YOUR Project - Step by Step

## ✅ Good News: Polylines Are Already Implemented!

Your Uber clone **already has polyline drawing fully working**. Let me show you exactly how it works in your codebase.

---

## 📍 Where Polylines Are Implemented

### **1. Backend - Getting Route from Google**

**File**: `backend/apps/rides/services/distance.py`

```python
def get_planned_route(origin, destination):
    """
    This function is called when a rider requests a ride.
    It contacts Google Directions API and gets the optimal route.
    """
    lat1, lng1 = origin
    lat2, lng2 = destination
    
    # Call Google Directions API
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{lat1},{lng1}",
        "destination": f"{lat2},{lng2}",
        "mode": "driving",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    
    resp = requests.get(url, params=params, timeout=5)
    data = resp.json()
    
    if data.get("status") == "OK":
        route = data["routes"][0]
        leg = route["legs"][0]
        
        return {
            "polyline": route["overview_polyline"]["points"],  # ← Encoded polyline string
            "distance_km": leg["distance"]["value"] / 1000,
            "duration_min": leg["duration"]["value"] / 60,
        }
```

**When is this called?**
- When rider clicks "Request Ride" button
- Location: `backend/apps/rides/views.py` → `CreateRideView`

---

### **2. Database - Storing Polyline**

**File**: `backend/apps/rides/views.py`

```python
class CreateRideView(APIView):
    def post(self, request):
        # Get pickup and dropoff from request
        pickup_lat = float(request.data["pickup_lat"])
        pickup_lng = float(request.data["pickup_lng"])
        drop_lat = float(request.data["drop_lat"])
        drop_lng = float(request.data["drop_lng"])
        
        # Get route from Google
        route = get_planned_route(
            (pickup_lat, pickup_lng), 
            (drop_lat, drop_lng)
        )
        
        # Create ride and store polyline
        ride = Ride.objects.create(
            rider=request.user,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            drop_lat=drop_lat,
            drop_lng=drop_lng,
            planned_route_polyline=route["polyline"],  # ← Stored here!
            planned_distance_km=route["distance_km"],
            planned_duration_min=route["duration_min"],
            status=Ride.Status.SEARCHING,
        )
```

**Database Field**: `Ride.planned_route_polyline` (TextField)

---

### **3. WebSocket - Sending to Frontend**

**File**: `backend/apps/rides/consumers.py`

```python
class RideConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # When rider connects to WebSocket
        ride = await self._get_ride()
        
        # Send ride data including polyline
        await self.send_json({
            "type": "WS_CONNECTED",
            "ride_id": ride.id,
            "payload": {
                "ride": {
                    "id": ride.id,
                    "status": ride.status,
                    "polyline": ride.planned_route_polyline,  # ← Sent to frontend
                    "pickup": {
                        "lat": ride.pickup_lat,
                        "lng": ride.pickup_lng
                    },
                    "dropoff": {
                        "lat": ride.drop_lat,
                        "lng": ride.drop_lng
                    }
                }
            }
        })
```

---

### **4. Frontend - Receiving Polyline**

**File**: `frontend/rider-web/src/domains/tracking/tracking.socket.ts`

```typescript
// WebSocket message handler
socket.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === "WS_CONNECTED") {
    const ride = msg.payload.ride;
    
    // Store polyline in state
    useRideStore.getState().setPolyline(ride.polyline);  // ← Received!
    useRideStore.getState().setPickup({
      lat: ride.pickup.lat,
      lng: ride.pickup.lng
    });
    useRideStore.getState().setDropoff({
      lat: ride.dropoff.lat,
      lng: ride.dropoff.lng
    });
  }
};
```

---

### **5. Frontend - Decoding Polyline**

**File**: `frontend/rider-web/src/components/MapView.tsx`

```tsx
export default function MapView({ center }: Props) {
  // Get encoded polyline from store
  const encodedPolyline = useRideStore((s) => s.polyline);
  
  // Decode it into array of {lat, lng} points
  const path = useMemo(() => {
    if (!isLoaded || !encodedPolyline || !window.google) return [];
    
    try {
      // Google's decoder: string → [{lat, lng}, {lat, lng}, ...]
      return google.maps.geometry.encoding.decodePath(encodedPolyline);
    } catch (e) {
      console.error("Failed to decode polyline:", e);
      return [];
    }
  }, [isLoaded, encodedPolyline]);
  
  // path is now an array like:
  // [
  //   {lat: 13.0827, lng: 80.2707},
  //   {lat: 13.0825, lng: 80.2705},
  //   {lat: 13.0820, lng: 80.2700},
  //   ...
  // ]
}
```

---

### **6. Frontend - Drawing Polylines**

**File**: `frontend/rider-web/src/components/MapView.tsx`

```tsx
return (
  <GoogleMap
    center={center}
    zoom={14}
    onLoad={(map) => setMapInstance(map)}
  >
    {/* Only render if we have decoded path */}
    {path.length > 0 && (
      <>
        {/* POLYLINE 1: Grey - Full Planned Route */}
        <Polyline
          path={path}  // ← The decoded coordinates
          options={{
            strokeColor: "#e5e7eb",  // Light grey
            strokeOpacity: 0.8,
            strokeWeight: 6,
            zIndex: 1,  // Behind blue line
          }}
        />
        
        {/* POLYLINE 2: Blue - Completed Route */}
        <Polyline
          path={completedRoute}  // ← Grows as driver moves
          options={{
            strokeColor: "#2563eb",  // Blue
            strokeOpacity: 1.0,
            strokeWeight: 6,
            zIndex: 2,  // On top of grey line
          }}
        />
      </>
    )}
    
    {/* Driver marker, pickup/dropoff markers, etc. */}
  </GoogleMap>
);
```

---

## 🔄 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. RIDER REQUESTS RIDE                                      │
│    - Selects pickup: (13.0827, 80.2707)                     │
│    - Selects dropoff: (13.0569, 80.2425)                    │
│    - Clicks "Request Ride"                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. BACKEND CALLS GOOGLE DIRECTIONS API                      │
│    File: backend/apps/rides/services/distance.py            │
│                                                              │
│    GET https://maps.googleapis.com/maps/api/directions/json │
│    ?origin=13.0827,80.2707                                  │
│    &destination=13.0569,80.2425                             │
│    &mode=driving                                            │
│    &key=YOUR_API_KEY                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. GOOGLE RETURNS ROUTE DATA                                │
│    {                                                         │
│      "routes": [{                                           │
│        "overview_polyline": {                               │
│          "points": "a~l~Fjk~uOnqC_c@{~@_dB..."  ← Encoded!  │
│        },                                                    │
│        "legs": [{                                           │
│          "distance": {"value": 4200},                       │
│          "duration": {"value": 720}                         │
│        }]                                                    │
│      }]                                                      │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. BACKEND STORES IN DATABASE                               │
│    File: backend/apps/rides/views.py                        │
│                                                              │
│    Ride.objects.create(                                     │
│      planned_route_polyline="a~l~Fjk~uOnqC_c@{~@_dB...",   │
│      planned_distance_km=4.2,                               │
│      planned_duration_min=12,                               │
│      ...                                                     │
│    )                                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. BACKEND SENDS VIA WEBSOCKET                              │
│    File: backend/apps/rides/consumers.py                    │
│                                                              │
│    socket.send({                                            │
│      "type": "WS_CONNECTED",                                │
│      "payload": {                                           │
│        "ride": {                                            │
│          "polyline": "a~l~Fjk~uOnqC_c@{~@_dB...",          │
│          "pickup": {lat: 13.0827, lng: 80.2707},           │
│          "dropoff": {lat: 13.0569, lng: 80.2425}           │
│        }                                                     │
│      }                                                       │
│    })                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. FRONTEND RECEIVES & STORES                               │
│    File: rider-web/src/domains/tracking/tracking.socket.ts │
│                                                              │
│    useRideStore.setPolyline("a~l~Fjk~uOnqC_c@{~@_dB...")   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. FRONTEND DECODES POLYLINE                                │
│    File: rider-web/src/components/MapView.tsx               │
│                                                              │
│    const path = google.maps.geometry.encoding.decodePath(  │
│      "a~l~Fjk~uOnqC_c@{~@_dB..."                           │
│    );                                                        │
│                                                              │
│    Result:                                                   │
│    [                                                         │
│      {lat: 13.0827, lng: 80.2707},                         │
│      {lat: 13.0825, lng: 80.2705},                         │
│      {lat: 13.0820, lng: 80.2700},                         │
│      ... (100+ points)                                      │
│      {lat: 13.0569, lng: 80.2425}                          │
│    ]                                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. FRONTEND DRAWS ON MAP                                    │
│    File: rider-web/src/components/MapView.tsx               │
│                                                              │
│    <Polyline                                                │
│      path={path}  ← Array of coordinates                    │
│      options={{                                             │
│        strokeColor: "#e5e7eb",  // Grey                     │
│        strokeWeight: 6                                      │
│      }}                                                      │
│    />                                                        │
│                                                              │
│    Result: Grey line appears on map! ✅                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Visual Result

When a ride is created, you see:

```
📍 Pickup (Green Marker)
   |
   | ← Grey Polyline (Full planned route from Google)
   |
   ●─────────────────────────────────────────────────────────● Dropoff (Red Marker)
   |
   | ← Blue Polyline (Completed route - grows as driver moves)
   |
   🚗 Driver Marker (Animated, follows blue line)
```

---

## 🧪 How to Test It's Working

### **Step 1: Start Backend**
```bash
cd backend
docker compose up -d
```

### **Step 2: Start Rider Web App**
```bash
cd frontend/rider-web
npm run dev
# Opens at http://localhost:5173
```

### **Step 3: Create a Ride**
1. Login as a rider
2. Select pickup location on map
3. Select dropoff location
4. Click "Request Ride"

### **Step 4: Check for Polyline**
✅ You should see a **grey line** connecting pickup to dropoff
✅ The line follows actual roads (not straight line)
✅ Line appears immediately after ride creation

### **Step 5: Accept Ride as Driver**
1. Open driver app
2. Go online
3. Accept the ride offer

### **Step 6: Watch Blue Line Grow**
✅ As driver moves, **blue line** grows over grey line
✅ Blue line shows completed portion of journey

---

## 🔍 Debugging: If Polyline Doesn't Show

### **Check 1: Google Maps API Key**

**File**: `frontend/rider-web/.env`

```bash
# Make sure this is set
VITE_GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

**Verify it's loaded:**
```tsx
// In MapView.tsx
const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
console.log('API Key:', apiKey ? 'Loaded ✅' : 'Missing ❌');
```

### **Check 2: Backend API Key**

**File**: `backend/.env` or `backend/config/settings.py`

```python
GOOGLE_MAPS_API_KEY = 'your_actual_api_key_here'
```

**Test it:**
```bash
docker exec -it uber_backend python manage.py shell

>>> from django.conf import settings
>>> print(settings.GOOGLE_MAPS_API_KEY)
# Should print your API key
```

### **Check 3: Polyline Data in Database**

```bash
docker exec -it uber_backend python manage.py shell

>>> from apps.rides.models import Ride
>>> ride = Ride.objects.last()
>>> print(ride.planned_route_polyline)
# Should print something like: "a~l~Fjk~uOnqC_c@{~@_dB..."
# If empty or None, Google API call failed
```

### **Check 4: WebSocket Data**

**Open browser console** (F12) when on ride tracking page:

```javascript
// You should see WebSocket messages
{
  "type": "WS_CONNECTED",
  "payload": {
    "ride": {
      "polyline": "a~l~Fjk~uOnqC_c@{~@_dB...",  // ← Should be present
      ...
    }
  }
}
```

### **Check 5: Decoded Path**

**Add console.log in MapView.tsx:**

```tsx
const path = useMemo(() => {
  if (!isLoaded || !encodedPolyline || !window.google) return [];
  
  try {
    const decoded = google.maps.geometry.encoding.decodePath(encodedPolyline);
    console.log('Decoded path:', decoded.length, 'points');  // ← Add this
    return decoded;
  } catch (e) {
    console.error("Failed to decode polyline:", e);
    return [];
  }
}, [isLoaded, encodedPolyline]);
```

**Expected output:**
```
Decoded path: 127 points ✅
```

---

## 🎨 Customization Examples

### **Change Polyline Color**

**File**: `frontend/rider-web/src/components/MapView.tsx`

```tsx
{/* Change grey to green */}
<Polyline
  path={path}
  options={{
    strokeColor: "#10b981",  // Green instead of grey
    strokeOpacity: 0.8,
    strokeWeight: 6,
  }}
/>

{/* Change blue to purple */}
<Polyline
  path={completedRoute}
  options={{
    strokeColor: "#8b5cf6",  // Purple instead of blue
    strokeOpacity: 1.0,
    strokeWeight: 6,
  }}
/>
```

### **Make Line Thicker**

```tsx
<Polyline
  path={path}
  options={{
    strokeColor: "#e5e7eb",
    strokeWeight: 10,  // Change from 6 to 10
  }}
/>
```

### **Add Dashed Line**

```tsx
<Polyline
  path={path}
  options={{
    strokeColor: "#e5e7eb",
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

---

## 📊 Summary

### **Your Project Already Has:**

✅ **Backend**: Google Directions API integration
✅ **Database**: Polyline storage in `Ride` model
✅ **WebSocket**: Real-time polyline transfer
✅ **Frontend**: Polyline decoding and rendering
✅ **Dual Polylines**: Grey (planned) + Blue (completed)
✅ **Real-time Updates**: Blue line grows as driver moves

### **Files Involved:**

| Component | File | Purpose |
|-----------|------|---------|
| API Call | `backend/apps/rides/services/distance.py` | Get route from Google |
| Storage | `backend/apps/rides/models.py` | Store polyline in DB |
| Creation | `backend/apps/rides/views.py` | Create ride with polyline |
| WebSocket | `backend/apps/rides/consumers.py` | Send to frontend |
| Receive | `rider-web/src/domains/tracking/tracking.socket.ts` | Receive polyline |
| Decode | `rider-web/src/components/MapView.tsx` | Decode string |
| Render | `rider-web/src/components/MapView.tsx` | Draw on map |

### **How It Works:**

1. Rider requests ride → Backend calls Google API
2. Google returns encoded polyline → Stored in database
3. WebSocket sends to frontend → Frontend decodes
4. Decoded coordinates → Rendered as grey line
5. Driver moves → Blue line grows over grey line

---

## 🚀 Next Steps

1. ✅ **Verify it's working**: Create a test ride and check for grey line
2. ✅ **Customize colors**: Change to match your brand
3. ✅ **Test real-time updates**: Watch blue line grow as driver moves
4. ✅ **Add more features**: Markers, info windows, etc.

**Your polyline implementation is production-ready!** 🎉
