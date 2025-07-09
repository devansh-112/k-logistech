from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from app import app, db, mail
from models import Order, Zone, DeliveryPartner, Admin, GlobalPricingConfig, StateConfig, InvoiceTemplate, PricingSettings, DeliveryEvent, ContactSettings, SupportTicket
from utils import generate_pdf_bill, calculate_estimated_delivery
import logging
from functools import wraps
import io
from customer_billing import calculate_customer_bill
from werkzeug.utils import secure_filename
import os
import random, smtplib
from flask_mail import Message

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploaded_gst_bills')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not hasattr(current_user, 'get_id') or not current_user.get_id().startswith('admin_'):
            flash('You need to be logged in as an admin to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def partner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not hasattr(current_user, 'get_id') or not current_user.get_id().startswith('partner_'):
            flash('You need to be logged in as a delivery partner to access this page.', 'error')
            return redirect(url_for('partner_login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize default data function
def init_default_data():
    """Initialize default zones and delivery partner"""
    if Zone.query.count() == 0:
        default_zones = [
            Zone(name='Local (Same City)', base_rate=50.0, delivery_days=1),
            Zone(name='Regional (Same State)', base_rate=80.0, delivery_days=3),
            Zone(name='National (Different State)', base_rate=120.0, delivery_days=5),
            Zone(name='Express (Same City)', base_rate=100.0, delivery_days=1),
            Zone(name='International', base_rate=500.0, delivery_days=10)
        ]
        
        for zone in default_zones:
            db.session.add(zone)
        
        db.session.commit()
        logging.info("Default zones created")
    
    # Create default admin if none exists
    if Admin.query.count() == 0:
        admin = Admin(
            username='admin',
            email='admin@logistics.com',
            full_name='System Administrator',
            is_super_admin=True
        )
        # Demo admin password is hidden from documentation, but not changed here
        admin.set_password('admin123')
        db.session.add(admin)
        logging.info("Default admin created")
    
    # Create default delivery partner if none exists
    if DeliveryPartner.query.count() == 0:
        partner = DeliveryPartner(
            username='partner1',
            email='partner@logistics.com',
            full_name='Default Partner'
        )
        partner.set_password('partner123')
        db.session.add(partner)
        logging.info("Default delivery partner created")
    
    # Create default pricing settings
    if PricingSettings.query.count() == 0:
        default_settings = [
            PricingSettings(setting_name='volume_rate_per_cubic_meter', setting_value=50.0, 
                          description='Rate per cubic meter for volume-based pricing'),
            PricingSettings(setting_name='insurance_rate_percentage', setting_value=0.5, 
                          description='Insurance rate as percentage of declared value'),
            PricingSettings(setting_name='cod_fee_percentage', setting_value=2.0, 
                          description='Cash on delivery fee percentage'),
            PricingSettings(setting_name='card_payment_fee_percentage', setting_value=1.5, 
                          description='Card payment processing fee percentage'),
        ]
        for setting in default_settings:
            db.session.add(setting)
        logging.info("Default pricing settings created")
    
    # Create default global pricing configuration if it doesn't exist
    if GlobalPricingConfig.query.count() == 0:
        config = GlobalPricingConfig(
            gst_rate=0.18,
            pickup_charge_jaipur=100.0,
            pickup_charge_oda_jaipur=300.0,
            delivery_charge_jaipur_0_5=300.0,
            delivery_charge_jaipur_5_15=500.0,
            delivery_charge_rajasthan_base=800.0,
            delivery_charge_rajasthan_per_kg=20.0,
            delivery_charge_india_base=1500.0,
            delivery_charge_india_per_kg=30.0,
            oda_charge=300.0,
            min_weight=15.0,
            volume_rate=50.0
        )
        db.session.add(config)
        logging.info("Default global pricing configuration created")
    
    # Create default contact settings if it doesn't exist
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
        logging.info("Default contact settings created")
        
    db.session.commit()

# Initialize default data on first request
@app.before_request
def before_request():
    if not hasattr(app, '_initialized'):
        init_default_data()
        app._initialized = True

@app.route('/')
def index():
    """Landing page"""
    return render_template('modern_index.html')

@app.route('/place-order', methods=['GET', 'POST'])
def place_order():
    """Place a new delivery order"""
    if request.method == 'POST':
        # Remove OTP/email verification check
        try:
            # Get form data
            customer_name = request.form.get('customer_name')
            customer_email = request.form.get('customer_email')
            customer_phone = request.form.get('customer_phone')
            pickup_address_line = request.form.get('pickup_address_line')
            pickup_district = request.form.get('pickup_district')
            pickup_state = request.form.get('pickup_state')
            delivery_address_line = request.form.get('delivery_address_line')
            delivery_state = request.form.get('delivery_state')
            delivery_district = request.form.get('delivery_district')
            zone_id = request.form.get('zone_id')
            # Get form data
            package_type = request.form.get('package_type')
            weight_str = request.form.get('weight')
            length_str = request.form.get('length')
            width_str = request.form.get('width')
            height_str = request.form.get('height')
            insurance_value_str = request.form.get('insurance_value', '0')
            
            # Validate required fields
            if not package_type:
                flash('Please select a package type', 'error')
                return redirect(url_for('place_order'))
            
            # Validate numeric fields
            if not weight_str or not length_str or not width_str or not height_str:
                flash('Please fill in all required numeric fields (weight, length, width, height)', 'error')
                return redirect(url_for('place_order'))
            
            try:
                weight = float(weight_str)
                length = float(length_str)
                width = float(width_str)
                height = float(height_str)
                quantity = int(request.form.get('quantity', 1))
                insurance_value = float(insurance_value_str) if insurance_value_str else 0.0
            except ValueError:
                flash('Please enter valid numeric values for weight, length, width, and height', 'error')
                return redirect(url_for('place_order'))
            
            package_description = request.form.get('package_description')
            payment_mode = request.form.get('payment_mode')
            recipient_name = request.form.get('recipient_name')
            recipient_phone = request.form.get('recipient_phone')
            insurance_required = bool(request.form.get('insurance_required'))
            
            # Validate required fields
            if not all([customer_name, customer_email, customer_phone, pickup_address_line, pickup_district, pickup_state, delivery_address_line, delivery_state, delivery_district, zone_id, package_type, weight, length, width, height, payment_mode, recipient_name, recipient_phone]):
                flash('All fields are required', 'error')
                return redirect(url_for('place_order'))
            
            # Combine address fields for storage (or store separately if you wish)
            pickup_address = f"{pickup_address_line}, {pickup_district}, {pickup_state}"
            delivery_address = f"{delivery_address_line}, {delivery_district}, {delivery_state}"
            
            # Get zone
            zone = Zone.query.get(zone_id)
            if not zone:
                flash('Invalid zone selected', 'error')
                return redirect(url_for('place_order'))
            
            # Calculate estimated delivery
            estimated_delivery = calculate_estimated_delivery(zone.delivery_days)
            
            # Invoice file handling (optional for testing)
            gst_bill = request.files.get('gst_bill')
            filename = None
            if gst_bill and gst_bill.filename != '':
                # Check file extension
                if not gst_bill.filename.lower().endswith('.pdf'):
                    flash('Invoice must be a PDF file', 'error')
                    return redirect(url_for('place_order'))
                # Check file size (increased to 2MB for practicality)
                gst_bill.seek(0, os.SEEK_END)
                size = gst_bill.tell()
                gst_bill.seek(0)
                if size > 2 * 1024 * 1024:  # 2MB limit
                    flash('Invoice file size must be less than 2MB', 'error')
                    return redirect(url_for('place_order'))
                filename = secure_filename(gst_bill.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                gst_bill.save(save_path)
            
            # Create order
            order = Order(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                zone_id=zone_id,
                package_type=package_type,
                weight=weight,
                length=length,
                width=width,
                height=height,
                quantity=quantity,
                package_description=package_description,
                payment_mode=payment_mode,
                recipient_name=recipient_name,
                recipient_phone=recipient_phone,
                insurance_required=insurance_required,
                insurance_value=insurance_value,
                estimated_delivery=estimated_delivery
            )
            
            # Calculate total amount
            order.total_amount = order.calculate_total_amount()
            
            # Save order
            order.gst_bill_filename = filename
            db.session.add(order)
            db.session.commit()

            # Update reference number with order id
            order.reference_number = Order.generate_reference_number(order.id)
            db.session.commit()

            flash(f'Parcel booked! Reference Number: {order.reference_number}', 'success')
            return redirect(url_for('order_details', reference_number=order.reference_number))
            
        except Exception as e:
            logging.error(f"Error placing order: {str(e)}")
            logging.error(f"Form data: {dict(request.form)}")
            logging.error(f"Files: {dict(request.files)}")
            flash('Error placing order. Please try again.', 'error')
            return redirect(url_for('place_order'))
    
    # GET request - show form
    zones = Zone.query.all()
    return render_template('place_order.html', zones=zones)

@app.route('/track-package', methods=['GET', 'POST'])
def track_package():
    """Track package using reference number"""
    order = None
    
    if request.method == 'POST':
        reference_number = request.form.get('reference_number')
        if reference_number:
            order = Order.query.filter_by(reference_number=reference_number.upper()).first()
            if not order:
                flash('Order not found. Please check your reference number.', 'error')
    
    return render_template('modern_track_package.html', order=order)

@app.route('/order/<reference_number>')
def order_details(reference_number):
    """Show order details and generate PDF"""
    order = Order.query.filter_by(reference_number=reference_number.upper()).first()
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('index'))
    
    # Define size multipliers for the template
    size_multipliers = {
        'small': 1.0,
        'medium': 1.2,
        'large': 1.5,
        'extra_large': 2.0
    }
    
    return render_template('order_details.html', order=order, size_multipliers=size_multipliers)

@app.route('/download-bill/<reference_number>')
def download_bill(reference_number):
    """Download PDF bill"""
    order = Order.query.filter_by(reference_number=reference_number.upper()).first()
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('index'))
    
    try:
        pdf_content = generate_pdf_bill(order)
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=bill_{reference_number}.pdf'
        return response
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        flash('Error generating bill. Please try again.', 'error')
        return redirect(url_for('order_details', reference_number=reference_number))

@app.route('/download-gst-bill/<reference_number>')
@login_required  # Both admin and partner can access
def download_gst_bill(reference_number):
    order = Order.query.filter_by(reference_number=reference_number.upper()).first()
    if not order or not order.gst_bill_filename:
        flash('GST Bill not found for this order.', 'error')
        return redirect(url_for('order_details', reference_number=reference_number))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], order.gst_bill_filename)
    if not os.path.exists(file_path):
        flash('GST Bill file missing on server.', 'error')
        return redirect(url_for('order_details', reference_number=reference_number))
    return send_file(file_path, as_attachment=True, download_name=order.gst_bill_filename)

