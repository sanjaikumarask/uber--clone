# backend/apps/notifications/services/registry.py

# specific payload builders can be imported, or defined here
def default_builder(data):
    return data

EVENT_REGISTRY = {
    # ---------------------------------------------------------
    # FLOWCHART STEP: Broadcast (Find Driver)
    # ---------------------------------------------------------
    "DRIVER_RIDE_OFFER": {
        "channels": ["ws"],  # Websocket is critical for live driver screen
        "payload_builder": default_builder,
    },
    
    # ---------------------------------------------------------
    # FLOWCHART STEP: Ride Assigned (Notify Rider)
    # ---------------------------------------------------------
    "RIDE_ASSIGNED": {
        "channels": ["ws", "push"],
        "payload_builder": default_builder,
    },
    
    # ---------------------------------------------------------
    # FLOWCHART STEP: Ride Started / Ongoing
    # ---------------------------------------------------------
    "RIDE_STARTED": {
        "channels": ["ws"],
        "payload_builder": default_builder,
    },
    
    # ---------------------------------------------------------
    # FLOWCHART STEP: Ride Completed / Payment
    # ---------------------------------------------------------
    "RIDE_COMPLETED": {
        "channels": ["ws", "email"],
        "payload_builder": default_builder,
    },

    # ---------------------------------------------------------
    # FLOWCHART STEP: Cancelled / Issues
    # ---------------------------------------------------------
    "RIDE_CANCELLED": {
        "channels": ["ws", "push"],
        "payload_builder": default_builder,
    },
}