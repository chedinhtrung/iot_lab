import requests

data = {"name": "detect_high_co2", "data": "secret"}

response = requests.post("http://localhost:9000/api/event", 
                         json = data)

print(response.status_code)
print(response.json())