@app.route('/partner/login', methods=['GET', 'POST'])
def partner_login():
    """Delivery partner login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            partner = DeliveryPartner.query.filter_by(username=username).first()
            if partner and partner.check_password(password) and partner.is_active:
                session['partner_id'] = partner.id
                session['partner_username'] = partner.username
                flash('Login successful', 'success')
                return redirect(url_for('partner_dashboard'))
            else:
                flash('Invalid credentials', 'error')
        else:
            flash('Please enter both username and password', 'error')
    
    return render_template('partner_login.html')

@app.route('/partner/logout')
def partner_logout():
    """Delivery partner logout"""
    session.pop('partner_id', None)
    session.pop('partner_username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('partner_login'))

@app.route('/partner/dashboard')
def partner_dashboard():
    """Delivery partner dashboard"""
    if 'partner_id' not in session:
        flash('Please login to access the dashboard', 'error')
        return redirect(url_for('partner_login'))
    
    # Get orders with pagination
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = Order.query
    if status_filter != 'all':
        query = query.filter_by(delivery_status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Get remaining orders (not delivered)
    remaining_orders = Order.query.filter(
        Order.delivery_status != 'delivered'
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('partner_dashboard_simple.html', 
                         orders=orders, 
                         status_filter=status_filter,
                         remaining_orders=remaining_orders)

@app.route('/partner/update-order/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    """Update order status"""
    if 'partner_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    delivery_status = request.form.get('delivery_status')
    payment_status = request.form.get('payment_status')
    estimated_delivery = request.form.get('estimated_delivery')
    
    order = Order.query.get(order_id)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('partner_dashboard'))
    
    # Update delivery status
    if delivery_status:
        order.delivery_status = delivery_status
        if delivery_status == 'delivered':
            order.actual_delivery = datetime.utcnow()
    
    # Update payment status
    if payment_status:
        order.payment_status = payment_status
    
    # Update estimated delivery
    if estimated_delivery:
        try:
            order.estimated_delivery = datetime.strptime(estimated_delivery, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('partner_dashboard'))
    
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash('Order updated successfully', 'success')
    return redirect(url_for('partner_dashboard'))

@app.route('/partner/update-delivery-event', methods=['POST'])
def update_delivery_event():
    """Update delivery event (called by partner)"""
    if 'partner_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        order_id = request.form.get('order_id')
        event_type = request.form.get('event_type')
        description = request.form.get('description')
        location = request.form.get('location', '')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Create delivery event
        event = DeliveryEvent(
            order_id=order_id,
            event_type=event_type,
            description=description,
            location=location,
            updated_by=session.get('partner_username', 'partner')
        )
        
        # Update order status
        order.delivery_status = event_type
        if event_type == 'delivered':
            order.actual_delivery = datetime.utcnow()
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/partner/update-payment-status/<int:order_id>', methods=['POST'])
def update_payment_status(order_id):
    if 'partner_id' not in session:
        flash('Please login to update payment status', 'error')
        return redirect(url_for('partner_login'))
    order = Order.query.get(order_id)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('partner_dashboard'))
    payment_status = request.form.get('payment_status')
    if payment_status in ['paid', 'unpaid']:
        order.payment_status = payment_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Payment status updated', 'success')
    else:
        flash('Invalid payment status', 'error')
    return redirect(url_for('partner_dashboard'))

@app.route('/order/<reference_number>/timeline')
def order_timeline(reference_number):
    """Get delivery timeline for an order"""
    order = Order.query.filter_by(reference_number=reference_number.upper()).first()
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    events = order.delivery_events.order_by(DeliveryEvent.timestamp).all()
    timeline = []
    
    for event in events:
        timeline.append({
            'type': event.event_type,
            'description': event.description,
            'location': event.location,
            'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M'),
            'updated_by': event.updated_by
        })
    
    return jsonify({'timeline': timeline})

# Client routes
@app.route('/client/login', methods=['GET', 'POST'])
def client_login():
    """Client login using email and reference number"""
    if request.method == 'POST':
        email = request.form.get('email')
        reference_number = request.form.get('reference_number')
        
        if email and reference_number:
            # Find order with matching email and reference number
            order = Order.query.filter_by(
                customer_email=email, 
                reference_number=reference_number
            ).first()
            
            if order:
                # Store client session info
                session['client_email'] = email
                session['client_orders'] = [order.reference_number]
                flash('Login successful! Welcome back.', 'success')
                return redirect(url_for('client_dashboard'))
            else:
                flash('No orders found with that email and reference number.', 'error')
        else:
            flash('Please enter both email and reference number.', 'error')
    
    return render_template('client_login.html')

@app.route('/client/dashboard')
def client_dashboard():
    """Client dashboard showing their orders"""
    if 'client_email' not in session:
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('client_login'))
    # Get all orders for this client
    orders = Order.query.filter_by(customer_email=session['client_email']).all()
    # Calculate statistics
    total_orders = len(orders)
    pending_orders = len([o for o in orders if o.delivery_status == 'pending'])
    delivered_orders = len([o for o in orders if o.delivery_status == 'delivered'])
    in_transit_orders = len([o for o in orders if o.delivery_status == 'in_transit'])
    # Calculate balance due (unpaid, not cancelled)
    balance_due = sum(o.total_amount for o in orders if o.payment_status != 'paid' and o.delivery_status != 'cancelled')
    return render_template('client_dashboard.html',
                         orders=orders,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         delivered_orders=delivered_orders,
                         in_transit_orders=in_transit_orders,
                         balance_due=balance_due)

@app.route('/client/logout')
def client_logout():
    """Client logout"""
    session.pop('client_email', None)
    session.pop('client_orders', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('client_login'))

@app.route('/client/cancel-order/<reference_number>', methods=['POST'])
def client_cancel_order(reference_number):
    """Allow client to cancel their order if not picked up yet"""
    if 'client_email' not in session:
        flash('Please log in to cancel your order.', 'error')
        return redirect(url_for('client_login'))
    order = Order.query.filter_by(reference_number=reference_number.upper(), customer_email=session['client_email']).first()
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('client_dashboard'))
    if order.delivery_status != 'pending':
        flash('Order cannot be cancelled as it has already been picked up or processed.', 'error')
        return redirect(url_for('client_dashboard'))
    # Apply cancellation (no fee)
    order.delivery_status = 'cancelled'
    order.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f'Order {order.reference_number} cancelled successfully.', 'success')
    return redirect(url_for('client_dashboard'))

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            flash('Login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    # Get statistics
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(delivery_status='pending').count()
    delivered_orders = Order.query.filter_by(delivery_status='delivered').count()
    in_transit_orders = Order.query.filter_by(delivery_status='in_transit').count()
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Get zones
    zones = Zone.query.all()
    
    # Get delivery partners
    partners = DeliveryPartner.query.all()
    
    # Get pricing settings
    pricing_settings = PricingSettings.query.all()
    
    return render_template('admin_dashboard.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         delivered_orders=delivered_orders,
                         in_transit_orders=in_transit_orders,
                         recent_orders=recent_orders,
                         zones=zones,
                         partners=partners,
                         pricing_settings=pricing_settings)

@app.route('/admin/pricing-config', methods=['GET', 'POST'])
@admin_required
def admin_pricing_config():
    config = GlobalPricingConfig.query.first()
    if not config:
        config = GlobalPricingConfig()
        db.session.add(config)
        db.session.commit()
    if request.method == 'POST':
        config.gst_rate = float(request.form['gst_rate'])
        config.pickup_charge_jaipur = float(request.form['pickup_charge_jaipur'])
        config.pickup_charge_oda_jaipur = float(request.form['pickup_charge_oda_jaipur'])
        config.delivery_charge_jaipur_0_5 = float(request.form['delivery_charge_jaipur_0_5'])
        config.delivery_charge_jaipur_5_15 = float(request.form['delivery_charge_jaipur_5_15'])
        config.delivery_charge_rajasthan_base = float(request.form['delivery_charge_rajasthan_base'])
        config.delivery_charge_rajasthan_per_kg = float(request.form['delivery_charge_rajasthan_per_kg'])
        config.delivery_charge_india_base = float(request.form.get('delivery_charge_india_base', 0.0))
        config.delivery_charge_india_per_kg = float(request.form.get('delivery_charge_india_per_kg', 0.0))
        config.oda_charge = float(request.form.get('oda_charge', 0.0))
        config.min_weight = float(request.form.get('min_weight', 0.0))
        config.volume_rate = float(request.form.get('volume_rate', 0.0))
        # New fields for weight categories and cancellation charge
        config.weight_cat_0_5 = float(request.form.get('weight_cat_0_5', 0.0))
        config.weight_cat_5_15 = float(request.form.get('weight_cat_5_15', 0.0))
        config.weight_cat_15_plus = float(request.form.get('weight_cat_15_plus', 0.0))
        config.cancellation_charge = float(request.form.get('cancellation_charge', 300.0))
        db.session.commit()
        flash('Pricing configuration updated!', 'success')
        return redirect(url_for('admin_pricing_config'))
    return render_template('admin_pricing_config.html', config=config)

@app.route('/admin/save-global-config', methods=['POST'])
@admin_required
def save_global_config():
    """Save global pricing configuration"""
    try:
        config = GlobalPricingConfig.query.first()
        if not config:
            config = GlobalPricingConfig()
        config.gst_rate = float(request.form.get('gst_rate', 0.18))
        config.pickup_charge_jaipur = float(request.form.get('pickup_charge_jaipur', 100.0))
        config.pickup_charge_oda_jaipur = float(request.form.get('pickup_charge_oda_jaipur', 300.0))
        config.delivery_charge_jaipur_0_5 = float(request.form.get('delivery_charge_jaipur_0_5', 300.0))
        config.delivery_charge_jaipur_5_15 = float(request.form.get('delivery_charge_jaipur_5_15', 500.0))
        config.delivery_charge_rajasthan_base = float(request.form.get('delivery_charge_rajasthan_base', 800.0))
        config.delivery_charge_rajasthan_per_kg = float(request.form.get('delivery_charge_rajasthan_per_kg', 20.0))
        config.delivery_charge_india_base = float(request.form.get('delivery_charge_india_base', 1500.0))
        config.delivery_charge_india_per_kg = float(request.form.get('delivery_charge_india_per_kg', 30.0))
        config.oda_charge = float(request.form.get('oda_charge', 300.0))
        config.min_weight = float(request.form.get('min_weight', 15.0))
        config.volume_rate = float(request.form.get('volume_rate', 50.0))
        db.session.add(config)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/add-zone', methods=['POST'])
@admin_required
def add_zone():
    """Add new delivery zone"""
    try:
        data = request.get_json()
        zone = Zone(
            name=data['name'],
            base_rate=float(data['base_rate']),
            delivery_days=int(data['delivery_days'])
        )
        db.session.add(zone)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/update-zone', methods=['POST'])
@admin_required
def update_zone():
    """Update existing zone"""
    try:
        data = request.get_json()
        zone = Zone.query.get(data['zone_id'])
        if zone:
            zone.base_rate = float(data['base_rate'])
            zone.delivery_days = int(data['delivery_days'])
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Zone not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/delete-zone', methods=['POST'])
@admin_required
def delete_zone():
    """Delete zone"""
    try:
        data = request.get_json()
        zone = Zone.query.get(data['zone_id'])
        if zone:
            # Check if zone has orders
            if zone.orders:
                return jsonify({'success': False, 'error': 'Cannot delete zone with existing orders'})
            
            db.session.delete(zone)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Zone not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calculate-price', methods=['POST'])
def calculate_price():
    """Calculate price via API"""
    try:
        data = request.get_json()
        zone_id = data.get('zone_id')
        weight = float(data.get('weight', 0))
        length = float(data.get('length', 0))
        width = float(data.get('width', 0))
        height = float(data.get('height', 0))
        quantity = int(data.get('quantity', 1))
        payment_mode = data.get('payment_mode')
        insurance_required = data.get('insurance_required', False)
        insurance_value = float(data.get('insurance_value', 0))
        
        zone = Zone.query.get(zone_id)
        if not zone:
            return jsonify({'error': 'Invalid zone'}), 400
        
        # Create temporary order to calculate price
        temp_order = Order(
            zone_id=zone_id,
            weight=weight,
            length=length,
            width=width,
            height=height,
            quantity=quantity,
            payment_mode=payment_mode,
            insurance_required=insurance_required,
            insurance_value=insurance_value
        )
        temp_order.zone = zone
        
        total_amount = temp_order.calculate_total_amount()
        estimated_delivery = calculate_estimated_delivery(zone.delivery_days)
        
        # Calculate volume
        volume = (length * width * height) / 1000000  # Convert cm³ to m³
        
        return jsonify({
            'total_amount': total_amount,
            'estimated_delivery': estimated_delivery.strftime('%Y-%m-%d %H:%M:%S'),
            'delivery_days': zone.delivery_days,
            'volume': volume,
            'breakdown': {
                'base_cost': zone.base_rate * weight,
                'volume_cost': volume * 50,  # volume rate
                'insurance_cost': temp_order.insurance_premium,
                'payment_fee': total_amount - temp_order.insurance_premium - (zone.base_rate * weight) - (volume * 50)
            }
        })
        
    except Exception as e:
        logging.error(f"Error calculating price: {str(e)}")
        return jsonify({'error': 'Error calculating price'}), 500

@app.route('/admin/invoice-management')
@admin_required
def admin_invoice_management():
    """Admin invoice management page"""
    # Get all orders with optional filters
    status_filter = request.args.get('status')
    invoice_filter = request.args.get('invoice')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Order.query
    
    if status_filter:
        query = query.filter_by(delivery_status=status_filter)
    
    if invoice_filter:
        if invoice_filter == 'generated':
            query = query.filter_by(invoice_generated=True)
        elif invoice_filter == 'pending':
            query = query.filter_by(invoice_generated=False)
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    
    if date_to:
        query = query.filter(Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('admin_invoice_management.html', orders=orders)

@app.route('/admin/generate-invoice', methods=['POST'])
@admin_required
def generate_invoice():
    """Generate invoice for a single order"""
    try:
        data = request.get_json()
        order = Order.query.get(data['order_id'])
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'})
        
        # Generate invoice number if not exists
        if not order.invoice_number:
            order.invoice_number = f"INV-{order.reference_number}"
            order.invoice_date = datetime.now()
        
        order.invoice_generated = True
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/download-invoice/<int:order_id>')
@admin_required
def download_invoice(order_id):
    """Download invoice for a specific order"""
    try:
        order = Order.query.get(order_id)
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('admin_invoice_management'))
        
        # Generate PDF invoice
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Company Info
        company_info = [
            ["GotoFast Logistics", ""],
            ["123 Business Street", ""],
            ["City, State 12345", ""],
            ["Phone: +1 (555) 123-4567", ""],
            ["Email: info@gotofast.com", ""]
        ]
        
        company_table = Table(company_info, colWidths=[4*inch, 2*inch])
        company_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(company_table)
        story.append(Spacer(1, 20))
        
        # Invoice Details
        invoice_data = [
            ["Invoice Number:", order.invoice_number or f"INV-{order.reference_number}"],
            ["Date:", order.created_at.strftime('%Y-%m-%d')],
            ["Reference:", order.reference_number],
            ["Customer:", order.customer_name],
            ["Email:", order.customer_email],
            ["Phone:", order.customer_phone]
        ]
        
        invoice_table = Table(invoice_data, colWidths=[2*inch, 4*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(invoice_table)
        story.append(Spacer(1, 20))
        
        # Package Details
        package_data = [
            ["Pickup Address:", order.pickup_address],
            ["Delivery Address:", order.delivery_address],
            ["Zone:", order.zone.name if order.zone else "N/A"],
            ["Weight:", f"{order.weight} kg"],
            ["Dimensions:", f"{order.length}×{order.width}×{order.height} cm"],
            ["Quantity:", str(order.quantity)]
        ]
        
        package_table = Table(package_data, colWidths=[2*inch, 4*inch])
        package_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(package_table)
        story.append(Spacer(1, 20))
        
        # Pricing Breakdown
        pricing_data = [
            ["Description", "Amount"],
            ["Base Amount", f"${order.base_amount:.2f}"],
            ["Pickup Charge", f"${order.pickup_charge:.2f}"],
            ["Extra Weight Charge", f"${order.extra_weight_charge:.2f}"],
            ["Payment Fee", f"${order.payment_fee:.2f}"],
            ["Subtotal", f"${order.subtotal:.2f}"],
            ["GST (18%)", f"${order.gst_amount:.2f}"],
            ["Total Amount", f"${order.total_amount:.2f}"]
        ]
        
        pricing_table = Table(pricing_data, colWidths=[3*inch, 1.5*inch])
        pricing_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ]))
        story.append(pricing_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Return PDF as response
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order.reference_number}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Error generating invoice: {str(e)}', 'error')
        return redirect(url_for('admin_invoice_management'))

@app.route('/admin/export-data')
@admin_required
def export_data():
    """Export order data in CSV format"""
    import csv
    import io
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Reference Number', 'Customer Name', 'Customer Email', 'Customer Phone',
        'Pickup Address', 'Delivery Address', 'Zone', 'Weight (kg)', 
        'Dimensions (L×W×H)', 'Total Amount', 'Payment Mode', 'Payment Status',
        'Delivery Status', 'Invoice Generated', 'Created Date'
    ])
    
    # Write data
    for order in orders:
        writer.writerow([
            order.reference_number, order.customer_name, order.customer_email,
            order.customer_phone, order.pickup_address, order.delivery_address,
            order.zone.name if order.zone else '', order.weight,
            f"{order.length}×{order.width}×{order.height}", order.total_amount,
            order.payment_mode, order.payment_status, order.delivery_status,
            'Yes' if getattr(order, 'invoice_generated', False) else 'No',
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=orders_export.csv'
    
    return response

@app.route('/admin/partner-config')
@admin_required
def admin_partner_config():
    """Admin partner configuration page"""
    partners = DeliveryPartner.query.all()
    return render_template('admin_partner_config.html', partners=partners)

@app.route('/admin/create-partner', methods=['POST'])
@admin_required
def create_partner():
    """Create a new delivery partner"""
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        
        if not all([username, email, full_name, password]):
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        # Check if username or email already exists
        existing_partner = DeliveryPartner.query.filter(
            (DeliveryPartner.username == username) | (DeliveryPartner.email == email)
        ).first()
        
        if existing_partner:
            return jsonify({'success': False, 'error': 'Username or email already exists'})
        
        partner = DeliveryPartner(
            username=username,
            email=email,
            full_name=full_name
        )
        partner.set_password(password)
        
        db.session.add(partner)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/assign-order', methods=['POST'])
@admin_required
def assign_order_to_partner():
    """Assign an order to a delivery partner"""
    try:
        order_id = request.form.get('order_id')
        partner_id = request.form.get('partner_id')
        
        order = Order.query.get(order_id)
        partner = DeliveryPartner.query.get(partner_id)
        
        if not order or not partner:
            return jsonify({'success': False, 'error': 'Order or partner not found'})
        
        order.partner_id = partner_id
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/unassigned-orders')
@admin_required
def get_unassigned_orders():
    """Get orders that haven't been assigned to partners yet"""
    orders = Order.query.filter_by(partner_id=None).all()
    return jsonify({
        'orders': [{
            'id': order.id,
            'reference_number': order.reference_number,
            'customer_name': order.customer_name,
            'delivery_address': order.delivery_address
        } for order in orders]
    })

