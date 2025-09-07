#!/usr/bin/env python3
"""
French Real Estate Rental Hunter - Main Application Entry Point

This application automates the process of finding French rental properties,
contacting agencies, and tracking communications.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Config
from database.models import init_db
from web.app import create_app
from scrapers.scheduler import RentalScheduler
from utils.logger import setup_logging

def main():
    """Main application entry point"""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🏠 Starting French Real Estate Rental Hunter")
    logger.info(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize configuration
        config = Config()
        logger.info(f"📋 Configuration loaded successfully")
        
        # Initialize database
        init_db()
        logger.info("🗄️  Database initialized successfully")
        
        # Create Flask application
        app = create_app(config)
        logger.info("🌐 Flask application created successfully")
        
        # Initialize scheduler for background tasks
        scheduler = RentalScheduler(config)
        
        # Start scheduler in background
        if config.ENABLE_SCHEDULER:
            scheduler.start()
            logger.info("⏰ Background scheduler started")
        else:
            logger.info("⏰ Scheduler disabled in configuration")
        
        # Get port from environment or use default
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        logger.info(f"🚀 Starting web server on {host}:{port}")
        
        # Run Flask application
        app.run(
            host=host,
            port=port,
            debug=config.DEBUG,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted by user")
        
        # Cleanup scheduler
        if 'scheduler' in locals():
            scheduler.stop()
            logger.info("⏰ Scheduler stopped")
            
        logger.info("👋 French Real Estate Rental Hunter stopped")
        
    except Exception as e:
        logger.error(f"💥 Application failed to start: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()