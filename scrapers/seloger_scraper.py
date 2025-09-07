"""
SeLoger.com scraper for French rental properties
"""

import logging
from typing import List, Dict, Any
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from config.settings import SearchCriteria
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class SeLogerScraper(BaseScraper):
    """Scraper for SeLoger.com rental listings"""
    
    BASE_URL = "https://www.seloger.com"
    
    def _build_search_url_impl(self, criteria: SearchCriteria, city: str, page: int) -> str:
        """Build SeLoger search URL"""
        
        # Property type mapping
        type_mapping = {
            'apartment': '1',
            'house': '2',
            'studio': '1'
        }
        
        # Get property types
        property_types = []
        for prop_type in criteria.property_types:
            if prop_type.lower() in type_mapping:
                property_types.append(type_mapping[prop_type.lower()])
        
        # Build search parameters
        params = {
            'projects': '2',  # 2 = rent, 1 = buy
            'types': ','.join(property_types) if property_types else '1,2',
            'places': f'{city}',
            'price': f'/{criteria.min_price}/{criteria.max_price}',
            'surface': f'/{int(criteria.min_rooms * 20)}/NaN',  # Approximate surface
            'rooms': f'/{criteria.min_rooms}/{criteria.max_rooms}',
            'page': str(page),
            'sort': 'initial_publication',
            'order': 'desc'
        }
        
        # Build URL
        search_path = "/list.htm"
        query_string = urlencode(params, safe='/')
        return f"{self.BASE_URL}{search_path}?{query_string}"
    
    def parse_listing_page(self, html: str, search_criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Parse SeLoger listing page"""
        soup = BeautifulSoup(html, 'html.parser')
        properties = []
        
        # Find property listings
        listings = soup.find_all('article', class_='c-pa-list')
        
        if not listings:
            # Try alternative selectors
            listings = soup.find_all('div', {'data-listing-id': True})
        
        logger.debug(f"Found {len(listings)} listings on page")
        
        for listing in listings:
            try:
                property_data = self.parse_single_listing(listing)
                if property_data and self.meets_criteria(property_data, search_criteria):
                    properties.append(property_data)
            except Exception as e:
                logger.error(f"Error parsing listing: {str(e)}")
                continue
        
        return properties
    
    def parse_single_listing(self, listing) -> Dict[str, Any]:
        """Parse a single property listing"""
        data = {}
        
        # Title
        title_elem = listing.find('h2', class_='c-pa-list-title') or listing.find('a', class_='c-pa-link')
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)
            
            # URL from title link
            link = title_elem.find('a') if title_elem.name != 'a' else title_elem
            if link and link.get('href'):
                data['url'] = urljoin(self.BASE_URL, link['href'])
        
        # Price
        price_elem = listing.find('span', class_='c-pa-price') or listing.find('div', class_='c-pa-criterion--price')
        if price_elem:
            data['price'] = price_elem.get_text(strip=True)
        
        # Room information
        rooms_elem = listing.find('li', class_='c-pa-criterion--room') or listing.find('div', text=lambda x: x and ('pièce' in x or 'T' in x))
        if rooms_elem:
            data['rooms'] = rooms_elem.get_text(strip=True)
        
        # Area
        area_elem = listing.find('li', class_='c-pa-criterion--surface') or listing.find('div', text=lambda x: x and 'm²' in x)
        if area_elem:
            data['area'] = area_elem.get_text(strip=True)
        
        # Location
        location_elem = listing.find('div', class_='c-pa-city') or listing.find('span', class_='c-pa-list-city')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            data['address'] = location_text
            
            # Extract postal code if present
            parts = location_text.split()
            for part in parts:
                if part.isdigit() and len(part) == 5:
                    data['postal_code'] = part
                    break
        
        # Images
        img_elem = listing.find('img')
        if img_elem and img_elem.get('src'):
            data['images'] = [img_elem['src']]
        
        # Property type (try to infer from title/description)
        title_lower = data.get('title', '').lower()
        if 'studio' in title_lower:
            data['property_type'] = 'studio'
        elif 'maison' in title_lower or 'villa' in title_lower:
            data['property_type'] = 'house'
        else:
            data['property_type'] = 'apartment'
        
        # Get property ID from URL or data attributes
        if listing.get('data-listing-id'):
            data['id'] = listing['data-listing-id']
        elif data.get('url'):
            # Extract ID from URL
            url_parts = data['url'].split('/')
            for part in url_parts:
                if part.isdigit():
                    data['id'] = part
                    break
        
        return data
    
    def get_property_details(self, property_url: str) -> Dict[str, Any]:
        """Get detailed information for a specific property"""
        if not property_url:
            return {}
        
        try:
            response = self.safe_get(property_url)
            if not response:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            details = {}
            
            # Description
            desc_elem = soup.find('div', class_='c-pa-description') or soup.find('section', class_='description')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # Detailed features
            features = soup.find_all('li', class_='criterion-item') or soup.find_all('div', class_='c-pa-criterion')
            feature_list = []
            for feature in features:
                feature_text = feature.get_text(strip=True)
                if feature_text:
                    feature_list.append(feature_text)
            
            if feature_list:
                details['features_list'] = feature_list
            
            # Contact information
            contact_info = self.extract_contact_info_from_page(soup)
            if contact_info:
                details['contact'] = contact_info
            
            # Additional images
            img_gallery = soup.find('div', class_='c-pa-gallery') or soup.find('div', class_='slider-container')
            if img_gallery:
                images = []
                for img in img_gallery.find_all('img'):
                    if img.get('src'):
                        images.append(img['src'])
                    elif img.get('data-src'):  # Lazy loaded images
                        images.append(img['data-src'])
                
                if images:
                    details['images'] = images
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting property details from {property_url}: {str(e)}")
            return {}
    
    def extract_contact_info(self, property_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract contact information from property data"""
        contact = property_data.get('contact', {})
        
        return {
            'agency_name': contact.get('agency', ''),
            'phone': contact.get('phone', ''),
            'email': contact.get('email', ''),
            'name': contact.get('agent', '')
        }
    
    def extract_contact_info_from_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information from property detail page"""
        contact_info = {}
        
        # Agency name
        agency_elem = soup.find('div', class_='c-pa-agency-name') or soup.find('span', class_='agency-name')
        if agency_elem:
            contact_info['agency'] = agency_elem.get_text(strip=True)
        
        # Phone number (often hidden/protected)
        phone_elem = soup.find('span', {'data-phone': True}) or soup.find('button', class_='phone-button')
        if phone_elem:
            phone = phone_elem.get('data-phone') or phone_elem.get_text(strip=True)
            if phone and phone != 'Voir le numéro':
                contact_info['phone'] = phone
        
        # Email (usually requires interaction, look for contact forms)
        email_form = soup.find('form', class_='contact-form') or soup.find('div', class_='contact-email')
        if email_form:
            email_input = email_form.find('input', {'type': 'email'})
            if email_input and email_input.get('value'):
                contact_info['email'] = email_input['value']
        
        # Agent name
        agent_elem = soup.find('div', class_='agent-name') or soup.find('span', class_='c-pa-agent')
        if agent_elem:
            contact_info['agent'] = agent_elem.get_text(strip=True)
        
        return contact_info
    
    def meets_criteria(self, property_data: Dict[str, Any], criteria: SearchCriteria) -> bool:
        """Check if property meets search criteria"""
        # Price check
        price = self.parse_price(property_data.get('price', ''))
        if price:
            if price < criteria.min_price or price > criteria.max_price:
                return False
        
        # Room check
        rooms = self.parse_rooms(property_data.get('rooms', ''))
        if rooms:
            if rooms < criteria.min_rooms or rooms > criteria.max_rooms:
                return False
        
        # Property type check
        prop_type = property_data.get('property_type', '').lower()
        if prop_type and criteria.property_types:
            if prop_type not in [pt.lower() for pt in criteria.property_types]:
                return False
        
        # Keyword filtering
        text_content = f"{property_data.get('title', '')} {property_data.get('description', '')}".lower()
        
        # Exclude keywords check
        if criteria.exclude_keywords:
            for exclude_keyword in criteria.exclude_keywords:
                if exclude_keyword.lower() in text_content:
                    return False
        
        # Include keywords check (at least one should match if specified)
        if criteria.keywords:
            keyword_match = any(keyword.lower() in text_content for keyword in criteria.keywords)
            if not keyword_match:
                return False
        
        return True