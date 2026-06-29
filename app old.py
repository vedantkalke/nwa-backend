from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
CORS(app)

from admin import admin
app.register_blueprint(admin)

DATA_FILE     = 'data/enquiries.json'
BOOKINGS_FILE = 'data/bookings.json'

# ============================================================
# HELPERS
# ============================================================

def load_enquiries():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_enquiries(enquiries):
    os.makedirs('data', exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(enquiries, f, indent=2)

def load_bookings():
    if os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_bookings(bookings):
    os.makedirs('data', exist_ok=True)
    with open(BOOKINGS_FILE, 'w') as f:
        json.dump(bookings, f, indent=2)

def send_enquiry_emails(enquiry):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)

            team_msg = MIMEMultipart()
            team_msg['From'] = config.SENDER_EMAIL
            team_msg['To']   = config.TEAM_EMAIL
            team_msg['Subject'] = f"New Enquiry — {enquiry['firstName']} {enquiry['lastName']}"
            team_msg.attach(MIMEText(f"""
New student enquiry on the NWA India website.

STUDENT DETAILS
---------------
Name      : {enquiry['firstName']} {enquiry['lastName']}
Email     : {enquiry['email']}
Phone     : {enquiry['phone']}
Programme : {enquiry['programme']}
Licence   : {enquiry['licence']}
Message   : {enquiry['message']}
Time      : {enquiry['submittedAt']}
""", 'plain'))
            server.send_message(team_msg)

            student_msg = MIMEMultipart()
            student_msg['From']    = config.SENDER_EMAIL
            student_msg['To']      = enquiry['email']
            student_msg['Subject'] = f"We received your enquiry — {config.ACADEMY_NAME}"
            student_msg.attach(MIMEText(f"""
Dear {enquiry['firstName']},

Thank you for your interest in {config.ACADEMY_NAME}.

We have received your enquiry for the {enquiry['programme']} programme
and our admissions team will get back to you within 24 hours.

YOUR ENQUIRY DETAILS
--------------------
Name      : {enquiry['firstName']} {enquiry['lastName']}
Programme : {enquiry['programme']}
Submitted : {enquiry['submittedAt']}

Phone : +48 787 777 505
Email : biuro@nwa.aero

Best regards,
{config.ACADEMY_NAME} Admissions Team
""", 'plain'))
            server.send_message(student_msg)
            print(f"   Enquiry emails sent → {enquiry['email']}")
    except Exception as e:
        print(f"   Enquiry email error: {e}")

def send_booking_emails(booking):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)

            team_msg = MIMEMultipart()
            team_msg['From']    = config.SENDER_EMAIL
            team_msg['To']      = config.TEAM_EMAIL
            team_msg['Subject'] = f"New Counselling Booking — {booking['name']} ({booking['slot']})"
            team_msg.attach(MIMEText(f"""
New counselling slot booked on the NWA India website.

BOOKING DETAILS
---------------
Name   : {booking['name']}
Email  : {booking['email']}
Phone  : {booking['phone']}
Date   : {booking.get('date', booking['day'])}
Slot   : {booking['slot']} (30 minutes)
Booked : {booking['bookedAt']}
""", 'plain'))
            server.send_message(team_msg)

            student_msg = MIMEMultipart()
            student_msg['From']    = config.SENDER_EMAIL
            student_msg['To']      = booking['email']
            student_msg['Subject'] = f"Counselling Call Confirmed — {config.ACADEMY_NAME}"
            student_msg.attach(MIMEText(f"""
Dear {booking['name']},

Your counselling call has been confirmed with {config.ACADEMY_NAME}.

BOOKING DETAILS
---------------
Date   : {booking.get('date', booking['day'])}
Slot   : {booking['slot']} (30 minutes)
Booked : {booking['bookedAt']}

Our admissions team will call you at {booking['phone']} at the scheduled time.

To reschedule:
Phone : +48 787 777 505
Email : biuro@nwa.aero

Best regards,
{config.ACADEMY_NAME} Admissions Team
""", 'plain'))
            server.send_message(student_msg)
            print(f"   Booking emails sent → {booking['email']}")
    except Exception as e:
        print(f"   Booking email error: {e}")

# ============================================================
# ROUTES — Website
# ============================================================

@app.route('/')
def home():
    return jsonify({'status': 'NWA Backend running'})

@app.route('/website')
def website():
    return send_from_directory('static', 'index.html')

@app.route('/website/<path:filename>')
def website_files(filename):
    return send_from_directory('static', filename)

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ============================================================
# ROUTES — Enquiry Form
# ============================================================

