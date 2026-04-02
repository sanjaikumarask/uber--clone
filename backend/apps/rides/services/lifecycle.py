# backend/apps/rides/services/lifecycle.py
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.common.ordering import SequenceFencer
from apps.drivers.models import Driver
from apps.rides.models import Ride

from .otp import generate_and_attach_otp

logger = logging.getLogger(__name__)


def _handle_assigned(ride):
    """Logic for SEARCHING/OFFERED -> ASSIGNED."""
    otp = generate_and_attach_otp(ride)
    ride.save(update_fields=["otp_code", "otp_expires_at"])
    logger.info(f"Ride {ride.id}: Driver assigned, OTP {otp} generated")


def _handle_arrived(ride):
    """Logic for ASSIGNED -> ARRIVED."""
    ride.arrived_at = timezone.now()
    ride.save(update_fields=["arrived_at"])
    logger.info(f"Ride {ride.id}: Driver arrived")


def _handle_ongoing(ride):
    """Logic for ARRIVED -> ONGOING (Trip start)."""
    now = timezone.now()
    ride.otp_verified_at = now
    ride.start_time = now

    # Calculate waiting time
    ride.waiting_seconds = (
        int((now - ride.arrived_at).total_seconds()) if ride.arrived_at else 0
    )
    ride.save(update_fields=["otp_verified_at", "start_time", "waiting_seconds"])
    logger.info(f"Ride {ride.id}: Started. wait={ride.waiting_seconds}s")


def _handle_completed(ride):
    """Logic for ONGOING -> COMPLETED."""
    now = timezone.now()
    ride.completed_at = now
    ride.end_time = now
    ride.save(update_fields=["completed_at", "end_time", "status", "final_fare"])

    if ride.driver:
        # 1. Reset Driver Status
        ride.driver.status = Driver.Status.ONLINE
        ride.driver.save(update_fields=["status"])

        # 2. Update Stats
        from apps.drivers.models import DriverStats

        stats, _ = DriverStats.objects.get_or_create(driver=ride.driver.user)
        stats.completed_rides += 1
        stats.total_rides += 1
        stats.save()

        # 3. Create Earnings
        from decimal import Decimal

        from apps.payments.models import DriverEarnings

        commission = ride.final_fare * Decimal("0.20")
        DriverEarnings.objects.create(
            driver=ride.driver,
            ride=ride,
            amount=ride.final_fare,
            commission=commission,
            net_earning=ride.final_fare - commission,
        )

    # 4. Create Payment Placeholder
    from apps.payments.models import Payment

    Payment.objects.create(
        user=ride.rider,
        ride_id=ride.id,
        amount=ride.final_fare,
        status=Payment.Status.CREATED,
    )

    transaction.on_commit(lambda: _send_completion_notifications(ride))


def _handle_cancelled(ride):
    """Logic for ANY -> CANCELLED."""
    if ride.driver:
        ride.driver.status = Driver.Status.ONLINE
        ride.driver.save(update_fields=["status"])

    transaction.on_commit(lambda: _send_cancellation_notifications(ride))


def update_ride_status(
    ride: Ride, new_status: str, **kwargs
) -> Ride:
    """
    Central Ride State Authority.
    Uses state-specific handlers to maintain low cognitive complexity.
    """
    with transaction.atomic():
        try:
            ride.transition_to(new_status, **kwargs)
        except Exception as e:
            from apps.common.budget import FailureBudget

            FailureBudget.record_failure("ride_lifecycle")
            logger.error(f"[Authority] Rejected invalid state transition: {e}")
            raise

        handlers = {
            Ride.Status.OFFERED: lambda r: logger.info(
                f"Ride {r.id}: offered to driver"
            ),
            Ride.Status.ASSIGNED: _handle_assigned,
            Ride.Status.ARRIVED: _handle_arrived,
            Ride.Status.ONGOING: _handle_ongoing,
            Ride.Status.COMPLETED: _handle_completed,
            Ride.Status.CANCELLED: _handle_cancelled,
        }

        handler = handlers.get(new_status)
        if handler:
            handler(ride)

    # side effects
    transaction.on_commit(lambda: _broadcast_status_update(ride))

    if new_status in (
        Ride.Status.COMPLETED,
        Ride.Status.CANCELLED,
        Ride.Status.NO_SHOW,
    ):
        transaction.on_commit(lambda: SequenceFencer.clear_fence("ride", ride.id))
        from apps.common.ledger_recon import TripleEntryReconciliation

        transaction.on_commit(lambda: TripleEntryReconciliation.reconcile_ride(ride.id))

    return ride


