from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

from app.models.election import get_all_elections, get_election_results
from app.utils.database import get_db_connection

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    """Home page"""
    # Get active elections
    active_elections = get_all_elections(status='active')
    
    # Get completed elections
    completed_elections = get_all_elections(status='completed')
    
    # Get results for completed elections
    completed_election_results = {}
    for election in completed_elections:
        completed_election_results[election.id] = get_election_results(election.id)
    
    # Get trending candidates
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT c.id, c.election_id, u.name as candidate_name, c.ward_number as party,
           COUNT(v.id) as vote_count,
           e.title as election_title,
           (CASE
                WHEN COUNT(v.id) > 10 THEN 'Leading'
                WHEN COUNT(v.id) > 5 THEN 'Popular'
                ELSE 'Rising'
            END) as status
    FROM candidates c
    JOIN users u ON c.user_id = u.id
    JOIN elections e ON c.election_id = e.id
    LEFT JOIN votes v ON c.id = v.candidate_id
    WHERE c.approval_status = 'approved'
      AND e.is_active = 1
    GROUP BY c.id
    ORDER BY vote_count DESC
    LIMIT 6
    ''')
    
    trending_candidates = cursor.fetchall()
    conn.close()
    
    return render_template(
        'index.html',
        active_elections=active_elections,
        trending_candidates=trending_candidates,
        completed_elections=completed_elections,
        completed_election_results=completed_election_results
    ) 