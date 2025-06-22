import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import base64

load_dotenv()

# === CONFIGURATION ===

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

PRICE_THRESHOLD = 500

origin = "ORD"  # Chicago O'Hare
destinations = ["LIS", "CDG", "AMS", "ATH", "MAD"]  # Add more airport codes here

start_date = datetime.strptime("2025-09-15", "%Y-%m-%d")
end_date = datetime.strptime("2025-10-15", "%Y-%m-%d")
trip_duration = 7  # Days between departure and return

# === AUTHENTICATION ===
def get_access_token():
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    
    # Prepare Basic Auth header
    client_creds = f"{API_KEY}:{API_SECRET}"
    b64_creds = base64.b64encode(client_creds.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_creds}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post(auth_url, headers=headers, data=data)

    print("Auth response status code:", response.status_code)
    print("Auth response body:", response.text)

    try:
        return response.json()["access_token"]
    except KeyError:
        print("[ERROR] 'access_token' not found in response.")
        return None

# === SEARCH FLIGHTS ===
def search_flights(token):
    headers = {"Authorization": f"Bearer {token}"}
    cheap_deals = []

    for destination in destinations:
        for i in range((end_date - start_date).days + 1):
            departure_date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            return_date = (start_date + timedelta(days=i + trip_duration)).strftime("%Y-%m-%d")

            print(f"Searching: {origin} -> {destination} | Depart: {departure_date} | Return: {return_date}")

            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "returnDate": return_date,
                "adults": 1,
                "currencyCode": "USD",
                "max": 5
            }

            url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                offers = response.json().get("data", [])
                print(f"  - Found {len(offers)} offers")
                for offer in offers:
                    price = float(offer["price"]["total"])
                    if price <= PRICE_THRESHOLD:
                        itinerary = offer["itineraries"]
                        dep = itinerary[0]["segments"][0]["departure"]["at"]
                        ret = itinerary[1]["segments"][0]["departure"]["at"]
                        cheap_deals.append({
                            "from": origin,
                            "to": destination,
                            "depart": dep[:10],
                            "return": ret[:10],
                            "price": price
                        })
            else:
                print(f"  [ERROR] {response.status_code}: {response.text}")

    return cheap_deals

# === EMAIL ALERT ===
def send_email(deals):
    if not deals:
        return

    body = "\n\n".join(
        f"{deal['from']} -> {deal['to']}\nDepart: {deal['depart']}\nReturn: {deal['return']}\nPrice: ${deal['price']}"
        for deal in deals
    )

    msg = MIMEText(body)
    msg["Subject"] = "🔥 Cheap Flight Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# === MAIN WORKFLOW ===
if __name__ == "__main__":
    token = get_access_token()
    deals = search_flights(token)
    send_email(deals)

    if deals:
        print(f"{len(deals)} cheap flight(s) found. Email sent!")
    else:
        print("No cheap flights found.")
