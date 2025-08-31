import pandas as pd
import math
import os

class DataProcess:
    def __init__(self):
        """Initialize the data processor and load the CSV data"""
        self.csv_path = 'attached_assets/Last provider data.csv'
        self.df = self.load_data()
        
    def load_data(self):
        """Load and clean the CSV data"""
        try:
            df = pd.read_csv(self.csv_path)
            
            # Clean and standardize the data
            df = df.dropna(subset=['Latitude', 'Longitude', 'CMS Rating'])
            df['CMS Rating'] = pd.to_numeric(df['CMS Rating'], errors='coerce')
            df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce')
            df['Availability'] = pd.to_numeric(df['Availability'], errors='coerce')
            
            # Clean location data
            df['Location'] = df['Location'].str.strip()
            df['Type'] = df['Type'].str.strip()
            
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the distance between two points on Earth using Haversine formula"""
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r
    
    def find_nearby_providers(self, user_lat, user_lon, provider_type, radius_km=15):
        """Find providers within specified radius and of specified type"""
        if self.df.empty:
            return []
        
        # Filter by provider type
        if provider_type.lower() != 'all':
            # Handle different type variations
            type_filters = []
            if 'hospital' in provider_type.lower():
                type_filters = self.df['Type'].str.contains('Hospital|GENERAL ACUTE CARE|CRITICAL ACCESS', case=False, na=False)
            elif 'supplier' in provider_type.lower():
                type_filters = self.df['Source'].str.contains('Supplier', case=False, na=False)
            elif 'Scan Center' in provider_type.lower():
                type_filters = self.df['Type'].str.contains('Scan|Imaging|Radiology', case=False, na=False)
            elif 'nursing' in provider_type.lower():
                type_filters = self.df['Type'].str.contains('Nursing|LONG TERM CARE|REHABILITATION', case=False, na=False)
            else:
                # Default to hospital if type not recognized
                type_filters = self.df['Type'].str.contains('Hospital|GENERAL ACUTE CARE|CRITICAL ACCESS', case=False, na=False)
            
            filtered_df = self.df[type_filters]
        else:
            filtered_df = self.df
        
        # Calculate distances and filter by radius
        nearby_providers = []
        
        for _, row in filtered_df.iterrows():
            try:
                provider_lat = float(row['Latitude'])
                provider_lon = float(row['Longitude'])
                
                distance = self.haversine_distance(user_lat, user_lon, provider_lat, provider_lon)
                
                if distance <= radius_km:
                    provider_data = {
                        'name': row['Location'].split(',')[0] if ',' in str(row['Location']) else str(row['Location']),
                        'full_address': str(row['Location']),
                        'contact': str(row['Contact Number']) if pd.notna(row['Contact Number']) else 'N/A',
                        'type': str(row['Type']),
                        'latitude': provider_lat,
                        'longitude': provider_lon,
                        'cms_rating': float(row['CMS Rating']) if pd.notna(row['CMS Rating']) else 0,
                        'cost': float(row['Cost']) if pd.notna(row['Cost']) else 0,
                        'availability': int(row['Availability']) if pd.notna(row['Availability']) else 0,
                        'distance': round(distance, 2)
                    }
                    nearby_providers.append(provider_data)
                    
            except (ValueError, TypeError) as e:
                # Skip rows with invalid coordinates
                continue
        
        return nearby_providers
    
    def sort_providers_by_priority(self, providers):
        """Sort providers by CMS rating (desc) then by cost (asc)"""
        return sorted(providers, key=lambda x: (-x['cms_rating'], x['cost']))
    
    def get_provider_types(self):
        """Get unique provider types from the dataset"""
        if self.df.empty:
            return ['Hospital', 'Nursing Home']
        
        # Extract unique types and clean them
        types = ['Hospital', 'Nursing Home', 'Scan Center', 'Supplier']
        return types
