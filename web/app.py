"""
Flask web application for French Real Estate Rental Hunter
"""

import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

from config.settings import Config
from database.models import Property, Contact, Communication, ScrapingLog, PropertyStatus, get_db
from scrapers.seloger_scraper import SeLogerScraper

logger = logging.getLogger(__name__)

def create_app(config: Config = None) -> Flask:
    """Create and configure Flask application"""
    
    if config is None:
        config = Config()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db = SQLAlchemy()
    db.init_app(app)
    
    @app.route('/')
    def dashboard():
        """Main dashboard"""
        try:
            db_session = get_db()
            
            # Get statistics
            stats = {
                'total_properties': db_session.query(Property).count(),
                'new_properties': db_session.query(Property).filter(Property.status == PropertyStatus.NEW).count(),
                'contacted_properties': db_session.query(Property).filter(Property.status == PropertyStatus.CONTACTED).count(),
                'responded_properties': db_session.query(Property).filter(Property.status == PropertyStatus.RESPONDED).count(),
            }
            
            # Get recent properties
            recent_properties = db_session.query(Property).order_by(Property.first_seen.desc()).limit(10).all()
            
            # Get recent scraping logs
            recent_logs = db_session.query(ScrapingLog).order_by(ScrapingLog.started_at.desc()).limit(5).all()
            
            return render_template('dashboard.html', 
                                 stats=stats, 
                                 recent_properties=recent_properties,
                                 recent_logs=recent_logs)
            
        except Exception as e:
            logger.error(f"Error loading dashboard: {str(e)}")
            flash('Error loading dashboard data', 'error')
            return render_template('dashboard.html', stats={}, recent_properties=[], recent_logs=[])
        finally:
            if 'db_session' in locals():
                db_session.close()
    
    @app.route('/properties')
    def properties():
        """Properties listing page"""
        try:
            db_session = get_db()
            
            # Get filters from request
            city_filter = request.args.get('city', '')
            status_filter = request.args.get('status', '')
            min_price = request.args.get('min_price', type=float)
            max_price = request.args.get('max_price', type=float)
            page = request.args.get('page', 1, type=int)
            per_page = 20
            
            # Build query
            query = db_session.query(Property)
            
            if city_filter:
                query = query.filter(Property.city.ilike(f'%{city_filter}%'))
            
            if status_filter:
                query = query.filter(Property.status == PropertyStatus(status_filter))
            
            if min_price:
                query = query.filter(Property.price >= min_price)
            
            if max_price:
                query = query.filter(Property.price <= max_price)
            
            # Order by most recent first
            query = query.order_by(Property.first_seen.desc())
            
            # Paginate
            offset = (page - 1) * per_page
            properties_list = query.offset(offset).limit(per_page).all()
            
            # Get total count for pagination
            total_count = query.count()
            
            # Get available cities for filter
            available_cities = [city[0] for city in db_session.query(Property.city.distinct()).all()]
            
            return render_template('properties.html',
                                 properties=properties_list,
                                 cities=available_cities,
                                 current_filters={
                                     'city': city_filter,
                                     'status': status_filter,
                                     'min_price': min_price,
                                     'max_price': max_price
                                 },
                                 pagination={
                                     'page': page,
                                     'per_page': per_page,
                                     'total': total_count,
                                     'pages': (total_count + per_page - 1) // per_page
                                 })
            
        except Exception as e:
            logger.error(f"Error loading properties: {str(e)}")
            flash('Error loading properties', 'error')
            return render_template('properties.html', properties=[], cities=[], current_filters={}, pagination={})
        finally:
            if 'db_session' in locals():
                db_session.close()
    
    @app.route('/property/<int:property_id>')
    def property_detail(property_id):
        """Property detail page"""
        try:
            db_session = get_db()
            
            property_obj = db_session.query(Property).get(property_id)
            if not property_obj:
                flash('Property not found', 'error')
                return redirect(url_for('properties'))
            
            # Get contacts for this property
            contacts = db_session.query(Contact).filter(Contact.property_id == property_id).all()
            
            # Get communications for this property
            communications = db_session.query(Communication).filter(Communication.property_id == property_id).order_by(Communication.sent_at.desc()).all()
            
            return render_template('property_detail.html',
                                 property=property_obj,
                                 contacts=contacts,
                                 communications=communications)
            
        except Exception as e:
            logger.error(f"Error loading property {property_id}: {str(e)}")
            flash('Error loading property details', 'error')
            return redirect(url_for('properties'))
        finally:
            if 'db_session' in locals():
                db_session.close()
    
    @app.route('/contacts')
    def contacts():
        """Contacts management page"""
        try:
            db_session = get_db()
            
            # Get filters
            status_filter = request.args.get('status', '')
            
            query = db_session.query(Contact)
            if status_filter:
                query = query.filter(Contact.status == status_filter)
            
            contacts_list = query.order_by(Contact.created_at.desc()).all()
            
            return render_template('contacts.html', contacts=contacts_list, current_status=status_filter)
            
        except Exception as e:
            logger.error(f"Error loading contacts: {str(e)}")
            flash('Error loading contacts', 'error')
            return render_template('contacts.html', contacts=[], current_status='')
        finally:
            if 'db_session' in locals():
                db_session.close()
    
    @app.route('/scraping')
    def scraping():
        """Scraping logs and management"""
        try:
            db_session = get_db()
            
            # Get recent scraping logs
            logs = db_session.query(ScrapingLog).order_by(ScrapingLog.started_at.desc()).limit(50).all()
            
            return render_template('scraping.html', logs=logs)
            
        except Exception as e:
            logger.error(f"Error loading scraping logs: {str(e)}")
            flash('Error loading scraping data', 'error')
            return render_template('scraping.html', logs=[])
        finally:
            if 'db_session' in locals():
                db_session.close()
    
    @app.route('/api/scrape', methods=['POST'])
    def api_scrape():
        """API endpoint to trigger manual scraping"""
        try:
            data = request.get_json()
            city = data.get('city', 'Paris')
            site = data.get('site', 'seloger')
            
            # Start scraping task (this would typically be done in background)
            if site == 'seloger':
                scraper = SeLogerScraper(config)
                # This is a simplified version - in production, use Celery or similar
                properties = scraper.scrape_city(city, config.DEFAULT_SEARCH_CRITERIA)
                
                return jsonify({
                    'success': True,
                    'message': f'Found {len(properties)} properties in {city}',
                    'properties_count': len(properties)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Scraper {site} not implemented yet'
                }), 400
                
        except Exception as e:
            logger.error(f"Error in manual scraping: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Scraping failed: {str(e)}'
            }), 500
    
    @app.route('/api/property/<int:property_id>/status', methods=['POST'])
    def api_update_property_status(property_id):
        """API endpoint to update property status"""
        try:
            db_session = get_db()
            
            data = request.get_json()
            new_status = data.get('status')
            
            if not new_status:
                return jsonify({'success': False, 'message': 'Status is required'}), 400
            
            property_obj = db_session.query(Property).get(property_id)
            if not property_obj:
                return jsonify({'success': False, 'message': 'Property not found'}), 404
            
            # Update status
            property_obj.status = PropertyStatus(new_status)
            property_obj.last_updated = datetime.utcnow()
            
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Property status updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating property status: {str(e)}")
            if 'db_session' in locals():
                db_session.rollback()
            return jsonify({
                'success': False,
                'message': f'Failed to update status: {str(e)}'
            }), 500
        finally:
            if 'db_session' in locals():
                db_session.close()
    
    @app.route('/settings')
    def settings():
        """Settings page"""
        config_status = config.validate_config()
        return render_template('settings.html', config_status=config_status, config=config)
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    # Template filters
    @app.template_filter('datetime')
    def datetime_filter(dt):
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M')
        return dt
    
    @app.template_filter('price')
    def price_filter(price):
        if price:
            return f"{price:,.0f} €"
        return "N/A"
    
    return app