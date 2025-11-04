import os
import io
import uuid
import time
import json
import logging
import sqlite3
import threading
from datetime import datetime

import requests
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file, current_app

DATA_DIR = './data/logs'
DB_PATH = os.environ.get('EMAIL_LOG_DB', os.path.join(DATA_DIR, 'email_log.db'))

interview_bp = Blueprint('interview_email', __name__, template_folder='templates')

# Simple in-memory job store. For production, replace with persistent job queue.
JOBS = {}


def init_db():
    """Initialize the SQLite DB for logging email sends."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS email_logs (
            id TEXT PRIMARY KEY,
            name TEXT,
            surname TEXT,
            email TEXT,
            decision TEXT,
            email_text TEXT,
            timestamp TEXT,
            status TEXT,
            error_message TEXT
        )
        '''
    )
    conn.commit()
    conn.close()


def append_log_row(row):
    """Insert a log row into the SQLite DB and append to CSV for human readability."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'INSERT OR REPLACE INTO email_logs (id, name, surname, email, decision, email_text, timestamp, status, error_message) VALUES (?,?,?,?,?,?,?,?,?)',
            (
                row.get('id'), row.get('name'), row.get('surname'), row.get('email'), row.get('decision'),
                row.get('email_text'), row.get('timestamp'), row.get('status'), row.get('error_message')
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.exception('Failed to write log to sqlite: %s', e)

    # Append to CSV as a lightweight audit
    csv_path = os.path.join(DATA_DIR, 'email_log.csv')
    try:
        header = not os.path.exists(csv_path)
        df = pd.DataFrame([{
            'id': row.get('id'),
            'name': row.get('name'),
            'surname': row.get('surname'),
            'email': row.get('email'),
            'decision': row.get('decision'),
            'email_text': row.get('email_text'),
            'timestamp': row.get('timestamp'),
            'status': row.get('status'),
            'error_message': row.get('error_message')
        }])
        df.to_csv(csv_path, mode='a', header=header, index=False)
    except Exception:
        logging.exception('Failed to append email log to CSV')


def find_column(df, candidates):
    """Find the first matching column in df from a list of candidate names (case-insensitive).

    Matching strategy:
    - Normalize column names and candidate names (lower, strip, remove non-alphanum -> spaces, collapse spaces)
    - Try exact normalized match, then substring match, then token subset match.
    """
    def normalize(s):
        if s is None:
            return ''
        s = str(s)
        # strip BOM and whitespace
        s = s.strip('\ufeff\u200b\xa0').strip()
        s = s.lower()
        # replace non-alphanumeric with space
        import re
        s = re.sub(r'[^0-9a-z]+', ' ', s)
        s = ' '.join(s.split())
        return s

    col_map = {normalize(c): c for c in df.columns}

    for cand in candidates:
        n_cand = normalize(cand)
        # exact normalized match
        if n_cand in col_map:
            return col_map[n_cand]

    # substring match (candidate within column)
    for cand in candidates:
        n_cand = normalize(cand)
        for nc, orig in col_map.items():
            if n_cand and n_cand in nc:
                return orig

    # token subset: all tokens in candidate appear in column name
    for cand in candidates:
        n_cand = normalize(cand)
        cand_tokens = set(n_cand.split())
        if not cand_tokens:
            continue
        for nc, orig in col_map.items():
            col_tokens = set(nc.split())
            if cand_tokens.issubset(col_tokens):
                return orig

    return None


@interview_bp.route('/interview-emails')
def interview_emails_page():
    return render_template('interview_emails.html')


@interview_bp.route('/api/interview-emails/upload', methods=['POST'])
def upload_interview_csv():
    """Accept CSV upload, validate columns, save a preview and return a job_id for processing."""
    init_db()
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = f.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx')):
        return jsonify({'error': 'Only .csv or .xlsx files are supported'}), 400

    try:
        # Read file content and attempt delimiter detection and BOM handling
        import io
        raw = f.read()
        if isinstance(raw, bytes):
            # decode with utf-8-sig to remove BOM if present
            text = raw.decode('utf-8-sig', errors='replace')
        else:
            text = str(raw)

        # Try pandas auto-detection of separator
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.StringIO(text), sep=None, engine='python')
            except Exception:
                # Fallback to common delimiters
                try:
                    df = pd.read_csv(io.StringIO(text), sep=';')
                except Exception:
                    df = pd.read_csv(io.StringIO(text), sep=',')
        else:
            # For excel files, pass through to pandas
            df = pd.read_excel(io.BytesIO(raw))
    except Exception as e:
        logging.exception('Failed to read uploaded file: %s', e)
        return jsonify({'error': f'Failed to parse file: {str(e)}'}), 400

    # required logical columns and variations
    required_variations = {
        'name': ['Name', 'First Name', 'FirstName', 'Given Name', 'First'],
        'surname': ['Surname', 'Last Name', 'LastName', 'Last_Name', 'Family Name'],
        'email': ['Email Address', 'Email', 'E-mail', 'EmailAddress', 'Contact Email'],
        'feedback': ['Interview Feedback/Notes', 'Feedback', 'Notes', 'Interview Feedback'],
        'decision': ['Proceed/Decline/Hold', 'Decision', 'Status']
    }

    mapped = {}
    missing = []
    for key, variants in required_variations.items():
        col = find_column(df, variants)
        if col:
            mapped[key] = col
        else:
            missing.append(key)

    if missing:
        return jsonify({'error': 'Missing required columns', 'missing': missing}), 400

    # Build standardized preview rows
    preview = []
    for idx, row in df.iterrows():
        preview.append({
            'index': int(idx),
            'name': str(row.get(mapped['name'], '')).strip(),
            'surname': str(row.get(mapped['surname'], '')).strip(),
            'email': str(row.get(mapped['email'], '')).strip(),
            'feedback': str(row.get(mapped['feedback'], '')).strip(),
            'decision': str(row.get(mapped['decision'], '')).strip()
        })

    job_id = str(uuid.uuid4())
    job_path = os.path.join(DATA_DIR, f'interview_job_{job_id}.csv')
    # Save standardized CSV for processing
    pd.DataFrame(preview).to_csv(job_path, index=False)

    # Initialize job metadata
    JOBS[job_id] = {
        'id': job_id,
        'total': len(preview),
        'processed': 0,
        'succeeded': 0,
        'failed': 0,
        'rows': {str(p['index']): {'status': 'pending', 'message': ''} for p in preview},
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'finished': False,
    }

    return jsonify({'job_id': job_id, 'preview_rows': preview})


