// Custom JavaScript for E-Voting System

document.addEventListener('DOMContentLoaded', function() {
    // Auto-close alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Enhance candidate selection on ballot page
    const candidateCards = document.querySelectorAll('.ballot-card');
    if (candidateCards.length > 0) {
        candidateCards.forEach(function(card) {
            card.addEventListener('click', function(e) {
                // Don't trigger if the actual radio button was clicked
                if (e.target.type !== 'radio') {
                    const radio = card.querySelector('input[type="radio"]');
                    radio.checked = true;
                    
                    // Remove selected class from all cards
                    candidateCards.forEach(c => c.classList.remove('border-primary', 'bg-light'));
                    
                    // Add selected class to clicked card
                    card.classList.add('border-primary', 'bg-light');
                }
            });
        });
    }

    // Vote confirmation modal
    const voteForm = document.querySelector('form[action*="/vote/"]');
    if (voteForm) {
        voteForm.addEventListener('submit', function(e) {
            const selectedCandidate = voteForm.querySelector('input[name="candidate_id"]:checked');
            if (!selectedCandidate) {
                e.preventDefault();
                alert('Please select a candidate before submitting your vote.');
            } else if (!confirm('Are you sure you want to cast your vote? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    }

    // Candidate form validation
    const candidateForm = document.querySelector('form[action*="/candidate/register/"]');
    if (candidateForm) {
        candidateForm.addEventListener('submit', function(e) {
            const manifesto = candidateForm.querySelector('textarea[name="manifesto"]');
            if (manifesto && manifesto.value.trim().length < 10) {
                e.preventDefault();
                alert('Please provide a longer manifesto (at least 10 characters).');
                manifesto.focus();
            }
        });
    }

    // Election date validation
    const electionForm = document.querySelector('form[action*="/election/create"]');
    if (electionForm) {
        electionForm.addEventListener('submit', function(e) {
            const startTime = new Date(electionForm.querySelector('input[name="start_time"]').value);
            const endTime = new Date(electionForm.querySelector('input[name="end_time"]').value);
            const now = new Date();
            
            if (startTime < now) {
                e.preventDefault();
                alert('Start time must be in the future.');
            } else if (endTime <= startTime) {
                e.preventDefault();
                alert('End time must be after start time.');
            }
        });
    }

    // Format dates in a human-readable format
    const datesToFormat = document.querySelectorAll('.format-date');
    if (datesToFormat.length > 0) {
        datesToFormat.forEach(function(element) {
            const dateStr = element.textContent;
            if (dateStr) {
                const date = new Date(dateStr);
                if (!isNaN(date)) {
                    element.textContent = date.toLocaleString();
                }
            }
        });
    }

    // Add copy functionality for reference IDs
    const referenceId = document.querySelector('.reference-id');
    if (referenceId) {
        referenceId.addEventListener('click', function() {
            const textToCopy = referenceId.textContent;
            navigator.clipboard.writeText(textToCopy)
                .then(() => {
                    const originalText = referenceId.innerHTML;
                    referenceId.innerHTML = '<i class="fas fa-check-circle me-2"></i>Copied!';
                    setTimeout(() => {
                        referenceId.innerHTML = originalText;
                    }, 2000);
                })
                .catch(err => {
                    console.error('Could not copy text: ', err);
                });
        });

        // Add tooltip to indicate it's clickable
        referenceId.title = 'Click to copy';
        referenceId.style.cursor = 'pointer';
    }
});

/**
 * Live Results Update Functions
 */

// Display a vote increment animation
function showVoteIncrement(candidateId, increment) {
    if (increment <= 0) return;
    
    const resultItem = document.querySelector(`.result-item[data-candidate-id="${candidateId}"]`);
    if (!resultItem) return;
    
    // Create increment indicator
    const indicator = document.createElement('div');
    indicator.className = 'vote-change';
    indicator.textContent = `+${increment}`;
    resultItem.appendChild(indicator);
    
    // Highlight the row
    resultItem.classList.add('updated');
    setTimeout(() => {
        resultItem.classList.remove('updated');
    }, 2000);
    
    // Remove the indicator after animation completes
    setTimeout(() => {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }, 2000);
}

// Sort result items by vote count
function sortResultsByVotes() {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;
    
    const resultItems = Array.from(resultsContainer.querySelectorAll('.result-item'));
    
    // Sort by vote count (descending)
    resultItems.sort((a, b) => {
        const votesA = parseInt(a.querySelector('[id^="votes-"]').textContent);
        const votesB = parseInt(b.querySelector('[id^="votes-"]').textContent);
        return votesB - votesA;
    });
    
    // Reattach in sorted order
    resultItems.forEach(item => {
        resultsContainer.appendChild(item);
    });
    
    // Update winner badge
    const winnerBadges = document.querySelectorAll('.winner-badge');
    winnerBadges.forEach(badge => badge.remove());
    
    if (resultItems.length > 0) {
        const winner = resultItems[0];
        const badge = document.createElement('span');
        badge.className = 'badge bg-success float-end mt-1 winner-badge';
        badge.textContent = 'Winner';
        winner.appendChild(badge);
    }
} 