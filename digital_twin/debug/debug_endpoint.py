import requests

data = {"name": "train_bayesian_model", "data": "secret"}

response = requests.post("http://localhost:9000/api/event", 
                         json = data)

print(response.status_code)
print(response.json())
