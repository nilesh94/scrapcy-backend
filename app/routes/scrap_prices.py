import logging
from datetime import datetime, time
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, select, func, or_
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.database.connection import get_db
from app.models.scrap_master import (
    ProductCategory,
    MaterialFamily,
    MaterialType,
    ProductCatalog,
    ProductGrade,
    ProductDimension,
    ProductForm,
    ScrapPrice,
    ScrapPriceSource,
)
from app.models.market_data import Location
from app.schemas.scrap_master import (
    ProductCategoryOut,
    ScrapPriceRead,
    BulkSheetSyncRequest,
    BulkSheetSyncResponse,
    RowResult,
    SheetPriceRow,
    ScrapPriceSourceOut,
    UnresolvedItem,
)

router = APIRouter(
    prefix="/scrap-prices",
    tags=["scrap-prices"]
)

logger = logging.getLogger(__name__)

# Time slot mapping for effective_from construction
TIME_SLOT_MAP = {
    "MORNING": time(9, 0, 0),
    "AFTERNOON": time(14, 0, 0),
    "EVENING": time(18, 0, 0),
    None: time(0, 0, 0),
}


# ==========================================
# GET /master-catalog
# ==========================================
@router.get("/master-catalog", response_model=List[ProductCategoryOut])
def get_master_catalog(
    category_type: Optional[str] = Query(None, description="Filter by category type: SCRAP | SEMI_FINISHED | FINISHED"),
    db: Session = Depends(get_db)
):
    """
    Returns full hierarchy tree (categories → families → types → products → grades → dimensions).
    Uses eager loading to avoid N+1 queries.
    """
    query = (
        db.query(ProductCategory)
        .options(
            joinedload(ProductCategory.families).joinedload(MaterialFamily.types)
            .joinedload(MaterialType.products).joinedload(ProductCatalog.grades)
            .joinedload(ProductGrade.dimensions),
            joinedload(ProductCategory.families).joinedload(MaterialFamily.types)
            .joinedload(MaterialType.forms)
        )
    )

    if category_type:
        query = query.filter(ProductCategory.category_type == category_type.upper())

    categories = query.all()
    return categories


