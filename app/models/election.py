import sqlite3
from datetime import datetime
import uuid
import random
import string
from app.utils.database import get_db_connection, log_activity

class Election:
    def __init__(self, id, title, description, start_time, end_time, 
                 is_active=True, created_by=None, created_at=None):
        self.id = id
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.is_active = is_active
        self.created_by = created_by
        self.created_at = created_at
    
    def get_status(self):
        """Get the current status of the election"""
        now = datetime.now()
        
        if not self.is_active:
            return "inactive"
        elif now < self.start_time:
            return "upcoming"
        elif now >= self.start_time and now <= self.end_time:
            return "active"
        else:
            return "completed"
    
    def is_ongoing(self):
        """Check if the election is currently ongoing"""
        now = datetime.now()
        return self.is_active and now >= self.start_time and now <= self.end_time

def create_election(title, description, start_time, end_time, created_by):
    """Create a new election"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO elections (title, description, start_time, end_time, created_by)
    VALUES (?, ?, ?, ?, ?)
    ''', (title, description, start_time, end_time, created_by))
    
    election_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    log_activity(created_by, 'ELECTION_CREATE', f"Created election: {title}")
    
    return election_id

def get_election_by_id(election_id):
    """Get election by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM elections WHERE id = ?', (election_id,))
    election_data = cursor.fetchone()
    
    conn.close()
    
    if election_data:
        return Election(
            id=election_data['id'],
            title=election_data['title'],
            description=election_data['description'],
            start_time=datetime.fromisoformat(election_data['start_time']),
            end_time=datetime.fromisoformat(election_data['end_time']),
            is_active=election_data['is_active'],
            created_by=election_data['created_by'],
            created_at=election_data['created_at']
        )
    return None

def update_election(election_id, title=None, description=None, start_time=None, end_time=None, is_active=None):
    """Update election details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    if title:
        update_fields.append("title = ?")
        params.append(title)
    
    if description:
        update_fields.append("description = ?")
        params.append(description)
    
    if start_time:
        update_fields.append("start_time = ?")
        params.append(start_time)
    
    if end_time:
        update_fields.append("end_time = ?")
        params.append(end_time)
    
    if is_active is not None:
        update_fields.append("is_active = ?")
        params.append(is_active)
    
    if update_fields:
        query = f"UPDATE elections SET {', '.join(update_fields)} WHERE id = ?"
        params.append(election_id)
        
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def delete_election(election_id):
    """Delete an election"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the election has votes
    cursor.execute('SELECT COUNT(*) FROM votes WHERE election_id = ?', (election_id,))
    vote_count = cursor.fetchone()[0]
    
    if vote_count > 0:
        # Don't delete, just mark as inactive
        cursor.execute('UPDATE elections SET is_active = 0 WHERE id = ?', (election_id,))
        conn.commit()
        conn.close()
        return False
    
    # Delete associated candidates
    cursor.execute('DELETE FROM candidates WHERE election_id = ?', (election_id,))
    
    # Delete eligible voters
    cursor.execute('DELETE FROM eligible_voters WHERE election_id = ?', (election_id,))
    
    # Delete the election
    cursor.execute('DELETE FROM elections WHERE id = ?', (election_id,))
    
    conn.commit()
    conn.close()
    return True

def get_all_elections(status=None):
    """Get all elections, optionally filtered by status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM elections')
    elections_data = cursor.fetchall()
    conn.close()
    
    elections = []
    now = datetime.now()
    
    for election_data in elections_data:
        election = Election(
            id=election_data['id'],
            title=election_data['title'],
            description=election_data['description'],
            start_time=datetime.fromisoformat(election_data['start_time']),
            end_time=datetime.fromisoformat(election_data['end_time']),
            is_active=election_data['is_active'],
            created_by=election_data['created_by'],
            created_at=election_data['created_at']
        )
        
        # Filter by status if specified
        if status:
            if status == 'active' and election.get_status() == 'active':
                elections.append(election)
            elif status == 'upcoming' and election.get_status() == 'upcoming':
                elections.append(election)
            elif status == 'completed' and election.get_status() == 'completed':
                elections.append(election)
            elif status == 'inactive' and not election.is_active:
                elections.append(election)
        else:
            elections.append(election)
    
    return elections

def assign_voters_to_election(election_id, voter_ids):
    """Assign multiple voters to an election"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for voter_id in voter_ids:
        cursor.execute('''
        INSERT INTO eligible_voters (election_id, voter_id)
        VALUES (?, ?)
        ''', (election_id, voter_id))
    
    conn.commit()
    conn.close()

