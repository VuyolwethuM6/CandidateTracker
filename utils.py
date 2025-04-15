"""Utility functions for the candidate dashboard application."""

import os
import pandas as pd
import logging

def get_all_data():
    """
    Read and combine all program data files into a single DataFrame.
    
    Returns:
        pd.DataFrame: Combined DataFrame with all candidate data
    """
    try:
        data_dir = './data'
        all_data = []
        
        if not os.path.exists(data_dir):
            return pd.DataFrame()
        
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        
        if not csv_files:
            return pd.DataFrame()
        
        for file in csv_files:
            program_name = os.path.splitext(file)[0]
            try:
                df = pd.read_csv(os.path.join(data_dir, file))
                df['Program'] = program_name
                all_data.append(df)
            except Exception as e:
                logging.error(f"Error reading {file}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
    
    except Exception as e:
        logging.error(f"Error in get_all_data: {str(e)}")
        return pd.DataFrame()

def validate_columns(df, required_columns):
    """
    Validate if DataFrame contains all required columns.
    
    Args:
        df (pd.DataFrame): DataFrame to validate
        required_columns (list): List of required column names
    
    Returns:
        tuple: (is_valid, missing_columns)
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    return len(missing_columns) == 0, missing_columns

def calculate_diversity_metrics(df):
    """
    Calculate diversity metrics from candidate data.
    
    Args:
        df (pd.DataFrame): DataFrame with candidate data
    
    Returns:
        dict: Dictionary with diversity metrics
    """
    if df.empty:
        return {
            'total': 0,
            'female_count': 0,
            'female_percent': 0,
            'pwd_count': 0,
            'pwd_percent': 0
        }
    
    total = len(df)
    female_count = len(df[df['Gender'].str.lower() == 'female'])
    pwd_count = len(df[df['Disability Status'].str.lower() == 'yes'])
    
    female_percent = (female_count / total) * 100 if total > 0 else 0
    pwd_percent = (pwd_count / total) * 100 if total > 0 else 0
    
    return {
        'total': total,
        'female_count': female_count,
        'female_percent': round(female_percent, 2),
        'pwd_count': pwd_count,
        'pwd_percent': round(pwd_percent, 2)
    }
