import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class VehicleDataProcessor:
    """
    Processes vehicle registration data and calculates growth metrics
    """
    
    def __init__(self, db_path: str = "data/vehicle_data.db"):
        self.db_path = db_path
    
    def load_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load data from database with optional date filtering
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = "SELECT * FROM vehicle_registrations"
            params = []
            
            if start_date or end_date:
                query += " WHERE"
                conditions = []
                
                if start_date:
                    conditions.append(" date >= ?")
                    params.append(start_date)
                
                if end_date:
                    conditions.append(" date <= ?")
                    params.append(end_date)
                
                query += " AND".join(conditions)
            
            query += " ORDER BY date, state_code, vehicle_category, manufacturer"
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            # Convert date column to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            logger.info(f"Loaded {len(df)} records from database")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def calculate_yoy_growth(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Year-over-Year growth rates
        """
        df_yoy = df.copy()
        
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df_yoy['date']):
            df_yoy['date'] = pd.to_datetime(df_yoy['date'])
        
        df_yoy['year_month'] = df_yoy['date'].dt.to_period('M')
        
        # Group by relevant dimensions
        grouped = df_yoy.groupby(['year_month', 'vehicle_category', 'manufacturer'])['registrations'].sum().reset_index()
        
        # Calculate YoY growth
        grouped['year'] = grouped['year_month'].dt.year
        grouped['month'] = grouped['year_month'].dt.month
        
        yoy_results = []
        
        for category in grouped['vehicle_category'].unique():
            for manufacturer in grouped['manufacturer'].unique():
                cat_mfr_data = grouped[
                    (grouped['vehicle_category'] == category) & 
                    (grouped['manufacturer'] == manufacturer)
                ].copy()
                
                if len(cat_mfr_data) > 0:
                    cat_mfr_data = cat_mfr_data.sort_values('year_month')
                    cat_mfr_data['yoy_growth'] = cat_mfr_data['registrations'].pct_change(periods=12) * 100
                    
                    yoy_results.append(cat_mfr_data)
        
        if yoy_results:
            result_df = pd.concat(yoy_results, ignore_index=True)
            return result_df
        else:
            return pd.DataFrame()
    
    def calculate_qoq_growth(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Quarter-over-Quarter growth rates
        """
        df_qoq = df.copy()
        
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df_qoq['date']):
            df_qoq['date'] = pd.to_datetime(df_qoq['date'])
            
        df_qoq['year_quarter'] = df_qoq['date'].dt.to_period('Q')
        
        # Group by quarter
        grouped = df_qoq.groupby(['year_quarter', 'vehicle_category', 'manufacturer'])['registrations'].sum().reset_index()
        
        qoq_results = []
        
        for category in grouped['vehicle_category'].unique():
            for manufacturer in grouped['manufacturer'].unique():
                cat_mfr_data = grouped[
                    (grouped['vehicle_category'] == category) & 
                    (grouped['manufacturer'] == manufacturer)
                ].copy()
                
                if len(cat_mfr_data) > 0:
                    cat_mfr_data = cat_mfr_data.sort_values('year_quarter')
                    cat_mfr_data['qoq_growth'] = cat_mfr_data['registrations'].pct_change(periods=1) * 100
                    
                    qoq_results.append(cat_mfr_data)
        
        if qoq_results:
            result_df = pd.concat(qoq_results, ignore_index=True)
            return result_df
        else:
            return pd.DataFrame()
    
    def get_category_summary(self, df: pd.DataFrame, period: str = 'monthly') -> pd.DataFrame:
        """
        Get summary statistics by vehicle category
        """
        if period == 'monthly':
            group_cols = ['year', 'month', 'vehicle_category']
        elif period == 'quarterly':
            group_cols = ['year', 'quarter', 'vehicle_category']
        else:  # yearly
            group_cols = ['year', 'vehicle_category']
        
        summary = df.groupby(group_cols).agg({
            'registrations': ['sum', 'mean', 'count']
        }).reset_index()
        
        # Flatten column names
        summary.columns = [col[0] if col[1] == '' else f"{col[0]}_{col[1]}" for col in summary.columns]
        
        return summary
    
    def get_manufacturer_summary(self, df: pd.DataFrame, period: str = 'monthly') -> pd.DataFrame:
        """
        Get summary statistics by manufacturer
        """
        if period == 'monthly':
            group_cols = ['year', 'month', 'vehicle_category', 'manufacturer']
        elif period == 'quarterly':
            group_cols = ['year', 'quarter', 'vehicle_category', 'manufacturer']
        else:  # yearly
            group_cols = ['year', 'vehicle_category', 'manufacturer']
        
        summary = df.groupby(group_cols).agg({
            'registrations': ['sum', 'mean']
        }).reset_index()
        
        # Flatten column names
        summary.columns = [col[0] if col[1] == '' else f"{col[0]}_{col[1]}" for col in summary.columns]
        
        return summary
    
    def get_top_performers(self, df: pd.DataFrame, by: str = 'manufacturer', 
                          top_n: int = 10, period: str = 'yearly') -> pd.DataFrame:
        """
        Get top performing manufacturers or categories
        """
        if period == 'yearly':
            group_cols = ['year']
        elif period == 'quarterly':
            group_cols = ['year', 'quarter']
        else:
            group_cols = ['year', 'month']
        
        if by == 'manufacturer':
            group_cols.extend(['vehicle_category', 'manufacturer'])
        else:
            group_cols.append('vehicle_category')
        
        summary = df.groupby(group_cols)['registrations'].sum().reset_index()
        
        # Get latest period data
        latest_period = summary[group_cols[:-1] if by == 'manufacturer' else group_cols[:-1]].max()
        
        if period == 'yearly':
            latest_data = summary[summary['year'] == latest_period['year']]
        elif period == 'quarterly':
            latest_data = summary[
                (summary['year'] == latest_period['year']) & 
                (summary['quarter'] == latest_period['quarter'])
            ]
        else:
            latest_data = summary[
                (summary['year'] == latest_period['year']) & 
                (summary['month'] == latest_period['month'])
            ]
        
        return latest_data.nlargest(top_n, 'registrations')
    
    def calculate_market_share(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate market share by manufacturer within each category
        """
        # Calculate total registrations by category and period
        df_share = df.copy()
        
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df_share['date']):
            df_share['date'] = pd.to_datetime(df_share['date'])
            
        df_share['year_month'] = df_share['date'].dt.to_period('M')
        
        # Group by month, category, and manufacturer
        monthly_data = df_share.groupby(['year_month', 'vehicle_category', 'manufacturer'])['registrations'].sum().reset_index()
        
        # Calculate category totals
        category_totals = monthly_data.groupby(['year_month', 'vehicle_category'])['registrations'].sum().reset_index()
        category_totals.rename(columns={'registrations': 'category_total'}, inplace=True)
        
        # Merge and calculate market share
        result = monthly_data.merge(
            category_totals, 
            on=['year_month', 'vehicle_category']
        )
        result['market_share'] = (result['registrations'] / result['category_total']) * 100
        
        return result
    
    def get_trend_analysis(self, df: pd.DataFrame, category: Optional[str] = None, 
                          manufacturer: Optional[str] = None) -> Dict:
        """
        Perform trend analysis for specific category/manufacturer
        """
        filtered_df = df.copy()
        
        if category:
            filtered_df = filtered_df[filtered_df['vehicle_category'] == category]
        
        if manufacturer:
            filtered_df = filtered_df[filtered_df['manufacturer'] == manufacturer]
        
        # Monthly aggregation
        monthly_trend = filtered_df.groupby(['year', 'month'])['registrations'].sum().reset_index()
        monthly_trend['date'] = pd.to_datetime(monthly_trend[['year', 'month']].assign(day=1))
        monthly_trend = monthly_trend.sort_values('date')
        
        # Calculate various metrics
        total_registrations = monthly_trend['registrations'].sum()
        avg_monthly = monthly_trend['registrations'].mean()
        growth_rate = ((monthly_trend['registrations'].iloc[-1] - monthly_trend['registrations'].iloc[0]) / 
                      monthly_trend['registrations'].iloc[0] * 100) if len(monthly_trend) > 0 else 0
        
        # Volatility (standard deviation)
        volatility = monthly_trend['registrations'].std()
        
        return {
            'total_registrations': total_registrations,
            'avg_monthly_registrations': avg_monthly,
            'overall_growth_rate': growth_rate,
            'volatility': volatility,
            'trend_data': monthly_trend
        }

def main():
    """
    Test the data processor
    """
    processor = VehicleDataProcessor()
    
    # Load sample data
    df = processor.load_data()
    
    if not df.empty:
        print("Data loaded successfully!")
        print(f"Data shape: {df.shape}")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Test YoY calculation
        yoy_data = processor.calculate_yoy_growth(df)
        print(f"YoY data calculated: {len(yoy_data)} records")
        
        # Test QoQ calculation
        qoq_data = processor.calculate_qoq_growth(df)
        print(f"QoQ data calculated: {len(qoq_data)} records")

if __name__ == "__main__":
    main()