import requests

data = {"name": "train_bayesian_model", "data": {"str":"hello"}}

response = requests.post("http://localhost:8000/api/train_bayesian_model", 
                         json = data)

print(response.status_code)
print(response.json())