@app.route('/admin/contact-settings')
@admin_required
def admin_contact_settings():
    """Admin contact settings page"""
    contact_settings = ContactSettings.get_settings()
    return render_template('admin_contact_settings.html', contact_settings=contact_settings)

@app.route('/admin/save-contact-settings', methods=['POST'])
@admin_required
def save_contact_settings():
    """Save contact settings"""
    try:
        contact_settings = ContactSettings.get_settings()
        
        # Update contact settings
        contact_settings.company_name = request.form.get('company_name', 'GotoFast Logistics')
        contact_settings.company_address = request.form.get('company_address', '')
        contact_settings.company_phone = request.form.get('company_phone', '')
        contact_settings.company_email = request.form.get('company_email', '')
        contact_settings.company_website = request.form.get('company_website', '')
        contact_settings.support_phone = request.form.get('support_phone', '')
        contact_settings.support_email = request.form.get('support_email', '')
        contact_settings.business_hours = request.form.get('business_hours', '')
        contact_settings.facebook_url = request.form.get('facebook_url', '')
        contact_settings.twitter_url = request.form.get('twitter_url', '')
        contact_settings.linkedin_url = request.form.get('linkedin_url', '')
        contact_settings.instagram_url = request.form.get('instagram_url', '')
        contact_settings.updated_by = current_user.id
        
        db.session.commit()
        
        flash('Contact settings updated successfully!', 'success')
        return redirect(url_for('admin_contact_settings'))
    except Exception as e:
        flash(f'Error updating contact settings: {str(e)}', 'error')
        return redirect(url_for('admin_contact_settings'))

