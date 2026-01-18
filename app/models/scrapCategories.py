from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.oracle import NUMBER
from ..database.connection import Base

class ScrapCategory(Base):
    __tablename__ = "scrap_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    scrap_type = Column(String(100), nullable=False)        
    material_category = Column(String(100), nullable=False) 
    
    is_active = Column(Boolean, default=True) 
    
    # Relationship: One Category has many Materials
    materials = relationship("ScrapMaterial", back_populates="category")

class ScrapMaterial(Base):
    __tablename__ = "scrap_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("scrap_categories.id"))
    material_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship: Belongs to Category
    category = relationship("ScrapCategory", back_populates="materials")
    
    # Relationship: One Material has many Forms (Updated from grades)
    forms = relationship("ScrapForm", back_populates="material")

class ScrapForm(Base):
    # Note: DB table name is singular 'SCRAP_FORM' per your describe command
    __tablename__ = "scrap_form" 
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("scrap_materials.id"))
    form_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship: Belongs to Material
    material = relationship("ScrapMaterial", back_populates="forms")
    
    # Relationship: One Form has many Grades
    grades = relationship("ScrapGrade", back_populates="form")

class ScrapGrade(Base):
    __tablename__ = "scrap_grades"
    
    id = Column(Integer, primary_key=True, index=True)
    # Updated FK to link to Form instead of Material
    form_id = Column(Integer, ForeignKey("scrap_form.id")) 
    grade_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationship: Belongs to Form
    form = relationship("ScrapForm", back_populates="grades")
