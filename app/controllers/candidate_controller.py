from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid

from app.models.candidate import (
    create_candidate, get_candidate_by_user_election,
    update_candidate, get_user_elections_as_candidate
)
from app.models.election import get_all_elections, get_election_by_id
from app.utils.database import log_activity

candidate_bp = Blueprint('candidate', __name__, url_prefix='/candidate')

# Custom decorator to ensure user has CANDIDATE role
def candidate_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_candidate():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@candidate_bp.route('/dashboard')
@login_required
@candidate_required
def dashboard():
    """Candidate dashboard showing elections they're participating in"""
    # Get elections the candidate is participating in
    candidate_elections = get_user_elections_as_candidate(current_user.id)
    
    # Get active elections they could register for
    active_elections = get_all_elections(status='active')
    upcoming_elections = get_all_elections(status='upcoming')
    
    # Filter out elections they're already registered for
    registered_election_ids = [e.id for e in candidate_elections]
    available_elections = [e for e in active_elections + upcoming_elections 
                          if e.id not in registered_election_ids]
    
    return render_template(
        'candidate/dashboard.html',
        candidate_elections=candidate_elections,
        available_elections=available_elections
    )

@candidate_bp.route('/register/<int:election_id>', methods=['GET', 'POST'])
@login_required
@candidate_required
def register(election_id):
    """Register as a candidate for an election"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('candidate.dashboard'))
    
    # Check if election is active or upcoming
    if election.get_status() not in ['active', 'upcoming']:
        flash('Registration is only available for active or upcoming elections.', 'danger')
        return redirect(url_for('candidate.dashboard'))
    
    # Check if already registered
    existing_registration = get_candidate_by_user_election(current_user.id, election_id)
    if existing_registration:
        flash('You are already registered as a candidate for this election.', 'warning')
        return redirect(url_for('candidate.dashboard'))
    
    if request.method == 'POST':
        manifesto = request.form.get('manifesto')
        ward_number = request.form.get('ward_number')
        
        # Handle logo upload if present
        logo_path = None
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{logo.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                # Store only the relative path for database and template rendering
                logo_path = f"uploads/{filename}"
                # Save to the full path
                logo.save(upload_path)
        
        # Create candidate registration
        candidate_id = create_candidate(
            current_user.id, election_id, manifesto, ward_number, logo_path
        )
        
        if candidate_id:
            flash('Your candidacy has been submitted for approval.', 'success')
            return redirect(url_for('candidate.dashboard'))
        else:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('candidate/register.html', election=election)

@candidate_bp.route('/edit/<int:election_id>', methods=['GET', 'POST'])
@login_required
@candidate_required
def edit_candidacy(election_id):
    """Edit candidate details for an election"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('candidate.dashboard'))
    
    # Get candidate registration
    candidate = get_candidate_by_user_election(current_user.id, election_id)
    
    if not candidate:
        flash('You are not registered as a candidate for this election.', 'danger')
        return redirect(url_for('candidate.dashboard'))
    
    # Only allow editing if not approved yet
    if candidate.approval_status == 'approved':
        flash('You cannot edit your candidacy after it has been approved.', 'warning')
        return redirect(url_for('candidate.dashboard'))
    
    if request.method == 'POST':
        manifesto = request.form.get('manifesto')
        ward_number = request.form.get('ward_number')
        
        # Handle logo upload if present
        logo_path = None
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{logo.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                # Store only the relative path for database and template rendering
                logo_path = f"uploads/{filename}"
                # Save to the full path
                logo.save(upload_path)
        
        # Update candidate details
        update_candidate(candidate.id, manifesto, ward_number, logo_path)
        
        flash('Your candidacy details have been updated.', 'success')
        return redirect(url_for('candidate.dashboard'))
    
    return render_template('candidate/edit.html', election=election, candidate=candidate)

@candidate_bp.route('/view/<int:election_id>')
@login_required
@candidate_required
def view_candidacy(election_id):
    """View candidate details for an election"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('candidate.dashboard'))
    
    # Get candidate registration
    candidate = get_candidate_by_user_election(current_user.id, election_id)
    
    if not candidate:
        flash('You are not registered as a candidate for this election.', 'danger')
        return redirect(url_for('candidate.dashboard'))
    
    return render_template('candidate/view.html', election=election, candidate=candidate) 