@app.route('/admin/change-credentials')
@admin_required
def admin_change_credentials():
    """Admin credentials change page"""
    return render_template('admin_change_credentials.html')

@app.route('/admin/save-credentials', methods=['POST'])
@admin_required
def save_admin_credentials():
    """Save admin credentials"""
    try:
        current_password = request.form.get('current_password')
        new_username = request.form.get('new_username')
        new_email = request.form.get('new_email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('admin_change_credentials'))
        
        # Validate new password if provided
        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long', 'error')
                return redirect(url_for('admin_change_credentials'))
            
            if new_password != confirm_password:
                flash('New password and confirm password do not match', 'error')
                return redirect(url_for('admin_change_credentials'))
        
        # Update admin credentials
        if new_username:
            # Check if username already exists
            existing_admin = Admin.query.filter_by(username=new_username).first()
            if existing_admin and existing_admin.id != current_user.id:
                flash('Username already exists', 'error')
                return redirect(url_for('admin_change_credentials'))
            current_user.username = new_username
        
        if new_email:
            current_user.email = new_email
        
        if new_password:
            current_user.set_password(new_password)
        
        db.session.commit()
        
        flash('Admin credentials updated successfully!', 'success')
        return redirect(url_for('admin_change_credentials'))
    except Exception as e:
        flash(f'Error updating credentials: {str(e)}', 'error')
        return redirect(url_for('admin_change_credentials'))





@app.route('/admin/support-management')
@admin_required
def admin_support_management():
    """Admin support management page"""
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    query = SupportTicket.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    tickets = query.order_by(SupportTicket.created_at.desc()).all()
    
    # Get statistics
    total_tickets = SupportTicket.query.count()
    open_tickets = SupportTicket.query.filter_by(status='open').count()
    urgent_tickets = SupportTicket.query.filter_by(priority='urgent').count()
    resolved_tickets = SupportTicket.query.filter_by(status='resolved').count()
    
    return render_template('admin_support_management.html', 
                         tickets=tickets,
                         total_tickets=total_tickets,
                         open_tickets=open_tickets,
                         urgent_tickets=urgent_tickets,
                         resolved_tickets=resolved_tickets)

@app.route('/admin/update-ticket/<int:ticket_id>', methods=['POST'])
@admin_required
def update_support_ticket(ticket_id):
    """Update support ticket status and response"""
    try:
        ticket = SupportTicket.query.get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('admin_support_management'))
        
        ticket.status = request.form.get('status', ticket.status)
        ticket.priority = request.form.get('priority', ticket.priority)
        ticket.admin_response = request.form.get('admin_response', ticket.admin_response)
        ticket.assigned_to = current_user.id
        
        if ticket.status == 'resolved':
            ticket.resolved_at = datetime.utcnow()
        
        db.session.commit()
        flash('Ticket updated successfully!', 'success')
        return redirect(url_for('admin_support_management'))
    except Exception as e:
        flash(f'Error updating ticket: {str(e)}', 'error')
        return redirect(url_for('admin_support_management'))

