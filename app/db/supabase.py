"""
Supabase client configuration and initialization.
Provides both Supabase client and direct PostgreSQL connection.
"""

from typing import Optional
from supabase import create_client, Client
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool
import logging

from app.core.config import settings
from app.core.errors import DatabaseError

logger = logging.getLogger(__name__)


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

class SupabaseClient:
    """
    Singleton Supabase client for auth and storage operations.
    """
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.
        
        Returns:
            Supabase client instance
        """
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                raise DatabaseError(
                    message="Failed to connect to Supabase",
                    details={"error": str(e)}
                )
        
        return cls._instance
    
    @classmethod
    def get_auth_client(cls) -> Client:
        """
        Get Supabase client with anon key for auth operations.
        
        Returns:
            Supabase client with anon key
        """
        try:
            client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_ANON_KEY
            )
            return client
        except Exception as e:
            logger.error(f"Failed to create auth client: {str(e)}")
            raise DatabaseError(
                message="Failed to create auth client",
                details={"error": str(e)}
            )


# Singleton instance
supabase: Client = SupabaseClient.get_client()


# ============================================================================
# SQLALCHEMY DATABASE ENGINE
# ============================================================================

class DatabaseEngine:
    """
    SQLAlchemy database engine with connection pooling.
    """
    _engine = None
    _session_factory = None
    
    @classmethod
    def get_engine(cls):
        """
        Get or create database engine with connection pooling.
        
        Returns:
            SQLAlchemy engine instance
        """
        if cls._engine is None:
            try:
                cls._engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=QueuePool,
                    pool_size=settings.DB_POOL_SIZE,
                    max_overflow=settings.DB_MAX_OVERFLOW,
                    pool_timeout=settings.DB_POOL_TIMEOUT,
                    pool_recycle=settings.DB_POOL_RECYCLE,
                    pool_pre_ping=True,  # Verify connections before using
                    echo=settings.DEBUG,  # Log SQL queries in debug mode
                )
                
                # Configure engine events
                @event.listens_for(cls._engine, "connect")
                def receive_connect(dbapi_conn, connection_record):
                    """Configure connection on connect."""
                    logger.debug("Database connection established")
                
                @event.listens_for(cls._engine, "checkout")
                def receive_checkout(dbapi_conn, connection_record, connection_proxy):
                    """Verify connection on checkout."""
                    logger.debug("Database connection checked out from pool")
                
                logger.info(
                    f"Database engine initialized with pool_size={settings.DB_POOL_SIZE}, "
                    f"max_overflow={settings.DB_MAX_OVERFLOW}"
                )
                
            except Exception as e:
                logger.error(f"Failed to create database engine: {str(e)}")
                raise DatabaseError(
                    message="Failed to connect to database",
                    details={"error": str(e)}
                )
        
        return cls._engine
    
    @classmethod
    def get_session_factory(cls):
        """
        Get or create session factory.
        
        Returns:
            SQLAlchemy session factory
        """
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )
            logger.info("Database session factory created")
        
        return cls._session_factory


# ============================================================================
# BASE MODEL
# ============================================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# ============================================================================
# DATABASE SESSION DEPENDENCY
# ============================================================================

def get_db() -> Session:
    """
    Dependency function to get database session.
    Used in FastAPI dependency injection.
    
    Yields:
        SQLAlchemy database session
    
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    session_factory = DatabaseEngine.get_session_factory()
    db = session_factory()
    
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


# ============================================================================
# DATABASE UTILITIES
# ============================================================================

def test_database_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import text
        
        engine = DatabaseEngine.get_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False


def get_database_stats() -> dict:
    """
    Get database connection pool statistics.
    
    Returns:
        Dictionary with pool statistics
    """
    try:
        engine = DatabaseEngine.get_engine()
        pool = engine.pool
        
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {str(e)}")
        return {}


async def close_database_connections():
    """
    Close all database connections.
    Called during application shutdown.
    """
    try:
        engine = DatabaseEngine.get_engine()
        if engine:
            engine.dispose()
            logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")


# ============================================================================
# SUPABASE STORAGE UTILITIES
# ============================================================================

class SupabaseStorage:
    """
    Utilities for Supabase Storage operations.
    """
    
    @staticmethod
    def upload_file(
        bucket: str,
        file_path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file to Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            file_path: Path in bucket (e.g., "users/123/avatar.png")
            file_data: File data as bytes
            content_type: MIME type of file
        
        Returns:
            Public URL of uploaded file
        
        Raises:
            DatabaseError: If upload fails
        """
        try:
            client = SupabaseClient.get_client()
            
            # Upload file
            result = client.storage.from_(bucket).upload(
                path=file_path,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            # Get public URL
            public_url = client.storage.from_(bucket).get_public_url(file_path)
            
            logger.info(f"File uploaded successfully to {bucket}/{file_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise DatabaseError(
                message="Failed to upload file",
                details={"bucket": bucket, "path": file_path, "error": str(e)}
            )
    
    @staticmethod
    def delete_file(bucket: str, file_path: str) -> bool:
        """
        Delete file from Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            file_path: Path in bucket
        
        Returns:
            True if successful
        
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            client = SupabaseClient.get_client()
            client.storage.from_(bucket).remove([file_path])
            logger.info(f"File deleted successfully from {bucket}/{file_path}")
            return True
            
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            raise DatabaseError(
                message="Failed to delete file",
                details={"bucket": bucket, "path": file_path, "error": str(e)}
            )
    
    @staticmethod
    def get_file_url(bucket: str, file_path: str, expires_in: int = 3600) -> str:
        """
        Get signed URL for private file.
        
        Args:
            bucket: Storage bucket name
            file_path: Path in bucket
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed URL
        
        Raises:
            DatabaseError: If operation fails
        """
        try:
            client = SupabaseClient.get_client()
            url = client.storage.from_(bucket).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return url["signedURL"]
            
        except Exception as e:
            logger.error(f"Failed to create signed URL: {str(e)}")
            raise DatabaseError(
                message="Failed to create file URL",
                details={"bucket": bucket, "path": file_path, "error": str(e)}
            )


# ============================================================================
# INITIALIZATION CHECK
# ============================================================================

def initialize_database():
    """
    Initialize database connections and verify connectivity.
    Called during application startup.
    """
    logger.info("Initializing database connections...")
    
    # Initialize Supabase client
    SupabaseClient.get_client()
    
    # Initialize database engine
    DatabaseEngine.get_engine()
    
    # Test connection
    if test_database_connection():
        logger.info("✅ Database initialization successful")
        
        # Log pool stats
        stats = get_database_stats()
        logger.info(f"Connection pool stats: {stats}")
    else:
        logger.error("❌ Database initialization failed")
        raise DatabaseError("Failed to initialize database")