def _send_completion_notifications(ride: Ride):
    """
    Sends receipt email and push notification.
    Uses the notification app infrastructure.
    """
    from decimal import Decimal

    from apps.notifications.models import Notification

    # 1. Calculate Breakdown (Simulating 5% IGST as per user's image)
    total = ride.final_fare or Decimal("0.00")
    tax_rate = Decimal("0.05")
    subtotal = (total / (Decimal("1.0") + tax_rate)).quantize(Decimal("0.01"))
    tax_amount = (total - subtotal).quantize(Decimal("0.01"))

    # 2. Professional HTML Template
    html_receipt = f"""
    <div style="font-family: 'Uber Move', Helvetica, Arial, sans-serif; max-width: 500px; margin: auto; padding: 40px 20px; background-color: #ffffff; color: #000000;">
        <div style="margin-bottom: 40px;">
            <h1 style="font-size: 36px; margin: 0; font-weight: 500;">Uber</h1>
            <p style="text-align: right; margin-top: -30px; color: #555; font-size: 14px;">Total: ₹{total}<br>{ride.completed_at.strftime('%a, %b %d, %Y')}</p>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 50px;">
            <div style="width: 60%;">
                <h2 style="font-size: 28px; line-height: 1.2; margin: 0 0 10px;">Thanks for riding, {ride.rider.first_name or 'there'}</h2>
                <p style="font-size: 16px; color: #555; margin: 0;">We hope you enjoyed your ride this {(ride.completed_at.strftime('%p').lower() == 'am' and 'morning') or 'afternoon'}.</p>
            </div>
            <div style="width: 35%; text-align: right;">
                <img src="https://mobile-content.uber.com/receipts/car_map_icon.png" alt="Car" style="width: 100px; max-width: 100%;">
            </div>
        </div>

        <div style="display: flex; justify-content: space-between; border-top: 1px solid #eeeeee; padding: 30px 0; margin-bottom: 20px;">
            <span style="font-size: 32px; font-weight: 500;">Total</span>
            <span style="font-size: 32px; font-weight: 500;">₹{total}</span>
        </div>

        <div style="border-bottom: 1px solid #eeeeee; padding-bottom: 20px; margin-bottom: 30px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 15px; color: #555;">
                <span style="font-size: 14px;">Trip Fare</span>
                <span style="font-size: 14px;">₹{subtotal}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 15px; color: #555;">
                <span style="font-size: 14px;">Subtotal</span>
                <span style="font-size: 14px;">₹{subtotal}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 15px; color: #888;">
                <span style="font-size: 14px;">Before Taxes</span>
                <span style="font-size: 14px;">₹{subtotal}</span>
            </div>
            <div style="display: flex; justify-content: space-between; color: #888;">
                <span style="font-size: 14px;">IGST (5%)</span>
                <span style="font-size: 14px;">₹{tax_amount}</span>
            </div>
        </div>

        <div style="margin-top: 40px; border-top: 2px solid #000; padding-top: 20px;">
            <p style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">Amount Charged</p>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 14px;"><img src="https://mobile-content.uber.com/receipts/payment_visa.png" width="24" style="vertical-align: middle; margin-right: 8px;"> Paid via App</span>
                <span style="font-size: 18px; font-weight: 500;">₹{total}</span>
            </div>
        </div>
        
        <p style="font-size: 12px; color: #999; margin-top: 60px; text-align: center;">
            This is a replica of a receipt for Uber Clone.<br>
            Ride ID: {ride.id}
        </p>
    </div>
    """

    Notification.objects.create(
        user=ride.rider,
        channel="email",
        type="RIDE_RECEIPT",
        payload={
            "subject": f"Your {ride.completed_at.strftime('%A')} morning trip with Uber",
            "body": f"Thanks for riding, {ride.rider.first_name}! Your total was ₹{total}.",
            "html": html_receipt,
        },
    )

    # 3. Push Notification
    Notification.objects.create(
        user=ride.rider,
        channel="push",
        type="RIDE_COMPLETED",
        payload={
            "title": "Ride Completed",
            "body": f"Your ride has ended. Fare: ₹{total}",
            "data": {"ride_id": str(ride.id)},
        },
    )


def _send_cancellation_notifications(ride: Ride):
    from apps.notifications.models import Notification

    # Notify Rider if driver cancelled or admin cancelled
    Notification.objects.create(
        user=ride.rider,
        channel="push",
        type="RIDE_CANCELLED",
        payload={
            "title": "Ride Cancelled",
            "body": "Your ride has been cancelled.",
            "data": {"ride_id": str(ride.id)},
        },
    )
    # Notify Driver if rider cancelled or admin cancelled
    if ride.driver:
        Notification.objects.create(
            user=ride.driver.user,
            channel="push",
            type="RIDE_CANCELLED",
            payload={
                "title": "Ride Cancelled",
                "body": "The rider has cancelled the trip.",
                "data": {"ride_id": str(ride.id)},
            },
        )