# ==========================================
# GET /current-prices
# ==========================================
@router.get("/current-prices", response_model=List[ScrapPriceRead])
def get_current_prices(
    category: Optional[str] = None,
    category_type: Optional[str] = None,
    material_family: Optional[str] = None,
    material_type: Optional[str] = None,
    product_name: Optional[str] = None,
    product_code: Optional[str] = None,
    dimension: Optional[str] = None,
    form: Optional[str] = None,
    location_name: Optional[str] = None,
    location_id: Optional[int] = None,
    grade: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns current active prices from V_SCRAP_CURRENT_PRICES view.
    All filter params are optional.
    The view is fully denormalized - no joins needed.
    """
    sql = """
        SELECT
            PRICE_ID,
            CATEGORY,
            CATEGORY_TYPE,
            MATERIAL_FAMILY,
            MATERIAL_TYPE,
            PRODUCT_NAME,
            PRODUCT_CODE,
            GRADE,
            GRADE_CODE,
            DIMENSION,
            DIMENSION_UNIT,
            FORM,
            LOCATION_NAME,
            CITY,
            STATE,
            GEOGRAPHIC_ZONE,
            BASE_PRICE,
            PRICE_UNIT,
            CURRENCY,
            SOURCE_PRICES,
            SOURCE_COUNT,
            EFFECTIVE_FROM,
            PRICE_SOURCE,
            CREATED_BY
        FROM SCRAPCY_APP.V_SCRAP_CURRENT_PRICES
        WHERE 1=1
    """
    params = {}

    if category:
        sql += " AND UPPER(CATEGORY) = UPPER(:category)"
        params["category"] = category

    if category_type:
        sql += " AND UPPER(CATEGORY_TYPE) = UPPER(:category_type)"
        params["category_type"] = category_type

    if material_family:
        sql += " AND UPPER(MATERIAL_FAMILY) = UPPER(:material_family)"
        params["material_family"] = material_family

    if material_type:
        sql += " AND UPPER(MATERIAL_TYPE) = UPPER(:material_type)"
        params["material_type"] = material_type

    if product_name:
        sql += " AND UPPER(PRODUCT_NAME) = UPPER(:product_name)"
        params["product_name"] = product_name

    if product_code:
        sql += " AND UPPER(PRODUCT_CODE) = UPPER(:product_code)"
        params["product_code"] = product_code

    if dimension:
        sql += " AND UPPER(DIMENSION) = UPPER(:dimension)"
        params["dimension"] = dimension

    if form:
        sql += " AND UPPER(FORM) = UPPER(:form)"
        params["form"] = form

    if location_name:
        sql += " AND UPPER(LOCATION_NAME) = UPPER(:location_name)"
        params["location_name"] = location_name

    if location_id:
        sql += """
            AND PRODUCT_CODE IN (
                SELECT PRODUCT_CODE FROM SCRAPCY_APP.SCRAP_PRICES
                WHERE LOCATION_ID = :location_id AND IS_ACTIVE = 1
            )
        """
        params["location_id"] = location_id

    if grade:
        sql += " AND UPPER(GRADE) = UPPER(:grade)"
        params["grade"] = grade

    sql += " ORDER BY EFFECTIVE_FROM DESC"

    result = db.execute(text(sql), params)

    # ─────────────────────────────────────────────────────────────────────────
    # KEY FIX: build a case-insensitive row accessor.
    # Oracle oracledb in thin mode (Python 3.9) may return column keys in
    # lowercase even when the SQL aliases are uppercase.
    # We normalise all keys to uppercase so row access never fails.
    # ─────────────────────────────────────────────────────────────────────────
    raw_rows = result.fetchall()
    col_keys = [k.upper() for k in result.keys()]  # normalise to uppercase

    def get_col(row, col_name):
        """Case-insensitive column accessor. Returns None if column missing."""
        try:
            idx = col_keys.index(col_name.upper())
            return row[idx]
        except (ValueError, IndexError):
            return None

    prices = []
    for row in raw_rows:
        base_price_raw = get_col(row, "BASE_PRICE")
        base_price = Decimal(str(base_price_raw)) if base_price_raw is not None else Decimal("0")

        # Parse SOURCE_PRICES pipe-delimited string → list of source objects
        # Format: "SR_WHATSAPP:32200|SR_MM:32800" or None
        sources = []
        source_prices_raw = get_col(row, "SOURCE_PRICES")
        if source_prices_raw:
            for part in str(source_prices_raw).split("|"):
                part = part.strip()
                if ":" not in part:
                    continue
                try:
                    name, price_str = part.split(":", 1)
                    source_price = Decimal(price_str.strip())
                    sources.append(ScrapPriceSourceOut(
                        source_name=name.strip(),
                        source_price=source_price,
                        variance=source_price - base_price,
                        price_unit=None,
                        currency=None,
                        recorded_at=None
                    ))
                except Exception:
                    continue

        source_count_raw = get_col(row, "SOURCE_COUNT")
        source_count = int(source_count_raw) if source_count_raw is not None else len(sources)

        prices.append(ScrapPriceRead(
            price_id=get_col(row, "PRICE_ID"),
            category=get_col(row, "CATEGORY") or "",
            category_type=get_col(row, "CATEGORY_TYPE") or "",
            material_family=get_col(row, "MATERIAL_FAMILY") or "",
            material_type=get_col(row, "MATERIAL_TYPE") or "",
            product_name=get_col(row, "PRODUCT_NAME") or "",
            product_code=get_col(row, "PRODUCT_CODE") or "",
            grade=get_col(row, "GRADE") or "",
            grade_code=get_col(row, "GRADE_CODE"),
            dimension=get_col(row, "DIMENSION"),
            dimension_unit=get_col(row, "DIMENSION_UNIT"),
            form=get_col(row, "FORM"),
            location_name=get_col(row, "LOCATION_NAME") or "",
            city=get_col(row, "CITY"),
            state=get_col(row, "STATE"),
            geographic_zone=get_col(row, "GEOGRAPHIC_ZONE"),
            base_price=base_price,
            price_unit=get_col(row, "PRICE_UNIT") or "INR/MT",
            currency=get_col(row, "CURRENCY") or "INR",
            effective_from=get_col(row, "EFFECTIVE_FROM"),
            price_source=get_col(row, "PRICE_SOURCE") or "",
            sources=sources,
            source_count=source_count
        ))

    return prices


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORARY DEBUG ENDPOINT
# Hit it once after deploy to confirm what keys Oracle actually returns.
# Remove it once the main endpoint works.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/debug-columns")
def debug_columns(db: Session = Depends(get_db)):
    """
    Temporary debug endpoint. Shows exactly what column keys Oracle returns
    for V_SCRAP_CURRENT_PRICES. Remove after confirming get_current_prices works.
    """
    result = db.execute(text("""
        SELECT * FROM SCRAPCY_APP.V_SCRAP_CURRENT_PRICES
        WHERE ROWNUM = 1
    """))
    keys = list(result.keys())
    return {
        "column_count": len(keys),
        "columns_as_returned_by_driver": keys,
        "columns_uppercased": [k.upper() for k in keys]
    }


def parse_source_prices_string(raw: Optional[str], base_price: Decimal) -> List[ScrapPriceSourceOut]:
    """
    Parse SOURCE_PRICES column from V_SCRAP_CURRENT_PRICES view.
    Format: "SR_WHATSAPP:32200|SR_MM:32800"
    """
    if not raw:
        return []
    
    results = []
    for part in raw.split('|'):
        if ':' not in part:
            continue
        name, price_str = part.split(':', 1)
        try:
            source_price = Decimal(price_str)
            results.append(ScrapPriceSourceOut(
                source_name=name,
                source_price=source_price,
                variance=source_price - base_price,
                recorded_at=None  # not available from view string
            ))
        except (ValueError, Decimal.InvalidOperation):
            continue
    return results


# ==========================================
# GET /price-history/{product_code}
# ==========================================
@router.get("/price-history/{product_code}", response_model=List[ScrapPriceRead])
def get_price_history(
    product_code: str,
    location_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Returns full price history for a product code across all locations.
    Ordered by effective_from DESC.
    Includes ScrapPriceSource records loaded via joinedload.
    """
    query = (
        db.query(ScrapPrice)
        .join(ProductCatalog, ScrapPrice.product_id == ProductCatalog.id)
        .options(joinedload(ScrapPrice.price_sources))
        .filter(func.upper(ProductCatalog.product_code) == product_code.upper())
        .filter(ScrapPrice.is_active == 1)
    )

    if location_id:
        query = query.filter(ScrapPrice.location_id == location_id)

    if from_date:
        query = query.filter(ScrapPrice.effective_from >= from_date)

    if to_date:
        query = query.filter(ScrapPrice.effective_from <= to_date)

    prices = query.order_by(ScrapPrice.effective_from.desc()).all()

    # Build response with denormalized data
    # Need to traverse hierarchy: ScrapPrice → ProductCatalog → MaterialType → MaterialFamily → ProductCategory
    results = []
    for p in prices:
        # Traverse hierarchy for category/family/type info
        product = p.product
        material_type = product.type if product else None
        material_family = material_type.family if material_type else None
        product_category = material_family.category if material_family else None

        # Build source list from ScrapPriceSource records
        sources = []
        for src in p.price_sources:
            sources.append(ScrapPriceSourceOut(
                source_name=src.source_name,
                source_price=Decimal(str(src.source_price)),
                variance=Decimal(str(src.variance)) if src.variance is not None else None,
                price_unit=src.price_unit,
                currency=src.currency,
                recorded_at=src.recorded_at,
            ))

        results.append(ScrapPriceRead(
            price_id=p.id,
            category=product_category.category_name if product_category else "",
            category_type=product_category.category_type if product_category else "",
            material_family=material_family.family_name if material_family else "",
            material_type=material_type.type_name if material_type else "",
            product_name=product.product_name if product else "",
            product_code=p.product_code or (product.product_code if product else ""),
            grade=p.grade.grade_name if p.grade else "",
            grade_code=p.grade.grade_code if p.grade else None,
            dimension=p.dimension.dimension_value if p.dimension else None,
            dimension_unit=p.dimension.unit_type if p.dimension else None,
            form=p.form.form_name if p.form else None,
            location_name=p.location.location_name if p.location else "",
            city=p.location.city if p.location else None,
            state=p.location.state if p.location else None,
            geographic_zone=p.location.geographic_zone if p.location else None,
            base_price=Decimal(str(p.base_price)),
            price_unit=p.price_unit,
            currency=p.currency,
            effective_from=p.effective_from,
            price_source=p.source,
            sources=sources,
            source_count=len(sources),
        ))

    return results


# ==========================================
# POST /bulk-sheet-sync
# ==========================================
@router.post("/bulk-sheet-sync", response_model=BulkSheetSyncResponse)
def bulk_sheet_sync(
    request: BulkSheetSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Receives raw rows from Google Sheets via n8n.
    - Resolves names to IDs using case-insensitive lookups.
    - Prevents duplicates for the same day.
    - Inserts new prices into SCRAP_PRICES.
    - Inserts source price readings into SCRAP_PRICE_SOURCES.
    - DB triggers handle PRODUCT_CODE population and closing previous rows.
    
    Follows exact pattern from market_prices.py bulk-sheet-sync.
    """
    logger.info(f"Bulk sheet sync started: {len(request.rows)} rows, dry_run={request.dry_run}")

    results: List[RowResult] = []
    unresolved: List[UnresolvedItem] = []
    inserted_count = 0
    skipped_count = 0
    error_count = 0

    # --- A. Pre-fetch Maps (Optimization) ---
    # Build cache lazily on first miss per key
    cache: Dict[str, Dict] = {
        "categories": {},   # upper(name) → id
        "families": {},     # (upper(name), category_id) → id
        "types": {},        # (upper(name), family_id) → id
        "products": {},     # (upper(name), type_id) → id
        "grades": {},       # (upper(name), product_id) → id
        "dimensions": {},   # (upper(value), grade_id) → id | None
        "forms": {},        # (upper(name), type_id) → id | None
        "locations": {},    # upper(name) → id
    }

    def _populate_locations():
        if not cache["locations"]:
            all_locations = db.query(Location).filter(Location.is_active == 1).all()
            for loc in all_locations:
                if loc.location_name:
                    cache["locations"][loc.location_name.strip().upper()] = loc.id
                if loc.city:
                    cache["locations"][loc.city.strip().upper()] = loc.id
                if loc.search_aliases:
                    aliases = [a.strip().upper() for a in loc.search_aliases.split(',') if a.strip()]
                    for alias in aliases:
                        cache["locations"][alias] = loc.id

    def _populate_categories():
        if not cache["categories"]:
            for c in db.query(ProductCategory).filter(ProductCategory.is_active == 1).all():
                cache["categories"][c.category_name.strip().upper()] = c.id

    def _populate_families(category_id: int):
        key = ("ALL", category_id)
        if key not in cache["families"]:
            for f in db.query(MaterialFamily).filter(
                MaterialFamily.is_active == 1,
                MaterialFamily.category_id == category_id
            ).all():
                cache["families"][(f.family_name.strip().upper(), category_id)] = f.id
            cache["families"][key] = True

    def _populate_types(family_id: int):
        key = ("ALL", family_id)
        if key not in cache["types"]:
            for t in db.query(MaterialType).filter(
                MaterialType.is_active == 1,
                MaterialType.family_id == family_id
            ).all():
                cache["types"][(t.type_name.strip().upper(), family_id)] = t.id
            cache["types"][key] = True

    def _populate_products(type_id: int):
        key = ("ALL", type_id)
        if key not in cache["products"]:
            for p in db.query(ProductCatalog).filter(
                ProductCatalog.is_active == 1,
                ProductCatalog.type_id == type_id
            ).all():
                cache["products"][(p.product_name.strip().upper(), type_id)] = p.id
            cache["products"][key] = True

    def _populate_grades(product_id: int):
        key = ("ALL", product_id)
        if key not in cache["grades"]:
            for g in db.query(ProductGrade).filter(
                ProductGrade.is_active == 1,
                ProductGrade.product_id == product_id
            ).all():
                cache["grades"][(g.grade_name.strip().upper(), product_id)] = g.id
            cache["grades"][key] = True

    def _populate_dimensions(grade_id: int):
        key = ("ALL", grade_id)
        if key not in cache["dimensions"]:
            for d in db.query(ProductDimension).filter(
                ProductDimension.is_active == 1,
                ProductDimension.grade_id == grade_id
            ).all():
                cache["dimensions"][(d.dimension_value.strip().upper(), grade_id)] = d.id
            cache["dimensions"][key] = True

    def _populate_forms(type_id: int):
        key = ("ALL", type_id)
        if key not in cache["forms"]:
            for f in db.query(ProductForm).filter(
                ProductForm.is_active == 1,
                ProductForm.type_id == type_id
            ).all():
                cache["forms"][(f.form_name.strip().upper(), type_id)] = f.id
            cache["forms"][key] = True

    try:
        # Pre-populate locations (commonly used)
        _populate_locations()
        _populate_categories()
    except Exception as e:
        logger.error(f"Failed to load reference data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load reference data: {str(e)}")

    # --- B. Pre-fetch existing prices for bulk duplicate checking ---
    # Build a set of existing (product_id, grade_id, dimension_id, location_id, effective_from, base_price) tuples
    existing_prices_set = set()
    if not request.dry_run:
        try:
            # Get all active prices - we'll check against this set in memory
            all_active_prices = db.execute(text("""
                SELECT PRODUCT_ID, GRADE_ID, DIMENSION_ID, LOCATION_ID, EFFECTIVE_FROM, BASE_PRICE
                FROM SCRAPCY_APP.SCRAP_PRICES
                WHERE IS_ACTIVE = 1
            """)).fetchall()
            
            for p in all_active_prices:
                # Use -1 for NULL dimension_id to match NVL logic
                dim_id = p.DIMENSION_ID if p.DIMENSION_ID is not None else -1
                existing_prices_set.add((p.PRODUCT_ID, p.GRADE_ID, dim_id, p.LOCATION_ID, p.EFFECTIVE_FROM, float(p.BASE_PRICE)))
        except Exception as e:
            logger.error(f"Failed to load existing prices for duplicate check: {str(e)}")

    # Lists for bulk insert operations
    prices_to_insert = []
    sources_to_insert = []
    CHUNK_SIZE = 1000

    # --- C. Loop through Rows ---
    for i, row in enumerate(request.rows):
        row_index = i + 1
        try:
            # Parse date - handle both "2024-01-15" and "15/01/2024" formats
            parsed_date = None
            for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    parsed_date = datetime.strptime(row.date.strip(), fmt).date()
                    break
                except ValueError:
                    continue

            if not parsed_date:
                results.append(RowResult(
                    row_index=row_index,
                    status="error",
                    reason=f"Unrecognised date format: '{row.date}'"
                ))
                error_count += 1
                continue

            # Construct effective_from from date + time_slot
            slot_time = time(0, 0, 0) # default
            if row.time_slot:
                ts_str = row.time_slot.strip().upper()
                if ts_str in TIME_SLOT_MAP:
                    slot_time = TIME_SLOT_MAP[ts_str]
                else:
                    # Try to parse "HH:MM" or "HH:MM:SS" directly from the sheet
                    try:
                        slot_time = datetime.strptime(ts_str, "%H:%M").time()
                    except ValueError:
                        try:
                            slot_time = datetime.strptime(ts_str, "%H:%M:%S").time()
                        except ValueError:
                            logger.warning(f"Unrecognized time format: {ts_str}, defaulting to 00:00:00")
            
            effective_from = datetime.combine(parsed_date, slot_time)

            # --- ID Resolution ---
            # 1. CATEGORY_ID [HARD]
            _populate_categories()
            cat_id = cache["categories"].get(row.category.strip().upper())
            if not cat_id:
                unresolved.append(UnresolvedItem(
                    row_index=row_index,
                    field="category",
                    value=row.category,
                    full_row=row.model_dump(exclude={"source_prices"})
                ))
                results.append(RowResult(
                    row_index=row_index,
                    status="unresolved",
                    reason=f"category not found in catalog: '{row.category}'"
                ))
                continue

            # 2. FAMILY_ID [HARD]
            _populate_families(cat_id)
            family_id = cache["families"].get((row.material_family.strip().upper(), cat_id))
            if not family_id:
                unresolved.append(UnresolvedItem(
                    row_index=row_index,
                    field="material_family",
                    value=row.material_family,
                    full_row=row.model_dump(exclude={"source_prices"})
                ))
                results.append(RowResult(
                    row_index=row_index,
                    status="unresolved",
                    reason=f"material_family not found: '{row.material_family}'"
                ))
                continue

            # 3. TYPE_ID [HARD]
            _populate_types(family_id)
            type_id = cache["types"].get((row.material_type.strip().upper(), family_id))
            if not type_id:
                unresolved.append(UnresolvedItem(
                    row_index=row_index,
                    field="material_type",
                    value=row.material_type,
                    full_row=row.model_dump(exclude={"source_prices"})
                ))
                results.append(RowResult(
                    row_index=row_index,
                    status="unresolved",
                    reason=f"material_type not found: '{row.material_type}'"
                ))
                continue

            # 4. PRODUCT_ID [HARD]
            _populate_products(type_id)
            product_id = cache["products"].get((row.product_name.strip().upper(), type_id))
            if not product_id:
                unresolved.append(UnresolvedItem(
                    row_index=row_index,
                    field="product_name",
                    value=row.product_name,
                    full_row=row.model_dump(exclude={"source_prices"})
                ))
                results.append(RowResult(
                    row_index=row_index,
                    status="unresolved",
                    reason=f"product_name not found in catalog: '{row.product_name}'"
                ))
                continue

            # 5. GRADE_ID [HARD]
            _populate_grades(product_id)
            grade_id = cache["grades"].get((row.grade.strip().upper(), product_id))
            if not grade_id:
                unresolved.append(UnresolvedItem(
                    row_index=row_index,
                    field="grade",
                    value=row.grade,
                    full_row=row.model_dump(exclude={"source_prices"})
                ))
                results.append(RowResult(
                    row_index=row_index,
                    status="unresolved",
                    reason=f"grade not found: '{row.grade}'"
                ))
                continue

            # 6. DIMENSION_ID [SOFT]
            dimension_id = None
            if row.dimensions and row.dimensions.strip().upper() != "NA":
                _populate_dimensions(grade_id)
                dimension_id = cache["dimensions"].get((row.dimensions.strip().upper(), grade_id))
                if not dimension_id:
                    logger.warning(f"Row {row_index}: Dimension '{row.dimensions}' not found, setting to NULL")
                    dimension_id = None

            # 7. FORM_ID [SOFT]
            form_id = None
            if row.form and row.form.strip().upper() != "NA":
                _populate_forms(type_id)
                form_id = cache["forms"].get((row.form.strip().upper(), type_id))
                if not form_id:
                    logger.warning(f"Row {row_index}: Form '{row.form}' not found, setting to NULL")
                    form_id = None

            # 8. LOCATION_ID [HARD]
            _populate_locations()
            loc_id = cache["locations"].get(row.location.strip().upper())
            if not loc_id:
                # Fallback: search SEARCH_ALIASES column
                loc_id = cache["locations"].get(f",{row.location.strip().upper()},")
                if not loc_id:
                    unresolved.append(UnresolvedItem(
                        row_index=row_index,
                        field="location",
                        value=row.location,
                        full_row=row.model_dump(exclude={"source_prices"})
                    ))
                    results.append(RowResult(
                        row_index=row_index,
                        status="unresolved",
                        reason=f"location not found: '{row.location}'"
                    ))
                    continue

            # --- Duplicate check (in-memory) ---
            dim_id_for_check = dimension_id if dimension_id is not None else -1
            dup_key = (product_id, grade_id, dim_id_for_check, loc_id, effective_from, float(row.price))
            
            if dup_key in existing_prices_set:
                results.append(RowResult(
                    row_index=row_index,
                    status="skipped",
                    product_code=None,
                    location=row.location,
                    price=row.price,
                    sources_inserted=0,
                    reason="identical price already recorded for today"
                ))
                skipped_count += 1
                continue

            # --- Skip if dry_run ---
            if request.dry_run:
                results.append(RowResult(
                    row_index=row_index,
                    status="success",
                    product_code=None,
                    location=row.location,
                    price=row.price,
                    sources_inserted=0,
                    reason="dry_run - no insert"
                ))
                inserted_count += 1
                continue

            # --- Prepare SCRAP_PRICES for bulk insert ---
            created_by = f"n8n|SHEET_SYNC|{row.time_slot or 'NO_SLOT'}"
            new_price = ScrapPrice(
                product_id=product_id,
                grade_id=grade_id,
                dimension_id=dimension_id,
                form_id=form_id,
                location_id=loc_id,
                base_price=row.price,
                price_unit=row.per_unit,
                currency=row.currency,
                effective_from=effective_from,
                is_active=1,
                source=request.source,
                created_by=created_by,
                # DO NOT SET: product_code (trigger-managed)
                # DO NOT SET: effective_to (trigger-managed)
                # DO NOT SET: updated_at (trigger-managed)
            )
            prices_to_insert.append((new_price, row_index, row.location, row.price))

            # --- Prepare SCRAP_PRICE_SOURCES for bulk insert ---
            sources_inserted = 0
            for source_name, source_price in row.source_prices.items():
                # Skip if value is None, empty, or zero
                if source_price is None:
                    continue

                source_row = ScrapPriceSource(
                    price_id=None,  # Will be set after flush
                    source_name=source_name.upper(),  # normalise to uppercase
                    source_price=source_price,
                    price_unit=None,  # inherit from parent
                    currency=None,    # inherit from parent
                    variance=source_price - row.price,  # SOURCE_PRICE - BASE_PRICE
                    notes=None,
                    recorded_at=effective_from
                )
                sources_to_insert.append((source_row, len(prices_to_insert) - 1))  # Index into prices_to_insert
                sources_inserted += 1

            # Track sources count for this row
            results.append(RowResult(
                row_index=row_index,
                status="pending",  # Will be updated after flush
                product_code=None,  # Will be updated after flush
                location=row.location,
                price=row.price,
                sources_inserted=sources_inserted,
                reason=None
            ))
            inserted_count += 1

            # --- Chunk processing: flush when reaching CHUNK_SIZE ---
            if len(prices_to_insert) >= CHUNK_SIZE:
                # Add all prices in chunk
                for price_obj, _, _, _ in prices_to_insert:
                    db.add(price_obj)
                db.flush()  # This populates price_obj.id via trigger
                
                # Add the corresponding sources (now that IDs are populated)
                for source_obj, price_idx in sources_to_insert:
                    source_obj.price_id = prices_to_insert[price_idx][0].id
                    db.add(source_obj)
                db.flush()  # Flush sources
                
                # Update results with product codes and mark as success
                for j, (price_obj, r_idx, r_loc, r_price) in enumerate(prices_to_insert):
                    results[r_idx - 1] = RowResult(
                        row_index=r_idx,
                        status="success",
                        product_code=price_obj.product_code,
                        location=r_loc,
                        price=r_price,
                        sources_inserted=results[r_idx - 1].sources_inserted,
                        reason=None
                    )
                
                # Clear lists for next chunk
                prices_to_insert = []
                sources_to_insert = []

        except Exception as e:
            logger.error(f"Row {row_index} processing error: {str(e)}")
            results.append(RowResult(
                row_index=row_index,
                status="error",
                reason=str(e)
            ))
            error_count += 1

    # --- Flush remaining items after loop ---
    if prices_to_insert and not request.dry_run:
        try:
            # Add all remaining prices
            for price_obj, _, _, _ in prices_to_insert:
                db.add(price_obj)
            db.flush()
            
            # Add the corresponding sources
            for source_obj, price_idx in sources_to_insert:
                source_obj.price_id = prices_to_insert[price_idx][0].id
                db.add(source_obj)
            db.flush()
            
            # Update results with product codes and mark as success
            for j, (price_obj, r_idx, r_loc, r_price) in enumerate(prices_to_insert):
                results[r_idx - 1] = RowResult(
                    row_index=r_idx,
                    status="success",
                    product_code=price_obj.product_code,
                    location=r_loc,
                    price=r_price,
                    sources_inserted=results[r_idx - 1].sources_inserted,
                    reason=None
                )
        except Exception as e:
            logger.error(f"Failed to flush remaining items: {str(e)}")
            # Mark remaining as errors
            for _, r_idx, _, _ in prices_to_insert:
                results[r_idx - 1] = RowResult(
                    row_index=r_idx,
                    status="error",
                    reason=f"Flush failed: {str(e)}"
                )

    # --- D. Commit Changes ---
    if not request.dry_run:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            return BulkSheetSyncResponse(
                total=len(request.rows),
                inserted=0,
                skipped=0,
                errors=len(request.rows),
                unresolved_count=0,
                dry_run=False,
                results=[RowResult(row_index=i+1, status="error", reason=f"Commit failed: {str(e)}") 
                        for i in range(len(request.rows))],
                unresolved=[]
            )

    logger.info(f"Bulk sheet sync completed: {inserted_count} inserted, {skipped_count} skipped, {error_count} errors, {len(unresolved)} unresolved")

    return BulkSheetSyncResponse(
        total=len(request.rows),
        inserted=inserted_count,
        skipped=skipped_count,
        errors=error_count,
        unresolved_count=len(unresolved),
        dry_run=request.dry_run,
        results=results,
        unresolved=unresolved,
    )
