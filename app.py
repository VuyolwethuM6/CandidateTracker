import os
import logging
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import json
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Create data directory if it doesn't exist
DATA_DIR = './data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Define required columns for uploaded files
REQUIRED_COLUMNS = [
    'Candidate ID', 'First Name', 'Surname', 'South African ID Number', 
    'Age', 'Email Address', 'Contact Numbers', 'Home Language', 
    'Province and Suburb', 'Race', 'Gender', 'Disability Status',
    'Highest Qualification', 'NQF Level', 'Qualification Field', 'Institution Name'
]

# Optional column
OPTIONAL_COLUMNS = ['Employment Status']

# Define target metrics
TOTAL_TARGET = 610
FEMALE_TARGET_PERCENT = 70
PWD_TARGET_PERCENT = 5

@app.route('/')
def home():
    """Render the home dashboard page."""
    return render_template('home.html')

@app.route('/upload')
def upload():
    """Render the upload page for program data."""
    return render_template('upload.html')

@app.route('/programs')
def programs():
    """Render the programs page."""
    return render_template('programs.html')

@app.route('/candidates')
def candidates():
    """Render the candidates management page."""
    return render_template('candidates.html')

@app.route('/upload-program', methods=['POST'])
def upload_program():
    """Handle program data file uploads."""
    if 'program_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('upload'))
    
    program_file = request.files['program_file']
    program_name = request.form.get('program_name', '').strip()
    
    # Validate file and program name
    if program_file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('upload'))
    
    if not program_name:
        flash('Program name is required', 'danger')
        return redirect(url_for('upload'))
    
    # Sanitize program name (alphanumeric with spaces and underscores only)
    if not re.match(r'^[a-zA-Z0-9_\s]+$', program_name):
        flash('Program name contains invalid characters', 'danger')
        return redirect(url_for('upload'))
    
    filename = secure_filename(program_file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Check file extension
    if file_ext not in ['.csv', '.xlsx']:
        flash('Only .csv and .xlsx files are allowed', 'danger')
        return redirect(url_for('upload'))
    
    try:
        # Read the file with pandas
        if file_ext == '.csv':
            df = pd.read_csv(program_file)
        else:  # .xlsx
            df = pd.read_excel(program_file)
        
        # Validate required columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            flash(f'Missing required columns: {", ".join(missing_columns)}', 'danger')
            return redirect(url_for('upload'))
        
        # Save the data as CSV
        output_path = os.path.join(DATA_DIR, f"{program_name}.csv")
        df.to_csv(output_path, index=False)
        
        flash(f'Successfully uploaded data for program: {program_name}', 'success')
        return redirect(url_for('programs'))
    
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        flash(f'Error processing file: {str(e)}', 'danger')
        return redirect(url_for('upload'))

@app.route('/api/programs')
def get_programs():
    """API endpoint to get all programs."""
    try:
        programs = []
        # List all CSV files in the data directory
        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.csv'):
                program_name = os.path.splitext(filename)[0]
                file_path = os.path.join(DATA_DIR, filename)
                
                # Read the CSV file
                df = pd.read_csv(file_path)
                
                # Calculate metrics
                total_candidates = len(df)
                female_count = len(df[df['Gender'].str.lower() == 'female'])
                pwd_count = len(df[df['Disability Status'].str.lower() == 'yes'])
                
                female_percent = (female_count / total_candidates * 100) if total_candidates > 0 else 0
                pwd_percent = (pwd_count / total_candidates * 100) if total_candidates > 0 else 0
                
                programs.append({
                    'name': program_name,
                    'total_candidates': total_candidates,
                    'female_count': female_count,
                    'female_percent': round(female_percent, 2),
                    'pwd_count': pwd_count,
                    'pwd_percent': round(pwd_percent, 2),
                    'meets_female_target': female_percent >= FEMALE_TARGET_PERCENT,
                    'meets_pwd_target': pwd_percent >= PWD_TARGET_PERCENT
                })
        
        return jsonify(programs)
    
    except Exception as e:
        logging.error(f"Error retrieving programs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/program/<program_name>')
def get_program_candidates(program_name):
    """API endpoint to get candidates for a specific program."""
    try:
        file_path = os.path.join(DATA_DIR, f"{program_name}.csv")
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Program not found'}), 404
        
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Convert DataFrame to dict for JSON response
        candidates = df.fillna('').to_dict('records')
        
        return jsonify(candidates)
    
    except Exception as e:
        logging.error(f"Error retrieving program candidates: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/candidates')
def get_all_candidates():
    """API endpoint to get all candidates across all programs."""
    try:
        all_candidates = []
        program_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        
        for file in program_files:
            program_name = os.path.splitext(file)[0]
            file_path = os.path.join(DATA_DIR, file)
            
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Add program column
            df['Program'] = program_name
            
            # Append to all candidates
            all_candidates.append(df)
        
        if all_candidates:
            # Concatenate all DataFrames
            all_df = pd.concat(all_candidates, ignore_index=True)
            
            # Convert DataFrame to dict for JSON response
            candidates = all_df.fillna('').to_dict('records')
            
            return jsonify(candidates)
        else:
            return jsonify([])
    
    except Exception as e:
        logging.error(f"Error retrieving all candidates: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/metrics')
def get_dashboard_metrics():
    """API endpoint to get dashboard metrics."""
    try:
        # Initialize metrics
        metrics = {
            'total_candidates': 0,
            'female_count': 0,
            'male_count': 0,
            'pwd_count': 0,
            'program_counts': {},
            'institution_counts': {},
            'nqf_level_counts': {}
        }
        
        # List all CSV files in the data directory
        program_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        
        if not program_files:
            return jsonify(metrics)
        
        all_candidates = []
        
        for file in program_files:
            program_name = os.path.splitext(file)[0]
            file_path = os.path.join(DATA_DIR, file)
            
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Add program column
            df['Program'] = program_name
            
            # Append to all candidates
            all_candidates.append(df)
        
        # Concatenate all DataFrames
        if all_candidates:
            all_df = pd.concat(all_candidates, ignore_index=True)
            
            # Calculate metrics
            metrics['total_candidates'] = len(all_df)
            metrics['female_count'] = len(all_df[all_df['Gender'].str.lower() == 'female'])
            metrics['male_count'] = len(all_df[all_df['Gender'].str.lower() == 'male'])
            metrics['pwd_count'] = len(all_df[all_df['Disability Status'].str.lower() == 'yes'])
            
            # Calculate female and PWD percentages
            metrics['female_percent'] = round((metrics['female_count'] / metrics['total_candidates'] * 100), 2) if metrics['total_candidates'] > 0 else 0
            metrics['pwd_percent'] = round((metrics['pwd_count'] / metrics['total_candidates'] * 100), 2) if metrics['total_candidates'] > 0 else 0
            
            # Check if targets are met
            metrics['female_target_met'] = metrics['female_percent'] >= FEMALE_TARGET_PERCENT
            metrics['pwd_target_met'] = metrics['pwd_percent'] >= PWD_TARGET_PERCENT
            
            # Calculate progress towards total target
            metrics['total_target'] = TOTAL_TARGET
            metrics['total_percent'] = round((metrics['total_candidates'] / TOTAL_TARGET * 100), 2)
            
            # Count candidates by program
            program_counts = all_df['Program'].value_counts().to_dict()
            metrics['program_counts'] = program_counts
            
            # Count candidates by institution
            institution_counts = all_df['Institution Name'].value_counts().to_dict()
            metrics['institution_counts'] = {k: v for k, v in sorted(institution_counts.items(), key=lambda item: item[1], reverse=True)[:10]}
            
            # Count candidates by NQF level
            nqf_level_counts = all_df['NQF Level'].value_counts().to_dict()
            metrics['nqf_level_counts'] = nqf_level_counts
        
        return jsonify(metrics)
    
    except Exception as e:
        logging.error(f"Error retrieving dashboard metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/candidates/delete', methods=['POST'])
def delete_candidate():
    """API endpoint to delete a candidate."""
    try:
        data = request.json
        candidate_id = data.get('candidate_id')
        program_name = data.get('program')
        
        if not candidate_id or not program_name:
            return jsonify({'error': 'Candidate ID and Program are required'}), 400
        
        file_path = os.path.join(DATA_DIR, f"{program_name}.csv")
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Program file not found'}), 404
        
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Find and remove the candidate
        df_filtered = df[df['Candidate ID'] != candidate_id]
        
        if len(df) == len(df_filtered):
            return jsonify({'error': 'Candidate not found in program'}), 404
        
        # Save the updated CSV
        df_filtered.to_csv(file_path, index=False)
        
        return jsonify({'success': True, 'message': 'Candidate deleted successfully'})
    
    except Exception as e:
        logging.error(f"Error deleting candidate: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
