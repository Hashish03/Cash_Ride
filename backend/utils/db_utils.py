from supabase import SupabaseClient
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SupabaseDB:
    def __init__(self, client: SupabaseClient):
        self.client = client

    def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Insert data into a table"""
        try:
            response = self.client.table(table).insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Insert error in {table}: {e}")
            return None

    def select(self, table: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Select data from a table"""
        try:
            query = self.client.table(table).select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Select error in {table}: {e}")
            return []

    def update(self, table: str, data: Dict, filters: Dict) -> Optional[Dict]:
        """Update data in a table"""
        try:
            query = self.client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Update error in {table}: {e}")
            return None

    def delete(self, table: str, filters: Dict) -> bool:
        """Delete data from a table"""
        try:
            query = self.client.table(table).delete()
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            query.execute()
            return True
        except Exception as e:
            logger.error(f"Delete error in {table}: {e}")
            return False