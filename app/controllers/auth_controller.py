from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timedelta
import secrets

from app.models.user import (
    get_user_by_email, authenticate_user, create_user, 
    get_user_by_id, change_password, verify_reset_token
)
from app.utils.database import log_activity

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = authenticate_user(email, password)
        
        if user:
            login_user(user)
            flash('Login successful!', 'success')
            
            # Redirect based on role
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_voter():
                return redirect(url_for('voter.dashboard'))
            elif user.is_candidate():
                return redirect(url_for('candidate.dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'VOTER')  # Default role is VOTER
        contact = request.form.get('contact', '')
        
        # Basic validation
        if not all([name, email, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        
        # Check if email already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            flash('Email already in use. Please use a different email or login.', 'danger')
            return render_template('auth/register.html')
        
        # Handle photo upload if present
        photo_path = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{photo.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                # Store only the relative path for database and template rendering
                photo_path = f"uploads/{filename}"
                # Save to the full path
                photo.save(upload_path)
        
        # Create user
        user_id = create_user(email, password, name, role, contact, photo_path)
        
        if user_id:
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'USER_LOGOUT', f"{current_user.role} logged out")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        user = get_user_by_email(email)
        if user:
            # Generate reset token
            reset_token = user.get_reset_token()
            
            # In a real-world application, send the reset token via email
            # For this demo, we'll just show it in the flash message
            reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
            flash(f'Password reset link: {reset_url}', 'info')
            
            # Log the action
            log_activity(user.id, 'PASSWORD_RESET_REQUEST', "Password reset requested")
            
            flash('If the email exists, a password reset link has been sent.', 'info')
            return redirect(url_for('auth.login'))
        
        flash('If the email exists, a password reset link has been sent.', 'info')
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired token. Please try again.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('Password fields cannot be empty.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Update password
        change_password(user.id, password)
        
        flash('Your password has been updated. You can now login with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        
        # Handle photo upload if present
        photo_path = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{photo.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                # Store only the relative path for database and template rendering
                photo_path = f"uploads/{filename}"
                # Save to the full path
                photo.save(upload_path)
        
        # Update user
        from app.models.user import update_user
        update_user(current_user.id, name, None, contact, photo_path)
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html') 