document.addEventListener('DOMContentLoaded', function() {
    // Initialize candidates page
    loadCandidatesData();
    
    // Set up confirm delete handler
    setupDeleteHandler();
});

// DataTable instance
let candidatesTable;

/**
 * Load all candidates data from API
 */
function loadCandidatesData() {
    fetch('/api/candidates')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading, show content
            document.getElementById('candidates-loading').style.display = 'none';
            document.getElementById('candidates-content').style.display = 'block';
            
            // Check if data is empty
            if (data.length === 0) {
                document.getElementById('no-candidates-message').style.display = 'block';
                return;
            } else {
                document.getElementById('no-candidates-message').style.display = 'none';
            }
            
            // Display candidates in table
            displayCandidatesTable(data);
        })
        .catch(error => {
            console.error('Error fetching candidates data:', error);
            document.getElementById('candidates-loading').style.display = 'none';
            document.getElementById('candidates-content').style.display = 'block';
            document.getElementById('no-candidates-message').style.display = 'block';
        });
}

/**
 * Display candidates data in table
 */
function displayCandidatesTable(candidates) {
    const tableBody = document.getElementById('candidatesTableBody');
    tableBody.innerHTML = '';
    
    candidates.forEach(candidate => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${candidate['Candidate ID']}</td>
            <td>${candidate['First Name']} ${candidate['Surname']}</td>
            <td>${candidate['Gender']}</td>
            <td>${candidate['Disability Status']}</td>
            <td>${candidate['Program']}</td>
            <td>${candidate['Highest Qualification']}</td>
            <td>${candidate['NQF Level']}</td>
            <td>
                <button class="btn btn-sm btn-danger delete-candidate" 
                        data-id="${candidate['Candidate ID']}" 
                        data-program="${candidate['Program']}">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Initialize DataTable
    if (candidatesTable) {
        candidatesTable.destroy();
    }
    
    candidatesTable = $('#candidatesTable').DataTable({
        responsive: true,
        language: {
            search: "Search candidates:",
            emptyTable: "No candidates available"
        },
        columnDefs: [
            { responsivePriority: 1, targets: [0, 1, 6, 7] }, // Ensure these columns show first
            { responsivePriority: 2, targets: [2, 3] }        // Then these
        ]
    });
    
    // Add event listeners to delete buttons
    document.querySelectorAll('.delete-candidate').forEach(button => {
        button.addEventListener('click', function() {
            const candidateId = this.getAttribute('data-id');
            const program = this.getAttribute('data-program');
            
            // Show confirmation modal
            const modal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
            modal.show();
            
            // Set data attributes for confirm button
            document.getElementById('confirmDeleteButton').setAttribute('data-id', candidateId);
            document.getElementById('confirmDeleteButton').setAttribute('data-program', program);
        });
    });
}

/**
 * Set up delete confirmation handler
 */
function setupDeleteHandler() {
    document.getElementById('confirmDeleteButton').addEventListener('click', function() {
        const candidateId = this.getAttribute('data-id');
        const program = this.getAttribute('data-program');
        
        deleteCandidate(candidateId, program);
        
        // Hide modal
        bootstrap.Modal.getInstance(document.getElementById('confirmDeleteModal')).hide();
    });
}

/**
 * Delete a candidate
 */
function deleteCandidate(candidateId, program) {
    fetch('/api/candidates/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            candidate_id: candidateId,
            program: program
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Reload candidates data
            loadCandidatesData();
        } else {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error deleting candidate:', error);
        alert('Error deleting candidate. Please try again.');
    });
}
