"""
Background task scheduler for French Real Estate Rental Hunter
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from config.settings import Config
from database.models import get_db, Property, Contact, ScrapingLog, ContactStatus, PropertyStatus
from scrapers.seloger_scraper import SeLogerScraper
from communication.email_sender import EmailSender
from communication.phone_caller import PhoneCaller

logger = logging.getLogger(__name__)

class RentalScheduler:
    """Manages scheduled tasks for rental property hunting"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scheduler = BackgroundScheduler(timezone='Europe/Paris')
        self.email_sender = EmailSender(config)
        self.phone_caller = PhoneCaller(config)
        
        # Initialize scrapers
        self.scrapers = {
            'seloger': SeLogerScraper(config)
        }
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        
        # Schedule jobs
        self._schedule_jobs()
        
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("✅ Scheduler started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
            
    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
            
    def _schedule_jobs(self):
        """Schedule all background jobs"""
        
        # Scraping job
        if self.config.SCRAPING_SCHEDULE:
            self.scheduler.add_job(
                func=self.scrape_all_sites,
                trigger=CronTrigger.from_crontab(self.config.SCRAPING_SCHEDULE),
                id='scrape_properties',
                name='Scrape rental properties',
                max_instances=1,
                misfire_grace_time=600  # 10 minutes
            )
            logger.info(f"📅 Scheduled scraping: {self.config.SCRAPING_SCHEDULE}")
        
        # Contact initiation job
        if self.config.CONTACT_SCHEDULE:
            self.scheduler.add_job(
                func=self.initiate_contacts,
                trigger=CronTrigger.from_crontab(self.config.CONTACT_SCHEDULE),
                id='initiate_contacts',
                name='Initiate new contacts',
                max_instances=1,
                misfire_grace_time=300  # 5 minutes
            )
            logger.info(f"📅 Scheduled contact initiation: {self.config.CONTACT_SCHEDULE}")
        
        # Follow-up job
        if self.config.FOLLOW_UP_SCHEDULE:
            self.scheduler.add_job(
                func=self.send_follow_ups,
                trigger=CronTrigger.from_crontab(self.config.FOLLOW_UP_SCHEDULE),
                id='send_follow_ups',
                name='Send follow-up communications',
                max_instances=1,
                misfire_grace_time=300  # 5 minutes
            )
            logger.info(f"📅 Scheduled follow-ups: {self.config.FOLLOW_UP_SCHEDULE}")
        
        # Daily cleanup job
        self.scheduler.add_job(
            func=self.daily_cleanup,
            trigger=CronTrigger(hour=2, minute=0),  # 2 AM daily
            id='daily_cleanup',
            name='Daily database cleanup',
            max_instances=1
        )
        logger.info("📅 Scheduled daily cleanup: 02:00")
        
    def scrape_all_sites(self):
        """Scrape all enabled sites for all configured cities"""
        logger.info("🚀 Starting scheduled scraping of all sites")
        
        total_properties = 0
        total_new = 0
        
        for city in self.config.DEFAULT_SEARCH_CRITERIA.cities:
            city = city.strip()
            if not city:
                continue
                
            logger.info(f"🏙️ Scraping properties in {city}")
            
            for site_name, scraper in self.scrapers.items():
                if not self.config.ENABLED_SCRAPERS.get(site_name, False):
                    logger.debug(f"Skipping disabled scraper: {site_name}")
                    continue
                    
                try:
                    # Create scraping log
                    scraping_log = ScrapingLog(
                        site=site_name,
                        started_at=datetime.utcnow(),
                        status='running',
                        search_criteria={
                            'city': city,
                            'criteria': self.config.DEFAULT_SEARCH_CRITERIA.__dict__
                        }
                    )
                    
                    db = get_db()
                    db.add(scraping_log)
                    db.commit()
                    
                    # Scrape properties
                    properties = scraper.scrape_city(city, self.config.DEFAULT_SEARCH_CRITERIA)
                    
                    # Save properties to database
                    new_count = 0
                    for prop in properties:
                        try:
                            # Check if property already exists
                            existing = db.query(Property).filter(
                                Property.source_url == prop.source_url
                            ).first()
                            
                            if not existing:
                                db.add(prop)
                                new_count += 1
                            else:
                                # Update existing property
                                existing.last_updated = datetime.utcnow()
                                existing.still_available = True
                        except Exception as e:
                            logger.error(f"Error saving property: {str(e)}")
                            continue
                    
                    db.commit()
                    
                    # Update scraping log
                    scraping_log.completed_at = datetime.utcnow()
                    scraping_log.status = 'completed'
                    scraping_log.properties_found = len(properties)
                    scraping_log.properties_new = new_count
                    db.commit()
                    
                    total_properties += len(properties)
                    total_new += new_count
                    
                    logger.info(f"✅ {site_name} - {city}: {len(properties)} found, {new_count} new")
                    
                except Exception as e:
                    logger.error(f"❌ Error scraping {site_name} for {city}: {str(e)}")
                    
                    if 'scraping_log' in locals():
                        scraping_log.completed_at = datetime.utcnow()
                        scraping_log.status = 'failed'
                        scraping_log.error_message = str(e)
                        db.commit()
                        
                finally:
                    if 'db' in locals():
                        db.close()
        
        logger.info(f"🎉 Scraping completed: {total_properties} total properties, {total_new} new")
        
    def initiate_contacts(self):
        """Initiate contact for new properties"""
        logger.info("📧 Starting contact initiation for new properties")
        
        try:
            db = get_db()
            
            # Get new properties that haven't been contacted
            new_properties = db.query(Property).filter(
                Property.status == PropertyStatus.NEW,
                Property.still_available == True
            ).all()
            
            contacted_count = 0
            
            for property_obj in new_properties:
                try:
                    # Create contact record if it doesn't exist
                    existing_contact = db.query(Contact).filter(
                        Contact.property_id == property_obj.id
                    ).first()
                    
                    if not existing_contact:
                        # Extract contact info from property data
                        contact = Contact(
                            property_id=property_obj.id,
                            name='',  # Will be filled when contact details are found
                            agency_name='',
                            email='',
                            phone='',
                            status=ContactStatus.PENDING
                        )
                        db.add(contact)
                        db.commit()
                    
                    # Try to send initial contact
                    if self.email_sender.send_initial_contact_email(property_obj):
                        property_obj.status = PropertyStatus.CONTACTED
                        contacted_count += 1
                    
                except Exception as e:
                    logger.error(f"Error initiating contact for property {property_obj.id}: {str(e)}")
                    continue
            
            db.commit()
            logger.info(f"✅ Contact initiation completed: {contacted_count} properties contacted")
            
        except Exception as e:
            logger.error(f"❌ Error in contact initiation: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
    
    def send_follow_ups(self):
        """Send follow-up communications for properties without responses"""
        logger.info("🔄 Starting follow-up communications")
        
        try:
            db = get_db()
            
            # Get contacts that need follow-up
            follow_up_time = datetime.utcnow() - timedelta(hours=self.config.FOLLOW_UP_DELAY_HOURS)
            
            contacts_to_follow_up = db.query(Contact).filter(
                Contact.status.in_([ContactStatus.EMAIL_SENT, ContactStatus.PHONE_CALLED]),
                Contact.responded == False,
                Contact.last_contact_attempt < follow_up_time,
                Contact.contact_attempts < self.config.MAX_CONTACT_ATTEMPTS
            ).all()
            
            follow_up_count = 0
            
            for contact in contacts_to_follow_up:
                try:
                    # Determine next contact method
                    if contact.contact_attempts == 0:
                        # First attempt - email
                        success = self.email_sender.send_follow_up_email(contact)
                    elif contact.contact_attempts == 1:
                        # Second attempt - phone call
                        success = self.phone_caller.make_follow_up_call(contact)
                    else:
                        # Final attempt - email with urgency
                        success = self.email_sender.send_urgent_follow_up_email(contact)
                    
                    if success:
                        contact.contact_attempts += 1
                        contact.last_contact_attempt = datetime.utcnow()
                        contact.schedule_follow_up(self.config.FOLLOW_UP_DELAY_HOURS)
                        follow_up_count += 1
                    
                except Exception as e:
                    logger.error(f"Error in follow-up for contact {contact.id}: {str(e)}")
                    continue
            
            db.commit()
            logger.info(f"✅ Follow-up completed: {follow_up_count} follow-ups sent")
            
        except Exception as e:
            logger.error(f"❌ Error in follow-up process: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
    
    def daily_cleanup(self):
        """Perform daily database cleanup tasks"""
        logger.info("🧹 Starting daily cleanup")
        
        try:
            db = get_db()
            
            # Mark old properties as potentially unavailable
            old_threshold = datetime.utcnow() - timedelta(days=7)
            old_properties = db.query(Property).filter(
                Property.last_updated < old_threshold,
                Property.still_available == True
            )
            
            old_count = old_properties.count()
            old_properties.update({Property.still_available: False})
            
            # Clean up old scraping logs (keep last 30 days)
            old_logs_threshold = datetime.utcnow() - timedelta(days=30)
            old_logs = db.query(ScrapingLog).filter(
                ScrapingLog.started_at < old_logs_threshold
            )
            
            logs_count = old_logs.count()
            old_logs.delete()
            
            db.commit()
            
            logger.info(f"✅ Cleanup completed: {old_count} properties marked unavailable, {logs_count} old logs removed")
            
        except Exception as e:
            logger.error(f"❌ Error in daily cleanup: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
    
    def _job_executed_listener(self, event):
        """Handle job execution events"""
        job = self.scheduler.get_job(event.job_id)
        if job:
            logger.info(f"✅ Job '{job.name}' executed successfully")
    
    def _job_error_listener(self, event):
        """Handle job error events"""
        job = self.scheduler.get_job(event.job_id)
        if job:
            logger.error(f"❌ Job '{job.name}' failed: {event.exception}")
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        jobs_info = []
        
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'running': self.scheduler.running,
            'jobs': jobs_info
        }