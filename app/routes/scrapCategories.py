from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from ..database.connection import get_db
from ..models.scrapCategories import ScrapCategory, ScrapMaterial, ScrapForm, ScrapGrade

router = APIRouter(
    prefix="/categories",
    tags=["Scrap Categories"]
)

@router.get("/hierarchy")
def get_category_hierarchy(db: Session = Depends(get_db)):
    """
    Returns the full tree: Categories -> Materials -> Forms -> Grades
    """
    categories = db.query(ScrapCategory).options(
        # Load Materials inside Category
        joinedload(ScrapCategory.materials)
        # Load Forms inside Material
        .joinedload(ScrapMaterial.forms)
        # Load Grades inside Form
        .joinedload(ScrapForm.grades)
    ).filter(ScrapCategory.is_active == True).all()

    return categories
