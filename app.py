from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from functools import wraps
import time
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Lock CORS to allowed origins only
CORS(app, origins=config.ALLOWED_ORIGINS)

from admin import admin
app.register_blueprint(admin)

DATA_FILE     = 'data/enquiries.json'
BOOKINGS_FILE = 'data/bookings.json'

# ============================================================
# SECURITY — Rate Limiting (in-memory, per IP)
# ============================================================

rate_limit_store = {}

def rate_limit(max_requests=10, window_seconds=60):
    """Simple rate limiter: max_requests per window_seconds per IP."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr
            key = f"{f.__name__}:{ip}"
            now = time.time()

            if key not in rate_limit_store:
                rate_limit_store[key] = []

            # Remove expired timestamps
            rate_limit_store[key] = [t for t in rate_limit_store[key] if now - t < window_seconds]

            if len(rate_limit_store[key]) >= max_requests:
                return jsonify({'success': False, 'error': 'Too many requests. Please try again later.'}), 429

            rate_limit_store[key].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================
# SECURITY — Response Headers
# ============================================================

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

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
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context, timeout=10) as server:
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)

            team_msg = MIMEMultipart()
            team_msg['From'] = f"NWA Admissions <{config.SENDER_EMAIL}>"
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

            student_msg = MIMEMultipart('related')
            student_msg['From']    = f"Noble Wings Academy <{config.SENDER_EMAIL}>"
            student_msg['To']      = enquiry['email']
            student_msg['Subject'] = f"We received your enquiry — {config.ACADEMY_NAME}"

            student_html = f"""
<html>
<body style="margin:0; padding:0; font-family: Arial, Helvetica, sans-serif; color:#222; background:#f5f5f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5; padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:#0a1628; padding:28px 40px; text-align:center;">
            <h1 style="margin:0; font-size:22px; letter-spacing:6px; color:#ffffff; font-weight:300;">N O B L E W I N G S</h1>
            <p style="margin:4px 0 0; font-size:12px; letter-spacing:4px; color:#b0b8c8; font-weight:300;">A C A D E M Y</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 20px;">
            <p style="font-size:16px; margin:0 0 20px;">Dear {enquiry['firstName']},</p>
            <p style="font-size:15px; line-height:1.7; margin:0 0 20px; color:#333;">
              Thank you for your interest in <strong>Noble Wings Academy</strong>.<br>
              We have received your enquiry for the <strong>{enquiry['programme']}</strong> programme
              and our admissions team will get back to you within <strong>24 hours</strong>.
            </p>
          </td>
        </tr>

        <!-- Enquiry Details Box -->
        <tr>
          <td style="padding:0 40px 30px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8; border-radius:6px; border-left:4px solid #0a1628;">
              <tr><td style="padding:20px 24px;">
                <p style="margin:0 0 12px; font-size:13px; font-weight:bold; color:#0a1628; letter-spacing:1px;">YOUR ENQUIRY DETAILS</p>
                <table cellpadding="4" cellspacing="0" style="font-size:14px; color:#333;">
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Name</td><td>{enquiry['firstName']} {enquiry['lastName']}</td></tr>
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Programme</td><td>{enquiry['programme']}</td></tr>
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Licence</td><td>{enquiry['licence']}</td></tr>
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Submitted</td><td>{enquiry['submittedAt']}</td></tr>
                </table>
              </td></tr>
            </table>
          </td>
        </tr>

        <!-- Divider -->
        <tr><td style="padding:0 40px;"><hr style="border:none; border-top:1px solid #e0e0e0; margin:0;"></td></tr>

        <!-- Signature -->
        <tr>
          <td style="padding:24px 40px 12px;">
            <p style="margin:0 0 4px; font-size:14px; color:#333;">Best Regards,</p>
            <p style="margin:0 0 2px; font-size:15px; font-weight:bold; color:#0a1628;">Parth Kajavadra</p>
            <p style="margin:0 0 10px; font-size:13px; color:#555;">Noble Wings Academy</p>
            <p style="margin:0; font-size:12px; color:#666; line-height:1.6;">
              A-905, Rustomjee Central Park, Opp. Kanakia Wall Street,<br>
              Chakala, Andheri East, Mumbai, India &ndash; 400093
            </p>
            <p style="margin:10px 0 0; font-size:13px; color:#333;">
              &#128222; <a href="tel:+919930050444" style="color:#0a1628; text-decoration:none;">+91 9930050444</a><br>
              &#9993; <a href="mailto:pkajavadra@nwa.aero" style="color:#0a1628; text-decoration:none;">pkajavadra@nwa.aero</a><br>
              &#127760; <a href="https://www.nwa.aero" style="color:#0a1628; text-decoration:none;">www.nwa.aero</a>
            </p>
            <img src="https://nwa-backend-cba6.onrender.com/static/NW-logo.png" alt="Noble Wings Academy" style="width:150px; margin-top:16px;" />
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#0a1628; padding:16px 40px; text-align:right;">
            <p style="margin:0; font-size:13px; letter-spacing:3px; color:#b0b8c8; font-weight:bold;">AIM HIGH...</p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
            student_msg.attach(MIMEText(student_html, 'html'))
            server.send_message(student_msg)
            print(f"   Enquiry emails sent → {enquiry['email']}")
    except Exception as e:
        print(f"   Enquiry email error: {e}")

