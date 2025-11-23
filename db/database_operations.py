import sqlite3
from pathlib import Path

class DatabaseConnection:
    """Database connection manager for SQLite"""
    
    def __init__(self, db_path='db/horizon.db'):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection and initialize schema"""
        try:
            # Create db directory if it doesn't exist
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(exist_ok=True)
            
            # Connect to database
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.connection.cursor()
            
            # Initialize database schema if tables don't exist
            self._initialize_schema()
            
            print(f"Connected to database: {self.db_path}")
            return self.connection
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise
    
    def _initialize_schema(self):
        """Initialize database schema from SQL file"""
        sql_file = Path(__file__).parent / 'database.sql'
        
        if sql_file.exists():
            with open(sql_file, 'r') as f:
                sql_script = f.read()
                self.connection.executescript(sql_script)
            self.commit()
            print("Database schema initialized successfully!")
        else:
            print(f"Warning: Schema file not found at {sql_file}")
    
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
            print(f"Query: {query}")
            print(f"Params: {params}")
            raise
    
    def fetchone(self):
        """Fetch one result"""
        if self.cursor:
            return self.cursor.fetchone()
        return None
    
    def fetchall(self):
        """Fetch all results"""
        if self.cursor:
            return self.cursor.fetchall()
        return []
    
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
        print("Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
