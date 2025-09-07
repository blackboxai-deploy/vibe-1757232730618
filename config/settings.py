"""
Configuration settings for French Real Estate Rental Hunter
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class SearchCriteria:
    """Search criteria configuration"""
    cities: List[str]
    max_price: int
    min_price: int
    min_rooms: int
    max_rooms: int
    property_types: List[str]  # ['apartment', 'house', 'studio']
    keywords: List[str]
    exclude_keywords: List[str]

class Config:
    """Main configuration class"""
    
    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Ensure directories exist
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATA_DIR}/rental_hunter.db')
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Scraping configuration
    SCRAPING_DELAY_MIN = int(os.getenv('SCRAPING_DELAY_MIN', '2'))  # seconds
    SCRAPING_DELAY_MAX = int(os.getenv('SCRAPING_DELAY_MAX', '5'))  # seconds
    MAX_CONCURRENT_SCRAPERS = int(os.getenv('MAX_CONCURRENT_SCRAPERS', '3'))
    USE_PROXY = os.getenv('USE_PROXY', 'False').lower() == 'true'
    
    # User agent for web scraping
    USER_AGENT = os.getenv('USER_AGENT', 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
    
    # Email configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USERNAME)
    EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Rental Hunter Bot')
    
    # Twilio configuration for phone calls
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
    
    # Contact management
    MAX_CONTACT_ATTEMPTS = int(os.getenv('MAX_CONTACT_ATTEMPTS', '3'))
    FOLLOW_UP_DELAY_HOURS = int(os.getenv('FOLLOW_UP_DELAY_HOURS', '24'))
    EMAIL_TEMPLATE_DIR = BASE_DIR / "templates" / "email"
    
    # Scheduler configuration
    ENABLE_SCHEDULER = os.getenv('ENABLE_SCHEDULER', 'True').lower() == 'true'
    SCRAPING_SCHEDULE = os.getenv('SCRAPING_SCHEDULE', '0 9,15,21 * * *')  # 9AM, 3PM, 9PM daily
    CONTACT_SCHEDULE = os.getenv('CONTACT_SCHEDULE', '0 10,16 * * *')  # 10AM, 4PM daily
    FOLLOW_UP_SCHEDULE = os.getenv('FOLLOW_UP_SCHEDULE', '0 11,17 * * *')  # 11AM, 5PM daily
    
    # Search criteria - can be overridden via environment or web interface
    DEFAULT_SEARCH_CRITERIA = SearchCriteria(
        cities=os.getenv('SEARCH_CITIES', 'Paris,Lyon,Marseille,Toulouse,Nice').split(','),
        max_price=int(os.getenv('MAX_PRICE', '1500')),
        min_price=int(os.getenv('MIN_PRICE', '500')),
        min_rooms=int(os.getenv('MIN_ROOMS', '1')),
        max_rooms=int(os.getenv('MAX_ROOMS', '4')),
        property_types=os.getenv('PROPERTY_TYPES', 'apartment,studio').split(','),
        keywords=os.getenv('SEARCH_KEYWORDS', 'balcon,parking,métro,transport').split(','),
        exclude_keywords=os.getenv('EXCLUDE_KEYWORDS', 'meublé,furnished,colocation').split(',')
    )
    
    # Supported rental sites
    ENABLED_SCRAPERS = {
        'seloger': os.getenv('ENABLE_SELOGER', 'True').lower() == 'true',
        'leboncoin': os.getenv('ENABLE_LEBONCOIN', 'True').lower() == 'true',
        'pap': os.getenv('ENABLE_PAP', 'True').lower() == 'true',
        'logic_immo': os.getenv('ENABLE_LOGIC_IMMO', 'True').lower() == 'true',
        'bienici': os.getenv('ENABLE_BIENICI', 'True').lower() == 'true',
    }
    
    # Duplicate detection thresholds
    ADDRESS_SIMILARITY_THRESHOLD = float(os.getenv('ADDRESS_SIMILARITY_THRESHOLD', '0.85'))
    DESCRIPTION_SIMILARITY_THRESHOLD = float(os.getenv('DESCRIPTION_SIMILARITY_THRESHOLD', '0.75'))
    PRICE_DIFFERENCE_THRESHOLD = int(os.getenv('PRICE_DIFFERENCE_THRESHOLD', '50'))  # euros
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = LOGS_DIR / 'rental_hunter.log'
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []
        warnings = []
        
        # Check required email settings
        if not cls.SMTP_USERNAME or not cls.SMTP_PASSWORD:
            issues.append("SMTP credentials not configured")
        
        # Check Twilio settings if calling is enabled
        if not cls.TWILIO_ACCOUNT_SID or not cls.TWILIO_AUTH_TOKEN:
            warnings.append("Twilio not configured - phone calling disabled")
        
        # Check search criteria
        if not cls.DEFAULT_SEARCH_CRITERIA.cities:
            issues.append("No cities specified in search criteria")
        
        if cls.DEFAULT_SEARCH_CRITERIA.max_price <= cls.DEFAULT_SEARCH_CRITERIA.min_price:
            issues.append("Invalid price range in search criteria")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    @classmethod
    def get_scraper_urls(cls) -> Dict[str, str]:
        """Get base URLs for enabled scrapers"""
        return {
            'seloger': 'https://www.seloger.com',
            'leboncoin': 'https://www.leboncoin.fr',
            'pap': 'https://www.pap.fr',
            'logic_immo': 'https://www.logic-immo.com',
            'bienici': 'https://www.bienici.com'
        }