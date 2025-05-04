from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, Response, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import csv
import io

from app.models.election import (
    get_all_elections, get_election_by_id, create_election,
    update_election, delete_election, get_election_results,
    assign_voters_to_election
)
from app.models.user import get_all_users
from app.models.candidate import (
    get_candidates_by_election, get_pending_candidates,
    update_approval_status
)
from app.utils.database import get_db_connection, log_activity

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Custom decorator to ensure user has ADMIN role
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system overview"""
    # Get counts for overview
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "VOTER"')
    voter_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "CANDIDATE"')
    candidate_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM elections')
    election_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM elections WHERE is_active = 1')
    active_election_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM votes')
    vote_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM candidates WHERE approval_status = "pending"')
    pending_approval_count = cursor.fetchone()[0]
    
    # Get active elections with vote counts
    cursor.execute('''
    SELECT e.*, 
           (SELECT COUNT(*) FROM votes WHERE election_id = e.id) as vote_count
    FROM elections e
    WHERE e.is_active = 1 
      AND datetime('now') BETWEEN e.start_time AND e.end_time
    ORDER BY e.end_time ASC
    ''')
    active_elections = cursor.fetchall()
    
    # Get recent activity logs
    cursor.execute('''
    SELECT al.*, u.name, u.email 
    FROM activity_logs al
    LEFT JOIN users u ON al.user_id = u.id
    ORDER BY al.timestamp DESC LIMIT 10
    ''')
    recent_activity = cursor.fetchall()
    
    conn.close()
    
    return render_template(
        'admin/dashboard.html',
        voter_count=voter_count,
        candidate_count=candidate_count,
        election_count=election_count,
        active_election_count=active_election_count,
        vote_count=vote_count,
        pending_approval_count=pending_approval_count,
        active_elections=active_elections,
        recent_activity=recent_activity
    )

@admin_bp.route('/elections')
@login_required
@admin_required
def elections():
    """List all elections"""
    all_elections = get_all_elections()
    return render_template('admin/elections.html', elections=all_elections)

@admin_bp.route('/election/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_election_route():
    """Create a new election"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        # Basic validation
        if not all([title, start_time, end_time]):
            flash('All required fields must be filled.', 'danger')
            return render_template('admin/create_election.html')
        
        try:
            start_time = datetime.fromisoformat(start_time.replace('T', ' '))
            end_time = datetime.fromisoformat(end_time.replace('T', ' '))
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('admin/create_election.html')
        
        if start_time >= end_time:
            flash('End time must be after start time.', 'danger')
            return render_template('admin/create_election.html')
        
        election_id = create_election(title, description, start_time, end_time, current_user.id)
        
        if election_id:
            flash('Election created successfully!', 'success')
            return redirect(url_for('admin.elections'))
        else:
            flash('Failed to create election.', 'danger')
    
    return render_template('admin/create_election.html')

@admin_bp.route('/election/<int:election_id>')
@login_required
@admin_required
def view_election(election_id):
    """View election details"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('admin.elections'))
    
    # Get candidates for this election
    candidates = get_candidates_by_election(election_id)
    
    # Get election results if it's completed
    results = None
    if election.get_status() == 'completed':
        results = get_election_results(election_id)
    
    return render_template(
        'admin/view_election.html',
        election=election,
        candidates=candidates,
        results=results
    )

@admin_bp.route('/election/<int:election_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_election(election_id):
    """Edit an election"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('admin.elections'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        is_active = 'is_active' in request.form
        
        # Basic validation
        if not all([title, start_time, end_time]):
            flash('All required fields must be filled.', 'danger')
            return render_template('admin/edit_election.html', election=election)
        
        try:
            start_time = datetime.fromisoformat(start_time.replace('T', ' '))
            end_time = datetime.fromisoformat(end_time.replace('T', ' '))
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('admin/edit_election.html', election=election)
        
        if start_time >= end_time:
            flash('End time must be after start time.', 'danger')
            return render_template('admin/edit_election.html', election=election)
        
        update_election(election_id, title, description, start_time, end_time, is_active)
        
        flash('Election updated successfully!', 'success')
        return redirect(url_for('admin.view_election', election_id=election_id))
    
    return render_template('admin/edit_election.html', election=election)