@app.route('/contact-us', methods=['GET', 'POST'])
def contact_us():
    """Contact us page"""
    if request.method == 'POST':
        try:
            # Create support ticket
            ticket = SupportTicket(
                customer_name=request.form.get('name'),
                customer_email=request.form.get('email'),
                customer_phone=request.form.get('phone'),
                subject=request.form.get('subject'),
                message=request.form.get('message'),
                category=request.form.get('category', 'general'),
                priority='medium'
            )
            
            db.session.add(ticket)
            db.session.commit()
            
            flash(f'Thank you! Your ticket #{ticket.ticket_number} has been created. We will get back to you soon.', 'success')
            return redirect(url_for('contact_us'))
        except Exception as e:
            flash('Error submitting your request. Please try again.', 'error')
    
    # Get contact settings
    contact_settings = ContactSettings.get_settings()
    
    return render_template('contact_us.html', contact_settings=contact_settings)

@app.route('/about-us')
def about_us():
    """About us page"""
    contact_settings = ContactSettings.get_settings()
    
    return render_template('about_us.html', contact_settings=contact_settings)

@app.route('/faq')
def faq():
    """FAQ page"""
    contact_settings = ContactSettings.get_settings()
    
    return render_template('faq.html', contact_settings=contact_settings)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/admin/report')
