from models import Zone, Admin, DeliveryPartner, PricingSettings, GlobalPricingConfig, ContactSettings
from database import db
import logging

def initialize_contact_settings():
    """Initialize default contact settings"""
    if ContactSettings.query.count() == 0:
        contact_settings = ContactSettings(
            company_name='GotoFast Logistics',
            company_address='123 Logistics Street, City, State 12345',
            company_phone='+91 98765 43210',
            company_email='info@gotofast.com',
            company_website='https://gotofast.com',
            support_phone='+91 98765 43211',
            support_email='support@gotofast.com',
            business_hours='Monday - Friday: 9:00 AM - 6:00 PM'
        )
        db.session.add(contact_settings)
        db.session.commit()
        logging.info("Default contact settings created")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("All tables created.")
        initialize_contact_settings()
        print("Contact settings seeded.") 