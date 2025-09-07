"""
Base scraper class for French rental sites
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import Config, SearchCriteria
from database.models import Property, PropertyStatus
from utils.duplicate_detector import DuplicateDetector

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all rental site scrapers"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.duplicate_detector = DuplicateDetector(config)
        self.setup_session()
        
    def setup_session(self):
        """Setup HTTP session with headers and configuration"""
        self.session.headers.update({
            'User-Agent': self.config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_selenium_driver(self) -> webdriver.Chrome:
        """Create and configure Selenium Chrome driver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={self.config.USER_AGENT}')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
        
    def random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(self.config.SCRAPING_DELAY_MIN, self.config.SCRAPING_DELAY_MAX)
        time.sleep(delay)
        
    def safe_get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make safe HTTP request with error handling"""
        try:
            self.random_delay()
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None
            
    def parse_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
            
        # Remove common currency symbols and text
        price_clean = price_text.replace('€', '').replace('EUR', '').replace(' ', '')
        price_clean = price_clean.replace(',', '.').replace('CC', '').replace('charges', '')
        price_clean = ''.join(filter(lambda x: x.isdigit() or x == '.', price_clean))
        
        try:
            return float(price_clean) if price_clean else None
        except ValueError:
            return None
            
    def parse_area(self, area_text: str) -> Optional[float]:
        """Extract numeric area from text"""
        if not area_text:
            return None
            
        # Extract numbers followed by m² or m2
        area_clean = area_text.replace('m²', '').replace('m2', '').replace(' ', '')
        area_clean = ''.join(filter(lambda x: x.isdigit() or x == '.', area_clean))
        
        try:
            return float(area_clean) if area_clean else None
        except ValueError:
            return None
            
    def parse_rooms(self, rooms_text: str) -> Optional[int]:
        """Extract number of rooms from text"""
        if not rooms_text:
            return None
            
        # Common French room descriptions
        room_mappings = {
            'studio': 1,
            'T1': 1, 'F1': 1, '1 pièce': 1,
            'T2': 2, 'F2': 2, '2 pièces': 2,
            'T3': 3, 'F3': 3, '3 pièces': 3,
            'T4': 4, 'F4': 4, '4 pièces': 4,
            'T5': 5, 'F5': 5, '5 pièces': 5,
        }
        
        rooms_lower = rooms_text.lower()
        for key, value in room_mappings.items():
            if key.lower() in rooms_lower:
                return value
                
        # Extract first number found
        numbers = ''.join(filter(str.isdigit, rooms_text))
        try:
            return int(numbers[0]) if numbers else None
        except (ValueError, IndexError):
            return None
            
    def extract_features(self, description: str, title: str = '') -> Dict[str, bool]:
        """Extract property features from description and title"""
        text = f"{title} {description}".lower()
        
        features = {
            'balcony': any(word in text for word in ['balcon', 'terrasse', 'loggia']),
            'parking': any(word in text for word in ['parking', 'garage', 'stationnement']),
            'elevator': any(word in text for word in ['ascenseur', 'lift']),
            'cellar': any(word in text for word in ['cave', 'cellier']),
            'garden': any(word in text for word in ['jardin', 'garden']),
            'furnished': any(word in text for word in ['meublé', 'furnished']),
            'new': any(word in text for word in ['neuf', 'nouveau', 'récent']),
            'metro': any(word in text for word in ['métro', 'metro', 'rer', 'tramway']),
            'school': any(word in text for word in ['école', 'school', 'université']),
            'shops': any(word in text for word in ['commerce', 'magasin', 'shopping'])
        }
        
        return features
        
    def build_search_url(self, criteria: SearchCriteria, city: str, page: int = 1) -> str:
        """Build search URL for the specific site"""
        return self._build_search_url_impl(criteria, city, page)
        
    @abstractmethod
    def _build_search_url_impl(self, criteria: SearchCriteria, city: str, page: int) -> str:
        """Implementation of search URL building (to be implemented by subclasses)"""
        pass
        
    @abstractmethod
    def parse_listing_page(self, html: str, search_criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Parse a listing page and extract property information"""
        pass
        
    @abstractmethod
    def get_property_details(self, property_url: str) -> Dict[str, Any]:
        """Get detailed information for a specific property"""
        pass
        
    @abstractmethod
    def extract_contact_info(self, property_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract contact information from property data"""
        pass
        
    def scrape_city(self, city: str, criteria: SearchCriteria) -> List[Property]:
        """Scrape all properties for a specific city"""
        logger.info(f"🏙️ Starting to scrape {city} on {self.__class__.__name__}")
        
        properties = []
        page = 1
        max_pages = 10  # Limit to prevent infinite loops
        
        while page <= max_pages:
            try:
                search_url = self.build_search_url(criteria, city, page)
                logger.debug(f"📄 Scraping page {page}: {search_url}")
                
                response = self.safe_get(search_url)
                if not response:
                    logger.warning(f"Failed to get page {page} for {city}")
                    break
                    
                page_properties = self.parse_listing_page(response.text, criteria)
                
                if not page_properties:
                    logger.info(f"No more properties found on page {page}")
                    break
                    
                logger.info(f"📋 Found {len(page_properties)} properties on page {page}")
                
                # Process each property
                for prop_data in page_properties:
                    try:
                        # Get detailed information
                        detailed_data = self.get_property_details(prop_data.get('url', ''))
                        if detailed_data:
                            prop_data.update(detailed_data)
                            
                        # Create Property object
                        property_obj = self.create_property_from_data(prop_data, city)
                        if property_obj:
                            properties.append(property_obj)
                            
                    except Exception as e:
                        logger.error(f"Error processing property {prop_data.get('url', '')}: {str(e)}")
                        continue
                        
                page += 1
                
            except Exception as e:
                logger.error(f"Error scraping page {page} for {city}: {str(e)}")
                break
                
        logger.info(f"✅ Completed scraping {city}: found {len(properties)} properties")
        return properties
        
    def create_property_from_data(self, data: Dict[str, Any], city: str) -> Optional[Property]:
        """Create Property object from scraped data"""
        try:
            # Check for duplicate
            if self.duplicate_detector.is_duplicate(data):
                logger.debug(f"Skipping duplicate property: {data.get('url', '')}")
                return None
                
            property_obj = Property(
                title=data.get('title', ''),
                description=data.get('description', ''),
                price=self.parse_price(data.get('price', '')),
                rooms=self.parse_rooms(data.get('rooms', '')),
                area=self.parse_area(data.get('area', '')),
                property_type=data.get('property_type', ''),
                address=data.get('address', ''),
                city=city,
                postal_code=data.get('postal_code', ''),
                neighborhood=data.get('neighborhood', ''),
                source_site=self.__class__.__name__.lower().replace('scraper', ''),
                source_url=data.get('url', ''),
                source_id=data.get('id', ''),
                features=self.extract_features(data.get('description', ''), data.get('title', '')),
                images=data.get('images', []),
                status=PropertyStatus.NEW
            )
            
            return property_obj
            
        except Exception as e:
            logger.error(f"Error creating property from data: {str(e)}")
            return None
            
    def get_site_name(self) -> str:
        """Get the name of the scraping site"""
        return self.__class__.__name__.lower().replace('scraper', '')