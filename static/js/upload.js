document.addEventListener('DOMContentLoaded', function() {
    // File upload form validation and progress handling
    const uploadForm = document.getElementById('uploadForm');
    const programFileInput = document.getElementById('program_file');
    const programNameInput = document.getElementById('program_name');
    const uploadButton = document.getElementById('uploadButton');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = uploadProgress.querySelector('.progress-bar');
    
    // Validate form fields
    function validateForm() {
        let isValid = true;
        
        // Validate program name
        if (!programNameInput.value.trim()) {
            programNameInput.classList.add('is-invalid');
            isValid = false;
        } else if (!/^[a-zA-Z0-9_\s]+$/.test(programNameInput.value.trim())) {
            programNameInput.classList.add('is-invalid');
            isValid = false;
        } else {
            programNameInput.classList.remove('is-invalid');
        }
        
        // Validate file
        if (!programFileInput.files || programFileInput.files.length === 0) {
            programFileInput.classList.add('is-invalid');
            isValid = false;
        } else {
            const fileName = programFileInput.files[0].name;
            const fileExt = fileName.split('.').pop().toLowerCase();
            
            if (fileExt !== 'csv' && fileExt !== 'xlsx') {
                programFileInput.classList.add('is-invalid');
                isValid = false;
            } else {
                programFileInput.classList.remove('is-invalid');
            }
        }
        
        return isValid;
    }
    
    // Reset validation state when inputs change
    programNameInput.addEventListener('input', function() {
        this.classList.remove('is-invalid');
    });
    
    programFileInput.addEventListener('change', function() {
        this.classList.remove('is-invalid');
        
        // Show file name
        const fileName = this.files[0]?.name || 'No file chosen';
        const fileLabel = this.nextElementSibling;
        if (fileLabel) {
            fileLabel.textContent = fileName;
        }
    });
    
    // Form submission handler
    uploadForm.addEventListener('submit', function(e) {
        if (!validateForm()) {
            e.preventDefault();
            return;
        }
        
        // Show progress bar
        uploadButton.disabled = true;
        uploadProgress.style.display = 'block';
        progressBar.style.width = '0%';
        
        // Simulate progress (in a real application, this would be tied to actual upload progress)
        let progress = 0;
        const interval = setInterval(function() {
            progress += 5;
            progressBar.style.width = `${Math.min(progress, 95)}%`;
            
            if (progress >= 95) {
                clearInterval(interval);
            }
        }, 100);
    });
});
