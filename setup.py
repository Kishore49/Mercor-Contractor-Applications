#!/usr/bin/env python3
"""
Setup and validation script for Mercor Contractor Management System
Run this first to validate your configuration and test API connections
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
import google.generativeai as genai

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_status(message, status):
    """Print status message"""
    status_text = "PASS" if status else "FAIL"
    print(f"[{status_text}] {message}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("CHECKING ENVIRONMENT CONFIGURATION")
    
    if not os.path.exists('.env'):
        print_status(".env file exists", False)
        print("\nPlease create a .env file using .env.example as template:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your actual API keys and tokens")
        return False
    
    print_status(".env file exists", True)
    
    load_dotenv()
    
    required_vars = {
        'AIRTABLE_TOKEN': 'Airtable API Token',
        'AIRTABLE_BASE_ID': 'Airtable Base ID', 
        'GEMINI_API_KEY': 'Google Gemini API Key'
    }
    
    all_present = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        has_value = bool(value and value.strip())
        print_status(f"{description} configured", has_value)
        
        if has_value and var == 'AIRTABLE_TOKEN':
            print(f"   Token starts with: {value[:10]}...")
        elif has_value and var == 'AIRTABLE_BASE_ID':
            print(f"   Base ID: {value}")
        elif has_value and var == 'GEMINI_API_KEY':
            print(f"   API key starts with: {value[:15]}...")
            
        all_present = all_present and has_value
    
    return all_present

def test_airtable_connection():
    """Test Airtable API connection"""
    print_header("TESTING AIRTABLE CONNECTION")
    
    token = os.getenv('AIRTABLE_TOKEN')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not token or not base_id:
        print_status("Airtable credentials available", False)
        return False
    
    try:
        url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print_status("Airtable API connection", True)
            
            tables = response.json().get('tables', [])
            print(f"\nFound {len(tables)} tables in base:")
            for table in tables:
                print(f"   - {table['name']} ({table['id']})")
            
            table_names = [table['name'] for table in tables]
            required_tables = [
                'Applicants', 'Personal Details', 'Work Experience', 
                'Salary Preferences', 'Shortlisted Leads'
            ]
            
            print(f"\nChecking required tables:")
            all_tables_present = True
            for req_table in required_tables:
                present = req_table in table_names
                print_status(f"Table '{req_table}' exists", present)
                all_tables_present = all_tables_present and present
            
            return all_tables_present
            
        elif response.status_code == 401:
            print_status("Airtable API connection", False)
            print("   Authentication failed - check your API token")
            return False
        elif response.status_code == 404:
            print_status("Airtable API connection", False)
            print("   Base not found - check your Base ID")
            return False
        else:
            print_status("Airtable API connection", False)
            print(f"   HTTP {response.status_code}: {response.text[:100]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_status("Airtable API connection", False)
        print(f"   Connection error: {e}")
        return False

def test_gemini_connection():
    """Test Google Gemini AI connection"""
    print_header("TESTING GEMINI AI CONNECTION")
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print_status("Gemini API key available", False)
        return False
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        test_prompt = "Please respond with just the word 'SUCCESS' if you can read this."
        response = model.generate_content(test_prompt)
        
        if response and response.text:
            print_status("Gemini AI connection", True)
            print(f"   Response: {response.text.strip()}")
            return True
        else:
            print_status("Gemini AI connection", False)
            print("   No response received")
            return False
            
    except Exception as e:
        print_status("Gemini AI connection", False)
        print(f"   Error: {e}")
        return False

def test_sample_data_processing():
    """Test the data processing with sample data"""
    print_header("TESTING DATA PROCESSING")
    
    sample_data = {
        "personal": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "location": "San Francisco, CA, US",
            "linkedin": "https://linkedin.com/in/johndoe"
        },
        "experience": [
            {
                "company": "Google",
                "title": "Software Engineer",
                "start": "2020-01-01",
                "end": "2023-12-31",
                "technologies": "Python, JavaScript, React"
            }
        ],
        "salary": {
            "preferred_rate": 85,
            "minimum_rate": 70,
            "currency": "USD",
            "availability": 30
        }
    }
    
    try:
        json_str = json.dumps(sample_data, indent=2)
        print_status("JSON serialization", True)
        
        parsed_data = json.loads(json_str)
        print_status("JSON deserialization", True)
        
        has_tier1 = any('google' in exp['company'].lower() for exp in parsed_data['experience'])
        rate_ok = parsed_data['salary']['preferred_rate'] <= 100
        availability_ok = parsed_data['salary']['availability'] >= 20
        location_ok = 'us' in parsed_data['personal']['location'].lower()
        
        criteria_met = has_tier1 and rate_ok and availability_ok and location_ok
        
        print_status("Shortlist criteria evaluation", True)
        print(f"   - Tier-1 company: {'PASS' if has_tier1 else 'FAIL'}")
        print(f"   - Rate <= $100/hr: {'PASS' if rate_ok else 'FAIL'}")
        print(f"   - Availability >= 20hrs: {'PASS' if availability_ok else 'FAIL'}")
        print(f"   - Qualified location: {'PASS' if location_ok else 'FAIL'}")
        print(f"   - Would be shortlisted: {'PASS' if criteria_met else 'FAIL'}")
        
        return True
        
    except Exception as e:
        print_status("Data processing test", False)
        print(f"   Error: {e}")
        return False

def create_sample_applicant():
    """Create a sample applicant for testing"""
    print_header("CREATING SAMPLE TEST DATA")
    
    token = os.getenv('AIRTABLE_TOKEN')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not token or not base_id:
        print_status("Cannot create sample data - missing credentials", False)
        return False
    
    try:
        api_url = f"https://api.airtable.com/v0/{base_id}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        applicant_data = {
            'fields': {
                'Applicant ID': f'TEST-{int(time.time())}',
                'Shortlist Status': 'Pending'
            }
        }
        
        response = requests.post(f"{api_url}/Applicants", headers=headers, json=applicant_data)
        
        if response.status_code == 200:
            applicant = response.json()
            applicant_id = applicant['fields']['Applicant ID']
            print_status(f"Sample applicant created: {applicant_id}", True)
            
            print("\nTo complete the test:")
            print("   1. Add personal details, work experience, and salary preferences")
            print("   2. Run the main.py script to process this applicant")
            print("   3. Check the results in your Airtable base")
            
            return True
        else:
            print_status("Sample applicant creation", False)
            print(f"   HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_status("Sample applicant creation", False)
        print(f"   Error: {e}")
        return False

def main():
    """Main setup and validation function"""
    print_header("MERCOR CONTRACTOR SYSTEM SETUP & VALIDATION")
    print("This script will validate your configuration and test all connections.")
    
    if not check_env_file():
        print("\nSetup incomplete. Please configure your .env file first.")
        return False
    
    airtable_ok = test_airtable_connection()
    gemini_ok = test_gemini_connection()
    processing_ok = test_sample_data_processing()
    
    print_header("SETUP SUMMARY")
    
    all_systems_ok = airtable_ok and gemini_ok and processing_ok
    
    if all_systems_ok:
        print("All systems are working correctly!")
        print("\nYou're ready to run the main application:")
        print("   python main.py")
        
        create_sample = input("\nWould you like to create sample test data? (y/n): ").lower().strip()
        if create_sample in ['y', 'yes']:
            create_sample_applicant()
    
    else:
        print("Some systems need attention before you can proceed:")
        if not airtable_ok:
            print("   - Fix Airtable connection issues")
        if not gemini_ok:
            print("   - Fix Gemini AI connection issues") 
        if not processing_ok:
            print("   - Fix data processing issues")
    
    return all_systems_ok

if __name__ == "__main__":
    import time
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
    except Exception as e:
        print(f"\nSetup failed with error: {e}")
        sys.exit(1)