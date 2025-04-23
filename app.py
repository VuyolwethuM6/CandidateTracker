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

# Define columns for uploaded files with possible variations
# Some columns are required, others are now optional for testing
REQUIRED_COLUMNS = {
    'Candidate ID': ['Candidate ID', 'CandidateID', 'ID', 'Candidate_ID', 'Applicant ID'],
    'First Name': ['First Name', 'FirstName', 'First_Name', 'Name', 'Given Name', 'First'], 
    'Surname': ['Surname', 'Last Name', 'LastName', 'Last_Name', 'Family Name'],
    'South African ID Number': ['South African ID Number', 'SA ID Number', 'ID Number', 'SA_ID', 'National ID', 'Identity Number', 'Please enter your S.A Identity Number'],
    'Age': ['Age', 'Years', 'What is your age?'],
    'Email Address': ['Email Address', 'Email', 'E-mail', 'EmailAddress', 'Contact Email'],
    'Gender': ['Gender', 'Sex', 'What gender group do you belong to?'],
    'Race': ['Race', 'Ethnicity', 'Which racial group do you belong to?']
}

# Make these columns optional for now
OPTIONAL_COLUMNS = {
    'Contact Numbers': ['Contact Numbers', 'Phone', 'Mobile', 'Telephone', 'Contact Number', 'Phone Number', 'Cell Number', 'Primary Contact Number', 'Alternative Contact Number'],
    'Home Language': ['Home Language', 'Language', 'Mother Tongue', 'First Language', 'What is your home language?'],
    'Province and Suburb': ['Province and Suburb', 'Address', 'Location', 'Residence', 'Region', 'Province', 'Suburb', 'Which province are you currently living in?', 'Which suburb are you currently living in?'],
    'Disability Status': ['Disability Status', 'Disability', 'PWD Status', 'PWD', 'Disabled', 'Do you have a disability?'],
    'Highest Qualification': ['Highest Qualification', 'Qualification', 'Education', 'Degree', 'Academic Qualification', 'What is your Highest completed qualification?', 'What was the qualification name?'],
    'NQF Level': ['NQF Level', 'NQF', 'Qualification Level', 'Education Level'], 
    'Qualification Field': ['Qualification Field', 'Field of Study', 'Study Field', 'Discipline', 'Major', 'What was the qualification field of study?'],
    'Institution Name': ['Institution Name', 'Institution', 'University', 'College', 'School', 'Academy'],
    'Employment Status': ['Employment Status', 'Employment', 'Job Status', 'Working Status', 'Employed'],
    'Disability Details': ['If Yes, do you have a valid doctors note to confirm your disability?', 'What is the nature of your disability?'],
    'Other Training': ['What other upskilling programmes have you completed?']
}

# Define target metrics
TOTAL_TARGET = 600  # 600 total candidates target
FEMALE_TARGET_PERCENT = 65  # 65% female target
PWD_TARGET_PERCENT = 5     # 5% PWD target

def check_logo_exists():
    """Check if a custom logo image exists."""
    logo_path = os.path.join('static', 'images', 'logo.png')
    return os.path.exists(logo_path)

@app.route('/')
def home():
    """Render the home dashboard page."""
    return render_template('home.html', logo_image_exists=check_logo_exists())

@app.route('/upload')
def upload():
    """Render the upload page for program data."""
    return render_template('upload.html', logo_image_exists=check_logo_exists())

@app.route('/programs')
def programs():
    """Render the programs page."""
    return render_template('programs.html', logo_image_exists=check_logo_exists())

