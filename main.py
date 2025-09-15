import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Configuration
AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Airtable API configuration
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_TOKEN}',
    'Content-Type': 'application/json'
}

# Table names
TABLES = {
    'applicants': 'Applicants',
    'personal': 'Personal Details',
    'experience': 'Work Experience',
    'salary': 'Salary Preferences',
    'shortlisted': 'Shortlisted Leads'
}

# Tier-1 companies for shortlisting
TIER1_COMPANIES = [
    'google', 'meta', 'facebook', 'openai', 'apple', 'microsoft', 
    'amazon', 'netflix', 'uber', 'airbnb', 'stripe', 'tesla'
]

# Qualified locations
QUALIFIED_LOCATIONS = ['us', 'usa', 'united states', 'canada', 'uk', 'united kingdom', 'germany', 'india']

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mercor_system.log'),
        logging.StreamHandler()
    ]
)

class MercorAirtableSystem:
    def __init__(self):
        self.validate_config()
        self.setup_gemini()
    
    def validate_config(self):
        """Validate that all required environment variables are set"""
        required_vars = ['AIRTABLE_TOKEN', 'AIRTABLE_BASE_ID', 'GEMINI_API_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        
        logging.info("Configuration validated successfully")
    
    def setup_gemini(self):
        """Initialize Gemini AI client"""
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            logging.info("Gemini AI configured successfully")
        except Exception as e:
            logging.error(f"Failed to setup Gemini AI: {e}")
            raise
    
    def airtable_request(self, method: str, endpoint: str, data: Dict = None, max_retries: int = 3) -> Dict:
        """Make request to Airtable API with retry logic"""
        url = f"{AIRTABLE_API_URL}/{endpoint}"
        
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=HEADERS)
                elif method == 'POST':
                    response = requests.post(url, headers=HEADERS, json=data)
                elif method == 'PATCH':
                    response = requests.patch(url, headers=HEADERS, json=data)
                elif method == 'PUT':
                    response = requests.put(url, headers=HEADERS, json=data)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logging.error(f"API request failed after {max_retries} attempts: {e}")
                    raise
                
                wait_time = 2 ** attempt
                logging.warning(f"Request failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def get_all_records(self, table_name: str) -> List[Dict]:
        """Get all records from a table with pagination"""
        all_records = []
        offset = None
        
        while True:
            endpoint = table_name
            if offset:
                endpoint += f"?offset={offset}"
            
            response = self.airtable_request('GET', endpoint)
            all_records.extend(response.get('records', []))
            
            offset = response.get('offset')
            if not offset:
                break
        
        logging.info(f"Retrieved {len(all_records)} records from {table_name}")
        return all_records
    
    def get_applicant_data(self, applicant_id: str) -> Dict:
        """Get all data for a specific applicant"""
        try:
            personal_records = self.get_all_records(TABLES['personal'])
            personal = next((r for r in personal_records 
                           if applicant_id in r.get('fields', {}).get('Applicant ID', [])), None)
            
            experience_records = self.get_all_records(TABLES['experience'])
            experience = [r for r in experience_records 
                         if applicant_id in r.get('fields', {}).get('Applicant ID', [])]
            
            salary_records = self.get_all_records(TABLES['salary'])
            salary = next((r for r in salary_records 
                          if applicant_id in r.get('fields', {}).get('Applicant ID', [])), None)
            
            return {
                'personal': personal,
                'experience': experience,
                'salary': salary
            }
        except Exception as e:
            logging.error(f"Error getting applicant data for {applicant_id}: {e}")
            return {}
    
    def compress_to_json(self, applicant_id: str) -> Dict:
        """Compress applicant data into JSON format"""
        try:
            data = self.get_applicant_data(applicant_id)
            
            compressed = {}
            
            if data['personal']:
                personal_fields = data['personal']['fields']
                compressed['personal'] = {
                    'name': personal_fields.get('Full Name', ''),
                    'email': personal_fields.get('Email', ''),
                    'location': personal_fields.get('Location', ''),
                    'linkedin': personal_fields.get('LinkedIn', '')
                }
            
            compressed['experience'] = []
            for exp in data['experience']:
                exp_fields = exp['fields']
                compressed['experience'].append({
                    'company': exp_fields.get('Company', ''),
                    'title': exp_fields.get('Title', ''),
                    'start': exp_fields.get('Start Date', ''),
                    'end': exp_fields.get('End Date', ''),
                    'technologies': exp_fields.get('Technologies', '')
                })
            
            if data['salary']:
                salary_fields = data['salary']['fields']
                compressed['salary'] = {
                    'preferred_rate': salary_fields.get('Preferred Rate', 0),
                    'minimum_rate': salary_fields.get('Minimum Rate', 0),
                    'currency': salary_fields.get('Currency', 'USD'),
                    'availability': salary_fields.get('Availability', 0)
                }
            
            logging.info(f"Compressed data for applicant {applicant_id}")
            return compressed
            
        except Exception as e:
            logging.error(f"Error compressing data for {applicant_id}: {e}")
            return {}
    
    def decompress_from_json(self, applicant_id: str, compressed_json: str) -> bool:
        """Decompress JSON back to normalized tables"""
        try:
            data = json.loads(compressed_json)
            
            if 'personal' in data:
                personal_data = {
                    'fields': {
                        'Applicant ID': [applicant_id],
                        'Full Name': data['personal'].get('name', ''),
                        'Email': data['personal'].get('email', ''),
                        'Location': data['personal'].get('location', ''),
                        'LinkedIn': data['personal'].get('linkedin', '')
                    }
                }
                
                existing = self.get_all_records(TABLES['personal'])
                existing_record = next((r for r in existing 
                                      if applicant_id in r.get('fields', {}).get('Applicant ID', [])), None)
                
                if existing_record:
                    self.airtable_request('PATCH', f"{TABLES['personal']}/{existing_record['id']}", 
                                        {'fields': personal_data['fields']})
                else:
                    self.airtable_request('POST', TABLES['personal'], personal_data)
            
            if 'experience' in data:
                existing_exp = self.get_all_records(TABLES['experience'])
                for exp in existing_exp:
                    if applicant_id in exp.get('fields', {}).get('Applicant ID', []):
                        requests.delete(f"{AIRTABLE_API_URL}/{TABLES['experience']}/{exp['id']}", 
                                      headers=HEADERS)
                
                for exp in data['experience']:
                    exp_data = {
                        'fields': {
                            'Applicant ID': [applicant_id],
                            'Company': exp.get('company', ''),
                            'Title': exp.get('title', ''),
                            'Start Date': exp.get('start', ''),
                            'End Date': exp.get('end', ''),
                            'Technologies': exp.get('technologies', '')
                        }
                    }
                    self.airtable_request('POST', TABLES['experience'], exp_data)
            
            if 'salary' in data:
                salary_data = {
                    'fields': {
                        'Applicant ID': [applicant_id],
                        'Preferred Rate': data['salary'].get('preferred_rate', 0),
                        'Minimum Rate': data['salary'].get('minimum_rate', 0),
                        'Currency': data['salary'].get('currency', 'USD'),
                        'Availability': data['salary'].get('availability', 0)
                    }
                }
                
                existing = self.get_all_records(TABLES['salary'])
                existing_record = next((r for r in existing 
                                      if applicant_id in r.get('fields', {}).get('Applicant ID', [])), None)
                
                if existing_record:
                    self.airtable_request('PATCH', f"{TABLES['salary']}/{existing_record['id']}", 
                                        {'fields': salary_data['fields']})
                else:
                    self.airtable_request('POST', TABLES['salary'], salary_data)
            
            logging.info(f"Decompressed data for applicant {applicant_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error decompressing data for {applicant_id}: {e}")
            return False
    
    def calculate_experience_years(self, experience: List[Dict]) -> float:
        """Calculate total years of experience"""
        total_months = 0
        
        for exp in experience:
            try:
                start_date = datetime.strptime(exp.get('start', ''), '%Y-%m-%d')
                end_str = exp.get('end', '')
                
                if end_str and end_str.lower() != 'present':
                    end_date = datetime.strptime(end_str, '%Y-%m-%d')
                else:
                    end_date = datetime.now()
                
                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                total_months += max(0, months)
                
            except ValueError:
                continue
        
        return total_months / 12.0
    
    def has_tier1_experience(self, experience: List[Dict]) -> bool:
        """Check if candidate has tier-1 company experience"""
        for exp in experience:
            company = exp.get('company', '').lower()
            if any(tier1 in company for tier1 in TIER1_COMPANIES):
                return True
        return False
    
    def evaluate_shortlist_criteria(self, compressed_json: str) -> tuple[bool, str]:
        """Evaluate if candidate meets shortlist criteria"""
        try:
            data = json.loads(compressed_json)
            reasons = []
            
            experience_years = self.calculate_experience_years(data.get('experience', []))
            has_tier1 = self.has_tier1_experience(data.get('experience', []))
            
            experience_passed = experience_years >= 4 or has_tier1
            if experience_passed:
                if experience_years >= 4:
                    reasons.append(f"{experience_years:.1f} years experience")
                if has_tier1:
                    reasons.append("Tier-1 company experience")
            
            salary = data.get('salary', {})
            preferred_rate = salary.get('preferred_rate', 0)
            availability = salary.get('availability', 0)
            
            compensation_passed = preferred_rate <= 100 and availability >= 20
            if compensation_passed:
                reasons.append(f"Rate ${preferred_rate}/hr, {availability}hrs/week available")
            
            location = data.get('personal', {}).get('location', '').lower()
            location_passed = any(qual_loc in location for qual_loc in QUALIFIED_LOCATIONS)
            if location_passed:
                reasons.append(f"Located in {location}")
            
            passed = experience_passed and compensation_passed and location_passed
            reason = f"{'QUALIFIED' if passed else 'NOT QUALIFIED'}: {'; '.join(reasons)}"
            
            return passed, reason
            
        except Exception as e:
            logging.error(f"Error evaluating shortlist criteria: {e}")
            return False, "Error in evaluation"
    
    def process_shortlist(self, applicant_id: str) -> bool:
        """Process shortlist evaluation for an applicant"""
        try:
            applicants = self.get_all_records(TABLES['applicants'])
            applicant = next((a for a in applicants if a['fields'].get('Applicant ID') == applicant_id), None)
            
            if not applicant:
                logging.error(f"Applicant {applicant_id} not found")
                return False
            
            compressed_json = applicant['fields'].get('Compressed JSON', '')
            if not compressed_json:
                logging.warning(f"No compressed JSON found for {applicant_id}")
                return False
            
            passed, reason = self.evaluate_shortlist_criteria(compressed_json)
            
            status = 'Shortlisted' if passed else 'Not Qualified'
            self.airtable_request('PATCH', f"{TABLES['applicants']}/{applicant['id']}", {
                'fields': {'Shortlist Status': status}
            })
            
            if passed:
                shortlist_data = {
                    'fields': {
                        'Applicant': [applicant['id']],
                        'Compressed JSON': compressed_json,
                        'Score Reason': reason
                    }
                }
                self.airtable_request('POST', TABLES['shortlisted'], shortlist_data)
                logging.info(f"Created shortlisted lead for {applicant_id}")
            
            logging.info(f"Shortlist processed for {applicant_id}: {status} - {reason}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing shortlist for {applicant_id}: {e}")
            return False
    
    def llm_evaluation(self, applicant_id: str, compressed_json: str) -> Dict:
        """Evaluate applicant using Gemini LLM"""
        prompt = f"""
You are a recruiting analyst. Given this JSON applicant profile, do four things:

1. Provide a concise 75-word summary.
2. Rate overall candidate quality from 1-10 (higher is better).
3. List any data gaps or inconsistencies you notice.
4. Suggest up to three follow-up questions to clarify gaps.

Applicant Profile JSON:
{compressed_json}

Return exactly in this format:
Summary: <text>
Score: <integer>
Issues: <comma-separated list or 'None'>
Follow-Ups: <bullet list>
"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.gemini_model.generate_content(prompt)
                
                if response.text:
                    lines = response.text.strip().split('\n')
                    result = {'summary': '', 'score': 0, 'issues': '', 'follow_ups': ''}
                    
                    for line in lines:
                        if line.startswith('Summary:'):
                            result['summary'] = line.replace('Summary:', '').strip()
                        elif line.startswith('Score:'):
                            try:
                                result['score'] = int(line.replace('Score:', '').strip())
                            except ValueError:
                                result['score'] = 5
                        elif line.startswith('Issues:'):
                            result['issues'] = line.replace('Issues:', '').strip()
                        elif line.startswith('Follow-Ups:'):
                            result['follow_ups'] = line.replace('Follow-Ups:', '').strip()
                        elif line.startswith('•') or line.startswith('-'):
                            result['follow_ups'] += '\n' + line.strip()
                    
                    logging.info(f"LLM evaluation completed for {applicant_id}")
                    return result
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"LLM evaluation failed after {max_retries} attempts: {e}")
                    return {
                        'summary': 'LLM evaluation failed',
                        'score': 0,
                        'issues': 'API error',
                        'follow_ups': 'Retry evaluation'
                    }
                
                wait_time = 2 ** attempt
                logging.warning(f"LLM request failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def process_llm_evaluation(self, applicant_id: str) -> bool:
        """Process LLM evaluation for an applicant"""
        try:
            applicants = self.get_all_records(TABLES['applicants'])
            applicant = next((a for a in applicants if a['fields'].get('Applicant ID') == applicant_id), None)
            
            if not applicant:
                logging.error(f"Applicant {applicant_id} not found")
                return False
            
            compressed_json = applicant['fields'].get('Compressed JSON', '')
            if not compressed_json:
                logging.warning(f"No compressed JSON found for {applicant_id}")
                return False
            
            evaluation = self.llm_evaluation(applicant_id, compressed_json)
            
            self.airtable_request('PATCH', f"{TABLES['applicants']}/{applicant['id']}", {
                'fields': {
                    'LLM Summary': evaluation['summary'],
                    'LLM Score': evaluation['score'],
                    'LLM Follow-Ups': evaluation['follow_ups']
                }
            })
            
            logging.info(f"LLM evaluation updated for {applicant_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing LLM evaluation for {applicant_id}: {e}")
            return False
    
    def process_all_applicants(self) -> Dict[str, int]:
        """Process all applicants through the complete pipeline"""
        results = {
            'compressed': 0,
            'shortlisted': 0,
            'llm_evaluated': 0,
            'errors': 0
        }
        
        try:
            applicants = self.get_all_records(TABLES['applicants'])
            
            for applicant in applicants:
                applicant_id = applicant['fields'].get('Applicant ID')
                if not applicant_id:
                    continue
                
                try:
                    compressed_data = self.compress_to_json(applicant_id)
                    if compressed_data:
                        compressed_json = json.dumps(compressed_data)
                        
                        self.airtable_request('PATCH', f"{TABLES['applicants']}/{applicant['id']}", {
                            'fields': {'Compressed JSON': compressed_json}
                        })
                        results['compressed'] += 1
                        
                        if self.process_shortlist(applicant_id):
                            results['shortlisted'] += 1
                        
                        if self.process_llm_evaluation(applicant_id):
                            results['llm_evaluated'] += 1
                
                except Exception as e:
                    logging.error(f"Error processing applicant {applicant_id}: {e}")
                    results['errors'] += 1
            
            logging.info(f"Batch processing completed: {results}")
            return results
            
        except Exception as e:
            logging.error(f"Error in batch processing: {e}")
            results['errors'] += 1
            return results
    
    def interactive_menu(self):
        """Interactive menu for system operations"""
        while True:
            print("\n" + "="*50)
            print("MERCOR CONTRACTOR MANAGEMENT SYSTEM")
            print("="*50)
            print("1. Compress Data for Applicant")
            print("2. Decompress Data for Applicant")
            print("3. Process Shortlist for Applicant")
            print("4. LLM Evaluation for Applicant")
            print("5. Full Processing for Applicant")
            print("6. Process All Applicants (Batch)")
            print("7. View System Stats")
            print("8. Exit")
            print("-"*50)
            
            choice = input("Enter your choice (1-8): ").strip()
            
            if choice == '1':
                applicant_id = input("Enter Applicant ID: ").strip()
                if applicant_id:
                    compressed_data = self.compress_to_json(applicant_id)
                    if compressed_data:
                        applicants = self.get_all_records(TABLES['applicants'])
                        applicant = next((a for a in applicants if a['fields'].get('Applicant ID') == applicant_id), None)
                        
                        if applicant:
                            self.airtable_request('PATCH', f"{TABLES['applicants']}/{applicant['id']}", {
                                'fields': {'Compressed JSON': json.dumps(compressed_data)}
                            })
                            print(f"Data compressed successfully for {applicant_id}")
                        else:
                            print(f"Applicant {applicant_id} not found")
                    else:
                        print(f"Failed to compress data for {applicant_id}")
            
            elif choice == '2':
                applicant_id = input("Enter Applicant ID: ").strip()
                if applicant_id:
                    applicants = self.get_all_records(TABLES['applicants'])
                    applicant = next((a for a in applicants if a['fields'].get('Applicant ID') == applicant_id), None)
                    
                    if applicant and applicant['fields'].get('Compressed JSON'):
                        if self.decompress_from_json(applicant_id, applicant['fields']['Compressed JSON']):
                            print(f"Data decompressed successfully for {applicant_id}")
                        else:
                            print(f"Failed to decompress data for {applicant_id}")
                    else:
                        print(f"No compressed data found for {applicant_id}")
            
            elif choice == '3':
                applicant_id = input("Enter Applicant ID: ").strip()
                if applicant_id:
                    if self.process_shortlist(applicant_id):
                        print(f"Shortlist processed successfully for {applicant_id}")
                    else:
                        print(f"Failed to process shortlist for {applicant_id}")
            
            elif choice == '4':
                applicant_id = input("Enter Applicant ID: ").strip()
                if applicant_id:
                    if self.process_llm_evaluation(applicant_id):
                        print(f"LLM evaluation completed for {applicant_id}")
                    else:
                        print(f"Failed to complete LLM evaluation for {applicant_id}")
            
            elif choice == '5':
                applicant_id = input("Enter Applicant ID: ").strip()
                if applicant_id:
                    print(f"Processing {applicant_id}...")
                    
                    compressed_data = self.compress_to_json(applicant_id)
                    if compressed_data:
                        applicants = self.get_all_records(TABLES['applicants'])
                        applicant = next((a for a in applicants if a['fields'].get('Applicant ID') == applicant_id), None)
                        
                        if applicant:
                            self.airtable_request('PATCH', f"{TABLES['applicants']}/{applicant['id']}", {
                                'fields': {'Compressed JSON': json.dumps(compressed_data)}
                            })
                            
                            shortlist_success = self.process_shortlist(applicant_id)
                            llm_success = self.process_llm_evaluation(applicant_id)
                            
                            print(f"Full processing completed for {applicant_id}")
                            print(f"   - Data compressed: Success")
                            print(f"   - Shortlist processed: {'Success' if shortlist_success else 'Failed'}")
                            print(f"   - LLM evaluation: {'Success' if llm_success else 'Failed'}")
                        else:
                            print(f"Applicant {applicant_id} not found")
                    else:
                        print(f"Failed to compress data for {applicant_id}")
            
            elif choice == '6':
                print("Processing all applicants... This may take a while.")
                results = self.process_all_applicants()
                print("\nBatch Processing Results:")
                print(f"   - Compressed: {results['compressed']}")
                print(f"   - Shortlisted: {results['shortlisted']}")
                print(f"   - LLM Evaluated: {results['llm_evaluated']}")
                print(f"   - Errors: {results['errors']}")
            
            elif choice == '7':
                self.show_system_stats()
            
            elif choice == '8':
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please enter 1-8.")
    
    def show_system_stats(self):
        """Show system statistics"""
        try:
            print("\nSYSTEM STATISTICS")
            print("-"*30)
            
            applicants = self.get_all_records(TABLES['applicants'])
            personal = self.get_all_records(TABLES['personal'])
            experience = self.get_all_records(TABLES['experience'])
            salary = self.get_all_records(TABLES['salary'])
            shortlisted = self.get_all_records(TABLES['shortlisted'])
            
            print(f"Total Applicants: {len(applicants)}")
            print(f"Personal Details: {len(personal)}")
            print(f"Work Experience Records: {len(experience)}")
            print(f"Salary Preferences: {len(salary)}")
            print(f"Shortlisted Candidates: {len(shortlisted)}")
            
            compressed_count = sum(1 for a in applicants if a['fields'].get('Compressed JSON'))
            shortlisted_count = sum(1 for a in applicants if a['fields'].get('Shortlist Status') == 'Shortlisted')
            llm_evaluated = sum(1 for a in applicants if a['fields'].get('LLM Summary'))
            
            print(f"\nProcessing Status:")
            print(f"- Compressed JSON: {compressed_count}/{len(applicants)}")
            print(f"- Shortlisted: {shortlisted_count}/{len(applicants)}")
            print(f"- LLM Evaluated: {llm_evaluated}/{len(applicants)}")
            
            scores = [a['fields'].get('LLM Score', 0) for a in applicants if a['fields'].get('LLM Score')]
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"- Average LLM Score: {avg_score:.1f}/10")
            
        except Exception as e:
            print(f"Error getting system stats: {e}")


def main():
    """Main function to run the system"""
    try:
        print("Starting Mercor Contractor Management System...")
        
        system = MercorAirtableSystem()
        system.interactive_menu()
        
    except KeyboardInterrupt:
        print("\n\nSystem interrupted by user. Goodbye!")
    except Exception as e:
        logging.error(f"System error: {e}")
        print(f"System error: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()