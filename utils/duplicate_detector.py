"""
Duplicate detection utilities for rental properties
"""

import logging
from typing import Dict, Any, Optional, List
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz
import re

from config.settings import Config
from database.models import Property, get_db

logger = logging.getLogger(__name__)

class DuplicateDetector:
    """Detects duplicate rental properties across different sources"""
    
    def __init__(self, config: Config):
        self.config = config
        self.address_threshold = config.ADDRESS_SIMILARITY_THRESHOLD
        self.description_threshold = config.DESCRIPTION_SIMILARITY_THRESHOLD
        self.price_threshold = config.PRICE_DIFFERENCE_THRESHOLD
    
    def is_duplicate(self, property_data: Dict[str, Any]) -> bool:
        """Check if a property is a duplicate of existing ones"""
        try:
            db = get_db()
            
            # Get existing properties in the same city with similar price range
            price = self.parse_price(property_data.get('price', ''))
            city = property_data.get('city', '').strip().lower()
            
            if not price or not city:
                return False
            
            # Query properties within price range
            price_min = price - self.price_threshold
            price_max = price + self.price_threshold
            
            existing_properties = db.query(Property).filter(
                Property.city.ilike(f'%{city}%'),
                Property.price >= price_min,
                Property.price <= price_max,
                Property.still_available == True
            ).all()
            
            # Check each existing property for similarity
            for existing in existing_properties:
                if self._is_same_property(property_data, existing):
                    logger.info(f"🔍 Found duplicate property: {property_data.get('url', 'Unknown')}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def _is_same_property(self, new_data: Dict[str, Any], existing: Property) -> bool:
        """Compare two properties to determine if they're the same"""
        
        # 1. Address similarity
        address_similarity = self._calculate_address_similarity(
            new_data.get('address', ''),
            existing.address or ''
        )
        
        if address_similarity > self.address_threshold:
            logger.debug(f"High address similarity: {address_similarity:.2f}")
            return True
        
        # 2. Description similarity (if addresses are somewhat similar)
        if address_similarity > 0.6:  # Lower threshold for address before checking description
            description_similarity = self._calculate_description_similarity(
                new_data.get('description', '') or new_data.get('title', ''),
                existing.description or existing.title
            )
            
            if description_similarity > self.description_threshold:
                logger.debug(f"High description similarity: {description_similarity:.2f}")
                return True
        
        # 3. Exact room/area/price match with similar location
        if (address_similarity > 0.4 and
            self._exact_specs_match(new_data, existing)):
            logger.debug("Exact specifications match with similar address")
            return True
        
        return False
    
    def _calculate_address_similarity(self, address1: str, address2: str) -> float:
        """Calculate similarity between two addresses"""
        if not address1 or not address2:
            return 0.0
        
        # Normalize addresses
        addr1_norm = self._normalize_address(address1)
        addr2_norm = self._normalize_address(address2)
        
        # Use fuzzy string matching
        similarity = fuzz.ratio(addr1_norm, addr2_norm) / 100.0
        
        # Boost similarity if key elements match
        addr1_parts = set(addr1_norm.split())
        addr2_parts = set(addr2_norm.split())
        
        # Check for street number matches
        nums1 = set(re.findall(r'\d+', addr1_norm))
        nums2 = set(re.findall(r'\d+', addr2_norm))
        
        if nums1 and nums2 and nums1.intersection(nums2):
            similarity += 0.1  # Boost for matching street numbers
        
        # Check for street name matches
        common_words = addr1_parts.intersection(addr2_parts)
        if common_words:
            word_bonus = min(0.3, len(common_words) * 0.1)
            similarity += word_bonus
        
        return min(1.0, similarity)
    
    def _calculate_description_similarity(self, desc1: str, desc2: str) -> float:
        """Calculate similarity between two property descriptions"""
        if not desc1 or not desc2:
            return 0.0
        
        # Normalize descriptions
        desc1_norm = self._normalize_description(desc1)
        desc2_norm = self._normalize_description(desc2)
        
        # Use token sort ratio for better results with reordered text
        similarity = fuzz.token_sort_ratio(desc1_norm, desc2_norm) / 100.0
        
        return similarity
    
    def _exact_specs_match(self, new_data: Dict[str, Any], existing: Property) -> bool:
        """Check if property specifications match exactly"""
        
        # Parse new data
        new_price = self.parse_price(new_data.get('price', ''))
        new_rooms = self.parse_rooms(new_data.get('rooms', ''))
        new_area = self.parse_area(new_data.get('area', ''))
        
        # Price match (within threshold)
        if new_price and existing.price:
            price_diff = abs(new_price - existing.price)
            if price_diff > self.price_threshold:
                return False
        
        # Rooms match
        if new_rooms and existing.rooms:
            if new_rooms != existing.rooms:
                return False
        
        # Area match (within 10% tolerance)
        if new_area and existing.area:
            area_diff = abs(new_area - existing.area)
            area_tolerance = existing.area * 0.1  # 10% tolerance
            if area_diff > area_tolerance:
                return False
        
        return True
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison"""
        if not address:
            return ''
        
        # Convert to lowercase and remove extra whitespace
        normalized = address.lower().strip()
        
        # Replace common abbreviations
        replacements = {
            'rue': 'r',
            'avenue': 'av',
            'boulevard': 'bd',
            'place': 'pl',
            'square': 'sq',
            'impasse': 'imp',
            'passage': 'pass',
            'allée': 'all',
            'quai': 'q',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Remove common suffixes/prefixes
        normalized = re.sub(r'\b(paris|lyon|marseille|france)\b', '', normalized)
        normalized = re.sub(r'\b\d{5}\b', '', normalized)  # Remove postal codes
        
        # Remove extra whitespace and punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _normalize_description(self, description: str) -> str:
        """Normalize description for comparison"""
        if not description:
            return ''
        
        # Convert to lowercase and remove extra whitespace
        normalized = description.lower().strip()
        
        # Remove common real estate jargon that doesn't help identify uniqueness
        jargon_to_remove = [
            'appartement', 'logement', 'location', 'louer', 'disponible',
            'immédiatement', 'libre', 'contact', 'visite', 'dossier'
        ]
        
        for jargon in jargon_to_remove:
            normalized = normalized.replace(jargon, ' ')
        
        # Remove extra whitespace and punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
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
    
    def find_similar_properties(self, property_data: Dict[str, Any], limit: int = 5) -> List[Property]:
        """Find similar properties (not necessarily duplicates)"""
        try:
            db = get_db()
            
            price = self.parse_price(property_data.get('price', ''))
            city = property_data.get('city', '').strip().lower()
            
            if not price or not city:
                return []
            
            # Query properties within broader price range
            price_min = price - (self.price_threshold * 2)
            price_max = price + (self.price_threshold * 2)
            
            similar_properties = db.query(Property).filter(
                Property.city.ilike(f'%{city}%'),
                Property.price >= price_min,
                Property.price <= price_max,
                Property.still_available == True
            ).limit(limit).all()
            
            return similar_properties
            
        except Exception as e:
            logger.error(f"Error finding similar properties: {str(e)}")
            return []
        finally:
            if 'db' in locals():
                db.close()