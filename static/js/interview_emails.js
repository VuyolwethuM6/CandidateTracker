document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const previewCard = document.getElementById('previewCard');
    const previewTableBody = document.querySelector('#previewTable tbody');
    const uploadBtn = document.getElementById('uploadBtn');
    const generateBtn = document.getElementById('generateBtn');
    const previewOnlyBtn = document.getElementById('previewOnlyBtn');
    const statusCard = document.getElementById('statusCard');
    const statusTableBody = document.querySelector('#statusTable tbody');
    const overallProgress = document.getElementById('overallProgress');
    const filterDecision = document.getElementById('filterDecision');

    let currentJobId = null;
    

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Choose a CSV file first');
            return;
        }

        uploadBtn.disabled = true;
        const fd = new FormData();
        fd.append('file', fileInput.files[0]);

        try {
            const resp = await fetch('/api/interview-emails/upload', { method: 'POST', body: fd });
            const payload = await resp.json();
            if (!resp.ok) {
                alert(payload.error || 'Upload failed');
                return;
            }

            // show preview
            previewTableBody.innerHTML = '';
            // store preview rows for potential use
            // (no template features in this UI version)
            // preview_rows retained for compatibility
            // but we won't use a client-side template editor
            // in this simplified flow.
            //
            // previewRows = payload.preview_rows || [];
            payload.preview_rows.forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${r.index}</td><td>${r.name}</td><td>${r.surname}</td><td>${r.email}</td><td>${r.decision}</td><td>${r.feedback}</td>`;
                previewTableBody.appendChild(tr);
            });
            previewCard.style.display = 'block';
            currentJobId = payload.job_id;
        } catch (err) {
            console.error(err);
            alert('Upload failed: ' + err.message);
        } finally {
            uploadBtn.disabled = false;
        }
    });

    async function startJob(previewOnly) {
        if (!currentJobId) return alert('No job to start. Upload CSV first.');

        generateBtn.disabled = true;
        previewOnlyBtn.disabled = true;

        const filterVal = filterDecision.value || null;
        const body = { job_id: currentJobId, send: !previewOnly, preview_only: previewOnly };
        if (filterVal) body.filter_decisions = [filterVal];
        // No client-side template is used in this simplified UI.

        try {
            const resp = await fetch('/api/interview-emails/start', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
            });
            const payload = await resp.json();
            if (!resp.ok) {
                alert(payload.error || 'Failed to start job');
                return;
            }
            statusCard.style.display = 'block';
            pollStatus(payload.job_id);
        } catch (err) {
            console.error(err);
            alert('Failed to start job: ' + err.message);
        }
    }

    generateBtn.addEventListener('click', function() { startJob(false); });
    previewOnlyBtn.addEventListener('click', function() { startJob(true); });

    // Template editor helpers
    function renderTemplateClient(tmpl, row, bodyText, sig) {
        // Simple replacement for common Jinja-like placeholders
        let out = tmpl || '';
        const map = {
            '{{name}}': row.name || '',
            '{{surname}}': row.surname || '',
            '{{email}}': row.email || '',
            '{{feedback}}': row.feedback || '',
            '{{decision}}': row.decision || '',
            '{{body}}': bodyText || '',
            '{{signature}}': sig || ''
        };
        Object.keys(map).forEach(k => {
            out = out.split(k).join(map[k]);
        });
        return out;
    }

    previewTemplateBtn.addEventListener('click', function() {
        const tmpl = htmlTemplateInput.value || '';
        const sig = signatureInput.value || '';
        if (!tmpl) return alert('Please paste an HTML template to preview.');
        if (!previewRows || previewRows.length === 0) return alert('Upload a CSV first so we can preview with actual data.');
        const sample = previewRows[0];
        const sampleBody = 'Dear ' + (sample.name || '') + ' ' + (sample.surname || '') + ',\n\nThank you for your time. We will be in touch shortly regarding next steps.';
        const rendered = renderTemplateClient(tmpl, sample, sampleBody, sig);
        templatePreview.innerHTML = rendered;
        templatePreview.style.display = 'block';
        // store in localStorage for convenience
        try { localStorage.setItem('candidate_email_template', tmpl); localStorage.setItem('candidate_email_signature', sig); } catch(e){}
    });

    saveTemplateBtn.addEventListener('click', function() {
        try { localStorage.setItem('candidate_email_template', htmlTemplateInput.value || ''); localStorage.setItem('candidate_email_signature', signatureInput.value || ''); alert('Template saved to browser local storage.'); } catch(e) { alert('Save failed: ' + e.message); }
    });

    clearTemplateBtn.addEventListener('click', function() {
        if (!confirm('Clear template and signature?')) return;
        htmlTemplateInput.value = '';
        signatureInput.value = '';
        templatePreview.style.display = 'none';
        try { localStorage.removeItem('candidate_email_template'); localStorage.removeItem('candidate_email_signature'); } catch(e){}
    });

    // Load saved template from localStorage if present
    try {
        const savedT = localStorage.getItem('candidate_email_template');
        const savedS = localStorage.getItem('candidate_email_signature');
        if (savedT) htmlTemplateInput.value = savedT;
        if (savedS) signatureInput.value = savedS;
    } catch(e){}

    async function pollStatus(jobId) {
        try {
            const resp = await fetch(`/api/interview-emails/status?job_id=${encodeURIComponent(jobId)}`);
            const payload = await resp.json();
            if (!resp.ok) {
                console.error('Status error', payload);
                return;
            }

            // update progress
            const total = payload.total || 0;
            const processed = payload.processed || 0;
            const percent = total ? Math.round((processed / total) * 100) : 0;
            overallProgress.style.width = percent + '%';
            overallProgress.textContent = percent + '%';

            // update rows
            statusTableBody.innerHTML = '';
            Object.entries(payload.rows || {}).forEach(([idx, info]) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${idx}</td><td>${info.generated ? '—' : ''}</td><td>${info.status}</td><td>${info.message || ''}</td>`;
                statusTableBody.appendChild(tr);
            });

            if (!payload.finished) {
                setTimeout(() => pollStatus(jobId), 1500);
            } else {
                generateBtn.disabled = false;
                previewOnlyBtn.disabled = false;
                alert('Job finished. Review the status table and download logs if needed.');
            }
        } catch (err) {
            console.error('Polling error', err);
            setTimeout(() => pollStatus(jobId), 3000);
        }
    }
});
