
import os
import sys
import sqlite3
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
src_path = current_dir / 'src'
sys.path.insert(0, str(src_path))

def initialize_app():
    """Initialize the application with sample data if needed"""
    
    # Check if database exists
    db_path = current_dir / 'data' / 'vehicle_data.db'
    
    if not db_path.exists():
        print("🔧 Database not found. Initializing sample data...")
        
        # Create directories
        os.makedirs('data', exist_ok=True)
        
        # Import after adding to path
        from Data_collector import VahanDataCollector
        from database import DatabaseManager
        
        # Initialize components
        collector = VahanDataCollector()
        db_manager = DatabaseManager()
        
        # Generate sample data
        print("🎲 Generating sample vehicle registration data...")
        sample_data = collector.collect_data()
        
        print(f"✅ Generated {len(sample_data):,} sample records")
        print("📊 Data initialized successfully!")
        
        return True
    else:
        # Check if database has data
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicle_registrations")
            count = cursor.fetchone()[0]
            conn.close()
            
            if count > 0:
                print(f"✅ Database found with {count:,} records")
                return True
            else:
                print("⚠️ Database found but empty. Reinitializing...")
                # Remove empty db and reinitialize
                db_path.unlink()
                return initialize_app()
                
        except Exception as e:
            print(f"❌ Database error: {e}")
            print("🔄 Reinitializing database...")
            if db_path.exists():
                db_path.unlink()
            return initialize_app()

if __name__ == "__main__":
    initialize_app()