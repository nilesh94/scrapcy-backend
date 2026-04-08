#!/usr/bin/env python3
"""
Test script to validate the SCRAP_PRICES v4 implementation.
This script checks that all the required components are properly implemented.
"""

import sys
import importlib.util
from pathlib import Path

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    
    # Test models import
    try:
        from app.models.scrap_master import (
            ProductCategory, MaterialFamily, MaterialType, 
            ProductCatalog, ProductGrade, ProductDimension, 
            ProductForm, ScrapPrice, ScrapPriceSource
        )
        print("✓ Models imported successfully")
    except ImportError as e:
        print(f"✗ Models import failed: {e}")
        return False
    
    # Test schemas import
    try:
        from app.schemas.scrap_master import (
            ProductCategoryOut, ScrapPriceRead, BulkSheetSyncRequest,
            BulkSheetSyncResponse, SheetPriceRow, ScrapPriceSourceOut,
            UnresolvedItem, RowResult
        )
        print("✓ Schemas imported successfully")
    except ImportError as e:
        print(f"✗ Schemas import failed: {e}")
        return False
    
    # Test routes import
    try:
        from app.routes.scrap_prices import router
        print("✓ Routes imported successfully")
    except ImportError as e:
        print(f"✗ Routes import failed: {e}")
        return False
    
    return True

def test_model_structure():
    """Test that models have the correct structure."""
    print("\nTesting model structure...")
    
    from app.models.scrap_master import ScrapPrice, ScrapPriceSource
    
    # Check ScrapPrice has correct columns
    scrap_price_columns = [col.name for col in ScrapPrice.__table__.columns]
    required_columns = ['product_id', 'grade_id', 'dimension_id', 'form_id', 'location_id', 'base_price']
    
    for col in required_columns:
        if col in scrap_price_columns:
            print(f"✓ ScrapPrice has {col}")
        else:
            print(f"✗ ScrapPrice missing {col}")
            return False
    
    # Check ScrapPriceSource has correct columns
    scrap_price_source_columns = [col.name for col in ScrapPriceSource.__table__.columns]
    required_source_columns = ['price_id', 'source_name', 'source_price', 'variance']
    
    for col in required_source_columns:
        if col in scrap_price_source_columns:
            print(f"✓ ScrapPriceSource has {col}")
        else:
            print(f"✗ ScrapPriceSource missing {col}")
            return False
    
    # Check relationships
    if hasattr(ScrapPrice, 'price_sources'):
        print("✓ ScrapPrice has price_sources relationship")
    else:
        print("✗ ScrapPrice missing price_sources relationship")
        return False
    
    if hasattr(ScrapPriceSource, 'price'):
        print("✓ ScrapPriceSource has price relationship")
    else:
        print("✗ ScrapPriceSource missing price relationship")
        return False
    
    return True

def test_schema_structure():
    """Test that schemas have the correct structure."""
    print("\nTesting schema structure...")
    
    from app.schemas.scrap_master import (
        ScrapPriceRead, BulkSheetSyncResponse, SheetPriceRow
    )
    
    # Check ScrapPriceRead has required fields
    scrap_price_read_fields = ScrapPriceRead.model_fields.keys()
    required_fields = ['price_id', 'product_code', 'base_price', 'sources', 'source_count']
    
    for field in required_fields:
        if field in scrap_price_read_fields:
            print(f"✓ ScrapPriceRead has {field}")
        else:
            print(f"✗ ScrapPriceRead missing {field}")
            return False
    
    # Check BulkSheetSyncResponse has required fields
    bulk_response_fields = BulkSheetSyncResponse.model_fields.keys()
    required_response_fields = ['total', 'inserted', 'skipped', 'errors', 'unresolved_count', 'results', 'unresolved']
    
    for field in required_response_fields:
        if field in bulk_response_fields:
            print(f"✓ BulkSheetSyncResponse has {field}")
        else:
            print(f"✗ BulkSheetSyncResponse missing {field}")
            return False
    
    # Check SheetPriceRow has source_prices field
    sheet_row_fields = SheetPriceRow.model_fields.keys()
    if 'source_prices' in sheet_row_fields:
        print("✓ SheetPriceRow has source_prices field")
    else:
        print("✗ SheetPriceRow missing source_prices field")
        return False
    
    return True

def test_route_endpoints():
    """Test that routes have the correct endpoints."""
    print("\nTesting route endpoints...")
    
    from app.routes.scrap_prices import router
    
    # Check that router has the required endpoints
    endpoints = [route.path for route in router.routes]
    
    required_endpoints = [
        '/scrap-prices/master-catalog',
        '/scrap-prices/current-prices', 
        '/scrap-prices/price-history/{product_code}',
        '/scrap-prices/bulk-sheet-sync'
    ]
    
    for endpoint in required_endpoints:
        if endpoint in endpoints:
            print(f"✓ Router has {endpoint}")
        else:
            print(f"✗ Router missing {endpoint}")
            return False
    
    return True

def main():
    """Run all tests."""
    print("SCRAP_PRICES v4 Implementation Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_model_structure,
        test_schema_structure,
        test_route_endpoints
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! Implementation looks good.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())