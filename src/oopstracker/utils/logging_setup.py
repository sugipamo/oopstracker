"""
Logging setup utilities for OOPStracker.
"""
import logging


def setup_logging(level: str = "WARNING"):
    """Set up logging configuration."""
    # Create a custom formatter that shortens module names
    class ShortNameFormatter(logging.Formatter):
        def format(self, record):
            # Shorten the logger name to just the last component
            parts = record.name.split('.')
            if len(parts) > 1:
                record.short_name = parts[-1]
            else:
                record.short_name = record.name
            return super().format(record)
    
    # Configure root logger
    handler = logging.StreamHandler()
    
    # Only show timestamps and messages for INFO level, more detail for DEBUG
    if level.upper() == "INFO":
        # Simplified format for INFO level
        formatter = ShortNameFormatter('%(message)s')
    else:
        # More detailed format for DEBUG level
        formatter = ShortNameFormatter('%(asctime)s - %(short_name)s - %(levelname)s - %(message)s')
    
    handler.setFormatter(formatter)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(handler)
    
    # Suppress verbose logging from specific modules
    if level.upper() in ["INFO", "WARNING"]:
        logging.getLogger('oopstracker.ast_simhash_detector').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.ast_database').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.ignore_patterns').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.intent_tree_fixed_adapter').setLevel(logging.WARNING)
        logging.getLogger('oopstracker.intent_tree_adapter').setLevel(logging.WARNING)
        # Suppress external library logs
        logging.getLogger('intent_unified').setLevel(logging.WARNING)
        logging.getLogger('llm_providers').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('intent_tree').setLevel(logging.WARNING)
        logging.getLogger('intent_tree.core').setLevel(logging.WARNING)
        logging.getLogger('intent_tree.data').setLevel(logging.WARNING)