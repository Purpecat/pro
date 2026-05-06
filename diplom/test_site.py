import requests

API_KEY = "e21592892b6804ed299a4769778bda688d69239b"
SECRET = "7d299f0844fc146b35bb79a5bd57ff5c054e4571"

url = "https://cleaner.dadata.ru/api/v1/clean/address"
headers = {
    "Authorization": f"Token {API_KEY}",
    "X-Secret": SECRET,
    "Content-Type": "application/json"
}
data = ["Новосибирск Красный проспект 1"]

response = requests.post(url, json=data, headers=headers)
print(response.json())