# Logistics Transport Platform

A complete logistics management system with admin, partner, and consumer dashboards.

## Features

- **Multi-role Dashboard:** Admin, Delivery Partner, and Consumer interfaces
- **Order Management:** Book shipments, assign to partners, track delivery status
- **Real-time Updates:** Partners can update delivery status with quick action buttons
- **Custom Reference Numbers:** Format: ABCD2507241234 (random letters + date + voucher)
- **Easy Branding:** Change company name via `branding_config.py`

## Quick Setup

### Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

3. Access at: http://localhost:5001

### Default Login Credentials

<!--
**Admin:**
- Username: `admin`
- Password: `admin123`

**Partner:**
- Username: `partner1`
- Password: `partner123`
-->

## Deployment

### Render (Recommended)
1. Fork/clone this repository
2. Create account at [render.com](https://render.com)
3. Create new Web Service
4. Connect your repository
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `gunicorn wsgi:app`
7. Deploy!

### Heroku
1. Install Heroku CLI
2. Run: `heroku create your-app-name`
3. Run: `git push heroku main`

## Customization

### Change Company Name
Edit `branding_config.py`:
```python
SITE_NAME = "Your Company Name"
COMPANY_NAME = "Your Company Name Ltd"
```

### Admin Features
- View all orders and assign to partners
- Create new delivery partners
- Manage pricing and zones
- Generate invoices

### Partner Features
- View assigned orders
- Update delivery status with one-click buttons
- Track remaining orders

### Consumer Features
- Book shipments with custom reference numbers
- Track packages
- View order history

## File Structure

- `app.py` - Main Flask application
- `models.py` - Database models
- `routes.py` - All route handlers
- `templates/` - HTML templates
- `static/` - CSS, JS, images
- `branding_config.py` - Easy rebranding
- `wsgi.py` - Production entry point

## Support

For setup help or customization, contact the developer. 