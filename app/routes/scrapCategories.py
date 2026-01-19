from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..database.connection import get_db
from ..models.scrapCategories import ScrapCategory, ScrapMaterial, ScrapForm, ScrapGrade
# Import the new schemas
from ..schemas.scrapCategorySchema import CategoryHierarchyResponse, FormResponse

router = APIRouter(
    prefix="/categories",
    tags=["Scrap Categories"]
)

# --- 1. FULL HIERARCHY (Best for cascading dropdowns on load) ---
@router.get("/hierarchy", response_model=List[CategoryHierarchyResponse])
def get_category_hierarchy(db: Session = Depends(get_db)):
    """
    Returns the full tree: 
    Categories -> Materials -> Forms -> Grades
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

# --- 2. GET FORMS BY MATERIAL ID (Best for Lazy Loading) ---
@router.get("/material/{material_id}/forms", response_model=List[FormResponse])
def get_forms_by_material(material_id: int, db: Session = Depends(get_db)):
    """
    Returns only the Forms (and their grades) for a specific Material ID.
    Useful if the frontend loads data step-by-step.
    """
    # Verify Material exists
    material = db.query(ScrapMaterial).filter(ScrapMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Fetch Forms for this Material
    forms = db.query(ScrapForm).options(
        joinedload(ScrapForm.grades)
    ).filter(
        ScrapForm.material_id == material_id,
        ScrapForm.is_active == True
    ).all()

    return forms
