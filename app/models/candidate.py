import sqlite3
from datetime import datetime
from app.utils.database import get_db_connection, log_activity
from app.models.user import get_user_by_id

class Candidate:
    def __init__(self, id, user_id, election_id, manifesto=None, ward_number=None, 
                 approval_status='pending', logo_path=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.election_id = election_id
        self.manifesto = manifesto
        self.ward_number = ward_number
        self.approval_status = approval_status
        self.logo_path = logo_path
        self.created_at = created_at
        self._user = None
    
    @property
    def user(self):
        """Get the user associated with this candidate"""
        if self._user is None:
            self._user = get_user_by_id(self.user_id)
        return self._user
    
    @property
    def name(self):
        """Get the candidate's name from the user"""
        return self.user.name if self.user else "Unknown"

def create_candidate(user_id, election_id, manifesto=None, ward_number=None, logo_path=None):
    """Create a new candidate entry"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO candidates (user_id, election_id, manifesto, ward_number, logo_path)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, election_id, manifesto, ward_number, logo_path))
    
    candidate_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    log_activity(user_id, 'CANDIDATE_REGISTER', f"Registered as candidate for election ID: {election_id}")
    
    return candidate_id

def get_candidate_by_id(candidate_id):
    """Get candidate by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate_data = cursor.fetchone()
    
    conn.close()
    
    if candidate_data:
        return Candidate(
            id=candidate_data['id'],
            user_id=candidate_data['user_id'],
            election_id=candidate_data['election_id'],
            manifesto=candidate_data['manifesto'],
            ward_number=candidate_data['ward_number'],
            approval_status=candidate_data['approval_status'],
            logo_path=candidate_data['logo_path'],
            created_at=candidate_data['created_at']
        )
    return None

def get_candidate_by_user_election(user_id, election_id):
    """Get candidate by user ID and election ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM candidates 
    WHERE user_id = ? AND election_id = ?
    ''', (user_id, election_id))
    
    candidate_data = cursor.fetchone()
    
    conn.close()
    
    if candidate_data:
        return Candidate(
            id=candidate_data['id'],
            user_id=candidate_data['user_id'],
            election_id=candidate_data['election_id'],
            manifesto=candidate_data['manifesto'],
            ward_number=candidate_data['ward_number'],
            approval_status=candidate_data['approval_status'],
            logo_path=candidate_data['logo_path'],
            created_at=candidate_data['created_at']
        )
    return None

def update_candidate(candidate_id, manifesto=None, ward_number=None, logo_path=None):
    """Update candidate details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    if manifesto:
        update_fields.append("manifesto = ?")
        params.append(manifesto)
    
    if ward_number:
        update_fields.append("ward_number = ?")
        params.append(ward_number)
    
    if logo_path:
        update_fields.append("logo_path = ?")
        params.append(logo_path)
    
    if update_fields:
        query = f"UPDATE candidates SET {', '.join(update_fields)} WHERE id = ?"
        params.append(candidate_id)
        
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def update_approval_status(candidate_id, status, admin_id):
    """Update a candidate's approval status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE candidates 
    SET approval_status = ? 
    WHERE id = ?
    ''', (status, candidate_id))
    
    # Get candidate details for logging
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate_data = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    log_activity(admin_id, 'CANDIDATE_STATUS_UPDATE', 
                f"Updated candidate ID {candidate_id} status to {status}")
    
    return True

def get_candidates_by_election(election_id, status=None):
    """Get all candidates for an election, optionally filtered by approval status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('''
        SELECT * FROM candidates 
        WHERE election_id = ? AND approval_status = ?
        ''', (election_id, status))
    else:
        cursor.execute('''
        SELECT * FROM candidates 
        WHERE election_id = ?
        ''', (election_id,))
    
    candidates_data = cursor.fetchall()
    conn.close()
    
    candidates = []
    for candidate_data in candidates_data:
        candidates.append(Candidate(
            id=candidate_data['id'],
            user_id=candidate_data['user_id'],
            election_id=candidate_data['election_id'],
            manifesto=candidate_data['manifesto'],
            ward_number=candidate_data['ward_number'],
            approval_status=candidate_data['approval_status'],
            logo_path=candidate_data['logo_path'],
            created_at=candidate_data['created_at']
        ))
    
    return candidates

def get_pending_candidates():
    """Get all candidates with pending approval status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT c.*, e.title as election_title
    FROM candidates c
    JOIN elections e ON c.election_id = e.id
    WHERE c.approval_status = 'pending'
    ''')
    
    candidates_data = cursor.fetchall()
    conn.close()
    
    candidates = []
    for candidate_data in candidates_data:
        candidate = Candidate(
            id=candidate_data['id'],
            user_id=candidate_data['user_id'],
            election_id=candidate_data['election_id'],
            manifesto=candidate_data['manifesto'],
            ward_number=candidate_data['ward_number'],
            approval_status=candidate_data['approval_status'],
            logo_path=candidate_data['logo_path'],
            created_at=candidate_data['created_at']
        )
        # Add election title as a property
        candidate.election_title = candidate_data['election_title']
        candidates.append(candidate)
    
    return candidates

def get_user_elections_as_candidate(user_id):
    """Get all elections a user is participating in as a candidate"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT e.*, c.approval_status, c.id as candidate_id
    FROM elections e
    JOIN candidates c ON e.id = c.election_id
    WHERE c.user_id = ?
    ''', (user_id,))
    
    elections_data = cursor.fetchall()
    conn.close()
    
    from app.models.election import Election
    
    elections = []
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
        # Add candidate specific details
        election.approval_status = election_data['approval_status']
        election.candidate_id = election_data['candidate_id']
        elections.append(election)
    
    return elections 