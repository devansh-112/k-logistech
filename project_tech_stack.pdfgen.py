from fpdf import FPDF
from datetime import datetime

pdf = FPDF()
pdf.add_page()
pdf.set_font('Arial', 'B', 16)
pdf.cell(0, 10, 'GotoFast Logistics - Technology Stack Overview', ln=1, align='C')
pdf.set_font('Arial', '', 12)
pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=1)
pdf.ln(5)

# Backend Section
pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Backend', ln=1)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, (
    "- Python 3: The core programming language for all backend logic.\n"
    "- Flask: Lightweight web framework for routing, request handling, and templating.\n"
    "- SQLAlchemy: ORM for database access and migrations.\n"
    "- SQLite: Embedded database for development and production.\n"
    "- FPDF: Used for generating PDF invoices and reports.\n"
    "- Flask-Login: User session and authentication management.\n"
    "- Jinja2: Template engine for rendering HTML with dynamic data.\n"
    "- Other: Werkzeug (WSGI), logging, and standard Python libraries."
))
pdf.ln(3)

# Frontend Section
pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Frontend', ln=1)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, (
    "- HTML5: Markup for all web pages and forms.\n"
    "- CSS3: Custom styles and layout.\n"
    "- Bootstrap 5: Responsive design, grid system, and UI components.\n"
    "- JavaScript: Client-side interactivity and validation.\n"
    "- Chart.js: Data visualization for admin reports.\n"
    "- Font Awesome: Iconography throughout the UI.\n"
    "- Jinja2: Dynamic HTML rendering from Flask backend."
))
pdf.ln(3)

# Other/Deployment Section
pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Other & Deployment', ln=1)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, (
    "- Railway: Cloud deployment platform for hosting the Flask app.\n"
    "- Gunicorn (optional): For production WSGI serving.\n"
    "- Environment Variables: For configuration and secrets.\n"
    "- Git & GitHub: Version control and collaboration.\n"
    "- Replit: Used for initial prototyping and development."
))
pdf.ln(3)

# Summary
pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Summary', ln=1)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, (
    "GotoFast Logistics is a modern, full-stack web application built with Python Flask on the backend and Bootstrap-powered HTML/CSS/JS on the frontend. It leverages SQLAlchemy ORM for database management, FPDF for PDF generation, and Chart.js for analytics. The stack is chosen for rapid development, reliability, and ease of deployment."
))

pdf.output('GotoFast_Logistics_Tech_Stack.pdf')
print('PDF generated: GotoFast_Logistics_Tech_Stack.pdf') 