@app.route('/candidates')
def candidates():
    """Render the candidates management page."""
    return render_template('candidates.html', logo_image_exists=check_logo_exists())

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
        
        # Map column variations to standard column names
        mapped_columns = {}
        missing_standard_columns = []
        
        # Create a dictionary mapping all variations to the standard column names
        all_variations = {}
        for standard_col, variations in REQUIRED_COLUMNS.items():
            for variation in variations:
                all_variations[variation.lower()] = standard_col
        
        # Also add optional columns to all_variations
        for standard_col, variations in OPTIONAL_COLUMNS.items():
            for variation in variations:
                all_variations[variation.lower()] = standard_col
        
        # Check for each required standard column if we can find a matching column in the dataframe
        for standard_col in REQUIRED_COLUMNS.keys():
            found = False
            
            # First check if exact column name exists
            if standard_col in df.columns:
                mapped_columns[standard_col] = standard_col
                found = True
            else:
                # Check for each column in the dataframe if it matches any of our known variations
                for col in df.columns:
                    if col.lower() in all_variations and all_variations[col.lower()] == standard_col:
                        mapped_columns[standard_col] = col
                        found = True
                        break
            
            if not found:
                missing_standard_columns.append(standard_col)
        
        # If required columns are missing, show error
        if missing_standard_columns:
            flash(f'Missing required columns: {", ".join(missing_standard_columns)}', 'danger')
            return redirect(url_for('upload'))
        
        # Create a new dataframe with standardized column names
        standardized_df = pd.DataFrame()
        
        # Copy data from original columns to standardized columns
        for standard_col, original_col in mapped_columns.items():
            standardized_df[standard_col] = df[original_col]
        
        # Check for optional columns
        for standard_col, variations in OPTIONAL_COLUMNS.items():
            for col in df.columns:
                if col in variations or col.lower() in [v.lower() for v in variations]:
                    standardized_df[standard_col] = df[col]
                    break
        
        # Save the standardized data as CSV
        output_path = os.path.join(DATA_DIR, f"{program_name}.csv")
        standardized_df.to_csv(output_path, index=False)
        
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
                
                # Calculate female candidates with fallback
                if 'Gender' in df.columns:
                    female_count = len(df[df['Gender'].str.lower().str.contains('female', na=False)])
                else:
                    female_count = 0
                
                # Calculate PWD candidates with fallback
                if 'Disability Status' in df.columns:
                    pwd_count = len(df[df['Disability Status'].str.lower().str.contains('yes|y', na=False, regex=True)])
                else:
                    pwd_count = 0
                
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
            'nqf_level_counts': {},
            'race_counts': {}
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
            
            # Handle Gender metrics
            if 'Gender' in all_df.columns:
                # Apply a case-insensitive filter to handle variations in 'female'
                metrics['female_count'] = len(all_df[all_df['Gender'].str.lower().str.contains('female', na=False)])
                metrics['male_count'] = len(all_df[all_df['Gender'].str.lower().str.contains('male', na=False)])
            else:
                metrics['female_count'] = 0
                metrics['male_count'] = 0
            
            # Handle Disability Status metrics with graceful fallbacks
            if 'Disability Status' in all_df.columns:
                # Look for "yes" or "y" in disability status
                metrics['pwd_count'] = len(all_df[all_df['Disability Status'].str.lower().str.contains('yes|y', na=False, regex=True)])
            else:
                metrics['pwd_count'] = 0
                
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
            
            # Count candidates by institution (if the column exists)
            if 'Institution Name' in all_df.columns:
                institution_counts = all_df['Institution Name'].value_counts().to_dict()
                metrics['institution_counts'] = {k: v for k, v in sorted(institution_counts.items(), key=lambda item: item[1], reverse=True)[:10]}
            else:
                metrics['institution_counts'] = {"Unknown": metrics['total_candidates']}
            
            # Count candidates by NQF level (if the column exists)
            if 'NQF Level' in all_df.columns:
                nqf_level_counts = all_df['NQF Level'].value_counts().to_dict()
                metrics['nqf_level_counts'] = nqf_level_counts
            else:
                metrics['nqf_level_counts'] = {"Unknown": metrics['total_candidates']}
                
            # Count candidates by race (if the column exists)
            if 'Race' in all_df.columns:
                race_counts = all_df['Race'].value_counts().to_dict()
                metrics['race_counts'] = race_counts
            else:
                metrics['race_counts'] = {"Unknown": metrics['total_candidates']}
        
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
        
        # Find and remove the candidate - check if Candidate ID column exists
        if 'Candidate ID' in df.columns:
            df_filtered = df[df['Candidate ID'] != candidate_id]
            
            if len(df) == len(df_filtered):
                return jsonify({'error': 'Candidate not found in program'}), 404
        else:
            # Try to find a matching column that might be the candidate ID
            id_column = None
            for col in df.columns:
                if "id" in col.lower() or "candidate" in col.lower():
                    id_column = col
                    break
            
            if id_column:
                df_filtered = df[df[id_column] != candidate_id]
                
                if len(df) == len(df_filtered):
                    return jsonify({'error': 'Candidate not found in program'}), 404
            else:
                return jsonify({'error': 'Candidate ID column not found in file'}), 400
        
        # Save the updated CSV
        df_filtered.to_csv(file_path, index=False)
        
        return jsonify({'success': True, 'message': 'Candidate deleted successfully'})
    
    except Exception as e:
        logging.error(f"Error deleting candidate: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/programs/delete', methods=['POST'])
def delete_program():
    """API endpoint to delete an entire program."""
    try:
        data = request.json
        program_name = data.get('program_name')
        
        if not program_name:
            return jsonify({'error': 'Program name is required'}), 400
        
        file_path = os.path.join(DATA_DIR, f"{program_name}.csv")
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Program file not found'}), 404
        
        # Delete the program file
        os.remove(file_path)
        
        return jsonify({'success': True, 'message': f'Program "{program_name}" deleted successfully'})
    
    except Exception as e:
        logging.error(f"Error deleting program: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
