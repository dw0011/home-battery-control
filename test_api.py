import urllib.request
import json
import socket
import pprint

def test():
    print("Checking localhost:8123...")
    url = "http://127.0.0.1:8123/hbc/api/status"
    try:
        req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"Data received. Keys: {data.keys()}")
            
            print("\nFirst 2 rows of Plan from API:")
            if 'plan' in data and len(data['plan']) > 0:
                pprint.pprint(data['plan'][:2])
            else:
                print("No 'plan' array.")
                
            print("\nFirst 2 rows of solar_forecast:")
            if 'solar_forecast' in data and len(data['solar_forecast']) > 0:
                pprint.pprint(data['solar_forecast'][:2])
            else:
                print("No 'solar_forecast' array.")
                
            print("\nFirst 2 rows of load_forecast:")
            if 'load_forecast' in data and len(data['load_forecast']) > 0:
                pprint.pprint(data['load_forecast'][:2])
            else:
                print("No 'load_forecast' array.")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test()