@app.route('/submit-enquiry', methods=['POST'])
def submit_enquiry():
    data = request.get_json()
    for field in ['firstName', 'lastName', 'email', 'phone', 'programme']:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400

    enquiry = {
        'id':          datetime.now().strftime('%Y%m%d%H%M%S'),
        'firstName':   data.get('firstName'),
        'lastName':    data.get('lastName'),
        'email':       data.get('email'),
        'phone':       data.get('phone'),
        'programme':   data.get('programme'),
        'licence':     data.get('licence', 'Not specified'),
        'message':     data.get('message', ''),
        'status':      'new',
        'submittedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    enquiries = load_enquiries()
    enquiries.append(enquiry)
    save_enquiries(enquiries)
    send_enquiry_emails(enquiry)

    print(f"\n New enquiry: {enquiry['firstName']} {enquiry['lastName']} — {enquiry['programme']}")
    return jsonify({'success': True, 'message': 'Enquiry received'})

@app.route('/enquiries', methods=['GET'])
def get_enquiries():
    return jsonify({'total': len(load_enquiries()), 'enquiries': load_enquiries()})

# ============================================================
# ROUTES — Counselling Slot Booking
# ============================================================

@app.route('/book-slot', methods=['POST'])
def book_slot():
    try:
        data = request.get_json()
        for field in ['name', 'email', 'phone', 'day', 'time']:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        # Validate booking is within current week
        booking_date = data.get('date', '')
        if booking_date:
            try:
                bdate = datetime.strptime(booking_date, '%Y-%m-%d').date()
                today = datetime.now().date()
                # Monday of this week
                week_start = today - timedelta(days=today.weekday())
                week_end   = week_start + timedelta(days=4)  # Friday
                if bdate < today:
                    return jsonify({'success': False, 'error': 'Cannot book a slot in the past.'}), 400
                if bdate > week_end:
                    return jsonify({'success': False, 'error': 'Bookings are only available for this week.'}), 400
            except ValueError:
                pass

        booking = {
            'id':       datetime.now().strftime('%Y%m%d%H%M%S'),
            'name':     data['name'],
            'email':    data['email'],
            'phone':    data['phone'],
            'day':      data['day'],
            'time':     data['time'],
            'date':     booking_date,
            'slot':     f"{data['day']} {data['time']}",
            'status':   'confirmed',
            'bookedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        bookings = load_bookings()
        bookings.append(booking)
        save_bookings(bookings)
        send_booking_emails(booking)

        print(f"\n New booking: {booking['name']} @ {booking['slot']} ({booking_date})")
        return jsonify({'success': True, 'message': 'Booking confirmed'})

    except Exception as e:
        print(f"   Book slot error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/bookings', methods=['GET'])
def get_bookings():
    return jsonify({'total': len(load_bookings()), 'bookings': load_bookings()})

# ============================================================
# ROUTES — Captain Aero AI Chat
# ============================================================

NWA_SYSTEM_PROMPT = """You are Captain Aero, the AI flight assistant for Noble Wings Academy (NWA) India.

ABOUT NWA:
- Noble Wings Academy is an EASA-approved ATO based in Leszno, Poland
- NWA India hub is in Andheri, Mumbai
- Director: Capt. Rasiklal Tapase

COURSES: ATPL(A) Integrated, ATPL(A) 100 KSA, CPL(A)+IR/ME, PPL(A) Theory, PPL(A) Practice,
LAPL(A), VFR Night Rating, FI(A), UPRT Advanced, ICAO Aviation English, Hour Building, First Start.

KEY FACTS: EASA licences valid across 27 EU countries. DGCA conversion prep available.
Fleet: Tomark Viper SD-4, Tecnam P2008JC, Piper PA-28R Arrow, Tecnam P2006T.
Simulators: ALSIM AL250 FNPT II.

PERSONALITY: Calm, precise airline captain voice. Encouraging to aspiring pilots.
For fees, direct to admissions team. Contact: biuro@nwa.aero / +48 787 777 505"""

@app.route('/chat', methods=['POST'])
def chat():
    try:
        import anthropic
        data     = request.get_json()
        messages = data.get('messages', [])
        if not messages:
            return jsonify({'success': False, 'error': 'No messages'}), 400

        client   = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=600,
            system=NWA_SYSTEM_PROMPT,
            messages=messages
        )
        reply = response.content[0].text
        print(f"   Captain Aero replied ({len(reply)} chars)")
        return jsonify({'success': True, 'reply': reply})
    except Exception as e:
        print(f"   Chat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# START SERVER
# ============================================================

if __name__ == '__main__':
    print("NWA Backend starting...")
    print("Website      : http://localhost:5000/website")
    print("Admin portal : http://localhost:5000/admin")
    app.run(debug=True, port=5000)