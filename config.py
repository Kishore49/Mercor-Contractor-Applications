import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Airtable Configuration
AIRTABLE_CONFIG = {
    'token': os.getenv('AIRTABLE_TOKEN'),
    'base_id': os.getenv('AIRTABLE_BASE_ID'),
    'api_url': f"https://api.airtable.com/v0/{os.getenv('AIRTABLE_BASE_ID')}",
    'headers': {
        'Authorization': f'Bearer {os.getenv("AIRTABLE_TOKEN")}',
        'Content-Type': 'application/json'
    }
}

# Table Names Configuration
TABLE_NAMES = {
    'applicants': 'Applicants',
    'personal': 'Personal Details',
    'experience': 'Work Experience',
    'salary': 'Salary Preferences',
    'shortlisted': 'Shortlisted Leads'
}

# Gemini AI Configuration
GEMINI_CONFIG = {
    'api_key': os.getenv('GEMINI_API_KEY'),
    'model': 'gemini-pro',
    'max_retries': 3,
    'timeout': 30
}

# Shortlisting Criteria
SHORTLIST_CRITERIA = {
    'tier1_companies': [
        'google', 'meta', 'facebook', 'openai', 'apple', 'microsoft',
        'amazon', 'netflix', 'uber', 'airbnb', 'stripe', 'tesla',
        'salesforce', 'adobe', 'nvidia', 'spacex', 'palantir'
    ],
    'qualified_locations': [
        'us', 'usa', 'united states', 'canada', 'uk', 'united kingdom',
        'germany', 'india', 'australia', 'singapore', 'netherlands'
    ],
    'min_experience_years': 4,
    'max_hourly_rate': 100,
    'min_availability_hours': 20
}

# System Settings
SYSTEM_SETTINGS = {
    'max_api_retries': 3,
    'retry_backoff_factor': 2,
    'log_level': 'INFO',
    'log_file': 'mercor_system.log',
    'batch_size': 10,
    'rate_limit_delay': 0.5  # seconds between API calls
}

# LLM Prompt Templates
LLM_PROMPTS = {
    'evaluation': """
You are a recruiting analyst. Given this JSON applicant profile, do four things:

1. Provide a concise 75-word summary highlighting key qualifications and experience.
2. Rate overall candidate quality from 1-10 (higher is better) considering:
   - Technical skills and experience relevance
   - Career progression and achievements  
   - Communication and presentation quality
   - Overall fit for contractor roles

3. List any data gaps or inconsistencies you notice (or 'None' if everything looks good).
4. Suggest up to three follow-up questions to clarify gaps or get more details.

Applicant Profile JSON:
{profile_json}

Return exactly in this format:
Summary: <75-word summary>
Score: <integer 1-10>
Issues: <comma-separated list or 'None'>
Follow-Ups: 
• <question 1>
• <question 2>
• <question 3>
""",
    
    'enrichment': """
Based on this contractor application, suggest 3 relevant skills or technologies 
they should highlight, and 2 potential project types they'd be good for:

{profile_json}

Return as:
Suggested Skills: <skill1>, <skill2>, <skill3>
Project Types: <type1>, <type2>
"""
}

# Validation Rules
VALIDATION_RULES = {
    'email_required': True,
    'name_min_length': 2,
    'experience_required': True,
    'salary_range_required': True,
    'location_required': True,
    'linkedin_format_check': True
}

# Data Export Settings
EXPORT_SETTINGS = {
    'json_indent': 2,
    'include_metadata': True,
    'date_format': '%Y-%m-%d',
    'currency_symbol': '$'
}

def validate_config():
    """Validate that all required configuration is present"""
    required_env_vars = [
        'AIRTABLE_TOKEN',
        'AIRTABLE_BASE_ID', 
        'GEMINI_API_KEY'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

def get_table_mapping():
    """Get table name to ID mapping for Airtable API calls"""
    return {
        name: TABLE_NAMES[key] 
        for key, name in TABLE_NAMES.items()
    }

def get_shortlist_companies():
    """Get list of tier-1 companies for shortlisting"""
    return SHORTLIST_CRITERIA['tier1_companies']

def get_qualified_locations():
    """Get list of qualified locations for shortlisting"""
    return SHORTLIST_CRITERIA['qualified_locations']