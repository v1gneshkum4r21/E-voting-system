from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from functools import wraps

from app.models.election import (
    get_all_elections, get_election_by_id, is_voter_eligible,
    cast_vote, get_eligible_elections_for_voter, get_election_results
)
from app.models.candidate import get_candidates_by_election
from app.utils.database import get_db_connection

voter_bp = Blueprint('voter', __name__, url_prefix='/voter')

# Custom decorator to ensure user has VOTER role
def voter_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_voter():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@voter_bp.route('/dashboard')
@login_required
@voter_required
def dashboard():
    """Voter dashboard showing active, upcoming and past elections"""
    # Get active elections the voter is eligible for
    active_elections = get_eligible_elections_for_voter(current_user.id)
    
    # Get upcoming elections
    upcoming_elections = get_all_elections(status='upcoming')
    
    # Get user's voting history
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT e.title, e.start_time, e.end_time, c.id as candidate_id, u.name as candidate_name, v.vote_time, v.reference_id
    FROM votes v
    JOIN elections e ON v.election_id = e.id
    JOIN candidates c ON v.candidate_id = c.id
    JOIN users u ON c.user_id = u.id
    WHERE v.voter_id = ?
    ORDER BY v.vote_time DESC
    ''', (current_user.id,))
    
    voting_history = cursor.fetchall()
    
    # Get popular candidates
    cursor.execute('''
    SELECT c.id, c.election_id, u.name as candidate_name, c.ward_number as party,
           COUNT(v.id) as vote_count,
           e.title as election_title
    FROM candidates c
    JOIN users u ON c.user_id = u.id
    JOIN elections e ON c.election_id = e.id
    LEFT JOIN votes v ON c.id = v.candidate_id
    WHERE c.approval_status = 'approved'
      AND e.is_active = 1
      AND datetime('now') BETWEEN e.start_time AND e.end_time
    GROUP BY c.id
    ORDER BY vote_count DESC
    LIMIT 5
    ''')
    
    popular_candidates = cursor.fetchall()
    
    # Get party distribution
    cursor.execute('''
    SELECT c.ward_number as party, 
           COUNT(v.id) as vote_count,
           (SELECT COUNT(*) FROM votes WHERE election_id IN 
               (SELECT id FROM elections WHERE is_active = 1 AND datetime('now') BETWEEN start_time AND end_time)
           ) as total_votes
    FROM candidates c
    JOIN votes v ON c.id = v.candidate_id
    JOIN elections e ON c.election_id = e.id
    WHERE c.approval_status = 'approved'
      AND e.is_active = 1
      AND datetime('now') BETWEEN e.start_time AND e.end_time
      AND c.ward_number IS NOT NULL
    GROUP BY c.ward_number
    ORDER BY vote_count DESC
    ''')
    
    party_data = []
    party_rows = cursor.fetchall()
    
    for row in party_rows:
        if row['total_votes'] > 0:
            percentage = round((row['vote_count'] / row['total_votes']) * 100, 1)
        else:
            percentage = 0
            
        party_data.append({
            'name': row['party'] or 'Independent',
            'votes': row['vote_count'],
            'percentage': percentage
        })
    
    conn.close()
    
    return render_template(
        'voter/dashboard.html',
        active_elections=active_elections,
        upcoming_elections=upcoming_elections,
        voting_history=voting_history,
        popular_candidates=popular_candidates,
        party_data=party_data
    )

@voter_bp.route('/elections')
@login_required
@voter_required
def elections():
    """List all active elections the voter is eligible for"""
    eligible_elections = get_eligible_elections_for_voter(current_user.id)
    return render_template('voter/elections.html', elections=eligible_elections)

@voter_bp.route('/election/<int:election_id>')
@login_required
@voter_required
def view_election(election_id):
    """View election details and ballot"""
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('voter.elections'))
    
    # Check if voter is eligible to vote in this election
    is_eligible = is_voter_eligible(current_user.id, election_id)
    
    # Check if election is active
    is_active = election.is_ongoing()
    
    # Get candidates for this election
    candidates = get_candidates_by_election(election_id, status='approved')
    
    # Get results if election is completed
    results = None
    if election.get_status() == 'completed':
        results = get_election_results(election_id)
    
    return render_template(
        'voter/view_election.html',
        election=election,
        candidates=candidates,
        is_eligible=is_eligible,
        is_active=is_active,
        results=results
    )

@voter_bp.route('/vote/<int:election_id>', methods=['POST'])
@login_required
@voter_required
def vote(election_id):
    """Process a vote"""
    candidate_id = request.form.get('candidate_id')
    
    if not candidate_id:
        flash('Please select a candidate.', 'danger')
        return redirect(url_for('voter.view_election', election_id=election_id))
    
    election = get_election_by_id(election_id)
    
    if not election:
        flash('Election not found.', 'danger')
        return redirect(url_for('voter.elections'))
    
    # Check if election is active
    if not election.is_ongoing():
        flash('This election is not currently active.', 'danger')
        return redirect(url_for('voter.view_election', election_id=election_id))
    
    # Check if voter is eligible
    if not is_voter_eligible(current_user.id, election_id):
        flash('You are not eligible to vote in this election or have already voted.', 'danger')
        return redirect(url_for('voter.view_election', election_id=election_id))
    
    # Cast the vote
    reference_id = cast_vote(current_user.id, election_id, candidate_id)
    
    if reference_id:
        flash(f'Your vote has been recorded. Reference ID: {reference_id}', 'success')
        return render_template('voter/vote_confirmation.html', 
                              election=election, 
                              reference_id=reference_id)
    else:
        flash('There was an error processing your vote. Please try again.', 'danger')
        return redirect(url_for('voter.view_election', election_id=election_id))

@voter_bp.route('/history')
@login_required
@voter_required
def voting_history():
    """View voter's voting history"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT e.title, e.start_time, e.end_time, c.id as candidate_id, u.name as candidate_name, v.vote_time, v.reference_id
    FROM votes v
    JOIN elections e ON v.election_id = e.id
    JOIN candidates c ON v.candidate_id = c.id
    JOIN users u ON c.user_id = u.id
    WHERE v.voter_id = ?
    ORDER BY v.vote_time DESC
    ''', (current_user.id,))
    
    history = cursor.fetchall()
    
    conn.close()
    
    return render_template('voter/voting_history.html', history=history)

@voter_bp.route('/election/<int:election_id>/live-results')
@login_required
@voter_required
def live_election_results(election_id):
    """Get live election results in JSON format for AJAX polling"""
    election = get_election_by_id(election_id)
    
    if not election:
        return jsonify({'error': 'Election not found'}), 404
    
    # Only provide results for completed elections
    if election.get_status() != 'completed':
        return jsonify({'error': 'Results not available until election is completed'}), 403
    
    results = get_election_results(election_id)
    
    if not results:
        return jsonify({'error': 'No results available'}), 404
    
    return jsonify(results) 