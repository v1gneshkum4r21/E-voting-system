import sqlite3
import os
import bcrypt
from datetime import datetime
import hashlib

# Database path
db_path = os.path.join('database', 'evoting.db')

def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash password with bcrypt or fallback to SHA-256 if bcrypt fails"""
    try:
        # Try using bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except (AttributeError, ImportError) as e:
        # Fallback to SHA-256 if bcrypt has compatibility issues
        print(f"Warning: Bcrypt error ({str(e)}), falling back to SHA-256")
        sha256 = hashlib.sha256()
        sha256.update(password.encode('utf-8'))
        return sha256.hexdigest()

def init_db():
    """Initialize the database with required tables"""
    # Make sure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        contact TEXT,
        photo_path TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reset_token TEXT,
        reset_token_expiry TIMESTAMP
    )
    ''')
    
    # Create Elections table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS elections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )
    ''')
    
    # Create Candidates table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        election_id INTEGER NOT NULL,
        manifesto TEXT,
        ward_number TEXT,
        approval_status TEXT DEFAULT 'pending',
        logo_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (election_id) REFERENCES elections (id)
    )
    ''')
    
    # Create Votes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id INTEGER NOT NULL,
        election_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reference_id TEXT UNIQUE NOT NULL,
        FOREIGN KEY (voter_id) REFERENCES users (id),
        FOREIGN KEY (election_id) REFERENCES elections (id),
        FOREIGN KEY (candidate_id) REFERENCES candidates (id)
    )
    ''')
    
    # Create EligibleVoters table for group-based voting eligibility
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS eligible_voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        election_id INTEGER NOT NULL,
        voter_id INTEGER NOT NULL,
        FOREIGN KEY (election_id) REFERENCES elections (id),
        FOREIGN KEY (voter_id) REFERENCES users (id)
    )
    ''')
    
    # Create ActivityLogs table for auditing
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create admin user if not exists
    cursor.execute("SELECT * FROM users WHERE email = 'admin@evoting.com'")
    if not cursor.fetchone():
        # Hash password for admin
        hashed_password = hash_password('admin123')
        
        cursor.execute('''
        INSERT INTO users (email, password, name, role, is_active)
        VALUES (?, ?, ?, ?, ?)
        ''', ('admin@evoting.com', hashed_password, 'System Admin', 'ADMIN', 1))
    
    # Create default voter if not exists
    cursor.execute("SELECT * FROM users WHERE email = 'voter@evoting.com'")
    if not cursor.fetchone():
        hashed_password = hash_password('voter123')
        
        cursor.execute('''
        INSERT INTO users (email, password, name, role, is_active)
        VALUES (?, ?, ?, ?, ?)
        ''', ('voter@evoting.com', hashed_password, 'Default Voter', 'VOTER', 1))
    
    # Create default candidate if not exists
    cursor.execute("SELECT * FROM users WHERE email = 'candidate@evoting.com'")
    if not cursor.fetchone():
        hashed_password = hash_password('candidate123')
        
        cursor.execute('''
        INSERT INTO users (email, password, name, role, is_active)
        VALUES (?, ?, ?, ?, ?)
        ''', ('candidate@evoting.com', hashed_password, 'Default Candidate', 'CANDIDATE', 1))
    
    conn.commit()
    conn.close()

def log_activity(user_id, action, details=None, ip_address=None):
    """Log user activity for auditing purposes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO activity_logs (user_id, action, details, ip_address)
    VALUES (?, ?, ?, ?)
    ''', (user_id, action, details, ip_address))
    
    conn.commit()
    conn.close() 