def gemini_generate(prompt_text, api_key, timeout=30):
    """Call Google Gemini generative API. Returns generated text or raises Exception."""
    # Local test mode: return placeholder without calling external API
    if os.environ.get('GEMINI_LOCAL_TEST', '').lower() in ('1', 'true', 'yes'):
        logging.info('GEMINI_LOCAL_TEST enabled — returning placeholder text')
        return 'Hello {name},\n\nThank you for your time. We will be in touch shortly regarding next steps.'

    if not api_key:
        raise RuntimeError('Missing GEMINI_API_KEY')

    # Prefer the flash model by default (lower-latency for shorter outputs)
    model = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')
    # By default use the X-goog-api-key header (matches curl examples); can be overridden via env
    use_key_header = os.environ.get('GEMINI_KEY_AS_HEADER', '1').lower() in ('1', 'true', 'yes')
    if use_key_header:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

        # Raise for HTTP errors but capture body for better diagnostics
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            body = None
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            logging.error('Gemini HTTP error %s: %s', resp.status_code, body)
            resp.raise_for_status()

        data = resp.json()
        # Defensive parsing
        cand = data.get('candidates') or []
        if not cand:
            raise RuntimeError('No candidates in Gemini response')
        parts = cand[0].get('content', {}).get('parts') or []
        if not parts:
            raise RuntimeError('No content parts in Gemini response')
        return parts[0].get('text', '').strip()
    except Exception as e:
        logging.exception('Gemini API error: %s', e)
        raise