@admin_required
def admin_report():
    from sqlalchemy import func
    # Total orders
    total_orders = Order.query.count()
    delivered_orders = Order.query.filter_by(delivery_status='delivered').count()
    pending_orders = Order.query.filter_by(delivery_status='pending').count()
    in_transit_orders = Order.query.filter_by(delivery_status='in_transit').count()
    cancelled_orders = Order.query.filter_by(delivery_status='cancelled').count()

    # Total revenue
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0

    # Revenue by month (last 12 months)
    revenue_by_month = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.sum(Order.total_amount)
    ).group_by('month').order_by('month').all()
    months = [row[0] for row in revenue_by_month]
    revenues = [float(row[1]) for row in revenue_by_month]

    # Orders by status
    status_counts = db.session.query(Order.delivery_status, func.count(Order.id)).group_by(Order.delivery_status).all()
    status_labels = [row[0].title() for row in status_counts]
    status_values = [row[1] for row in status_counts]

    # Top delivery partners
    top_partners = db.session.query(
        DeliveryPartner.full_name, func.count(Order.id)
    ).join(Order, Order.partner_id == DeliveryPartner.id)\
    .group_by(DeliveryPartner.id)\
    .order_by(func.count(Order.id).desc())\
    .limit(5).all()

    # Top zones
    top_zones = db.session.query(
        Zone.name, func.count(Order.id), func.sum(Order.total_amount)
    ).join(Order, Order.zone_id == Zone.id)\
    .group_by(Zone.id)\
    .order_by(func.sum(Order.total_amount).desc())\
    .limit(5).all()

    return render_template(
        'admin_report.html',
        total_orders=total_orders,
        delivered_orders=delivered_orders,
        pending_orders=pending_orders,
        in_transit_orders=in_transit_orders,
        cancelled_orders=cancelled_orders,
        total_revenue=total_revenue,
        months=months,
        revenues=revenues,
        status_labels=status_labels,
        status_values=status_values,
        top_partners=top_partners,
        top_zones=top_zones
    )

