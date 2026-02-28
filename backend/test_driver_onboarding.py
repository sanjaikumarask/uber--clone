import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_driver_onboarding():
    print("🚀 Starting Driver Onboarding Test...")
    
    # 1. Signup a new driver
    driver_phone = f"+9199999{int(time.time()) % 100000}"
    print(f"--- 1. Signing up driver: {driver_phone} ---")
    reg_response = requests.post(f"{BASE_URL}/users/register/", json={
        "phone": driver_phone,
        "password": "password123",
        "role": "driver",
        "first_name": "Test",
        "last_name": "Driver"
    })
    print(f"Signup Status: {reg_response.status_code}")
    
    # 2. Login as Driver
    print("\n--- 2. Logging in as Driver ---")
    login_res = requests.post(f"{BASE_URL}/users/login/driver/", json={
        "phone": driver_phone,
        "password": "password123"
    })
    driver_token = login_res.json()["access"]
    driver_id = login_res.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {driver_token}"}
    print(f"Login Success. Token acquired for User ID: {driver_id}")

    # 3. Upload Documents (License, RC, Insurance)
    print("\n--- 3. Uploading Documents ---")
    doc_types = ["LICENSE", "RC", "INSURANCE"]
    for doc_type in doc_types:
        upload_res = requests.post(
            f"{BASE_URL}/drivers/documents/upload/",
            headers=headers,
            json={
                "document_type": doc_type,
                "file": f"https://example.com/mock-{doc_type.lower()}.jpg"
            }
        )
        print(f"Uploaded {doc_type}: {upload_res.status_code}")

    # 4. Login as Admin
    print("\n--- 4. Logging in as Admin ---")
    admin_login_res = requests.post(f"{BASE_URL}/users/login/admin/", json={
        "username": "admin",
        "password": "adminpassword"
    })
    admin_token = admin_login_res.json()["access"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin Token acquired.")

    # 5. Admin fetches pending documents
    print("\n--- 5. Admin fetching pending docs ---")
    pending_res = requests.get(f"{BASE_URL}/drivers/admin/documents/pending/", headers=admin_headers)
    pending_docs = pending_res.json()
    print(f"Found {len(pending_docs)} pending documents total.")

    # 6. Admin approves our driver's documents
    print(f"\n--- 6. Admin approving docs for Driver User {driver_id} ---")
    our_docs = [d for d in pending_docs if d["phone"] == driver_phone]
    for doc in our_docs:
        app_res = requests.post(
            f"{BASE_URL}/drivers/admin/documents/{doc['id']}/approve/",
            headers=admin_headers,
            json={"action": "approve"}
        )
        print(f"Approved {doc['type']}: {app_res.status_code}")

    # 7. Final Verification Check
    print("\n--- 7. Final Verification Check ---")
    # Login again to see updated user state
    final_res = requests.get(f"{BASE_URL}/users/me/", headers=headers)
    user_data = final_res.json()
    print(f"User is_verified: {user_data['is_verified']}")
    
    if user_data['is_verified']:
        print("\n✅ TEST PASSED: Driver ID created and verified successfully!")
    else:
        print("\n❌ TEST FAILED: Driver is still unverified.")

if __name__ == "__main__":
    test_driver_onboarding()
