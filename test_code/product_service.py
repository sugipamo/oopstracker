"""Product service with similar patterns."""

def validate_product_name(name: str) -> bool:
    """Validate product name format."""
    import re
    pattern = r'^[a-zA-Z0-9\s\-_]{3,50}$'
    return re.match(pattern, name) is not None

def validate_product_price(price: float) -> bool:
    """Validate product price."""
    return price > 0 and price <= 10000

def process_product_creation(product_data: dict) -> dict:
    """Process product creation with validation."""
    # Validate name
    if not product_data.get('name'):
        return {'error': 'Product name is required'}
    
    if not validate_product_name(product_data['name']):
        return {'error': 'Invalid product name format'}
    
    # Validate price
    if not product_data.get('price'):
        return {'error': 'Price is required'}
    
    if not validate_product_price(product_data['price']):
        return {'error': 'Invalid price range'}
    
    # Process creation
    return {'success': True, 'product_id': 67890}

def process_product_update(product_data: dict) -> dict:
    """Process product update with validation."""
    # Validate name
    if not product_data.get('name'):
        return {'error': 'Product name is required'}
    
    if not validate_product_name(product_data['name']):
        return {'error': 'Invalid product name format'}
    
    # Validate price
    if not product_data.get('price'):
        return {'error': 'Price is required'}
    
    if not validate_product_price(product_data['price']):
        return {'error': 'Invalid price range'}
    
    # Process update
    return {'success': True, 'updated': True}