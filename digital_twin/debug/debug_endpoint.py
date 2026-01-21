import requests

data = {"name": "train_bayesian_model", "data": "secret"}

response = requests.post("http://192.168.0.103:30032/api/event", 
                         json = data)

print(response.status_code)
print(response.json())
