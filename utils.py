from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import logging

def calculate_estimated_delivery(delivery_days):
    """Calculate estimated delivery date"""
    now = datetime.utcnow()
    # Skip weekends for business days calculation
    delivery_date = now
    days_added = 0
    
    while days_added < delivery_days:
        delivery_date += timedelta(days=1)
        # Skip weekends (Saturday = 5, Sunday = 6)
        if delivery_date.weekday() < 5:
            days_added += 1
    
    return delivery_date

def generate_pdf_bill(order):
    """Generate PDF bill for order"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6
        )
        
        # Title
        title = Paragraph("LOGISTICS DELIVERY BILL", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Order Information
        order_info = [
            ['Reference Number:', order.reference_number],
            ['Order Date:', order.created_at.strftime('%B %d, %Y at %I:%M %p')],
            ['Delivery Status:', order.delivery_status.replace('_', ' ').title()],
            ['Payment Status:', order.payment_status.replace('_', ' ').title()],
        ]
        
        order_table = Table(order_info, colWidths=[2*inch, 4*inch])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(order_table)
        elements.append(Spacer(1, 20))
        
        # Customer Information
        customer_heading = Paragraph("Customer Information", heading_style)
        elements.append(customer_heading)
        
        customer_info = [
            ['Name:', order.customer_name],
            ['Email:', order.customer_email],
            ['Phone:', order.customer_phone],
            ['Pickup Address:', order.pickup_address],
            ['Delivery Address:', order.delivery_address],
        ]
        
        # Add recipient information if different
        if order.recipient_name and order.recipient_name != order.customer_name:
            customer_info.extend([
                ['', ''],
                ['Recipient Name:', order.recipient_name],
                ['Recipient Phone:', order.recipient_phone],
            ])
        
        customer_table = Table(customer_info, colWidths=[2*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(customer_table)
        elements.append(Spacer(1, 20))
        
        # Package Information
        package_heading = Paragraph("Package Information", heading_style)
        elements.append(package_heading)
        
        package_info = [
            ['Zone:', order.zone.name],
            ['Weight:', f"{order.weight} kg"],
            ['Dimensions (L×W×H):', f"{order.length} × {order.width} × {order.height} cm"],
            ['Quantity:', f"{order.quantity} package(s)"],
            ['Description:', order.package_description or 'N/A'],
            ['Payment Mode:', order.payment_mode.replace('_', ' ').title()],
        ]
        
        # Add insurance information
        if order.insurance_required:
            package_info.extend([
                ['', ''],
                ['Insurance Required:', 'Yes'],
                ['Declared Value:', f"₹{order.insurance_value}"],
                ['Insurance Premium:', f"₹{order.insurance_premium}"],
            ])
        else:
            package_info.append(['Insurance Required:', 'No'])
        
        package_table = Table(package_info, colWidths=[2*inch, 4*inch])
        package_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(package_table)
        elements.append(Spacer(1, 20))
        
        # Delivery Information
        delivery_heading = Paragraph("Delivery Information", heading_style)
        elements.append(delivery_heading)
        
        delivery_info = [
            ['Estimated Delivery:', order.estimated_delivery.strftime('%B %d, %Y at %I:%M %p')],
            ['Actual Delivery:', order.actual_delivery.strftime('%B %d, %Y at %I:%M %p') if order.actual_delivery else 'Pending'],
        ]
        
        delivery_table = Table(delivery_info, colWidths=[2*inch, 4*inch])
        delivery_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(delivery_table)
        elements.append(Spacer(1, 20))
        
        # Billing Information
        billing_heading = Paragraph("Billing Information", heading_style)
        elements.append(billing_heading)
        
        # Calculate breakdown using the same logic as the model
        base_cost = order.zone.base_rate * order.weight * order.quantity
        volume = (order.length * order.width * order.height) / 1000000  # Convert cm³ to m³
        volume_cost = volume * 50  # ₹50 per cubic meter
        shipping_cost = max(base_cost, volume_cost)
        
        payment_fees = {
            'cash_on_delivery': 0.02,
            'online_payment': 0.0,
            'card_payment': 0.015
        }
        payment_fee_rate = payment_fees.get(order.payment_mode, 0.0)
        payment_fee = shipping_cost * payment_fee_rate
        
        insurance_cost = order.insurance_premium if order.insurance_required else 0.0
        
        billing_info = [
            ['Weight-based Cost:', f"₹{base_cost:.2f}"],
            ['Volume-based Cost:', f"₹{volume_cost:.2f}"],
            ['Shipping Cost (Higher of above):', f"₹{shipping_cost:.2f}"],
            ['Payment Processing Fee:', f"₹{payment_fee:.2f}"],
        ]
        
        if order.insurance_required and insurance_cost > 0:
            billing_info.append(['Insurance Premium:', f"₹{insurance_cost:.2f}"])
        
        billing_info.extend([
            ['', ''],
            ['Total Amount:', f"₹{order.total_amount:.2f}"],
        ])
        
        billing_table = Table(billing_info, colWidths=[3*inch, 2*inch])
        billing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -2), colors.HexColor('#ecf0f1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, -2), colors.black),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -2), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 12),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('GRID', (0, -1), (-1, -1), 2, colors.black)
        ]))
        
        elements.append(billing_table)
        elements.append(Spacer(1, 30))
        
        # Footer
        footer_text = Paragraph(
            "Thank you for choosing our logistics service!<br/>"
            "For any queries, please contact us with your reference number.<br/>"
            f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#7f8c8d')
            )
        )
        elements.append(footer_text)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
        
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        raise e