def send_email_smtp(sender_email, sender_password, candidate_email, email_body, subject='Update on Your Application', smtp_host='smtp.office365.com', smtp_port=587, use_tls=True):
    """
    Send an email via SMTP. Builds an HTML message with Aptos font (12pt) and appends
    a signature from the OUTLOOK_SIGNATURE env var if present. The From header will
    display as "CAPACITI Recruitment <sender_email>" while the SMTP envelope still uses sender_email.

    email_body is expected to be plain text (generated by Gemini). This function will
    convert that to simple HTML paragraphs and include a plain-text alternative.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.utils import formataddr

    # Build HTML body — prefer to detect if email_body already looks like HTML
    is_html = False
    if isinstance(email_body, str) and ('<' in email_body and '>' in email_body and '</' in email_body):
        is_html = True

    def plaintext_to_html(txt):
        # split paragraphs by two newlines
        parts = [p.strip() for p in txt.split('\n\n') if p.strip()]
        html_pars = []
        for p in parts:
            # replace single newlines with <br>
            p_html = p.replace('\n', '<br>')
            html_pars.append(f"<p style='margin:0 0 12px 0;'>" + p_html + "</p>")
        return '\n'.join(html_pars)

    if is_html:
        body_html_core = email_body
    else:
        body_html_core = plaintext_to_html(email_body)

    # Signature: allow user to provide HTML or plain text in an env var
    signature = os.environ.get('OUTLOOK_SIGNATURE', '').strip()
    signature_html = ''
    if signature:
        # If signature contains HTML tags, trust it; otherwise convert newlines to <br>
        if '<' in signature and '>' in signature:
            signature_html = signature
        else:
            signature_html = '<div style="margin-top:12px;">' + signature.replace('\n', '<br>') + '</div>'
    else:
        # Fallback minimal signature
        signature_html = '<div style="margin-top:12px;">Kind regards,<br>CAPACITI Recruitment</div>'

    # Remove any accidental 'Sincerely, The CAPACITI Team' from the signature to avoid duplication
    try:
        import re
        signature_html = re.sub(r"(?is)<(p|div)[^>]*>\s*sincerely[,\s]*</\1>\s*(?:<(?:p|div)[^>]*>\s*the\s+capaciti\s+team\s*</(?:p|div)>)?", "", signature_html)
        signature_html = re.sub(r"(?is)sincerely\s*(?:<br\s*/?>|&nbsp;|\s){1,5}the\s+capaciti\s+team", "", signature_html)
        signature_html = re.sub(r"(?im)\s*sincerely,?\s*(?:\r\n|\n|\s){0,5}the\s+capaciti\s+team\s*", "", signature_html)
        signature_html = re.sub(r"(?i)sincerely,?\s*the\s+capaciti\s+team", "", signature_html)
    except Exception:
        pass

    # Outer HTML with inline style for font and spacing. Aptos may not be available on all clients,
    # so include fallbacks.
    html_template = f"""