def is_voter_eligible(voter_id, election_id):
    """Check if a voter is eligible to vote in an election"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT COUNT(*) FROM eligible_voters 
    WHERE voter_id = ? AND election_id = ?
    ''', (voter_id, election_id))
    
    count = cursor.fetchone()[0]
    
    # Also check if they've already voted
    cursor.execute('''
    SELECT COUNT(*) FROM votes 
    WHERE voter_id = ? AND election_id = ?
    ''', (voter_id, election_id))
    
    has_voted = cursor.fetchone()[0] > 0
    
    conn.close()
    
    # Voter is eligible if they're in the eligible_voters table and haven't voted yet
    return count > 0 and not has_voted

def cast_vote(voter_id, election_id, candidate_id):
    """Cast a vote in an election"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if voter is eligible
    if not is_voter_eligible(voter_id, election_id):
        conn.close()
        return None
    
    # Generate a unique reference ID
    reference_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    try:
        cursor.execute('''
        INSERT INTO votes (voter_id, election_id, candidate_id, reference_id)
        VALUES (?, ?, ?, ?)
        ''', (voter_id, election_id, candidate_id, reference_id))
        
        conn.commit()
        log_activity(voter_id, 'VOTE_CAST', f"Vote cast in election ID: {election_id}")
        
        conn.close()
        return reference_id
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return None

def get_election_results(election_id):
    """Get the results of an election"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get election details
    cursor.execute('SELECT * FROM elections WHERE id = ?', (election_id,))
    election_data = cursor.fetchone()
    
    if not election_data:
        conn.close()
        return None
    
    # Count total eligible voters
    cursor.execute('''
        SELECT COUNT(*) FROM eligible_voters
        WHERE election_id = ?
    ''', (election_id,))
    total_eligible = cursor.fetchone()[0]
    
    # Get all votes for this election
    cursor.execute('''
        SELECT c.id, c.user_id, u.name, 
               COUNT(v.id) as vote_count
        FROM candidates c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN votes v ON c.id = v.candidate_id
        WHERE c.election_id = ? AND c.approval_status = 'approved'
        GROUP BY c.id
        ORDER BY vote_count DESC
    ''', (election_id,))
    
    candidates_votes = cursor.fetchall()
    
    # Count total votes
    cursor.execute('SELECT COUNT(*) FROM votes WHERE election_id = ?', (election_id,))
    total_votes = cursor.fetchone()[0]
    
    # Calculate voter turnout
    turnout_percentage = 0
    if total_eligible > 0:
        turnout_percentage = round((total_votes / total_eligible) * 100, 2)
    
    # Calculate percentage for each candidate
    candidates = []
    for candidate in candidates_votes:
        percentage = 0
        if total_votes > 0:
            percentage = round((candidate['vote_count'] / total_votes) * 100, 2)
        
        # Get candidate details
        cursor.execute('''
            SELECT manifesto, ward_number, logo_path
            FROM candidates
            WHERE id = ?
        ''', (candidate['id'],))
        candidate_details = cursor.fetchone()
        
        candidates.append({
            'candidate_id': candidate['id'],
            'candidate_name': candidate['name'],
            'votes': candidate['vote_count'],
            'percentage': percentage,
            'manifesto': candidate_details['manifesto'] if candidate_details else '',
            'ward_number': candidate_details['ward_number'] if candidate_details else '',
            'logo_path': candidate_details['logo_path'] if candidate_details else None
        })
    
    conn.close()
    
    # Sort candidates by vote count (descending)
    candidates.sort(key=lambda x: x['votes'], reverse=True)
    
    # Determine winner
    winner = None
    if candidates and total_votes > 0:
        winner = candidates[0]
    
    return {
        'election_id': election_id,
        'election_title': election_data['title'],
        'total_votes': total_votes,
        'total_eligible': total_eligible,
        'turnout_percentage': turnout_percentage,
        'candidates': candidates,
        'winner': winner
    }

def get_eligible_elections_for_voter(voter_id):
    """Get elections that a voter is eligible to vote in"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT e.* FROM elections e
    JOIN eligible_voters ev ON e.id = ev.election_id
    LEFT JOIN votes v ON e.id = v.election_id AND v.voter_id = ?
    WHERE ev.voter_id = ? AND e.is_active = 1 AND v.id IS NULL
    ''', (voter_id, voter_id))
    
    elections_data = cursor.fetchall()
    conn.close()
    
    elections = []
    now = datetime.now()
    
    for election_data in elections_data:
        election = Election(
            id=election_data['id'],
            title=election_data['title'],
            description=election_data['description'],
            start_time=datetime.fromisoformat(election_data['start_time']),
            end_time=datetime.fromisoformat(election_data['end_time']),
            is_active=election_data['is_active'],
            created_by=election_data['created_by'],
            created_at=election_data['created_at']
        )
        
        # Only include active or upcoming elections
        if election.get_status() in ['active', 'upcoming']:
            elections.append(election)
    
    return elections 