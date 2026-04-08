from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


# ============================================================================
# HIERARCHY READ SCHEMAS (Nested)
# ============================================================================

class ProductDimensionOut(BaseModel):
    id: int
    dimension_value: str
    unit_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductFormOut(BaseModel):
    id: int
    form_name: str

    model_config = ConfigDict(from_attributes=True)


class ProductGradeOut(BaseModel):
    id: int
    grade_name: str
    grade_code: Optional[str] = None
    dimensions: List[ProductDimensionOut] = []

    model_config = ConfigDict(from_attributes=True)


class ProductCatalogOut(BaseModel):
    id: int
    product_name: str
    product_code: str
    grades: List[ProductGradeOut] = []

    model_config = ConfigDict(from_attributes=True)


class MaterialTypeOut(BaseModel):
    id: int
    type_name: str
    products: List[ProductCatalogOut] = []
    forms: List[ProductFormOut] = []

    model_config = ConfigDict(from_attributes=True)


class MaterialFamilyOut(BaseModel):
    id: int
    family_name: str
    types: List[MaterialTypeOut] = []

    model_config = ConfigDict(from_attributes=True)


class ProductCategoryOut(BaseModel):
    id: int
    category_name: str
    category_type: str
    display_label: Optional[str] = None
    families: List[MaterialFamilyOut] = []

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ProductCategorySchema = ProductCategoryOut


# ============================================================================
# PRICE SOURCE SCHEMAS
# ============================================================================

class ScrapPriceSourceOut(BaseModel):
    source_name: str
    source_price: Decimal
    variance: Optional[Decimal] = None  # SOURCE_PRICE - BASE_PRICE
    price_unit: Optional[str] = None
    currency: Optional[str] = None
    recorded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScrapPriceSourceCreate(BaseModel):
    source_name: str
    source_price: Decimal
    price_unit: Optional[str] = None
    currency: Optional[str] = None
    variance: Optional[Decimal] = None
    notes: Optional[str] = None
    recorded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PRICE READ SCHEMA (Flat - mirrors V_SCRAP_CURRENT_PRICES view)
# ============================================================================

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
    # NEW: populated when fetching with sources
    sources: List[ScrapPriceSourceOut] = []
    source_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ScrapPriceOut = ScrapPriceRead


# ============================================================================
# BULK SYNC SCHEMAS (Google Sheet → API)
# ============================================================================

class SheetPriceRow(BaseModel):
    """
    One row from the Google Sheet.

    Fixed headers (required):
      Date | Time_Slot | CATEGORY | MATERIAL_FAMILY | MATERIAL_TYPE |
      PRODUCT_NAME | GRADE | DIMENSIONS | FORM | LOCATION | Price |
      Currency | Per_unit

    Dynamic source headers (optional, any number):
      SR_WHATSAPP | SR_MM | SR_OTHER_APP | SR_<ANY_NEW_SOURCE>

    Source columns are identified by the SR_ prefix convention.
    Any key starting with SR_ (case-insensitive) is treated as a source reading.
    No schema changes needed when new SR_ columns are added to the sheet.
    """
    date: str
    time_slot: Optional[str] = None  # MORNING | AFTERNOON | EVENING | None
    category: str
    material_family: str
    material_type: str
    product_name: str
    grade: str
    dimensions: Optional[str] = None  # "NA" or None → DIMENSION_ID = NULL
    form: Optional[str] = None  # "NA" or None → FORM_ID = NULL
    location: str
    price: Decimal  # BASE_PRICE — ops-confirmed price
    currency: str  # INR | USD
    per_unit: str  # maps to PRICE_UNIT: INR/MT | INR/KG etc.

    # Dynamic source fields — captured via model_validator
    # Any key prefixed SR_ (e.g. sr_whatsapp, SR_MM) is extracted here
    # Keys normalised to uppercase in the validator.
    # Null/empty values for a source column → exclude from dict (don't insert)
    source_prices: Dict[str, Decimal] = {}

    model_config = ConfigDict(extra='allow')

    @model_validator(mode='before')
    @classmethod
    def extract_source_prices(cls, values):
        """Extract any field starting with SR_ (case-insensitive) into source_prices dict."""
        if not isinstance(values, dict):
            return values

        source_prices = {}
        keys_to_remove = []

        for key, value in values.items():
            # Check if key starts with SR_ (case-insensitive)
            if isinstance(key, str) and key.upper().startswith('SR_'):
                # Normalize key to uppercase
                upper_key = key.upper()
                # Only include non-null, non-empty values
                if value is not None and value != '' and value != 0:
                    try:
                        # Convert to Decimal
                        source_prices[upper_key] = Decimal(str(value))
                    except Exception:
                        # Skip invalid values
                        pass
                # Mark for removal from main dict
                keys_to_remove.append(key)

        # Remove source keys from main values
        for key in keys_to_remove:
            del values[key]

        values['source_prices'] = source_prices
        return values


class BulkSheetSyncRequest(BaseModel):
    rows: List[SheetPriceRow]
    source: str = "MARKET_FEED"
    dry_run: bool = False

    model_config = ConfigDict(from_attributes=True)


class RowResult(BaseModel):
    row_index: int
    status: str  # "success" | "skipped" | "error" | "unresolved"
    product_code: Optional[str] = None
    location: Optional[str] = None
    price: Optional[Decimal] = None
    sources_inserted: int = 0  # NEW: how many SR_ source rows were inserted
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UnresolvedItem(BaseModel):
    row_index: int
    field: str  # "category"|"material_family"|"material_type"|"product_name"|"grade"|"location"
    value: str
    full_row: dict

    model_config = ConfigDict(from_attributes=True)


class BulkSheetSyncResponse(BaseModel):
    total: int
    inserted: int
    skipped: int
    errors: int
    unresolved_count: int = 0
    dry_run: bool
    results: List[RowResult]
    unresolved: List[UnresolvedItem] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# LEGACY SCHEMAS (for backward compatibility)
# ============================================================================

class ProductDimensionSchema(ProductDimensionOut):
    pass


class ProductFormSchema(ProductFormOut):
    pass


class ProductGradeSchema(ProductGradeOut):
    pass


class ProductCatalogSchema(ProductCatalogOut):
    pass


class MaterialTypeSchema(MaterialTypeOut):
    pass


class MaterialFamilySchema(MaterialFamilyOut):
    pass


class ScrapPriceCreate(BaseModel):
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