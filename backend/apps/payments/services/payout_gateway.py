import razorpay
from django.conf import settings

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


from apps.common.circuit_breaker import circuit_breaker

@circuit_breaker(service_name="razorpay_payouts", failure_threshold=5, recovery_timeout=120)
def create_driver_payout(*, payout):
    """
    Calls Razorpay Payout API
    """

    user = payout.driver
    driver_profile = user.driver  # Access related Driver profile

    # RazorpayX Payouts API - using direct POST as 'payouts' helper is missing
    return client.post("/payouts", data={
        "account_number": settings.RAZORPAY_ACCOUNT_NUMBER,
        "amount": int(payout.net_amount * 100),  # paise
        "currency": "INR",
        "mode": "IMPS",
        "purpose": "payout",
        "fund_account": {
            "account_type": "bank_account",
            "bank_account": {
                "name": user.get_full_name(),
                "ifsc": driver_profile.ifsc_code,
                "account_number": driver_profile.bank_account_number,
            },
            "contact": {
                "name": user.get_full_name(),
                "email": user.email,
                "contact": user.phone,
                "type": "employee",
            },
        },
        "reference_id": payout.reference,
        "queue_if_low_balance": True,
    })


@circuit_breaker(service_name="razorpay_payouts", failure_threshold=5, recovery_timeout=120)
def get_payout_status(*, gateway_payout_id=None, reference_id=None):
    """
    Fetches the latest status of a payout from Razorpay.
    """
    if gateway_payout_id:
        return client.get(f"/payouts/{gateway_payout_id}", params={})
    
    if reference_id:
        # Payouts can be searched by reference_id
        response = client.get("/payouts", params={"reference_id": reference_id})
        items = response.get("items", [])
        return items[0] if items else None
        
    raise ValueError("Either gateway_payout_id or reference_id must be provided")
