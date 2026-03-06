import requests
import csv
from datetime import datetime
import time
import os
from dotenv import load_dotenv
#pip install requests python-dotenv


class AdzunaJobFetcher:
    """
    Fetches job data from Adzuna API and exports to CSV.
    
    Usage:
        1. Register at https://developer.adzuna.com/signup to get your API credentials
        2. Create a .env.local file in the same directory as this script
        3. Add your credentials to .env.local:
           ADZUNA_APP_ID=your_app_id_here
           ADZUNA_APP_KEY=your_app_key_here
        4. Install python-dotenv: pip install python-dotenv
        5. Run the script
    """
    
    def __init__(self, app_id, app_key, country='us'):
        """
        Initialize the Adzuna API client.
        
        Args:
            app_id (str): Your Adzuna app ID
            app_key (str): Your Adzuna app key
            country (str): Country code (default: 'us')
        """
        self.app_id = app_id
        self.app_key = app_key
        self.country = country
        self.base_url = f'https://api.adzuna.com/v1/api/jobs/{country}/search'
    
    def search_jobs(self, what='', where='', results_per_page=50, page=1, **kwargs):
        """
        Search for jobs using the Adzuna API.
        
        Args:
            what (str): Keywords to search for (e.g., 'python developer')
            where (str): Location to search in (e.g., 'New York')
            results_per_page (int): Number of results per page (max 50)
            page (int): Page number to fetch
            **kwargs: Additional API parameters (sort_by, max_days_old, etc.)
        
        Returns:
            dict: API response containing job listings
        """
        url = f'{self.base_url}/{page}'
        
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'results_per_page': results_per_page,
            'content-type': 'application/json'
        }
        
        if what:
            params['what'] = what
        if where:
            params['where'] = where
        
        # Add any additional parameters
        params.update(kwargs)
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None
    
    def parse_job_data(self, job):
        """
        Parse job data and extract required fields.
        
        Args:
            job (dict): Job data from API response
        
        Returns:
            dict: Parsed job data with standardized fields
        """
        # Extract date posted (created field)
        date_posted = job.get('created', '')
        if date_posted:
            try:
                # Convert ISO format to readable date
                dt = datetime.fromisoformat(date_posted.replace('Z', '+00:00'))
                date_posted = dt.strftime('%Y-%m-%d')
            except:
                pass
        
        # Extract company name
        company = ''
        if job.get('company'):
            company = job['company'].get('display_name', '')
        
        # Extract job type (contract_type)
        job_type = job.get('contract_type', '')
        
        # Extract expected start date (if available in contract_time)
        expected_start_date = job.get('contract_time', '')
        
        # Extract salary range
        salary_min = job.get('salary_min', '')
        salary_max = job.get('salary_max', '')
        salary_range = ''
        if salary_min and salary_max:
            salary_range = f"${salary_min:,.0f} - ${salary_max:,.0f}"
        elif salary_min:
            salary_range = f"${salary_min:,.0f}+"
        elif salary_max:
            salary_range = f"Up to ${salary_max:,.0f}"
        
        # Extract job description
        job_description = job.get('description', '')
        # Clean up description (remove excessive whitespace)
        if job_description:
            job_description = ' '.join(job_description.split())
        
        return {
            'date_posted': date_posted,
            'company': company,
            'job_type': job_type,
            'expected_start_date': expected_start_date,
            'salary_range': salary_range,
            'job_description': job_description
        }
    
    def fetch_and_export(self, output_file='jobs.csv', what='', where='', 
                        max_results=100, **kwargs):
        """
        Fetch jobs and export to CSV.
        
        Args:
            output_file (str): Output CSV filename
            what (str): Keywords to search for
            where (str): Location to search in
            max_results (int): Maximum number of jobs to fetch
            **kwargs: Additional search parameters
        """
        all_jobs = []
        results_per_page = min(50, max_results)  # API max is 50 per page
        page = 1
        
        print(f"Fetching jobs from Adzuna API...")
        print(f"Search: what='{what}', where='{where}'")
        
        while len(all_jobs) < max_results:
            print(f"Fetching page {page}...")
            
            response = self.search_jobs(
                what=what,
                where=where,
                results_per_page=results_per_page,
                page=page,
                **kwargs
            )
            
            if not response or 'results' not in response:
                print("No more results or error occurred")
                break
            
            jobs = response['results']
            if not jobs:
                print("No more jobs found")
                break
            
            all_jobs.extend(jobs)
            print(f"Fetched {len(jobs)} jobs (total: {len(all_jobs)})")
            
            # Stop if we've reached max_results
            if len(all_jobs) >= max_results:
                all_jobs = all_jobs[:max_results]
                break
            
            page += 1
            
            # Be respectful to the API - add a small delay
            time.sleep(0.5)
        
        # Parse and write to CSV
        print(f"\nWriting {len(all_jobs)} jobs to {output_file}...")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'date_posted',
                'company',
                'job_type',
                'expected_start_date',
                'salary_range',
                'job_description'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in all_jobs:
                parsed_job = self.parse_job_data(job)
                writer.writerow(parsed_job)
        
        print(f"Successfully exported {len(all_jobs)} jobs to {output_file}")
        return len(all_jobs)


# Example usage
if __name__ == '__main__':
    # Load environment variables from .env.local file
    load_dotenv('.env.local')
   
    # Debug: Check what was loaded
    print(f"APP_ID loaded: {os.getenv('ADZUNA_APP_ID')}")
    print(f"APP_KEY loaded: {os.getenv('ADZUNA_APP_KEY')}")
    
    # Get API credentials from environment variables
    APP_ID = os.getenv('ADZUNA_APP_ID')
    APP_KEY = os.getenv('ADZUNA_APP_KEY')
    
    # Validate credentials are loaded
    if not APP_ID or not APP_KEY:
        raise ValueError(
            "Missing API credentials. Please ensure your .env.local file contains:\n"
            "ADZUNA_APP_ID=your_app_id\n"
            "ADZUNA_APP_KEY=your_app_key"
        )
    
    # Initialize the fetcher
    fetcher = AdzunaJobFetcher(app_id=APP_ID, app_key=APP_KEY, country='us')
    
    # Example 1: Search for Python developer jobs in New York
    fetcher.fetch_and_export(
        output_file='python_jobs_ny.csv',
        what='python developer',
        where='New York',
        max_results=100
    )
    
    # Example 2: Search for data analyst jobs with salary sorting
    # fetcher.fetch_and_export(
    #     output_file='data_analyst_jobs.csv',
    #     what='data analyst',
    #     where='California',
    #     max_results=50,
    #     sort_by='salary'
    # )
    
