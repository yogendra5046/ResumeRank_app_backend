import requests
import uuid

BASE_URL = "http://localhost:8000/v1/auth"

def test_auth():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    full_name = "Test User"

    # 1. Register
    print(f"Registering user: {email}...")
    reg_data = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    try:
        response = requests.post(f"{BASE_URL}/register", json=reg_data)
        print(f"Register Status: {response.status_code}")
        print(f"Register Response: {response.json()}")

        if response.status_code != 200:
            return

        # 2. Login
        print(f"\nLogging in user: {email}...")
        login_data = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"Login Status: {response.status_code}")
        login_res = response.json()
        print(f"Login Response: {login_res}")

        if response.status_code == 200:
            print("\n✅ Auth Flow Working Correctly!")
            print(f"Token: {login_res['access_token'][:20]}...")
        else:
            print("\n❌ Auth Flow Failed!")

    except Exception as e:
        print(f"Error during auth test: {e}")
        print("Note: Make sure the server is running on http://localhost:8000")

if __name__ == "__main__":
    test_auth()
