
import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
import json
import os
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VahanDataCollector:
    """
    Collects vehicle registration data from Vahan Dashboard
    """
    
    def __init__(self, db_path: str = "data/vehicle_data.db"):
        self.base_url = "https://vahan.parivahan.gov.in/vahan4dashboard/"
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Ensure data directories exist
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)
        
    def get_state_list(self) -> List[Dict]:
        """
        Get list of states from Vahan dashboard
        """
        try:
            # Sample state data (you would typically scrape this)
            states = [
                {"state_code": "DL", "state_name": "Delhi"},
                {"state_code": "MH", "state_name": "Maharashtra"},
                {"state_code": "KA", "state_name": "Karnataka"},
                {"state_code": "TN", "state_name": "Tamil Nadu"},
                {"state_code": "UP", "state_name": "Uttar Pradesh"},
                {"state_code": "GJ", "state_name": "Gujarat"},
                {"state_code": "RJ", "state_name": "Rajasthan"},
                {"state_code": "WB", "state_name": "West Bengal"},
                {"state_code": "AP", "state_name": "Andhra Pradesh"},
                {"state_code": "TS", "state_name": "Telangana"},
            ]
            return states
        except Exception as e:
            logger.error(f"Error fetching state list: {e}")
            return []
    
    def generate_sample_data(self) -> pd.DataFrame:
        """
        Generate sample vehicle registration data
        Since actual scraping requires handling of the Vahan portal's security,
        we'll generate realistic sample data for demonstration
        """
        
        # Vehicle categories and manufacturers
        vehicle_categories = ['2W', '3W', '4W']
        manufacturers_2w = ['Hero', 'Honda', 'Bajaj', 'TVS', 'Yamaha', 'Royal Enfield']
        manufacturers_3w = ['Bajaj', 'TVS', 'Mahindra', 'Piaggio', 'Force Motors']
        manufacturers_4w = ['Maruti Suzuki', 'Hyundai', 'Tata Motors', 'Mahindra', 'Honda', 'Toyota']
        
        manufacturers_map = {
            '2W': manufacturers_2w,
            '3W': manufacturers_3w,
            '4W': manufacturers_4w
        }
        
        # Generate data for the last 3 years
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        data = []
        states = self.get_state_list()
        
        # Generate monthly data
        current_date = start_date
        while current_date <= end_date:
            for state in states:
                for category in vehicle_categories:
                    for manufacturer in manufacturers_map[category]:
                        # Generate realistic registration numbers
                        base_registrations = {
                            '2W': {'Hero': 8000, 'Honda': 6000, 'Bajaj': 4000, 'TVS': 3000, 'Yamaha': 2000, 'Royal Enfield': 1000},
                            '3W': {'Bajaj': 1500, 'TVS': 1000, 'Mahindra': 800, 'Piaggio': 600, 'Force Motors': 400},
                            '4W': {'Maruti Suzuki': 3000, 'Hyundai': 2000, 'Tata Motors': 1500, 'Mahindra': 1200, 'Honda': 1000, 'Toyota': 800}
                        }
                        
                        base = base_registrations[category].get(manufacturer, 500)
                        
                        # Add seasonal variations and growth trends
                        month_factor = 1 + 0.2 * (current_date.month % 12) / 12
                        year_growth = 1 + 0.05 * (current_date.year - 2022)  # 5% annual growth
                        random_factor = 0.8 + 0.4 * hash(f"{manufacturer}{current_date}") % 100 / 100
                        
                        registrations = int(base * month_factor * year_growth * random_factor)
                        
                        data.append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'year': current_date.year,
                            'quarter': f"Q{(current_date.month-1)//3 + 1}",
                            'month': current_date.month,
                            'state_code': state['state_code'],
                            'state_name': state['state_name'],
                            'vehicle_category': category,
                            'manufacturer': manufacturer,
                            'registrations': registrations
                        })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} records of sample data")
        return df
    
    def save_to_database(self, df: pd.DataFrame):
        """
        Save data to SQLite database
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Create table if not exists
            create_table_query = """
            CREATE TABLE IF NOT EXISTS vehicle_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                year INTEGER,
                quarter TEXT,
                month INTEGER,
                state_code TEXT,
                state_name TEXT,
                vehicle_category TEXT,
                manufacturer TEXT,
                registrations INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            conn.execute(create_table_query)
            
            # Insert data
            df.to_sql('vehicle_registrations', conn, if_exists='replace', index=False)
            conn.commit()
            conn.close()
            
            logger.info(f"Saved {len(df)} records to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None):
        """
        Save data to CSV file
        """
        if filename is None:
            filename = f"data/raw/vehicle_registrations_{datetime.now().strftime('%Y%m%d')}.csv"
        
        df.to_csv(filename, index=False)
        logger.info(f"Saved data to {filename}")
    
    def collect_data(self) -> pd.DataFrame:
        """
        Main method to collect vehicle registration data
        """
        logger.info("Starting data collection...")
        
        # For this demo, we'll generate sample data
        # In a real implementation, you would scrape the Vahan dashboard
        df = self.generate_sample_data()
        
        # Save to both database and CSV
        self.save_to_database(df)
        self.save_to_csv(df)
        
        return df

def main():
    """
    Main function to run data collection
    """
    collector = VahanDataCollector()
    data = collector.collect_data()
    print(f"Data collection completed. Collected {len(data)} records.")

if __name__ == "__main__":
    main()