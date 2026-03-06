import requests
import pprint
endpoint = "https://www.googleapis.com/books/v1/volumes/"
params = {
    "key": "AIzaSyDcZHyec-pFO-wuWAVsNh3XqQkTsO1357I",
    "maxResults": 5,
    "q" : "Naruto"
}

response = requests.get(endpoint, params=params).json()
for book in response.get('items', []):
    published_date = book.get('volumeInfo', {}).get('publishedDate', None)
    if published_date:
        print(published_date[:4])
        

