# Logistics Transport Web Application

## Overview

This is a web-based logistics and delivery management system built with Flask and SQLAlchemy. The application provides a comprehensive platform for managing delivery orders, tracking packages, and handling delivery partner operations. It features a customer-facing interface for placing orders and tracking shipments, along with a partner dashboard for managing deliveries.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with Python
- **Database**: SQLAlchemy ORM with SQLite as default (configurable via environment variables)
- **Authentication**: Session-based authentication with Werkzeug password hashing
- **PDF Generation**: ReportLab for generating delivery bills and receipts
- **Logging**: Python's built-in logging module for debugging and monitoring

### Frontend Architecture
- **Templates**: Jinja2 templating engine with Flask
- **CSS Framework**: Bootstrap 5 for responsive design
- **Icons**: Font Awesome for UI iconography
- **JavaScript**: Vanilla JavaScript for client-side functionality

### Database Schema
- **DeliveryPartner**: User accounts for delivery personnel
- **Zone**: Delivery zones with pricing and delivery time configuration
- **Order**: Customer orders with package details and delivery information

## Key Components

### Core Models
1. **DeliveryPartner Model**
   - Manages delivery partner authentication and accounts
   - Includes password hashing and verification methods
   - Tracks partner activity status

2. **Zone Model**
   - Defines delivery zones with base rates and delivery timeframes
   - Supports different pricing tiers (Local, Regional, National, Express, International)

3. **Order Model**
   - Stores customer order information and package details
   - Links to zones for pricing calculation
   - Tracks delivery status and payment information

### Application Structure
- **app.py**: Application factory and database configuration
- **models.py**: Database model definitions
- **routes.py**: HTTP route handlers and business logic
- **utils.py**: Utility functions for PDF generation and date calculations
- **main.py**: Application entry point

### Key Features
1. **Order Placement**: Customer interface for creating delivery orders
2. **Package Tracking**: Real-time order status tracking system
3. **Partner Dashboard**: Administrative interface for delivery partners
4. **PDF Bill Generation**: Automated receipt and bill generation
5. **Zone-based Pricing**: Flexible pricing based on delivery zones

## Data Flow

1. **Order Creation Flow**:
   - Customer fills order form → Form validation → Order creation → Reference number generation → Confirmation page

2. **Tracking Flow**:
   - Customer enters reference number → Database lookup → Status display → Order details presentation

3. **Partner Dashboard Flow**:
   - Partner login → Authentication → Dashboard with order statistics → Order management interface

## External Dependencies

### Python Packages
- Flask: Web framework
- Flask-SQLAlchemy: Database ORM
- Werkzeug: Password hashing and WSGI utilities
- ReportLab: PDF generation library

### Frontend Dependencies
- Bootstrap 5: CSS framework (CDN)
- Font Awesome: Icon library (CDN)

### Database
- SQLite: Default database (development)
- PostgreSQL: Production database support via DATABASE_URL environment variable

## Deployment Strategy

### Environment Configuration
- **SESSION_SECRET**: Session encryption key
- **DATABASE_URL**: Database connection string
- **Development Mode**: Debug mode enabled for local development

### Database Management
- Automatic table creation on application startup
- Default data initialization for zones and admin partner
- Connection pooling with automatic reconnection

### WSGI Configuration
- ProxyFix middleware for handling reverse proxy headers
- Production-ready WSGI application setup

## Changelog
- July 07, 2025. Initial setup
- July 07, 2025. Added admin authentication system with Flask-Login
- July 07, 2025. Implemented volume-based pricing with insurance options  
- July 07, 2025. Redesigned UI with modern, clean interface inspired by trackon.in

## Recent Changes
- Created modern homepage with centered tracking input and gradient design
- Added responsive service cards with hover effects and smooth animations
- Implemented clean tracking results page with timeline visualization
- Updated order placement form with modern styling and better UX
- Fixed JavaScript syntax errors and updated pricing calculation
- Enhanced navigation with three separate login options (Consumer, Partner, Admin)
- Fixed database schema by adding missing columns to orders table
- Created consistent aesthetic design across all pages matching homepage
- Added mobile-responsive design with improved touch targets
- Implemented light/dark mode toggle functionality
- Fixed JavaScript selector errors for better user experience

## User Preferences

Preferred communication style: Simple, everyday language.
UI Design: Modern, clean interface inspired by trackon.in with smooth animations, responsive design, and mobile-friendly layout.