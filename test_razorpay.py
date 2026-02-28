import os
import razorpay
import sys

key_id = "rzp_test_SC2WBsKRJifL4Z"
key_secret = "e8J6Lyo7dSI57xL2fZ"

print(f"Testing Razorpay credentials...")
print(f"Key ID: {key_id}")
print(f"Key Secret Length: {len(key_secret)}")

client = razorpay.Client(auth=(key_id, key_secret))

try:
    # Try to fetch orders (minimal request)
    client.order.all({"count": 1})
    print("SUCCESS: Credentials are valid!")
except Exception as e:
    print(f"FAILED: {str(e)}")
