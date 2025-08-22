
import sqlite3
import pandas as pd
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database operations for vehicle registration data
    """
    
    def __init__(self, db_path: str = "data/vehicle_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """
        Initialize database with required tables
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Main vehicle registrations table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS vehicle_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                year INTEGER NOT NULL,
                quarter TEXT NOT NULL,
                month INTEGER NOT NULL,
                state_code TEXT NOT NULL,
                state_name TEXT NOT NULL,
                vehicle_category TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                registrations INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            conn.execute(create_table_query)
            
            # Index for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_date ON vehicle_registrations(date)",
                "CREATE INDEX IF NOT EXISTS idx_category ON vehicle_registrations(vehicle_category)",
                "CREATE INDEX IF NOT EXISTS idx_manufacturer ON vehicle_registrations(manufacturer)",
                "CREATE INDEX IF NOT EXISTS idx_state ON vehicle_registrations(state_code)",
                "CREATE INDEX IF NOT EXISTS idx_year ON vehicle_registrations(year)",
            ]
            
            for index_query in indexes:
                conn.execute(index_query)
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def get_connection(self):
        """
        Get database connection
        """
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as DataFrame
        """
        try:
            conn = self.get_connection()
            if params:
                df = pd.read_sql_query(query, conn, params=params)
            else:
                df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return pd.DataFrame()
    
    def get_unique_values(self, column: str) -> List:
        """
        Get unique values for a specific column
        """
        query = f"SELECT DISTINCT {column} FROM vehicle_registrations ORDER BY {column}"
        df = self.execute_query(query)
        return df[column].tolist() if not df.empty else []
    
    def get_date_range(self) -> Dict:
        """
        Get the date range of available data
        """
        query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM vehicle_registrations"
        df = self.execute_query(query)
        
        if not df.empty:
            return {
                'min_date': df['min_date'].iloc[0],
                'max_date': df['max_date'].iloc[0]
            }
        return {'min_date': None, 'max_date': None}
    
    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics from the database
        """
        queries = {
            'total_records': "SELECT COUNT(*) as count FROM vehicle_registrations",
            'total_registrations': "SELECT SUM(registrations) as total FROM vehicle_registrations",
            'unique_manufacturers': "SELECT COUNT(DISTINCT manufacturer) as count FROM vehicle_registrations",
            'unique_states': "SELECT COUNT(DISTINCT state_code) as count FROM vehicle_registrations"
        }
        
        stats = {}
        for key, query in queries.items():
            df = self.execute_query(query)
            if not df.empty:
                col_name = df.columns[0]
                stats[key] = df[col_name].iloc[0]
            else:
                stats[key] = 0
        
        return stats
    
    def get_filtered_data(self, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         vehicle_categories: Optional[List[str]] = None,
                         manufacturers: Optional[List[str]] = None,
                         states: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get filtered data based on various criteria
        """
        query = "SELECT * FROM vehicle_registrations WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        if vehicle_categories:
            placeholders = ','.join(['?' for _ in vehicle_categories])
            query += f" AND vehicle_category IN ({placeholders})"
            params.extend(vehicle_categories)
        
        if manufacturers:
            placeholders = ','.join(['?' for _ in manufacturers])
            query += f" AND manufacturer IN ({placeholders})"
            params.extend(manufacturers)
        
        if states:
            placeholders = ','.join(['?' for _ in states])
            query += f" AND state_code IN ({placeholders})"
            params.extend(states)
        
        query += " ORDER BY date, state_code, vehicle_category, manufacturer"
        
        return self.execute_query(query, tuple(params))
    
    def get_aggregated_data(self, 
                           group_by: List[str], 
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get aggregated registration data
        """
        group_columns = ', '.join(group_by)
        query = f"""
        SELECT {group_columns}, SUM(registrations) as total_registrations, 
               COUNT(*) as record_count,
               AVG(registrations) as avg_registrations
        FROM vehicle_registrations 
        WHERE 1=1
        """
        
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += f" GROUP BY {group_columns} ORDER BY {group_columns}"
        
        return self.execute_query(query, tuple(params))
    
    def backup_database(self, backup_path: str):
        """
        Create a backup of the database
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")

def main():
    """
    Test database operations
    """
    db = DatabaseManager()
    
    # Get summary stats
    stats = db.get_summary_stats()
    print("Database Summary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get unique values
    categories = db.get_unique_values('vehicle_category')
    print(f"\nVehicle Categories: {categories}")
    
    manufacturers = db.get_unique_values('manufacturer')
    print(f"Total Manufacturers: {len(manufacturers)}")
    
    # Get date range
    date_range = db.get_date_range()
    print(f"\nDate Range: {date_range['min_date']} to {date_range['max_date']}")

if __name__ == "__main__":
    main()