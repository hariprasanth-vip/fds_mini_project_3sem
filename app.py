from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
# openpyxl தேவை: pip install openpyxl
from openpyxl import Workbook 

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24) 
EXCEL_FILE = 'Exports/bookings_export.xlsx'

# --- Database Functions ---
def get_db_connection():
    # SQLite Row Factory பயன்படுத்தி, தரவுத்தள முடிவுகளை அகராதியாக (Dictionary) பெறலாம்
    conn = sqlite3.connect('hall_booking.db')
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Users, Halls, and Bookings table creations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'staff')
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS halls (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, capacity INTEGER NOT NULL)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, staff_username TEXT NOT NULL, hall_id INTEGER NOT NULL, date TEXT NOT NULL, attendees INTEGER, FOREIGN KEY (hall_id) REFERENCES halls(id))
    """)

    # Sample Data (Username: staff, Password: staffpass)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('staff', 'staffpass')) 
    
    if conn.execute("SELECT COUNT(*) FROM halls").fetchone()[0] == 0:
        cur.executemany("INSERT INTO halls (name, capacity) VALUES (?, ?)", [
            ("Main Auditorium", 300), ("Conference Hall", 120), ("Seminar Hall", 80), ("Mini Hall", 50)
        ])
    conn.commit()
    conn.close()


# app.py-la mela import section-la 'os' irukkanumnu check pannunga
import os 
# ...

# --- Excel Export Function (CORRECTED with Directory Check) ---
def export_bookings_to_excel():
    """SQLite-இல் உள்ள மொத்த முன்பதிவுத் தரவுகளையும் Excel-இல் சேமிக்கிறது."""
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT 
            b.id AS Booking_ID, 
            h.name AS Hall_Name, 
            b.date AS Booking_Date, 
            b.attendees AS Attendees_Count,
            b.staff_username AS Booked_By
        FROM bookings b
        JOIN halls h ON b.hall_id = h.id
        ORDER BY b.date DESC
    """, conn)
    conn.close()

    if df.empty:
        print("ℹ️ No bookings yet to export to Excel.")
        return False
        
    try:
        # ✅ FIX: Directory இல்லையென்றால், அதை தானாகவே உருவாக்கவும்
        # EXCEL_FILE is 'Exports/bookings_export.xlsx'
        export_dir = os.path.dirname(EXCEL_FILE) 
        if export_dir and not os.path.exists(export_dir):
            os.makedirs(export_dir) # Folder-a create pannum
            print(f"📁 Created directory: {export_dir}")


        # Excel File-இல் சேமிக்கவும்
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        print(f"✅ Data successfully exported to {EXCEL_FILE}")
        return True
        
    except Exception as e:
        # Permission denied error vandha, idhu help pannum
        print(f"❌ Error exporting data to Excel (Check file lock/permissions): {e}")
        return False

# --- Wi-Fi Data Center Notification Logic (Mock) ---
def send_wifi_notification(hall_name, booking_date, attendees):
    """Placeholder: Wi-Fi Data Center-க்கு அறிவிப்பை அனுப்பும் செயல்பாடு."""
    print(f"--- Wi-Fi Data Center Notification ---")
    print(f"Hall: {hall_name}, Date: {booking_date}")
    print(f"**Action: Prepare network for {attendees} participants.**")
    print("-------------------------------------")
    return True

# --- Routes ---

# 1. Staff Login Page (Default Route)
@app.route('/')
def login_page():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# 2. Staff Login API
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
    conn.close()

    if user:
        session['username'] = user['username']
        return redirect(url_for('index'))
    else:
        return render_template('login.html', error="Invalid Credentials")

# 3. Main Booking Page (Login Required)
@app.route('/booking')
def index():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('main_booking.html', username=session.get('username'))

# 4. Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login_page'))

# 5. Fetch halls with availability for given date (API)
@app.route('/api/halls')
def get_halls():
    if 'username' not in session: return jsonify({"error": "Unauthorized"}), 401
    date = request.args.get('date')
    if not date: return jsonify([]), 200

    conn = get_db_connection()
    halls = conn.execute("SELECT * FROM halls").fetchall()
    booked = conn.execute("SELECT hall_id FROM bookings WHERE date = ?", (date,)).fetchall()
    booked_ids = {row['hall_id'] for row in booked}
    conn.close()

    hall_list = [
        {"id": h["id"], "name": h["name"], "capacity": h["capacity"], "available": h["id"] not in booked_ids}
        for h in halls
    ]
    return jsonify(hall_list)

# 6. Book a hall (API)
@app.route('/api/book', methods=['POST'])
def book_hall():
    if 'username' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    hall_id, date, attendees = data.get('hall_id'), data.get('date'), int(data.get('attendees'))
    staff_username = session.get('username')

    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Check existing booking
    cur.execute("SELECT * FROM bookings WHERE hall_id = ? AND date = ?", (hall_id, date))
    if cur.fetchone():
        conn.close()
        return jsonify({"error": "Hall already booked on this date"}), 400
    
    # 2. Check Capacity
    hall = conn.execute("SELECT name, capacity FROM halls WHERE id = ?", (hall_id,)).fetchone()
    if attendees > hall['capacity']:
        conn.close()
        return jsonify({"error": f"Attendees ({attendees}) exceed hall capacity ({hall['capacity']})"}), 400

    # 3. Insert Booking
    cur.execute("INSERT INTO bookings (staff_username, hall_id, date, attendees) VALUES (?, ?, ?, ?)",
                (staff_username, hall_id, date, attendees))
    conn.commit()
    conn.close()

    # 4. Export data to Excel and Send Wi-Fi Notification
    export_bookings_to_excel()
    send_wifi_notification(hall['name'], date, attendees)

    return jsonify({"message": f"Hall {hall['name']} booked successfully by {staff_username}. Data updated in {EXCEL_FILE}"})

# 7. View all bookings for dashboard (API)
@app.route('/api/bookings')
def get_bookings():
    conn = get_db_connection()
    # Pandas default JSON output: orient='records'
    df = pd.read_sql_query("""
        SELECT 
            b.id AS Booking_ID, 
            h.name AS Hall_Name, 
            b.date AS Booking_Date, 
            b.attendees AS Attendees_Count,
            b.staff_username AS Booked_By
        FROM bookings b
        JOIN halls h ON b.hall_id = h.id
        ORDER BY b.date DESC
    """, conn)
    conn.close()
    return df.to_json(orient='records')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')


if __name__ == '__main__':
    init_db()
    export_bookings_to_excel() 
    app.run(debug=True)