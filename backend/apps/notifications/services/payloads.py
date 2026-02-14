def ride_assigned_payload(data: dict):
    return {
        "title": "Driver Assigned",
        "body": f"Your driver {data['driver_name']} is on the way",
        "ride_id": data["ride_id"],
        "vehicle": data["vehicle"],
    }


def ride_started_payload(data: dict):
    return {
        "title": "Ride Started",
        "body": "Your ride has started",
        "ride_id": data["ride_id"],
    }


def ride_completed_payload(data: dict):
    return {
        "title": "Ride Completed",
        "body": "Thanks for riding with us",
        "ride_id": data["ride_id"],
        "fare": data.get("fare"),
    }