@admin_bp.route('/election/<int:election_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_election_route(election_id):
    """Delete an election"""
    result = delete_election(election_id)
    
    if result:
        flash('Election deleted successfully!', 'success')
    else:
        flash('Election has votes and cannot be deleted. It has been marked as inactive.', 'warning')
    
    return redirect(url_for('admin.elections'))

@admin_bp.route('/election/<int:election_id>/assign-voters', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_voters(election_id):
    """Assign voters to an election"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('admin.elections'))
    
    # Get all voters
    voters = get_all_users(role='VOTER')
    
    if request.method == 'POST':
        voter_ids = request.form.getlist('voter_ids')
        
        if not voter_ids:
            flash('No voters selected.', 'danger')
            return render_template('admin/assign_voters.html', election=election, voters=voters)
        
        # Convert to integers
        voter_ids = [int(vid) for vid in voter_ids]
        
        assign_voters_to_election(election_id, voter_ids)
        
        flash(f'Successfully assigned {len(voter_ids)} voters to the election.', 'success')
        return redirect(url_for('admin.view_election', election_id=election_id))
    
    return render_template('admin/assign_voters.html', election=election, voters=voters)

@admin_bp.route('/candidates/pending')
@login_required
@admin_required
def pending_candidates():
    """List candidates pending approval"""
    candidates = get_pending_candidates()
    return render_template('admin/pending_candidates.html', candidates=candidates)

@admin_bp.route('/candidate/<int:candidate_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_candidate(candidate_id):
    """Approve a candidate"""
    update_approval_status(candidate_id, 'approved', current_user.id)
    flash('Candidate approved successfully!', 'success')
    return redirect(url_for('admin.pending_candidates'))

@admin_bp.route('/candidate/<int:candidate_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_candidate(candidate_id):
    """Reject a candidate"""
    update_approval_status(candidate_id, 'rejected', current_user.id)
    flash('Candidate rejected.', 'success')
    return redirect(url_for('admin.pending_candidates'))

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    all_users = get_all_users()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """View system logs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT al.*, u.name, u.email 
    FROM activity_logs al
    LEFT JOIN users u ON al.user_id = u.id
    ORDER BY al.timestamp DESC LIMIT 100
    ''')
    
    logs = cursor.fetchall()
    conn.close()
    
    return render_template('admin/logs.html', logs=logs)

@admin_bp.route('/election/<int:election_id>/export-results')
@login_required
@admin_required
def export_election_results(election_id):
    """Export election results as CSV"""
    from app.models.election import get_election_by_id, get_election_results
    
    election = get_election_by_id(election_id)
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('admin.elections'))
    
    # Get election results
    results = get_election_results(election_id)
    
    if not results:
        flash('No results available for this election.', 'warning')
        return redirect(url_for('admin.view_election', election_id=election_id))
    
    # Create CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Election', election.title])
    writer.writerow(['Start Date', election.start_time])
    writer.writerow(['End Date', election.end_time])
    writer.writerow(['Total Votes', results['total_votes']])
    writer.writerow([])  # Empty row as separator
    writer.writerow(['Candidate', 'Votes', 'Percentage'])
    
    # Write candidate results
    for candidate in sorted(results['candidates'], key=lambda x: x['votes'], reverse=True):
        writer.writerow([
            candidate['candidate_name'],
            candidate['votes'],
            f"{candidate['percentage']}%"
        ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"election_results_{election_id}_{timestamp}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@admin_bp.route('/election/<int:election_id>/live-results')
@login_required
@admin_required
def live_election_results(election_id):
    """Get live election results in JSON format for AJAX polling"""
    election = get_election_by_id(election_id)
    
    if not election:
        return jsonify({'error': 'Election not found'}), 404
    
    results = get_election_results(election_id)
    
    if not results:
        return jsonify({'error': 'No results available'}), 404
    
    return jsonify(results) 