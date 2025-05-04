import sqlite3
import bcrypt
import uuid
from datetime import datetime, timedelta
from flask_login import UserMixin
import jwt
import os
import hashlib
from app.utils.database import get_db_connection, log_activity

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

def verify_password(password, hashed_password):
    """Verify password with bcrypt or fallback to SHA-256 if bcrypt fails"""
    try:
        # Try using bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (AttributeError, ImportError) as e:
        # Fallback to SHA-256 if bcrypt has compatibility issues
        print(f"Warning: Bcrypt error ({str(e)}), falling back to SHA-256")
        sha256 = hashlib.sha256()
        sha256.update(password.encode('utf-8'))
        return sha256.hexdigest() == hashed_password

class User(UserMixin):
    def __init__(self, id, email, name, role, contact=None, photo_path=None, 
                 is_active=True, created_at=None, password=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.contact = contact
        self.photo_path = photo_path
        self._is_active = is_active
        self.created_at = created_at
        self.password = password
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_active(self):
        """Return whether the user is active"""
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        """Set whether the user is active"""
        self._is_active = value
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    def is_voter(self):
        return self.role == 'VOTER'
    
    def is_candidate(self):
        return self.role == 'CANDIDATE'
    
    def get_reset_token(self, expires_in=3600):
        """Generate a reset token for password reset"""
        reset_token = str(uuid.uuid4())
        
        # Store token and expiry in database
        conn = get_db_connection()
        cursor = conn.cursor()
        expiry = datetime.now() + timedelta(seconds=expires_in)
        
        cursor.execute('''
        UPDATE users SET reset_token = ?, reset_token_expiry = ?
        WHERE id = ?
        ''', (reset_token, expiry, self.id))
        
        conn.commit()
        conn.close()
        
        return reset_token

def create_user(email, password, name, role, contact=None, photo_path=None):
    """Create a new user in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the password
    hashed_password = hash_password(password)
    
    cursor.execute('''
    INSERT INTO users (email, password, name, role, contact, photo_path)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (email, hashed_password, name, role, contact, photo_path))
    
    user_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    log_activity(user_id, 'USER_CREATE', f"New {role} account created")
    
    return user_id

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    conn.close()
    
    if user_data:
        return User(
            id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            role=user_data['role'],
            contact=user_data['contact'],
            photo_path=user_data['photo_path'],
            is_active=user_data['is_active'],
            created_at=user_data['created_at']
        )
    return None

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user_data = cursor.fetchone()
    
    conn.close()
    
    if user_data:
        return User(
            id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            role=user_data['role'],
            contact=user_data['contact'],
            photo_path=user_data['photo_path'],
            is_active=user_data['is_active'],
            created_at=user_data['created_at'],
            password=user_data['password']
        )
    return None

def authenticate_user(email, password):
    """Authenticate a user with email and password"""
    user = get_user_by_email(email)
    
    if user and user.is_active:
        # Check password
        if verify_password(password, user.password):
            log_activity(user.id, 'USER_LOGIN', f"{user.role} logged in")
            return user
    
    return None

def update_user(user_id, name=None, email=None, contact=None, photo_path=None):
    """Update user details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    if name:
        update_fields.append("name = ?")
        params.append(name)
    
    if email:
        update_fields.append("email = ?")
        params.append(email)
    
    if contact:
        update_fields.append("contact = ?")
        params.append(contact)
    
    if photo_path:
        update_fields.append("photo_path = ?")
        params.append(photo_path)
    
    if update_fields:
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        params.append(user_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        log_activity(user_id, 'USER_UPDATE', "User profile updated")
    
    conn.close()

def change_password(user_id, new_password):
    """Change user password"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the new password
    hashed_password = hash_password(new_password)
    
    cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
    conn.commit()
    conn.close()
    
    log_activity(user_id, 'PASSWORD_CHANGE', "Password changed")

def verify_reset_token(token):
    """Verify a password reset token"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM users 
    WHERE reset_token = ? AND reset_token_expiry > ?
    ''', (token, datetime.now()))
    
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return get_user_by_id(user_data['id'])
    
    return None

def get_all_users(role=None):
    """Get all users, optionally filtered by role"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if role:
        cursor.execute('SELECT * FROM users WHERE role = ?', (role,))
    else:
        cursor.execute('SELECT * FROM users')
    
    users_data = cursor.fetchall()
    conn.close()
    
    users = []
    for user_data in users_data:
        users.append(User(
            id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            role=user_data['role'],
            contact=user_data['contact'],
            photo_path=user_data['photo_path'],
            is_active=user_data['is_active'],
            created_at=user_data['created_at']
        ))
    
    return users 