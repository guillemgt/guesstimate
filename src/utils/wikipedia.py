import requests
import json

def do_wiki_request(query):
    query_string = "&".join([f"{key}={requests.utils.quote(str(value))}" for key, value in query.items()])
    url = f"https://en.wikipedia.org/w/api.php?{query_string}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises exception for HTTP errors
        return response.text
    except requests.RequestException as e:
        print("[ERROR]", e)
        return None

def normalize_article(title):
    body = do_wiki_request({
        "action": "query",
        "titles": title,
        "format": "json",
        "formatversion": 2,
    })
    
    if body:
        try:
            json_data = json.loads(body)
            if json_data["query"]["pages"]:
                return json_data["query"]["pages"][0]["title"]
        except Exception as e:
            print("[ERROR]", e)
    return None

def normalize_articles(titles):
    body = do_wiki_request({
        "action": "query",
        "titles": "|".join(titles),
        "format": "json",
        "formatversion": 2,
    })
    
    if body:
        try:
            json_data = json.loads(body)
            return [page["title"] for page in json_data["query"]["pages"]]
        except Exception as e:
            print("[ERROR]", e)
    return []

def is_disambiguation(title):
    body = do_wiki_request({
        "action": "query",
        "prop": "categories",
        "titles": title,
        "format": "json",
        "formatversion": 2,
    })
    
    if body:
        try:
            json_data = json.loads(body)
            pages = json_data["query"]["pages"]
            if pages and "categories" in pages[0]:
                categories = pages[0]["categories"]
                for category in categories:
                    if category["title"] == "Category:All article disambiguation pages":
                        return True
            return False
        except Exception as e:
            print("[ERROR]", e)
    return False

def are_disambiguation(titles):
    body = do_wiki_request({
        "action": "query",
        "prop": "categories",
        "titles": "|".join(titles),
        "format": "json",
        "formatversion": 2,
    })
    
    disambiguation_titles = []
    
    if body:
        try:
            json_data = json.loads(body)
            for page in json_data["query"]["pages"]:
                if "categories" in page:
                    for category in page["categories"]:
                        if category["title"] == "Category:All article disambiguation pages" or category["title"] == "Category:Disambiguation pages":
                            disambiguation_titles.append(page["title"])
        except Exception as e:
            print("[ERROR]", e)
    return disambiguation_titles

def query(query_term):
    return do_wiki_request({
        "action": "parse",
        "prop": "text",
        "redirects": True,
        "format": "json",
        "page": query_term
    })
