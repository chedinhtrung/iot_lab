import requests

data = {"name": "detect_high_co2", "data": "secret"}

response = requests.post("http://192.168.0.103:30032/api/event", 
                         json = data)

print(response.status_code)
print(response.json())
