"""
Base Service Class
Provides common database session management and utilities
"""
from typing import Optional, List, Type, TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone
from app.database.connection import get_db
from app.e_auction.utils.exceptions import DatabaseException

# Generic type for models
ModelType = TypeVar("ModelType")


class BaseService(Generic[ModelType]):
    """
    Base service class with common database operations
    All services inherit from this to get standard CRUD operations
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get_by_id(self, db: Session, id: int) -> Optional[ModelType]:
        """Get single record by ID"""
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            raise DatabaseException(f"Error fetching {self.model.__name__}: {str(e)}")
    
    def get_all(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[dict] = None
    ) -> List[ModelType]:
        """Get all records with pagination and optional filters"""
        try:
            query = db.query(self.model)
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if value is not None and hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            raise DatabaseException(f"Error fetching {self.model.__name__} list: {str(e)}")
    
    def count(self, db: Session, filters: Optional[dict] = None) -> int:
        """Count records with optional filters"""
        try:
            query = db.query(func.count(self.model.id))
            
            if filters:
                for key, value in filters.items():
                    if value is not None and hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            
            return query.scalar()
        except Exception as e:
            raise DatabaseException(f"Error counting {self.model.__name__}: {str(e)}")
    
    def create(self, db: Session, obj_in: dict) -> ModelType:
        """Create new record"""
        try:
            # SaaS FIX: Automatically inject UTC timestamps if fields exist in model
            if hasattr(self.model, 'created_at') and 'created_at' not in obj_in:
                obj_in['created_at'] = datetime.now(timezone.utc)
            if hasattr(self.model, 'updated_at') and 'updated_at' not in obj_in:
                obj_in['updated_at'] = datetime.now(timezone.utc)

            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            raise DatabaseException(f"Error creating {self.model.__name__}: {str(e)}")
    
    def update(self, db: Session, db_obj: ModelType, obj_in: dict) -> ModelType:
        """Update existing record"""
        try:
            for field, value in obj_in.items():
                if value is not None and hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # SaaS FIX: Ensure updated_at is refreshed in UTC on every update
            if hasattr(db_obj, 'updated_at'):
                setattr(db_obj, 'updated_at', datetime.now(timezone.utc))

            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            raise DatabaseException(f"Error updating {self.model.__name__}: {str(e)}")
    
    def delete(self, db: Session, id: int) -> bool:
        """Delete record by ID"""
        try:
            obj = self.get_by_id(db, id)
            if obj:
                db.delete(obj)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise DatabaseException(f"Error deleting {self.model.__name__}: {str(e)}")
    
    def exists(self, db: Session, id: int) -> bool:
        """Check if record exists"""
        try:
            return db.query(
                db.query(self.model).filter(self.model.id == id).exists()
            ).scalar()
        except Exception as e:
            raise DatabaseException(f"Error checking existence: {str(e)}")


class ServiceDependency:
    """
    Dependency injection helper for services
    Ensures database session is properly managed
    """
    
    @staticmethod
    def get_db_session():
        """Get database session (generator)"""
        return get_db()
