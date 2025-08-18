#!/usr/bin/env python3

import requests

# Test the token endpoint with alice/bob credentials
base_url = "http://localhost:8000"

# Test alice credentials
print("Testing alice/password...")
response = requests.post(
    f"{base_url}/token",
    data={"username": "alice", "password": "password"}
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("SUCCESS: alice login works")
    print(f"Token: {response.json()['access_token'][:50]}...")
else:
    print(f"FAILED: {response.json()}")

# Test bob credentials
print("\nTesting bob/password...")
response = requests.post(
    f"{base_url}/token",
    data={"username": "bob", "password": "password"}
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("SUCCESS: bob login works")
    print(f"Token: {response.json()['access_token'][:50]}...")
else:
    print(f"FAILED: {response.json()}")

# Test invalid credentials
print("\nTesting invalid credentials...")
response = requests.post(
    f"{base_url}/token",
    data={"username": "alice", "password": "wrongpassword"}
)

print(f"Status Code: {response.status_code}")
if response.status_code == 401:
    print("SUCCESS: Invalid credentials properly rejected")
else:
    print(f"UNEXPECTED: {response.json()}")