@app.route('/admin/report/download/pdf')
@admin_required
def download_report_pdf():
    from fpdf import FPDF
    from datetime import datetime
    # Gather stats (reuse logic from admin_report)
    from sqlalchemy import func
    total_orders = Order.query.count()
    delivered_orders = Order.query.filter_by(delivery_status='delivered').count()
    pending_orders = Order.query.filter_by(delivery_status='pending').count()
    in_transit_orders = Order.query.filter_by(delivery_status='in_transit').count()
    cancelled_orders = Order.query.filter_by(delivery_status='cancelled').count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    # Top partners
    top_partners = db.session.query(
        DeliveryPartner.full_name, func.count(Order.id)
    ).join(Order, Order.partner_id == DeliveryPartner.id)\
    .group_by(DeliveryPartner.id)\
    .order_by(func.count(Order.id).desc())\
    .limit(5).all()
    # Top zones
    top_zones = db.session.query(
        Zone.name, func.count(Order.id), func.sum(Order.total_amount)
    ).join(Order, Order.zone_id == Zone.id)\
    .group_by(Zone.id)\
    .order_by(func.sum(Order.total_amount).desc())\
    .limit(5).all()
    # PDF generation
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'GotoFast Logistics - Overall Report', ln=1, align='C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=1)
    pdf.ln(5)
    pdf.cell(0, 10, f'Total Orders: {total_orders}', ln=1)
    pdf.cell(0, 10, f'Delivered: {delivered_orders}', ln=1)
    pdf.cell(0, 10, f'Pending: {pending_orders}', ln=1)
    pdf.cell(0, 10, f'In Transit: {in_transit_orders}', ln=1)
    pdf.cell(0, 10, f'Cancelled: {cancelled_orders}', ln=1)
    pdf.cell(0, 10, f'Total Revenue: INR {total_revenue:.2f}', ln=1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Top Delivery Partners', ln=1)
    pdf.set_font('Arial', '', 12)
    for partner, count in top_partners:
        pdf.cell(0, 10, f'{partner}: {count} orders', ln=1)
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Top Zones', ln=1)
    pdf.set_font('Arial', '', 12)
    for zone, count, revenue in top_zones:
        pdf.cell(0, 10, f'{zone}: {count} orders, INR {revenue or 0:.2f}', ln=1)
    # Output
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output = io.BytesIO(pdf_bytes)
    pdf_output.seek(0)
    return send_file(pdf_output, as_attachment=True, download_name='overall_report.pdf', mimetype='application/pdf')

@app.route('/admin/report/download/csv')
@admin_required
def download_report_csv():
    import csv
    from datetime import datetime
    from sqlalchemy import func
    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(['GotoFast Logistics - Overall Report'])
    writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M") }'])
    writer.writerow([])
    # Stats
    total_orders = Order.query.count()
    delivered_orders = Order.query.filter_by(delivery_status='delivered').count()
    pending_orders = Order.query.filter_by(delivery_status='pending').count()
    in_transit_orders = Order.query.filter_by(delivery_status='in_transit').count()
    cancelled_orders = Order.query.filter_by(delivery_status='cancelled').count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    writer.writerow(['Total Orders', total_orders])
    writer.writerow(['Delivered', delivered_orders])
    writer.writerow(['Pending', pending_orders])
    writer.writerow(['In Transit', in_transit_orders])
    writer.writerow(['Cancelled', cancelled_orders])
    writer.writerow(['Total Revenue (INR)', f'{total_revenue:.2f}'])
    writer.writerow([])
    # Top partners
    writer.writerow(['Top Delivery Partners'])
    writer.writerow(['Partner', 'Orders Delivered'])
    top_partners = db.session.query(
        DeliveryPartner.full_name, func.count(Order.id)
    ).join(Order, Order.partner_id == DeliveryPartner.id)\
    .group_by(DeliveryPartner.id)\
    .order_by(func.count(Order.id).desc())\
    .limit(5).all()
    for partner, count in top_partners:
        writer.writerow([partner, count])
    writer.writerow([])
    # Top zones
    writer.writerow(['Top Zones'])
    writer.writerow(['Zone', 'Orders', 'Revenue (INR)'])
    top_zones = db.session.query(
        Zone.name, func.count(Order.id), func.sum(Order.total_amount)
    ).join(Order, Order.zone_id == Zone.id)\
    .group_by(Zone.id)\
    .order_by(func.sum(Order.total_amount).desc())\
    .limit(5).all()
    for zone, count, revenue in top_zones:
        writer.writerow([zone, count, f'{revenue or 0:.2f}'])
    # Output
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=overall_report.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/api/customer-calculate-bill', methods=['POST'])
def api_customer_calculate_bill():
    """API endpoint for customer billing calculation"""
    try:
        data = request.get_json()
        invoice = calculate_customer_bill(data)
        return jsonify({'success': True, 'invoice': invoice})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/uploaded-invoice/<filename>')
def uploaded_invoice(filename):
    """Serve the uploaded invoice PDF from the uploaded_gst_bills folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
