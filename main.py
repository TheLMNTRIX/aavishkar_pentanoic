import os
import asyncio
import anthropic
from googleapiclient.discovery import build
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from requests.exceptions import RequestException

# Load environment variables from .env file
load_dotenv()

# Set up Google Custom Search API
API_KEY = "AIzaSyBmvwuRYAvlG8weBKvUYErEeIca7JEjb7Y"
SEARCH_ENGINE_ID = "06a1dba9d5ebb4d46"
service = build("customsearch", "v1", developerKey=API_KEY)

# Set up Anthropic client
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "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")
)

# System prompt for Claude Haiku
SYSTEM_PROMPT = """You are a SEO expert agent advising website owners how to improve their content. For this you will compare a superior ranked website 'SUPERIOR' ({superior_source}) with the website to be evaluated 'ORIGINAL' ({inferior_source}) and summarize why the superior website ranks better for the given 'KEYWORDS' in a maximum of 5 bullet points. Refer to SUPERIOR and ORIGINAL by their urls or page titles. You can include 1 or 2 concrete examples of what superior is doing better, or inferior is not doing good.
# SUPERIOR
{superior_content}
# ORIGINAL
{inferior_content}
# KEYWORDS
{keywords}
"""

def extract_keywords(text, max_keywords=8):
    """
    Extracts keywords from a given text using Claude Haiku.

    Args:
        text (str): The input text to extract keywords from.
        max_keywords (int): The maximum number of keywords to extract.

    Returns:
        list: A list of extracted keywords.
    """
    prompt = f"Extract up to {max_keywords} relevant keywords from the following text and the last keyword must be the type of text, example if the text is about e-commerce, the last keyword must be store :\n\n{text}"
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    response_text = message.content[0].text
    keywords = response_text.split(",")
    keywords = [kw.strip() for kw in keywords]
    return keywords

def get_top_results(keywords, num_results=6):
    """
    Retrieves the top URLs related to the given keywords using the Claude API.

    Args:
        keywords (list): The list of keywords to search for.
        num_results (int): The maximum number of results to retrieve.

    Returns:
        list: A list of top URLs related to the keywords.
    """
    keyword_str = ", ".join(keywords)
    system_prompt = f"""
    You are a search engine assistant. I will provide you with a list of keywords, and you will generate a list of up to {num_results} website URLs that are highly relevant and authoritative for those keywords. The URLs should be high-quality, reputable websites that provide valuable information related to the keywords. The output should only contain urls and no text or numbers. The URLs should be separated by new lines. Ensure to not inlude the path but just the protocol, subdomain, and domain name.\n\n
    Keywords: {keyword_str}
    """

    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": system_prompt}]
    )
    response_text = message.content[0].text
    top_urls = response_text.strip().split("\n")
    return top_urls

async def load_webpage_content(url):
    """
    Loads the content of a webpage using requests and BeautifulSoup.

    Args:
        url (str): The URL of the webpage to load.

    Returns:
        str: The content of the loaded webpage.
        None: If the URL cannot be accessed.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()
    except RequestException as e:
        print(f"Error accessing {url}: {e}")
        return None

def compare_content(given_content, top_contents, keywords, top_urls):
    """
    Compares the content of a given webpage with the content of top-ranking webpages
    and provides insights on why the latter ranks better.

    Args:
        given_content (str): The content of the given webpage.
        top_contents (list): A list of contents for the top-ranking webpages.
        keywords (list): The list of keywords used for the comparison.
        top_urls (list): A list of URLs for the top-ranking webpages.

    Returns:
        str: Insights and recommendations on how to improve the given webpage's content.
    """
    inferior_page = {
        "metadata": {"source": "Given Webpage"},
        "page_content": given_content
    }

    for superior_page_content, superior_page_url in zip(top_contents, top_urls):
        if superior_page_content is None:
            print(f"Skipping {superior_page_url} (content could not be fetched)")
            continue

        superior_page = {
            "metadata": {"source": superior_page_url},
            "page_content": superior_page_content
        }

        prompt = SYSTEM_PROMPT.replace("{superior_source}", superior_page["metadata"]["source"])
        prompt = prompt.replace("{superior_content}", superior_page["page_content"][:8000])
        prompt = prompt.replace("{inferior_source}", inferior_page["metadata"]["source"])
        prompt = prompt.replace("{inferior_content}", inferior_page["page_content"][:8000])
        prompt = prompt.replace("{keywords}", ", ".join(keywords))

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        response = message.content
        print(f"Insights and recommendations for '{superior_page['metadata']['source']}':\n{response}")
        
        
async def main():
    # Get user input for the webpage URL
    given_webpage_url = input("Enter the URL of the webpage (with 'https://'): ")

    # Load the given webpage content
    given_webpage_content = await load_webpage_content(given_webpage_url)

    # Extract keywords
    keywords = extract_keywords(given_webpage_content)
    print(f"Extracted keywords: {', '.join(keywords)}")

    # Get top search results
    top_urls = get_top_results(keywords)
    print(f"Top search results URLs: {', '.join(top_urls)}")

    # Load top webpage contents
    top_contents = [await load_webpage_content(url) for url in top_urls]

    # Compare the content and get insights
    compare_content(given_webpage_content, top_contents, keywords, top_urls)

if __name__ == "__main__":
    asyncio.run(main())