<div style="font-family: Aptos, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size:12pt; line-height:1.4; color:#000;">
{body_html_core}
{signature_html}
</div>
"""

    # Build multipart message with plain text alternative
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    # Display name should be friendly while using the real sender email as the address
    msg['From'] = formataddr(('CAPACITI Recruitment', sender_email))
    msg['To'] = candidate_email

    # Plain text alternative — use original email_body (or strip HTML tags if needed)
    plain_part = MIMEText(email_body, 'plain')
    html_part = MIMEText(html_template, 'html')
    msg.attach(plain_part)
    msg.attach(html_part)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [candidate_email], msg.as_string())
        server.quit()
    except Exception:
        logging.exception('SMTP send failed')
        raise


def process_job(job_id, send=True, filter_decisions=None, preview_only=False, html_template=None):
    """Background worker that processes a saved job CSV and sends emails."""
    job = JOBS.get(job_id)
    if not job:
        logging.error('Job not found: %s', job_id)
        return

    job_path = os.path.join(DATA_DIR, f'interview_job_{job_id}.csv')
    try:
        df = pd.read_csv(job_path, dtype=str).fillna('')
    except Exception as e:
        logging.exception('Failed to open job file: %s', e)
        job['finished'] = True
        job['error'] = f'Failed to open job file: {e}'
        return

    # Read secrets from environment variables (do NOT hardcode keys)
    gemini_key = os.environ.get('GEMINI_API_KEY')
    smtp_email = os.environ.get('OUTLOOK_EMAIL')
    smtp_password = os.environ.get('OUTLOOK_PASSWORD')

    if not gemini_key:
        logging.error('GEMINI_API_KEY environment variable is not set')
    if not smtp_email or not smtp_password:
        logging.warning('OUTLOOK_EMAIL and/or OUTLOOK_PASSWORD are not set; sending will fail if attempted')

    # If no html_template passed per-job, try env var EMAIL_HTML_TEMPLATE
    if not html_template:
        html_template = os.environ.get('EMAIL_HTML_TEMPLATE')

    for _, row in df.iterrows():
        idx = str(int(row.get('index', 0)))
        try:
            name = row.get('name', '')
            surname = row.get('surname', '')
            email = row.get('email', '')
            feedback = row.get('feedback', '')
            decision = row.get('decision', '')

            # Respect filter if provided
            if filter_decisions and decision not in filter_decisions:
                job['rows'][idx] = {'status': 'skipped', 'message': 'Filtered out'}
                job['processed'] += 1
                continue

            if not email:
                job['rows'][idx] = {'status': 'failed', 'message': 'Missing email address'}
                job['failed'] += 1
                job['processed'] += 1
                append_log_row({
                    'id': str(uuid.uuid4()), 'name': name, 'surname': surname, 'email': email,
                    'decision': decision, 'email_text': '', 'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'status': 'failed', 'error_message': 'Missing email address'
                })
                continue

            # Build prompt
            # Subject template (can be overridden via env)
            email_subject = os.environ.get('EMAIL_SUBJECT', 'CAPACITI — Update on Your Application')

            # If an HTML template is provided, we ask Gemini to produce a short plain-text
            # decision/next-steps paragraph (no signature, no placeholders). We'll then
            # render that into the HTML template using Jinja2. If no template is provided,
            # ask Gemini to return an HTML fragment (with <p> tags) that can be sent directly.
            if html_template:
                prompt_text = (
                    f"Write a short, polite and personalized paragraph specifically for {name} {surname}"
                    f" based on this interview feedback: \"{feedback}\". The decision is \"{decision}\". "
                    "Do NOT include placeholders like {name} or [Name]. Do NOT include a signature. "
                    "Keep it to one concise paragraph suitable for insertion into an HTML template. "
                    "Include the company name CAPACITI somewhere in the paragraph. Return only the paragraph text."
                )
            else:
                prompt_text = (
                    f"Write a short, polite, and personalized HTML email body specifically to {name} {surname} <{email}> "
                    f"based on this interview feedback: \"{feedback}\". The decision is \"{decision}\". "
                    "Start the email with 'Dear <Name> <Surname>,' (replace with the real name). "
                    "Include the company name 'CAPACITI' in the body and in the sign-off. "
                    "Do NOT include template placeholders such as {name}, [Name], [[name]], or similar — produce the final HTML text that can be sent as-is. "
                    "Return an HTML fragment (use <p> for paragraphs) and do not wrap it in <html>/<body> tags."
                )

            # Generate with Gemini (with retries)
            generated = ''
            gemini_error = None
            for attempt in range(3):
                try:
                    generated = gemini_generate(prompt_text, gemini_key)
                    break
                except Exception as e:
                    gemini_error = str(e)
                    sleep_for = (2 ** attempt)
                    time.sleep(sleep_for)

            # Strip common code-fence markers that LLMs sometimes include, e.g. ```html ... ```
            def strip_code_fences(text):
                if not isinstance(text, str):
                    return text
                import re
                # remove fenced blocks like ```html ... ``` or ``` ... ```
                text = re.sub(r"```\s*html\s*([\s\S]*?)```", r"\1", text, flags=re.IGNORECASE)
                text = re.sub(r"```([\s\S]*?)```", r"\1", text)
                # also remove any leading/trailing ``` markers
                text = text.replace('```', '')
                return text

            def remove_unwanted_closing(text):
                """Remove unwanted closing salutations like 'Sincerely,\n\nThe CAPACITI Team' or HTML variants.

                This attempts multiple patterns to catch HTML paragraphs, <br> variants, and plain-text variants.
                """
                if not isinstance(text, str):
                    return text
                import re
                out = text

                # 1) HTML block variant: <p>Sincerely,</p><p>The CAPACITI Team</p> (allow attributes)
                out = re.sub(r"(?is)<(p|div)[^>]*>\s*sincerely[,\s]*</\1>\s*(?:<(?:p|div)[^>]*>\s*the\s+capaciti\s+team\s*</(?:p|div)>)?", "", out)

                # 2) HTML inline with <br> between
                out = re.sub(r"(?is)sincerely\s*(?:<br\s*/?>|&nbsp;|\s){1,5}the\s+capaciti\s+team", "", out)

                # 3) Plain text multi-line variants with optional whitespace/newlines
                out = re.sub(r"(?im)\s*sincerely,?\s*(?:\r\n|\n|\s){0,5}the\s+capaciti\s+team\s*", "", out)

                # 4) Single-line catch-all
                out = re.sub(r"(?i)sincerely,?\s*the\s+capaciti\s+team", "", out)

                # Trim whitespace and redundant line breaks
                out = re.sub(r"\n{3,}", "\n\n", out)
                return out.strip()

            # Post-process generated output: replace common placeholder patterns with real name
            def replace_placeholders(text, name_val, surname_val):
                import re
                out = text
                # common name placeholders
                out = re.sub(r"\{\s*name\s*\}", name_val, out, flags=re.IGNORECASE)
                out = re.sub(r"\{\s*surname\s*\}", surname_val, out, flags=re.IGNORECASE)
                out = re.sub(r"\[\s*name\s*\]", name_val, out, flags=re.IGNORECASE)
                out = re.sub(r"\[\s*surname\s*\]", surname_val, out, flags=re.IGNORECASE)
                out = re.sub(r"\[\[\s*name\s*\]\]", name_val, out, flags=re.IGNORECASE)
                out = re.sub(r"\[\[\s*surname\s*\]\]", surname_val, out, flags=re.IGNORECASE)
                # angle-bracket placeholders
                out = re.sub(r"<\s*name\s*>", name_val, out, flags=re.IGNORECASE)
                out = re.sub(r"<\s*surname\s*>", surname_val, out, flags=re.IGNORECASE)
                return out

            if generated:
                # Remove code-fence artifacts (e.g. ```html ... ```) that may appear in LLM output
                generated = strip_code_fences(generated)
                # If we asked for plain text (because a template will be used), we still
                # perform placeholder replacement and then render into the template.
                generated = replace_placeholders(generated, name, surname)

                # If generated still contains placeholder-like characters, try up to 2 more regenerations
                import re
                placeholder_pattern = re.compile(r"\{\s*name|\{\s*surname|\[\[|\{\{|<\s*name", re.IGNORECASE)
                regen_attempts = 0
                while regen_attempts < 2 and placeholder_pattern.search(generated):
                    try:
                        regen_attempts += 1
                        generated = gemini_generate(prompt_text, gemini_key)
                        generated = replace_placeholders(generated, name, surname)
                    except Exception as e:
                        gemini_error = str(e)
                        break

                # If an HTML template is provided, render it now using Jinja2
                if html_template:
                    try:
                        from jinja2 import Template
                        tmpl = Template(html_template)
                        # Provide variables: name, surname, email, feedback, decision, body
                        rendered = tmpl.render(name=name, surname=surname, email=email, feedback=feedback, decision=decision, body=generated)
                        generated = rendered
                    except Exception:
                        logging.exception('Failed to render HTML template — falling back to plain generated text')
                        # If rendering fails, ensure we have some HTML wrapper
                        generated = '<p>' + generated.replace('\n', '<br>') + '</p>'

                else:
                    # For HTML output from Gemini, ensure CAPACITI is present; if not, append a sign-off
                    if 'capaciti' not in generated.lower():
                        generated = generated.strip()
                        if generated.endswith('</p>') or '<p' in generated:
                            generated = generated + "<p style='margin-top:12px;'>Kind regards,<br>CAPACITI</p>"
                        else:
                            generated = '<p>' + generated.replace('\n', '<br>') + '</p>' + "<p style='margin-top:12px;'>Kind regards,<br>CAPACITI</p>"

                # Remove any unwanted closing like 'Sincerely,\n\nThe CAPACITI Team'
                try:
                    generated = remove_unwanted_closing(generated)
                except Exception:
                    # non-fatal
                    pass

            if not generated:
                job['rows'][idx] = {'status': 'failed', 'message': f'Gemini failed: {gemini_error}'}
                job['failed'] += 1
                job['processed'] += 1
                append_log_row({
                    'id': str(uuid.uuid4()), 'name': name, 'surname': surname, 'email': email,
                    'decision': decision, 'email_text': '', 'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'status': 'failed', 'error_message': f'Gemini: {gemini_error}'
                })
                continue

            # If preview_only, do not send, but store generated text
            if preview_only or not send:
                job['rows'][idx] = {'status': 'generated', 'message': 'Generated (not sent)', 'generated': generated}
                job['succeeded'] += 1
                job['processed'] += 1
                append_log_row({
                    'id': str(uuid.uuid4()), 'name': name, 'surname': surname, 'email': email,
                    'decision': decision, 'email_text': generated, 'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'status': 'generated', 'error_message': ''
                })
                continue

            # Send via SMTP with retries
            smtp_error = None
            for attempt in range(3):
                try:
                    # Use the subject template and ensure CAPACITI appears in subject
                    subject = email_subject
                    if 'capaciti' not in subject.lower():
                        subject = f"CAPACITI — {subject}"
                    send_email_smtp(smtp_email, smtp_password, email, generated, subject=subject)
                    smtp_error = None
                    break
                except Exception as e:
                    smtp_error = str(e)
                    time.sleep(2 ** attempt)

            if smtp_error:
                job['rows'][idx] = {'status': 'failed', 'message': f'SMTP failed: {smtp_error}'}
                job['failed'] += 1
                job['processed'] += 1
                append_log_row({
                    'id': str(uuid.uuid4()), 'name': name, 'surname': surname, 'email': email,
                    'decision': decision, 'email_text': generated, 'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'status': 'failed', 'error_message': f'SMTP: {smtp_error}'
                })
                continue

            # Success
            job['rows'][idx] = {'status': 'sent', 'message': 'Sent', 'generated': generated}
            job['succeeded'] += 1
            job['processed'] += 1
            append_log_row({
                'id': str(uuid.uuid4()), 'name': name, 'surname': surname, 'email': email,
                'decision': decision, 'email_text': generated, 'timestamp': datetime.utcnow().isoformat() + 'Z',
                'status': 'sent', 'error_message': ''
            })

        except Exception as e:
            logging.exception('Unhandled error processing row: %s', e)
            job['rows'][idx] = {'status': 'failed', 'message': f'Unhandled: {str(e)}'}
            job['failed'] += 1
            job['processed'] += 1
            append_log_row({
                'id': str(uuid.uuid4()), 'name': row.get('name',''), 'surname': row.get('surname',''), 'email': row.get('email',''),
                'decision': row.get('decision',''), 'email_text': '', 'timestamp': datetime.utcnow().isoformat() + 'Z',
                'status': 'failed', 'error_message': str(e)
            })

    job['finished'] = True


@interview_bp.route('/api/interview-emails/start', methods=['POST'])
def start_interview_job():
    data = request.get_json() or {}
    job_id = data.get('job_id')
    send = data.get('send', True)
    preview_only = data.get('preview_only', False)
    filter_decisions = data.get('filter_decisions') or None
    # Optional HTML template provided by client (string). Can include Jinja2 placeholders
    html_template = data.get('html_template')

    if not job_id or job_id not in JOBS:
        return jsonify({'error': 'Invalid or missing job_id'}), 400

    # Start background thread
    thread = threading.Thread(target=process_job, args=(job_id, send, filter_decisions, preview_only, html_template), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'started'})


@interview_bp.route('/api/interview-emails/status')
def interview_job_status():
    job_id = request.args.get('job_id')
    if not job_id or job_id not in JOBS:
        return jsonify({'error': 'Job not found'}), 404
    job = JOBS[job_id]
    # Return a lightweight view
    return jsonify({
        'id': job['id'],
        'total': job['total'],
        'processed': job['processed'],
        'succeeded': job['succeeded'],
        'failed': job['failed'],
        'rows': job['rows'],
        'finished': job.get('finished', False)
    })


@interview_bp.route('/api/interview-emails/logs')
def download_email_logs():
    # Return CSV if exists else return sqlite dump
    csv_path = os.path.join(DATA_DIR, 'email_log.csv')
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True)

    # Fallback: export sqlite to CSV in-memory
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query('SELECT * FROM email_logs', conn)
        conn.close()
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return send_file(io.BytesIO(buf.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='email_log.csv')

    return jsonify({'error': 'No logs available'}), 404
