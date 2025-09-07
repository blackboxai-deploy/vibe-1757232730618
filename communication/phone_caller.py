"""
Phone calling automation for French Real Estate Rental Hunter
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from config.settings import Config
from database.models import Property, Contact, Communication, ContactMethod, get_db

logger = logging.getLogger(__name__)

class PhoneCaller:
    """Handles automated phone communications using Twilio"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        
        if self.config.TWILIO_ACCOUNT_SID and self.config.TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(
                    self.config.TWILIO_ACCOUNT_SID,
                    self.config.TWILIO_AUTH_TOKEN
                )
                logger.info("✅ Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio client: {str(e)}")
        else:
            logger.warning("⚠️ Twilio credentials not configured - phone calling disabled")
    
    def make_follow_up_call(self, contact: Contact) -> bool:
        """Make automated follow-up call"""
        if not self.client:
            logger.warning("Twilio not configured - cannot make phone call")
            return False
        
        if not contact.phone:
            logger.warning(f"No phone number for contact {contact.id}")
            return False
        
        try:
            db = get_db()
            property_obj = db.query(Property).get(contact.property_id)
            
            if not property_obj:
                return False
            
            # Create TwiML for the call
            twiml_message = self._generate_call_script(property_obj, contact)
            
            # Make the call
            call = self.client.calls.create(
                twiml=twiml_message,
                to=contact.phone,
                from_=self.config.TWILIO_PHONE_NUMBER,
                record=True,  # Record for quality assurance
                timeout=30,
                status_callback_event=['initiated', 'answered', 'completed'],
                status_callback_method='POST'
            )
            
            # Log communication
            self._log_communication(
                property_obj, 
                contact, 
                'phone', 
                f"Appel automatique - {property_obj.title}", 
                twiml_message, 
                'initiated',
                {'call_sid': call.sid, 'twilio_status': call.status}
            )
            
            logger.info(f"✅ Phone call initiated for contact {contact.id} - Call SID: {call.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"❌ Twilio error making call to contact {contact.id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error making call to contact {contact.id}: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def make_initial_call(self, contact: Contact) -> bool:
        """Make initial automated call"""
        if not self.client:
            logger.warning("Twilio not configured - cannot make phone call")
            return False
        
        if not contact.phone:
            logger.warning(f"No phone number for contact {contact.id}")
            return False
        
        try:
            db = get_db()
            property_obj = db.query(Property).get(contact.property_id)
            
            if not property_obj:
                return False
            
            # Create TwiML for initial call
            twiml_message = self._generate_initial_call_script(property_obj, contact)
            
            # Make the call
            call = self.client.calls.create(
                twiml=twiml_message,
                to=contact.phone,
                from_=self.config.TWILIO_PHONE_NUMBER,
                record=True,
                timeout=30
            )
            
            # Log communication
            self._log_communication(
                property_obj, 
                contact, 
                'phone', 
                f"Appel initial - {property_obj.title}", 
                twiml_message, 
                'initiated',
                {'call_sid': call.sid, 'twilio_status': call.status}
            )
            
            logger.info(f"✅ Initial phone call made for contact {contact.id} - Call SID: {call.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"❌ Twilio error making initial call to contact {contact.id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error making initial call to contact {contact.id}: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def _generate_call_script(self, property_obj: Property, contact: Contact) -> str:
        """Generate TwiML script for follow-up call"""
        agency_name = contact.agency_name or "votre agence"
        
        script = f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Pause length="1"/>
            <Say voice="alice" language="fr-FR">
                Bonjour, je vous appelle concernant le bien immobilier situé {property_obj.address or property_obj.city} 
                au prix de {property_obj.price} euros par mois. 
                
                Je vous ai envoyé un email récemment mais n'ai pas eu de retour. 
                
                Je suis très intéressé par ce bien et souhaiterais organiser une visite rapidement. 
                Je dispose de tous les documents nécessaires.
                
                Pourriez-vous me rappeler pour organiser une visite ? 
                
                Je vous remercie et vous souhaite une bonne journée.
            </Say>
            <Pause length="2"/>
            <Say voice="alice" language="fr-FR">
                Merci, au revoir.
            </Say>
        </Response>
        """
        
        return script.strip()
    
    def _generate_initial_call_script(self, property_obj: Property, contact: Contact) -> str:
        """Generate TwiML script for initial call"""
        script = f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Pause length="1"/>
            <Say voice="alice" language="fr-FR">
                Bonjour, je vous appelle concernant votre annonce immobilière pour le bien situé {property_obj.address or property_obj.city}.
                
                Le bien proposé à {property_obj.price} euros par mois m'intéresse beaucoup.
                
                Je souhaiterais organiser une visite dans les plus brefs délais. 
                Je dispose de tous les justificatifs nécessaires pour la location.
                
                Pourriez-vous me rappeler pour convenir d'un rendez-vous ?
                
                Je vous remercie et reste dans l'attente de votre retour.
            </Say>
            <Pause length="2"/>
            <Say voice="alice" language="fr-FR">
                Bonne journée.
            </Say>
        </Response>
        """
        
        return script.strip()
    
    def _log_communication(self, property_obj: Property, contact: Contact, method: str, subject: str, message: str, status: str, metadata: Dict[str, Any] = None):
        """Log phone communication in database"""
        try:
            db = get_db()
            
            communication = Communication(
                property_id=property_obj.id,
                contact_id=contact.id,
                method=ContactMethod.PHONE,
                subject=subject,
                message=message,
                status=status,
                sent_at=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            db.add(communication)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging phone communication: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
    
    def handle_call_status_update(self, call_sid: str, status: str, duration: str = None) -> bool:
        """Handle Twilio webhook for call status updates"""
        try:
            db = get_db()
            
            # Find communication record by call SID
            communication = db.query(Communication).filter(
                Communication.metadata.contains({'call_sid': call_sid})
            ).first()
            
            if communication:
                # Update communication status
                communication.status = status
                
                if status == 'completed' and duration:
                    if not communication.metadata:
                        communication.metadata = {}
                    communication.metadata['duration'] = duration
                    communication.delivered_at = datetime.utcnow()
                
                db.commit()
                logger.info(f"✅ Updated call status for SID {call_sid}: {status}")
                return True
            else:
                logger.warning(f"⚠️ Communication record not found for call SID: {call_sid}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error handling call status update: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def get_call_history(self, contact_id: int) -> list:
        """Get call history for a specific contact"""
        try:
            db = get_db()
            
            calls = db.query(Communication).filter(
                Communication.contact_id == contact_id,
                Communication.method == ContactMethod.PHONE
            ).order_by(Communication.sent_at.desc()).all()
            
            return [call.to_dict() for call in calls]
            
        except Exception as e:
            logger.error(f"Error getting call history for contact {contact_id}: {str(e)}")
            return []
        finally:
            if 'db' in locals():
                db.close()
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured"""
        return self.client is not None
    
    def test_configuration(self) -> Dict[str, Any]:
        """Test Twilio configuration"""
        if not self.client:
            return {
                'success': False,
                'message': 'Twilio client not initialized'
            }
        
        try:
            # Test by getting account info
            account = self.client.api.account.fetch()
            
            return {
                'success': True,
                'message': f'Twilio configured successfully - Account: {account.friendly_name}',
                'account_sid': account.sid,
                'status': account.status
            }
            
        except TwilioException as e:
            return {
                'success': False,
                'message': f'Twilio configuration error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error testing Twilio: {str(e)}'
            }