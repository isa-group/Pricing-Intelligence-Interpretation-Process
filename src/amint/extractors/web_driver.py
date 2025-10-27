import os
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
import chromedriver_autoinstaller
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

class WebDriver:
    """
    A robust web scraper utilizing Selenium and BeautifulSoup to fetch and clean
    HTML content, aiming to reduce content size while preserving relevant information,
    especially potential pricing data.
    """
    def __init__(self, chromedriver_install_path: str = "/app/chromedriver", page_load_timeout: int = 30):
        self.driver = None
        self.chromedriver_install_path = chromedriver_install_path
        self.page_load_timeout = page_load_timeout
        self.raw_html_length = 0
        self.cleaned_html_length = 0
        self._setup_chrome_driver()

    def _setup_chrome_driver(self):
        try:
            installed_path = chromedriver_autoinstaller.install(path=self.chromedriver_install_path)
            logger.info(f"ChromeDriver installed at: {installed_path}")

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            service = Service(executable_path=installed_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except WebDriverException as e:
            logger.critical(f"Failed to initialize Chrome WebDriver. Is Chrome browser installed? Error: {e}")
            raise
        except Exception as e:
            logger.critical(f"An unexpected error occurred during Chrome WebDriver setup: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def _clean_html_content(self, html_content: str) -> str:
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # Keep JSON-LD scripts
            scripts_to_keep = soup.find_all('script', type='application/ld+json') or []
            scripts_to_keep = [script.__copy__() for script in scripts_to_keep]

            # Remove unwanted tags
            tags_to_remove = [
                'script', 'style', 'link', 'meta', 'noscript', 'head', 
                'header', 'nav', 'form', 'iframe', 'object', 'embed',
                'picture', 'source', 'canvas', 'audio', 'video', 'map', 'area',
                'track', 'applet', 'param', 'base', 'template', 'footer'
            ]
            for tag in tags_to_remove:
                for element in soup.find_all(tag):
                    element.decompose()
                    
            logger.info("Content length after removing unwanted tags: %d characters", len(str(soup)))

            # Remove known junk selectors
            selectors_to_remove = [
                '#wm-ipp-base', '[id*="cookie"]',
                '[class*="modal"]', '[id*="modal"]', '[class*="overlay"]',
                '[class*="coBranded"]', '[class*="sdk"]', '[id*="sdk"]',
                '[role*="alertdialog"]', '#gatsby-announcer', '[class*="skip-link"]',
            ]
            for selector in selectors_to_remove:
                for element in soup.select(selector):
                    element.decompose()
            
            logger.info("Content length after removing junk selectors: %d characters", len(str(soup)))

            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            logger.info("Content length after removing comments: %d characters", len(str(soup)))

            # Strip attributes, keep only essential ones
            allowed_attrs = ['href', 'src', 'alt', 'title', 'id', 'role']
            for tag in soup.find_all(True):
                for attr in list(tag.attrs):
                    if not (attr.startswith('data-') or attr in allowed_attrs):
                        del tag[attr]
            
            logger.info("Content length after stripping attributes: %d characters", len(str(soup)))

            # Remove empty tags
            for tag in soup.find_all(True):
                if not tag.get_text(strip=True) and (tag.name and tag.name not in ['img', 'svg', 'path', 'circle', 'rect']):
                    tag.decompose()
                    
            logger.info("Content length after removing empty tags: %d characters", len(str(soup)))

            # Re-append JSON-LD scripts at the end
            if scripts_to_keep:
                for script in scripts_to_keep:
                    if script and soup:
                        # Insert a copy of the script to avoid issues if original was decomposed
                        soup.insert(len(soup.contents), script.__copy__())

            try:
                # Normalize whitespace
                # serialize only the non-None children of body (or root) to avoid stray None's
                cleaned_html = soup.prettify()

                # collapse spaces/tabs
                cleaned_html = re.sub(r'[ \t]+', ' ', cleaned_html)
                # collapse 3+ blank lines
                cleaned_html = re.sub(r'\n{3,}', '\n\n', cleaned_html)
                # strip each line
                cleaned_html = '\n'.join(line.strip() for line in cleaned_html.split('\n'))
                # remove any entirely blank lines
                cleaned_html = re.sub(r'^\s*$(?:\r\n?|\n)', '', cleaned_html, flags=re.MULTILINE)

                logger.info("HTML content cleaned successfully.")
                return cleaned_html.strip()
            except Exception as e:
                logger.error(f"Error normalizing whitespace in HTML content: {e}")
                return html_content
        except Exception as e:
            logger.error(f"Error cleaning HTML content: {e}")
            return html_content

    def get_page_content(self, url: str) -> str:
        if not self.driver:
            logger.error("WebDriver is not initialized. Cannot fetch content.")
            raise RuntimeError("WebDriver not initialized.")
        try:
            logger.info(f"Attempting to fetch content from URL: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, self.page_load_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.driver.implicitly_wait(10)
            raw_content = self.driver.page_source
            
            # Almacenar tamaño del HTML original
            self.raw_html_length = len(raw_content)
            logger.info(f"Raw content length: {self.raw_html_length} characters")
            
            cleaned_content = self._clean_html_content(raw_content)
            
            # Almacenar tamaño del HTML limpio
            self.cleaned_html_length = len(cleaned_content)
            logger.info(f"Cleaned content length: {self.cleaned_html_length} characters")
            
            logger.info(f"Successfully retrieved and cleaned content from {url}")
            logger.info(f"Content reduce characters: {self.raw_html_length - self.cleaned_html_length} characters")
            if self.cleaned_html_length > 0:
                logger.info(f"Cleaning reduce ratio: {self.raw_html_length / self.cleaned_html_length:.2f}x")
            else:
                logger.warning("Cleaned content length is zero, cannot calculate ratio.")
            
            return cleaned_content
        except TimeoutException:
            logger.warning(f"Timeout occurred while loading {url}. Returning current page source.")
            return self._clean_html_content(self.driver.page_source)
        except WebDriverException as e:
            logger.error(f"WebDriver error fetching {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching {url}: {e}")
            raise

    def cleanup(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Chrome WebDriver closed")
