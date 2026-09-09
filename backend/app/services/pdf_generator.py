import os
import qrcode
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from datetime import datetime

def generate_ticket_pdf(bookings, payment, schedule):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Colors
    primary_color = colors.HexColor('#2563eb')
    secondary_color = colors.HexColor('#f8fafc')
    text_dark = colors.HexColor('#0f172a')
    
    # Header Background
    c.setFillColor(primary_color)
    c.rect(0, height - 100, width, 100, fill=True, stroke=False)
    
    # Header Text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height - 50, "SmartBus AI")
    c.setFont("Helvetica", 12)
    c.drawString(40, height - 70, "E-Ticket & Boarding Pass")

    # Booking Reference
    c.setFillColor(text_dark)
    c.setFont("Helvetica-Bold", 14)
    txn_id = payment.transaction_id if payment else 'N/A'
    c.drawString(40, height - 140, f"Booking Ref: {txn_id}")
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 155, f"Date: {datetime.utcnow().strftime('%B %d, %Y')}")

    # Passenger Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 190, "Passenger Details")
    c.setFont("Helvetica", 10)
    
    y_offset = 210
    total_fare = 0
    seats = []
    
    for booking in bookings:
        p_name = booking.passenger_name or "Guest Traveler"
        p_age = booking.passenger_age
        p_gender = booking.passenger_gender or "--"
        
        p_type = "Adult"
        if p_age is not None:
            try:
                age_val = int(p_age)
                if age_val < 18:
                    p_type = "Child"
                else:
                    p_type = "Adult"
            except (ValueError, TypeError):
                pass
                
        age_str = f"{p_age}" if p_age is not None else "--"
        c.drawString(40, height - y_offset, f"{p_name} ({p_type}, Age: {age_str}, {p_gender}) - Seat: {booking.seat_number}")
        y_offset += 15
        total_fare += booking.fare_paid or 0
        seats.append(booking.seat_number)
        
    seats_str = ", ".join(seats)
    
    # Journey Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - 190, "Journey Details")
    c.setFont("Helvetica", 10)
    origin = schedule.route.origin.title() if schedule and schedule.route else "Unknown"
    dest = schedule.route.destination.title() if schedule and schedule.route else "Unknown"
    dept_time = schedule.departure_time.strftime('%I:%M %p') if schedule else "09:00 PM"
    arr_time = schedule.arrival_time.strftime('%I:%M %p') if schedule else "06:00 AM"
    
    c.drawString(300, height - 210, f"From: {origin} -> To: {dest}")
    c.drawString(300, height - 225, f"Departure: {dept_time} | Arrival: {arr_time}")
    
    # Seat & Bus
    info_y_offset = y_offset + 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - info_y_offset, "Seat & Bus Info")
    c.setFont("Helvetica", 10)
    bus_num = schedule.bus.bus_number if schedule and schedule.bus else "SMART-707"
    c.drawString(40, height - (info_y_offset + 20), f"Bus Number: {bus_num}")
    c.drawString(40, height - (info_y_offset + 35), f"Seat(s): {seats_str}")
    c.drawString(40, height - (info_y_offset + 50), f"Total Fare Paid: Rs. {total_fare}")

    # Gamification: Carbon Credits
    c.setFillColor(colors.HexColor('#10b981')) # Green
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - info_y_offset, "Green Wallet")
    c.setFont("Helvetica", 10)
    eco_rating = schedule.bus.eco_rating if schedule and schedule.bus else "High"
    points = (50 if eco_rating == "High" else 20) * len(bookings)
    c.drawString(300, height - (info_y_offset + 20), f"Eco Rating: {eco_rating}")
    c.drawString(300, height - (info_y_offset + 35), f"Carbon Credits Earned: +{points} pts")
    c.setFillColor(text_dark)

    # QR Code
    qr_data = f"TICKET:{txn_id}|SEATS:{seats_str}|BUS:{bus_num}"
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = BytesIO()
    img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(qr_buffer), 400, height - (info_y_offset + 140), width=100, height=100)
    
    # Footer
    c.setStrokeColor(colors.lightgrey)
    c.line(40, 100, width - 40, 100)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 80, "Thank you for choosing SmartBus AI. Have a safe and eco-friendly journey!")
    c.drawString(40, 65, "Please show this QR code to the driver upon boarding.")

    c.save()
    buffer.seek(0)
    return buffer
