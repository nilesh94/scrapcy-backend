from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database.connection import Base

class ScrapCategory(Base):
    __tablename__ = "scrap_categories"
    id = Column(Integer, primary_key=True, index=True)
    scrap_type = Column(String, nullable=False)        # Level 1
    material_category = Column(String, nullable=False) # Level 2
    is_active = Column(Boolean, default=True)
    
    materials = relationship("ScrapMaterial", back_populates="category")

class ScrapMaterial(Base):
    __tablename__ = "scrap_materials"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("scrap_categories.id"))
    material_name = Column(String, nullable=False)     # Level 3
    is_active = Column(Boolean, default=True)
    
    category = relationship("ScrapCategory", back_populates="materials")
    grades = relationship("ScrapGrade", back_populates="material")

class ScrapGrade(Base):
    __tablename__ = "scrap_grades"
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("scrap_materials.id"))
    grade_name = Column(String, nullable=False)        # Level 4
    is_active = Column(Boolean, default=True)

    material = relationship("ScrapMaterial", back_populates="grades")
