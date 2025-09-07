"""
Email automation for French Real Estate Rental Hunter
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any

from jinja2 import Template

from config.settings import Config
from database.models import Property, Contact, Communication, ContactMethod, get_db

logger = logging.getLogger(__name__)

class EmailSender:
    """Handles automated email communications"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def _get_smtp_connection(self):
        """Create SMTP connection"""
        try:
            server = smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT)
            server.starttls()
            server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
            return server
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            return None
    
    def _create_email_message(self, to_email: str, subject: str, body_html: str, body_text: str = None) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.config.EMAIL_FROM_NAME} <{self.config.EMAIL_FROM}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text version if provided
        if body_text:
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        # Add HTML version
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        
        return msg
    
    def send_initial_contact_email(self, property_obj: Property) -> bool:
        """Send initial contact email for a property"""
        try:
            # Get contact information (this would normally be scraped from the property page)
            db = get_db()
            contact = db.query(Contact).filter(Contact.property_id == property_obj.id).first()
            
            if not contact or not contact.email:
                logger.warning(f"No email contact found for property {property_obj.id}")
                return False
            
            # Prepare email content
            subject = f"Demande de visite - {property_obj.title}"
            
            email_template = Template(self._get_initial_contact_template())
            body_html = email_template.render(
                property=property_obj,
                contact=contact,
                sender_name=self.config.EMAIL_FROM_NAME
            )
            
            # Create and send email
            msg = self._create_email_message(contact.email, subject, body_html)
            
            server = self._get_smtp_connection()
            if not server:
                return False
            
            server.send_message(msg)
            server.quit()
            
            # Log communication
            self._log_communication(property_obj, contact, 'email', subject, body_html, 'sent')
            
            logger.info(f"✅ Initial contact email sent for property {property_obj.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send initial contact email: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def send_follow_up_email(self, contact: Contact) -> bool:
        """Send follow-up email"""
        try:
            if not contact.email:
                return False
            
            db = get_db()
            property_obj = db.query(Property).get(contact.property_id)
            
            if not property_obj:
                return False
            
            subject = f"Relance - Demande de visite - {property_obj.title}"
            
            email_template = Template(self._get_follow_up_template())
            body_html = email_template.render(
                property=property_obj,
                contact=contact,
                sender_name=self.config.EMAIL_FROM_NAME,
                attempt_number=contact.contact_attempts + 1
            )
            
            msg = self._create_email_message(contact.email, subject, body_html)
            
            server = self._get_smtp_connection()
            if not server:
                return False
            
            server.send_message(msg)
            server.quit()
            
            # Log communication
            self._log_communication(property_obj, contact, 'email', subject, body_html, 'sent')
            
            logger.info(f"✅ Follow-up email sent to contact {contact.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send follow-up email: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def send_urgent_follow_up_email(self, contact: Contact) -> bool:
        """Send urgent final follow-up email"""
        try:
            if not contact.email:
                return False
            
            db = get_db()
            property_obj = db.query(Property).get(contact.property_id)
            
            if not property_obj:
                return False
            
            subject = f"URGENT - Dernière relance - {property_obj.title}"
            
            email_template = Template(self._get_urgent_follow_up_template())
            body_html = email_template.render(
                property=property_obj,
                contact=contact,
                sender_name=self.config.EMAIL_FROM_NAME
            )
            
            msg = self._create_email_message(contact.email, subject, body_html)
            
            server = self._get_smtp_connection()
            if not server:
                return False
            
            server.send_message(msg)
            server.quit()
            
            # Log communication
            self._log_communication(property_obj, contact, 'email', subject, body_html, 'sent')
            
            logger.info(f"✅ Urgent follow-up email sent to contact {contact.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send urgent follow-up email: {str(e)}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def _log_communication(self, property_obj: Property, contact: Contact, method: str, subject: str, message: str, status: str):
        """Log communication in database"""
        try:
            db = get_db()
            
            communication = Communication(
                property_id=property_obj.id,
                contact_id=contact.id,
                method=ContactMethod.EMAIL,
                subject=subject,
                message=message,
                status=status,
                sent_at=datetime.utcnow()
            )
            
            db.add(communication)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging communication: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
    
    def _get_initial_contact_template(self) -> str:
        """Get initial contact email template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Demande de visite</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Demande de visite - {{ property.title }}</h2>
                
                <p>Bonjour{% if contact.name %} {{ contact.name }}{% endif %},</p>
                
                <p>Je me permets de vous contacter concernant le bien immobilier suivant :</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">{{ property.title }}</h3>
                    <p><strong>Prix :</strong> {{ property.price }} €/mois</p>
                    <p><strong>Ville :</strong> {{ property.city }}</p>
                    {% if property.rooms %}<p><strong>Pièces :</strong> {{ property.rooms }}</p>{% endif %}
                    {% if property.area %}<p><strong>Surface :</strong> {{ property.area }} m²</p>{% endif %}
                    <p><strong>Lien :</strong> <a href="{{ property.source_url }}">Voir l'annonce</a></p>
                </div>
                
                <p>Je suis très intéressé(e) par ce bien et souhaiterais organiser une visite dans les plus brefs délais.</p>
                
                <p>Mes disponibilités sont flexibles et je peux me déplacer rapidement. Je dispose de tous les documents nécessaires pour une location (fiches de paie, garanties, etc.).</p>
                
                <p>Pourriez-vous me confirmer vos disponibilités pour une visite ?</p>
                
                <p>Je reste à votre disposition pour toute information complémentaire.</p>
                
                <p style="margin-top: 30px;">
                    Cordialement,<br>
                    <strong>{{ sender_name }}</strong>
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                    <p>Ce message a été envoyé automatiquement par notre système de recherche immobilière.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_follow_up_template(self) -> str:
        """Get follow-up email template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Relance - Demande de visite</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">Relance - Demande de visite</h2>
                
                <p>Bonjour{% if contact.name %} {{ contact.name }}{% endif %},</p>
                
                <p>Je vous avais contacté(e) récemment concernant le bien immobilier suivant :</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">{{ property.title }}</h3>
                    <p><strong>Prix :</strong> {{ property.price }} €/mois</p>
                    <p><strong>Ville :</strong> {{ property.city }}</p>
                    <p><strong>Lien :</strong> <a href="{{ property.source_url }}">Voir l'annonce</a></p>
                </div>
                
                <p>N'ayant pas eu de retour de votre part, je me permets de vous relancer car ce bien correspond parfaitement à mes critères de recherche.</p>
                
                <p><strong>Je suis toujours très intéressé(e) et disponible pour une visite immédiate.</strong></p>
                
                <p>Si ce bien n'est plus disponible, pourriez-vous me le faire savoir ? Cela m'éviterait d'insister inutilement.</p>
                
                <p>Je vous remercie par avance pour votre retour.</p>
                
                <p style="margin-top: 30px;">
                    Cordialement,<br>
                    <strong>{{ sender_name }}</strong>
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                    <p>Relance automatique n°{{ attempt_number }} - Système de recherche immobilière</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_urgent_follow_up_template(self) -> str:
        """Get urgent follow-up email template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>URGENT - Dernière relance</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #c0392b; text-transform: uppercase;">🚨 URGENT - Dernière relance</h2>
                
                <p>Bonjour{% if contact.name %} {{ contact.name }}{% endif %},</p>
                
                <p><strong style="color: #e74c3c;">Il s'agit de ma dernière relance concernant ce bien.</strong></p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #e74c3c;">
                    <h3 style="margin-top: 0; color: #495057;">{{ property.title }}</h3>
                    <p><strong>Prix :</strong> {{ property.price }} €/mois</p>
                    <p><strong>Ville :</strong> {{ property.city }}</p>
                    <p><strong>Lien :</strong> <a href="{{ property.source_url }}">Voir l'annonce</a></p>
                </div>
                
                <p>Je vous ai contacté(e) à plusieurs reprises sans obtenir de réponse. Je comprends que vous puissiez être occupé(e), mais j'aimerais connaître le statut de ce bien :</p>
                
                <ul>
                    <li><strong>Est-il toujours disponible ?</strong></li>
                    <li><strong>Puis-je organiser une visite ?</strong></li>
                    <li><strong>Y a-t-il des documents spécifiques à préparer ?</strong></li>
                </ul>
                
                <p style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                    <strong>⏰ Je peux me déplacer aujourd'hui même si nécessaire.</strong><br>
                    Tous mes documents sont prêts (justificatifs de revenus, garants, etc.).
                </p>
                
                <p>Si vous ne souhaitez plus être contacté(e) ou si le bien n'est plus disponible, merci de me le faire savoir par un simple retour d'email.</p>
                
                <p>Je vous remercie par avance et reste dans l'attente de votre réponse.</p>
                
                <p style="margin-top: 30px;">
                    Cordialement,<br>
                    <strong>{{ sender_name }}</strong>
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                    <p>⚠️ Dernière relance automatique - Système de recherche immobilière</p>
                </div>
            </div>
        </body>
        </html>
        """