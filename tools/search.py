import os
from serpapi import GoogleSearch

def web_search(query):
    """
    Performs a Google search using SerpApi and returns the top results.
    Useful for finding real-time info like menus, weather, or news.
    """
    params = {
        "q": query,
        "location": "Austin, Texas, United States", # You can change this to your location
        "hl": "en",
        "gl": "us",
        "google_domain": "google.com",
        "api_key": os.getenv("SERPAPI_API_KEY")
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Extract the 'organic results' which are the standard web links
        organic_results = results.get("organic_results", [])
        
        # SOC2: Data Minimization. We only take the top 3 snippets to save on processing.
        snippets = [res.get("snippet", "") for res in organic_results[:3]]
        
        return " | ".join(snippets) if snippets else "No search results found."
    
    except Exception as e:
        return f"Search error: {str(e)}"