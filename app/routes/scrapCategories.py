from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from ..database.connection import get_db
from ..models.scrapCategories import ScrapCategory, ScrapMaterial, ScrapGrade

router = APIRouter(
    prefix="/categories",
    tags=["Scrap Categories"]
)

@router.get("/hierarchy")
def get_category_hierarchy(db: Session = Depends(get_db)):
    """
    Returns the full tree: Categories -> Materials -> Grades
    """
    categories = db.query(ScrapCategory).options(
        joinedload(ScrapCategory.materials).joinedload(ScrapMaterial.grades)
    ).filter(ScrapCategory.is_active == True).all()

    return categories
