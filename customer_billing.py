from models import GlobalPricingConfig

def calculate_customer_bill(data):
    config = GlobalPricingConfig.query.first()
    if not config:
        raise Exception("Pricing configuration not set.")

    gst_rate = config.gst_rate

    # Pickup Charges
    if data['location_type'] == 'jaipur_city':
        pickup_charge = config.pickup_charge_jaipur
    elif data['location_type'] == 'oda_jaipur':
        pickup_charge = config.pickup_charge_oda_jaipur
    else:
        pickup_charge = 0  # For Rajasthan/All India, handled in delivery

    # Delivery Charges
    weight = data['weight']
    delivery_charge = 0

    if data['location_type'] == 'jaipur_city':
        if data['distance_km'] <= 5:
            delivery_charge = config.delivery_charge_jaipur_0_5
        elif data['distance_km'] <= 15:
            delivery_charge = config.delivery_charge_jaipur_5_15
    elif data['location_type'] == 'rajasthan':
        if weight <= config.min_weight:
            delivery_charge = config.delivery_charge_rajasthan_base
        else:
            delivery_charge = config.delivery_charge_rajasthan_base + (weight - config.min_weight) * config.delivery_charge_rajasthan_per_kg
    elif data['location_type'] == 'all_india':
        if weight <= config.min_weight:
            delivery_charge = config.delivery_charge_india_base
        else:
            delivery_charge = config.delivery_charge_india_base + (weight - config.min_weight) * config.delivery_charge_india_per_kg

    # ODA Surcharge
    oda_charge = config.oda_charge if data.get('is_oda', False) else 0

    # Subtotal
    subtotal = pickup_charge + delivery_charge + oda_charge

    # GST
    gst = subtotal * gst_rate
    total = subtotal + gst

    # E-way Bill
    eway_bill_required = data['declared_value'] > 50000

    # Build Invoice Dict
    invoice = {
        "pickup_charge": pickup_charge,
        "delivery_charge": delivery_charge,
        "oda_charge": oda_charge,
        "subtotal": subtotal,
        "gst": gst,
        "total": total,
        "eway_bill_required": eway_bill_required,
        "product_description": data['description'],
        "declared_value": data['declared_value'],
        "weight": weight,
        "dimensions": data['dimensions'],
    }
    return invoice 