def send_booking_emails(booking):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context, timeout=10) as server:
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)

            team_msg = MIMEMultipart()
            team_msg['From']    = f"NWA Admissions <{config.SENDER_EMAIL}>"
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

            student_msg = MIMEMultipart('alternative')
            student_msg['From']    = f"Noble Wings Academy <{config.SENDER_EMAIL}>"
            student_msg['To']      = booking['email']
            student_msg['Subject'] = f"Counselling Call Confirmed — {config.ACADEMY_NAME}"

            student_html = f"""
<html>
<body style="margin:0; padding:0; font-family: Arial, Helvetica, sans-serif; color:#222; background:#f5f5f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5; padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:#0a1628; padding:28px 40px; text-align:center;">
            <h1 style="margin:0; font-size:22px; letter-spacing:6px; color:#ffffff; font-weight:300;">N O B L E W I N G S</h1>
            <p style="margin:4px 0 0; font-size:12px; letter-spacing:4px; color:#b0b8c8; font-weight:300;">A C A D E M Y</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 20px;">
            <p style="font-size:16px; margin:0 0 20px;">Dear {booking['name']},</p>
            <p style="font-size:15px; line-height:1.7; margin:0 0 20px; color:#333;">
              Your counselling call has been <strong>confirmed</strong> with <strong>Noble Wings Academy</strong>.<br>
              Our admissions team will call you at <strong>{booking['phone']}</strong> at the scheduled time.
            </p>
          </td>
        </tr>

        <!-- Booking Details Box -->
        <tr>
          <td style="padding:0 40px 30px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8; border-radius:6px; border-left:4px solid #0a1628;">
              <tr><td style="padding:20px 24px;">
                <p style="margin:0 0 12px; font-size:13px; font-weight:bold; color:#0a1628; letter-spacing:1px;">BOOKING DETAILS</p>
                <table cellpadding="4" cellspacing="0" style="font-size:14px; color:#333;">
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Date</td><td>{booking.get('date', booking['day'])}</td></tr>
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Slot</td><td>{booking['slot']} (30 minutes)</td></tr>
                  <tr><td style="font-weight:bold; color:#555; padding-right:16px;">Booked</td><td>{booking['bookedAt']}</td></tr>
                </table>
              </td></tr>
            </table>
          </td>
        </tr>

        <!-- Reschedule Note -->
        <tr>
          <td style="padding:0 40px 24px;">
            <p style="font-size:13px; color:#666; line-height:1.6; margin:0;">
              Need to reschedule? Contact us at
              <a href="tel:+919930050444" style="color:#0a1628;">+91 9930050444</a> or
              <a href="mailto:pkajavadra@nwa.aero" style="color:#0a1628;">pkajavadra@nwa.aero</a>
            </p>
          </td>
        </tr>

        <!-- Divider -->
        <tr><td style="padding:0 40px;"><hr style="border:none; border-top:1px solid #e0e0e0; margin:0;"></td></tr>

        <!-- Signature -->
        <tr>
          <td style="padding:24px 40px 12px;">
            <p style="margin:0 0 4px; font-size:14px; color:#333;">Best Regards,</p>
            <p style="margin:0 0 2px; font-size:15px; font-weight:bold; color:#0a1628;">Parth Kajavadra</p>
            <p style="margin:0 0 10px; font-size:13px; color:#555;">Noble Wings Academy</p>
            <p style="margin:0; font-size:12px; color:#666; line-height:1.6;">
              A-905, Rustomjee Central Park, Opp. Kanakia Wall Street,<br>
              Chakala, Andheri East, Mumbai, India &ndash; 400093
            </p>
            <p style="margin:10px 0 0; font-size:13px; color:#333;">
              &#128222; <a href="tel:+919930050444" style="color:#0a1628; text-decoration:none;">+91 9930050444</a><br>
              &#9993; <a href="mailto:pkajavadra@nwa.aero" style="color:#0a1628; text-decoration:none;">pkajavadra@nwa.aero</a><br>
              &#127760; <a href="https://www.nwa.aero" style="color:#0a1628; text-decoration:none;">www.nwa.aero</a>
            </p>
            <img src="cid:nwalogo" alt="Noble Wings Academy" style="width:150px; margin-top:16px;" />
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#0a1628; padding:16px 40px; text-align:right;">
            <p style="margin:0; font-size:13px; letter-spacing:3px; color:#b0b8c8; font-weight:bold;">AIM HIGH...</p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
            student_msg.attach(MIMEText(student_html, 'html'))
            logo_path = os.path.join('static', 'NW-logo.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as img_file:
                    logo = MIMEImage(img_file.read())
                    logo.add_header('Content-ID', '<nwalogo>')
                    logo.add_header('Content-Disposition', 'inline')
                    student_msg.attach(logo)
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
# ROUTES — Enquiry Form (rate limited: 5 per minute)
# ============================================================

@app.route('/submit-enquiry', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
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
    import threading
    def _send():
        try:
            print("Attempting enquiry email...")
            send_enquiry_emails(enquiry)
            print("Enquiry email sent!")
        except Exception as e:
            print(f"Email failed: {e}")
    threading.Thread(target=_send).start()

    print(f"\n New enquiry: {enquiry['firstName']} {enquiry['lastName']} — {enquiry['programme']}")
    return jsonify({'success': True, 'message': 'Enquiry received'})

@app.route('/enquiries', methods=['GET'])
def get_enquiries():
    return jsonify({'total': len(load_enquiries()), 'enquiries': load_enquiries()})

# ============================================================
# ROUTES — Counselling Slot Booking (rate limited: 5 per minute)
# ============================================================

@app.route('/book-slot', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
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

        import threading
        def _send_booking():
            try:
                print("Attempting booking email...")
                send_booking_emails(booking)
                print("Booking email sent!")
            except Exception as e:
                print(f"Booking email failed: {e}")
        threading.Thread(target=_send_booking).start()

        print(f"\n New booking: {booking['name']} @ {booking['slot']} ({booking_date})")
        return jsonify({'success': True, 'message': 'Booking confirmed'})

    except Exception as e:
        print(f"   Book slot error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/bookings', methods=['GET'])
def get_bookings():
    return jsonify({'total': len(load_bookings()), 'bookings': load_bookings()})

# ============================================================
# ROUTES — Captain Aero AI Chat (rate limited: 15 per minute)
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
@rate_limit(max_requests=15, window_seconds=60)
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
        return jsonify({'success': False, 'error': 'Chat service temporarily unavailable.'}), 500

# ============================================================
# START SERVER
# ============================================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  Noble Wings Academy — Backend")
    print("=" * 50)
    print(f"  Website      : http://localhost:5000/website")
    print(f"  Admin portal : http://localhost:5000/admin")
    print(f"  CORS origins : {config.ALLOWED_ORIGINS}")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)