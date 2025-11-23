import sqlite3
import os   
from pathlib import Path

class Database:
    """Database connection manager for SQLite"""
    
    def __init__(self, db_path='db/horizon.db'):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.connection.cursor()
            
            # Initialize schema if tables don't exist
            self._ensure_schema_exists()
            
            return self.connection
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise
    
    def _ensure_schema_exists(self):
        """Check if tables exist, if not, initialize schema"""
        try:
            # Check if events table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
            if not self.cursor.fetchone():
                # Tables don't exist, initialize from schema file
                sql_file = Path(__file__).parent / 'database.sql'
                if sql_file.exists():
                    with open(sql_file, 'r') as f:
                        sql_script = f.read()
                        self.connection.executescript(sql_script)
                    self.commit()
                    print("Database schema initialized from database.sql")
                else:
                    print(f"Warning: Schema file not found at {sql_file}")
        except sqlite3.Error as e:
            print(f"Error checking/initializing schema: {e}")
    
    def execute(self, query, params=None):
        """Execute a query"""
        if not self.cursor:
            self.connect()
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
        except sqlite3.Error as e:
            print(f"Query execution error: {e}")
            raise
    
    def fetchone(self):
        """Fetch one result"""
        return self.cursor.fetchone()
    
    def fetchall(self):
        """Fetch all results"""
        return self.cursor.fetchall()
    
    def commit(self):
        """Commit transaction"""
        if self.connection:
            self.connection.commit()
    
    def rollback(self):
        """Rollback transaction"""
        if self.connection:
            self.connection.rollback()
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def initialize_database(self):
        """Initialize database with schema from database.sql"""
        self.connect()
        
        # Read and execute SQL schema
        sql_file = Path(__file__).parent / 'database.sql'
        if sql_file.exists():
            with open(sql_file, 'r') as f:
                sql_script = f.read()
                self.connection.executescript(sql_script)
            self.commit()
            print("Database initialized successfully!")
        else:
            print(f"Schema file not found: {sql_file}")

# Singleton pattern for database connection
_db_instance = None

def get_database():
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.initialize_database()
    return _db_instance


