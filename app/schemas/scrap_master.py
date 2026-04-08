from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductDimensionSchema(BaseModel):
    id: int
    dimension_value: str
    unit_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductFormSchema(BaseModel):
    id: int
    form_name: str

    model_config = ConfigDict(from_attributes=True)


class ProductGradeSchema(BaseModel):
    id: int
    grade_name: str
    grade_code: Optional[str] = None
    dimensions: list[ProductDimensionSchema] = []

    model_config = ConfigDict(from_attributes=True)


class ProductCatalogSchema(BaseModel):
    id: int
    product_name: str
    product_code: str
    grades: list[ProductGradeSchema] = []

    model_config = ConfigDict(from_attributes=True)


class MaterialTypeSchema(BaseModel):
    id: int
    type_name: str
    products: list[ProductCatalogSchema] = []
    forms: list[ProductFormSchema] = []

    model_config = ConfigDict(from_attributes=True)


class MaterialFamilySchema(BaseModel):
    id: int
    family_name: str
    types: list[MaterialTypeSchema] = []

    model_config = ConfigDict(from_attributes=True)


class ProductCategorySchema(BaseModel):
    id: int
    category_name: str
    category_type: str
    display_label: Optional[str] = None
    families: list[MaterialFamilySchema] = []

    model_config = ConfigDict(from_attributes=True)


class ScrapPriceCreate(BaseModel):
    category_id: int
    family_id: int
    type_id: int
    product_id: int
    grade_id: int
    dimension_id: Optional[int] = None
    form_id: Optional[int] = None
    location_id: int
    base_price: Decimal
    price_unit: str
    currency: str
    effective_from: datetime
    source: str
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ScrapPriceRead(BaseModel):
    price_id: int
    category: str
    category_type: str
    material_family: str
    material_type: str
    product_name: str
    product_code: str
    grade: str
    grade_code: Optional[str] = None
    dimension: Optional[str] = None
    dimension_unit: Optional[str] = None
    form: Optional[str] = None
    location_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    geographic_zone: Optional[str] = None
    base_price: Decimal
    price_unit: str
    currency: str
    effective_from: datetime
    price_source: str

    model_config = ConfigDict(from_attributes=True)


class SheetPriceRow(BaseModel):
    date: str
    time_slot: Optional[str] = None
    category: str
    material_family: str
    material_type: str
    product_name: str
    grade: str
    dimensions: Optional[str] = None
    form: Optional[str] = None
    location: str
    price: Decimal
    currency: str
    per_unit: str

    model_config = ConfigDict(from_attributes=True)


class BulkSheetSyncRequest(BaseModel):
    rows: list[SheetPriceRow]
    source: str = "MARKET_FEED"
    dry_run: bool = False

    model_config = ConfigDict(from_attributes=True)


class RowResult(BaseModel):
    row_index: int
    status: str
    product_code: Optional[str] = None
    location: Optional[str] = None
    price: Optional[Decimal] = None
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BulkSheetSyncResponse(BaseModel):
    total: int
    inserted: int
    skipped: int
    errors: int
    dry_run: bool
    results: list[RowResult]

    model_config = ConfigDict(from_attributes=True)