def _send_status_push_notification(ride: Ride):
    """
    Sends contextual push notifications to the rider based on status.
    """
    from apps.notifications.models import Notification

    title = ""
    body = ""

    if ride.status == Ride.Status.ASSIGNED:
        title = "Driver On The Way"
        body = f"Driver {ride.driver.user.first_name} is coming to pick you up."
    elif ride.status == Ride.Status.ARRIVED:
        title = "Driver Arrived"
        body = f"Your driver is at the pickup location. Use OTP: {ride.otp_code}"
    elif ride.status == Ride.Status.ONGOING:
        title = "Ride Started"
        body = "Have a safe trip!"
    else:
        return

    Notification.objects.create(
        user=ride.rider,
        channel="push",
        type=f"RIDE_STATUS_{ride.status}",
        payload={
            "title": title,
            "body": body,
            "data": {"ride_id": str(ride.id), "status": ride.status},
        },
    )


def _broadcast_status_update(ride: Ride):
    """
    Pushes status change to:
    1. The Rider (tracking page)
    2. The Driver (rides socket)
    3. The Admin (live map)
    4. Push Notifications
    """
    channel_layer = get_channel_layer()

    # Send PUSH
    _send_status_push_notification(ride)

    # 1. To Rider
    _notify_rider_channel(channel_layer, ride)

    # 2. To Driver
    _notify_driver_channel(channel_layer, ride)

    # 3. To Admin
    _notify_admin_channel(channel_layer, ride)


def _notify_rider_channel(channel_layer, ride):
    async_to_sync(channel_layer.group_send)(
        f"ride_{ride.id}",
        {
            "type": "ride_status_update",
            "status": ride.status,
            "otp_code": (
                ride.otp_code
                if ride.status in [Ride.Status.ASSIGNED, Ride.Status.ARRIVED]
                else None
            ),
        },
    )

    if ride.status == Ride.Status.COMPLETED:
        async_to_sync(channel_layer.group_send)(
            f"ride_{ride.id}",
            {
                "type": "ride_completed",
                "ride_id": ride.id,
                "fare": float(ride.final_fare) if ride.final_fare else 0,
            },
        )
    elif ride.status == Ride.Status.CANCELLED:
        async_to_sync(channel_layer.group_send)(
            f"ride_{ride.id}",
            {
                "type": "ride_completed",  # Both use same handler pattern in consumer usually?
                "ride_id": ride.id,
            },
        )


def _notify_driver_channel(channel_layer, ride):
    if ride.driver:
        async_to_sync(channel_layer.group_send)(
            f"driver_{ride.driver.id}_rides",
            {
                "type": "ride_status_update",
                "ride_id": ride.id,
                "status": ride.status,
            },
        )


def _notify_admin_channel(channel_layer, ride):
    admin_data = {
        "ride_id": ride.id,
        "status": ride.status,
        "driver_id": ride.driver_id,
        "rider_id": ride.rider_id,
    }

    if ride.driver:
        _add_driver_info_to_admin_data(admin_data, ride.driver)

    if ride.status not in [Ride.Status.COMPLETED, Ride.Status.CANCELLED]:
        admin_data["ride"] = _prepare_admin_ride_details(ride)
    else:
        admin_data["ride"] = None

    async_to_sync(channel_layer.group_send)(
        "admin_live_map",
        {
            "type": "admin_generic_event",
            "event": "RIDE_STATUS_UPDATED",
            "data": admin_data,
        },
    )


def _add_driver_info_to_admin_data(admin_data, driver):
    admin_data["driver_status"] = driver.status
    admin_data["driver_name"] = driver.user.get_full_name() or driver.user.username
    admin_data["driver_phone"] = driver.user.phone or ""
    if driver.last_lat and driver.last_lng:
        admin_data["driver_lat"] = float(driver.last_lat)
        admin_data["driver_lng"] = float(driver.last_lng)


def _prepare_admin_ride_details(ride):
    from apps.payments.models import Payment

    payment = Payment.objects.filter(
        ride_id=ride.id, status=Payment.Status.CAPTURED
    ).first()

    return {
        "id": ride.id,
        "status": ride.status,
        "payment_status": payment.status if payment else None,
        "base_fare": str(ride.base_fare),
        "final_fare": str(ride.final_fare) if ride.final_fare else None,
        "pickup": {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
        "pickup_address": ride.pickup_address or "",
        "dropoff": {"lat": float(ride.drop_lat), "lng": float(ride.drop_lng)},
        "drop_address": ride.drop_address or "",
        "polyline": ride.planned_route_polyline,
        "rider_id": ride.rider_id,
        "rider_name": ride.rider.get_full_name() or ride.rider.username,
        "distance_km": round(float(ride.actual_distance_km), 2),
        "vehicle_type": ride.vehicle_type,
    }
