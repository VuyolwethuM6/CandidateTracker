document.addEventListener('DOMContentLoaded', function() {
    // Initialize programs page
    loadProgramsData();
    
    // Set up confirm delete handler
    setupDeleteHandler();
});

// DataTable instances
let programsTable, candidatesTable;

/**
 * Load programs data from API
 */
function loadProgramsData() {
    fetch('/api/programs')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading, show content
            document.getElementById('programs-loading').style.display = 'none';
            document.getElementById('programs-content').style.display = 'block';
            
            // Check if data is empty
            if (data.length === 0) {
                document.getElementById('no-programs-message').style.display = 'block';
                return;
            } else {
                document.getElementById('no-programs-message').style.display = 'none';
            }
            
            // Display programs in table
            displayProgramsTable(data);
        })
        .catch(error => {
            console.error('Error fetching programs data:', error);
            document.getElementById('programs-loading').style.display = 'none';
            document.getElementById('programs-content').style.display = 'block';
            document.getElementById('no-programs-message').style.display = 'block';
        });
}

/**
 * Display programs data in table
 */
function displayProgramsTable(programs) {
    const tableBody = document.getElementById('programsTableBody');
    tableBody.innerHTML = '';
    
    programs.forEach(program => {
        const row = document.createElement('tr');
        
        // Female target indicator
        const femaleMet = program.female_percent >= 70;
        const femaleIndicator = `<span class="target-indicator ${femaleMet ? 'target-met' : 'target-not-met'}"></span>`;
        
        // PWD target indicator
        const pwdMet = program.pwd_percent >= 5;
        const pwdIndicator = `<span class="target-indicator ${pwdMet ? 'target-met' : 'target-not-met'}"></span>`;
        
        // Target status
        const targetsMetHtml = `
            <div>
                ${femaleIndicator} Female: ${femaleMet ? 'Met' : 'Not Met'}<br>
                ${pwdIndicator} PWD: ${pwdMet ? 'Met' : 'Not Met'}
            </div>
        `;
        
        row.innerHTML = `
            <td>${program.name}</td>
            <td>${program.total_candidates}</td>
            <td>${program.female_percent}% (${program.female_count})</td>
            <td>${program.pwd_percent}% (${program.pwd_count})</td>
            <td>${targetsMetHtml}</td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-sm btn-primary view-program" data-program="${program.name}">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn btn-sm btn-danger delete-program" data-program="${program.name}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Initialize DataTable
    if (programsTable) {
        programsTable.destroy();
    }
    
    programsTable = $('#programsTable').DataTable({
        responsive: true,
        order: [[1, 'desc']], // Sort by candidates count
        language: {
            search: "Search programs:",
            emptyTable: "No programs available"
        }
    });
    
    // Add event listeners to view buttons
    document.querySelectorAll('.view-program').forEach(button => {
        button.addEventListener('click', function() {
            const programName = this.getAttribute('data-program');
            loadProgramCandidates(programName);
        });
    });
    
    // Add event listeners to delete program buttons
    document.querySelectorAll('.delete-program').forEach(button => {
        button.addEventListener('click', function() {
            const programName = this.getAttribute('data-program');
            if (confirm(`Are you sure you want to delete the program "${programName}" and all its candidate data? This action cannot be undone.`)) {
                deleteProgram(programName);
            }
        });
    });
}

/**
 * Load candidates for a specific program
 */
function loadProgramCandidates(programName) {
    // Show loading
    document.getElementById('program-details-section').style.display = 'none';
    document.getElementById('programs-loading').style.display = 'block';
    
    fetch(`/api/program/${programName}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(candidates => {
            // Hide loading, show program details
            document.getElementById('programs-loading').style.display = 'none';
            document.getElementById('program-details-section').style.display = 'block';
            
            // Update program title
            document.getElementById('selected-program-name').textContent = programName;
            
            // Display candidates
            displayProgramCandidates(candidates, programName);
        })
        .catch(error => {
            console.error(`Error fetching candidates for program ${programName}:`, error);
            document.getElementById('programs-loading').style.display = 'none';
            alert(`Error loading candidates for ${programName}. Please try again.`);
        });
}

/**
 * Display candidates for a specific program
 */
function displayProgramCandidates(candidates, programName) {
    const tableBody = document.getElementById('programCandidatesTableBody');
    tableBody.innerHTML = '';
    
    candidates.forEach(candidate => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${candidate['Candidate ID']}</td>
            <td>${candidate['First Name']} ${candidate['Surname']}</td>
            <td>${candidate['Gender']}</td>
            <td>${candidate['Disability Status']}</td>
            <td>${candidate['NQF Level']}</td>
            <td>${candidate['Institution Name']}</td>
            <td>
                <button class="btn btn-sm btn-danger delete-candidate" 
                        data-id="${candidate['Candidate ID']}" 
                        data-program="${programName}">
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
    
    candidatesTable = $('#programCandidatesTable').DataTable({
        responsive: true,
        language: {
            search: "Search candidates:",
            emptyTable: "No candidates in this program"
        }
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
            // Reload program data
            loadProgramCandidates(program);
            
            // Also reload programs list to update counts
            loadProgramsData();
        } else {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error deleting candidate:', error);
        alert('Error deleting candidate. Please try again.');
    });
}

/**
 * Delete an entire program
 */
function deleteProgram(programName) {
    fetch('/api/programs/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            program_name: programName
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
            // Show success alert
            alert(data.message);
            
            // Reload programs list
            loadProgramsData();
            
            // Hide program details section if it's showing the deleted program
            const selectedProgramName = document.getElementById('selected-program-name').textContent;
            if (selectedProgramName === programName) {
                document.getElementById('program-details-section').style.display = 'none';
            }
        } else {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error deleting program:', error);
        alert('Error deleting program. Please try again.');
    });
}
