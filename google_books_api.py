import requests, pprint

try:
    endpoint = "https://www.googleapis.com/books/v1/volumes"
    query_params = {
            "key": "AIzaSyAhmttZxkbUEsMvD_vgw3UUqu4g58W4f3o",
            "q": "intitle:Naruto",
            "maxResults": 5
        }
#     query_params = {
#     "q": "computer science",
#     "filter": "free-ebooks",
#     "printType": "books",
#     "langRestrict": "en",
#     "maxResults": 40
# }


    response = requests.get(endpoint, params=query_params)
    data = response.json()
    # pprint.pprint(data.get('items')[0].keys())
    # pprint.pprint(data)


    # pprint.pprint(data['items'][0]['volumeInfo'])
    
    # count = 0
    for book in data.get('items', []):
        book_info = book.get('volumeInfo', {})
        book_title = book_info.get('title', 'N/A')
        book_subtitle = book_info.get('subtitle', 'N/A')
        published_date = book_info.get('publishedDate', 'N/A')
        book_authors = ", ".join(book_info.get('authors', []))
        book_categories = ", ".join(book_info.get('categories', []))
        book_description = book_info.get('description', 'N/A')[:200]
        book_thumbnail = book_info.get('imageLinks', {}).get('thumbnail', 'N/A')
        book_link = book_info.get('infoLink', 'N/A')
        book_identifier = book_info.get('industryIdentifiers', [])
        book_id = book.get('id', '')
        for item in book_identifier:
            isbn_dict = item
        access_info = book.get('accessInfo', {})
        viewability = access_info.get('viewability')
        # if viewability=='NO_PAGES':
        #     print('Not Free')
        # elif viewability=='PARTIAL':
        #     print('Free')

        page_count = book_info.get('pageCount', 0)
        print(book_title)
        print(page_count)
        print()

        # pprint.pprint(data)

        # print(book_id)
        # print(book_link)
            # print(isbn_dict)
        # print()
        # print(book_title)
        # print(book_subtitle)
        # print(published_date)
        # print(book_authors)
        # print(book_categories)
        # print(book_description, end='.....\n')
        # print(book_thumbnail)
        # print(book_link)

    #     count += 1
    # print(count)
except Exception as e:
    print(e)


# word = 'Him'
# print(word[0:2])