import urllib.request
import json
from datetime import datetime

def parse_isoformat(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def test():
    data = json.loads(urllib.request.urlopen('http://homeassistant.local:8123/hbc/api/status', timeout=5).read().decode())
    rates = data.get('rates', [])
    solar = data.get('solar_forecast', [])
    
    if not rates or not solar:
        print("Missing data")
        return
        
    print(f"Rates length: {len(rates)}")
    print(f"Solar length: {len(solar)}")
    
    # Simulate coordinator's loop
    aligned_solar = []
    
    for rate in rates:
        rate_start = parse_isoformat(rate['start']) if isinstance(rate['start'], str) else rate['start']
        
        def diff(x):
            x_start = parse_isoformat(x['start']) if isinstance(x['start'], str) else x['start']
            return abs((x_start - rate_start).total_seconds())
            
        closest = min(solar, key=diff)
        diff_secs = diff(closest)
        
        if diff_secs <= 1800:
            aligned_solar.append(closest['kw'])
        else:
            aligned_solar.append(0.0)
            
    # How many non-zero?
    non_zeros = [x for x in aligned_solar if x > 0.0]
    print(f"Aligned solar Non-zeros: {len(non_zeros)}")
    if non_zeros:
        print(f"Max aligned solar: {max(non_zeros)}")
    else:
        print("All aligned solar are 0.0!")
        print(f"Sample rates[0]: {rates[0]['start']}, Sample solar[0]: {solar[0]['start']}")
        
    # Check max raw solar
    raw_max = max(x['kw'] for x in solar)
    print(f"Raw maximal solar: {raw_max}")

if __name__ == "__main__":
    test()
