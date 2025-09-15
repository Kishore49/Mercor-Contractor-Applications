# Mercor Contractor Management System

Automates contractor application processing using Airtable + AI evaluation.

## Quick Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Airtable
- Create base called "Mercor Contractor Applications"
- Create 5 tables: `Applicants`, `Personal Details`, `Work Experience`, `Salary Preferences`, `Shortlisted Leads`
- Get API token from Developer Hub
- Get Base ID 

### 3. Get Gemini AI Key
- Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
- Create API key

### 4. Configure Environment

Edit `.env` with your keys:
```bash
AIRTABLE_TOKEN="airtable_token_api"
AIRTABLE_BASE_ID="base_id_airtable"
GEMINI_API_KEY="gemini_api_key" 
```

### 5. Validate Setup
```bash
python setup.py
```

### 6. Run Application
```bash
python main.py
```

## How It Works

1. **Add contractor data** to Airtable tables (Personal Details, Work Experience, Salary Preferences)
2. **Run the script** to process applications
3. **System automatically:**
   - Compresses data into JSON format
   - Evaluates candidates for shortlisting
   - Uses AI to score and summarize applications
   - Updates all fields in Airtable

## Shortlist Criteria

Candidates must meet ALL criteria:
- **Experience:** 4+ years OR worked at tier-1 company (Google, Meta, etc.)
- **Rate:** ≤$100/hour preferred rate
- **Availability:** ≥20 hours/week
- **Location:** US, Canada, UK, Germany, or India

## Menu Options

1. **Compress Data** - Convert tables to JSON
2. **Decompress Data** - Extract JSON back to tables  
3. **Process Shortlist** - Run qualification rules
4. **LLM Evaluation** - AI analysis with Gemini
5. **Full Processing** - Complete pipeline for one applicant
6. **Batch Processing** - Process all applicants
7. **View Stats** - System statistics
8. **Exit**

## Files

- `main.py` - Complete application
- `config.py` - Settings and criteria  
- `setup.py` - Connection testing
- `requirements.txt` - Dependencies
- `.env` - Your API keys (create from .env.example)

## Troubleshooting

**"Invalid API token"**
- Check AIRTABLE_TOKEN in .env file

**"Table not found"**  
- Verify table names match exactly (case-sensitive)

**"Gemini API error"**
- Check GEMINI_API_KEY and quota limits

**Processing stuck**
- Run `python setup.py` to test connections
- Check logs for specific errors

## Support

- Run setup validation first: `python setup.py`
- Check system logs for detailed errors
- Verify all environment variables are set correctly
