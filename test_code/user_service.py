"""User service with some potential duplicates."""

def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone format."""
    import re
    pattern = r'^\+?1?[0-9]{10,15}$'
    return re.match(pattern, phone) is not None

def process_user_registration(user_data: dict) -> dict:
    """Process user registration with validation."""
    # Validate email
    if not user_data.get('email'):
        return {'error': 'Email is required'}
    
    if not validate_email(user_data['email']):
        return {'error': 'Invalid email format'}
    
    # Validate phone
    if not user_data.get('phone'):
        return {'error': 'Phone is required'}
    
    if not validate_phone(user_data['phone']):
        return {'error': 'Invalid phone format'}
    
    # Process registration
    return {'success': True, 'user_id': 12345}

def process_user_update(user_data: dict) -> dict:
    """Process user profile update with validation."""
    # Validate email
    if not user_data.get('email'):
        return {'error': 'Email is required'}
    
    if not validate_email(user_data['email']):
        return {'error': 'Invalid email format'}
    
    # Validate phone
    if not user_data.get('phone'):
        return {'error': 'Phone is required'}
    
    if not validate_phone(user_data['phone']):
        return {'error': 'Invalid phone format'}
    
    # Process update
    return {'success': True, 'updated': True}

class UserValidator:
    """User data validator."""
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone format."""
        import re
        pattern = r'^\+?1?[0-9]{10,15}$'
        return re.match(pattern, phone) is not None