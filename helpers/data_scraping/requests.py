import requests
import time

def fetch_with_retry(url, headers, payload=None, max_retries=2, timeout=4):
    """Helper function to fetch data with retry logic, to prevent hanging and infinite retries
    If data is not present."""
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(url, headers=headers, data=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Non-200 status code {response.status_code} for {url}")
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout on {url} (attempt {attempt + 1})")
        except requests.exceptions.RequestException as e:
            print(f"Request failed on {url}: {e}")
        attempt += 1
        time.sleep(0.1)  # brief pause before retry
    print(f"Failed after {max_retries} attempts: {url}")
    return None