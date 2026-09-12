import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'sectoriq.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        event_type TEXT NOT NULL,
        impact_level TEXT NOT NULL,
        latitude REAL,
        longitude REAL
    );
    CREATE TABLE IF NOT EXISTS hospitality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        location TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        bookings INTEGER NOT NULL,
        occupancy REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS retail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        location TEXT NOT NULL,
        product TEXT NOT NULL,
        sales REAL NOT NULL,
        inventory INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS financial_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        location TEXT NOT NULL,
        transaction_count INTEGER NOT NULL,
        transaction_value REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS entertainment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        venue TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        attendance INTEGER NOT NULL,
        ticket_sales REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sector TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL
    );
    ''')

    if conn.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0:
        events = [
            ('Diwali Festival','2026-10-20','Festival','High',28.6139,77.2090),
            ('Coldplay Concert','2026-11-15','Concert','High',28.5494,77.2501),
            ('India vs NZ Match','2026-11-02','Sports','Medium',28.6258,77.2167),
            ('New Year Celebrations','2026-12-31','Celebration','Medium',28.5244,77.1855),
        ]
        conn.executemany('INSERT INTO events(name,date,event_type,impact_level,latitude,longitude) VALUES (?,?,?,?,?,?)', events)

    if conn.execute('SELECT COUNT(*) FROM locations').fetchone()[0] == 0:
        locations = [
            ('Grand Delhi Hotel','Hotels',28.6139,77.2090),
            ('City Retail Hub','Retail',28.6280,77.2195),
            ('Central Bank','Financial',28.6328,77.2197),
            ('Arena Entertainment','Entertainment',28.5494,77.2501),
            ('Diwali Festival','Events',28.6130,77.2300),
            ('Lajpat Market','Retail',28.5677,77.2433),
            ('South Delhi Hotel','Hotels',28.5680,77.2140),
        ]
        conn.executemany('INSERT INTO locations(name,sector,latitude,longitude) VALUES (?,?,?,?)', locations)

    # Seed a small historical dataset for the forecasting layer.
    if conn.execute('SELECT COUNT(*) FROM hospitality').fetchone()[0] == 0:
        for i in range(30):
            date = f'2026-08-{i+1:02d}'
            occ = 62 + (i % 9) * 2
            conn.execute('INSERT INTO hospitality(date,location,capacity,bookings,occupancy) VALUES (?,?,?,?,?)',
                         (date,'New Delhi',100,round(occ),occ))
            conn.execute('INSERT INTO retail(date,location,product,sales,inventory) VALUES (?,?,?,?,?)',
                         (date,'New Delhi','Festival Essentials',1000+i*18,600-max(0,i*5)))
            conn.execute('INSERT INTO financial_transactions(date,location,transaction_count,transaction_value) VALUES (?,?,?,?)',
                         (date,'New Delhi',420+i*8,85000+i*1500))
            conn.execute('INSERT INTO entertainment(date,venue,capacity,attendance,ticket_sales) VALUES (?,?,?,?,?)',
                         (date,'New Delhi Arena',500,280+i*4,56000+i*900))

    conn.commit()
    conn.close()
