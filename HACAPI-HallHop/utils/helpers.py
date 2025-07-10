import logging
import requests
from bs4 import BeautifulSoup
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

def _get_retry_session(session=None, retries=3, backoff_factor=0.5,
                       status_forcelist=(429, 500, 502, 503, 504), allowed_methods=None):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods or frozenset(["HEAD", "GET", "OPTIONS", "POST"]),
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def safe_get(session: Session, url: str, **kwargs):
    session = _get_retry_session(session)
    try:
        logger.debug(f"GET {url}")
        response = session.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while requesting {url}: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error while requesting {url}: {e}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when requesting {url}")
    except Exception as e:
        logger.exception(f"Unexpected error during request to {url}: {e}")
    return None


def safe_post(session: Session, url: str, data=None, json=None, **kwargs):
    session = _get_retry_session(session)
    try:
        logger.debug(f"POST {url}")
        response = session.post(url, data=data, json=json, timeout=10, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while posting to {url}: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error while posting to {url}: {e}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when posting to {url}")
    except Exception as e:
        logger.exception(f"Unexpected error during POST to {url}: {e}")
    return None

def check_link(link):
    try:
        url = link.rstrip("/") + "/HomeAccess/Account/LogOn"
        logger.info(f"Checking HAC login URL: {url}")
        response = safe_get(requests.Session(), url)
        if not response:
            logger.warning("Failed to fetch the login page.")
            return False

        soup = BeautifulSoup(response.content, 'lxml')
        token_found = bool(soup.find('input', attrs={'name': '__RequestVerificationToken'}))

        if token_found:
            logger.info("✅ Link is valid and token retrieved.")
        else:
            logger.warning("⚠️ Link is reachable but token missing.")

        return token_found

    except Exception as e:
        logger.error(f"❌ Error checking link: {e}")
        return False

    
def safe_find_text(soup, id_):
    tag = soup.find('span', id=id_)
    return tag.text.strip() if tag else "N/A"