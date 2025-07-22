"""
Unified output formatter for OOPStracker.
Centralizes all output formatting logic for consistency.
"""

from typing import List, Dict, Any, Optional
import json


class OutputFormatter:
    """Centralized output formatting utilities."""
    
    # Unicode icons for different output types
    ICONS = {
        'search': '🔍',
        'folder': '📂',
        'file': '📝',
        'stats': '📊',
        'warning': '⚠️',
        'success': '✅',
        'error': '❌',
        'info': '💡',
        'time': '⏳',
        'reload': '🔄',
        'target': '🎯',
        'science': '🔬',
        'web': '🕸️',
        'link': '🔗',
        'tag': '🏷️',
        'hash': '🔍',
        'clock': '⏰',
        'doc': '📋',
        'code': '💻'
    }
    
    @classmethod
    def icon(cls, icon_type: str) -> str:
        """Get icon for the given type."""
        return cls.ICONS.get(icon_type, '')
        
    @classmethod
    def header(cls, text: str, icon_type: Optional[str] = None) -> str:
        """Format a section header."""
        icon = cls.icon(icon_type) + ' ' if icon_type else ''
        return f"\n{icon}{text}"
        
    @classmethod
    def subheader(cls, text: str, level: int = 1) -> str:
        """Format a subsection header."""
        indent = '   ' * level
        return f"{indent}{text}"
        
    @classmethod
    def item(cls, text: str, level: int = 1, bullet: str = '•') -> str:
        """Format a list item."""
        indent = '   ' * level
        return f"{indent}{bullet} {text}"
        
    @classmethod
    def progress(cls, current: int, total: int, unit: str = 'items') -> str:
        """Format progress information."""
        percentage = (current / total * 100) if total > 0 else 0
        return f"{cls.icon('time')} Processing: {current}/{total} {unit} ({percentage:.1f}%)"
        
    @classmethod
    def summary_section(cls, title: str, items: Dict[str, Any]) -> str:
        """Format a summary section with key-value pairs."""
        lines = [cls.header(title, 'stats')]
        
        for key, value in items.items():
            lines.append(f"   {key}: {value}")
            
        return '\n'.join(lines)
        
    @classmethod
    def table(cls, headers: List[str], rows: List[List[Any]], 
             max_widths: Optional[Dict[int, int]] = None) -> str:
        """Format data as a table.
        
        Args:
            headers: List of column headers
            rows: List of row data
            max_widths: Optional dict mapping column index to max width
            
        Returns:
            Formatted table string
        """
        if not rows:
            return "No data to display"
            
        # Calculate column widths
        widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
                
        # Apply max widths if specified
        if max_widths:
            for col_idx, max_width in max_widths.items():
                if col_idx < len(widths):
                    widths[col_idx] = min(widths[col_idx], max_width)
                    
        # Format header
        header_row = ' '.join(
            str(headers[i]).ljust(widths[i]) for i in range(len(headers))
        )
        separator = '-' * len(header_row)
        
        lines = [header_row, separator]
        
        # Format rows
        for row in rows:
            formatted_cells = []
            for i, cell in enumerate(row):
                cell_str = str(cell)
                if max_widths and i in max_widths and len(cell_str) > max_widths[i]:
                    cell_str = cell_str[:max_widths[i]-3] + '...'
                formatted_cells.append(cell_str.ljust(widths[i]))
            lines.append(' '.join(formatted_cells))
            
        return '\n'.join(lines)
        
    @classmethod
    def json_output(cls, data: Any, indent: int = 2) -> str:
        """Format data as JSON."""
        return json.dumps(data, indent=indent, default=str)
        
    @classmethod
    def error(cls, message: str) -> str:
        """Format an error message."""
        return f"{cls.icon('error')} Error: {message}"
        
    @classmethod
    def warning(cls, message: str) -> str:
        """Format a warning message."""
        return f"{cls.icon('warning')} Warning: {message}"
        
    @classmethod
    def success(cls, message: str) -> str:
        """Format a success message."""
        return f"{cls.icon('success')} {message}"
        
    @classmethod
    def info(cls, message: str) -> str:
        """Format an info/tip message."""
        return f"{cls.icon('info')} {message}"
        
    @classmethod
    def format_file_path(cls, file_path: str, line_number: Optional[int] = None) -> str:
        """Format a file path with optional line number."""
        if line_number:
            return f"{file_path}:{line_number}"
        return file_path
        
    @classmethod
    def format_percentage(cls, value: float, decimals: int = 1) -> str:
        """Format a percentage value."""
        return f"{value:.{decimals}f}%"
        
    @classmethod
    def format_similarity(cls, similarity: float) -> str:
        """Format a similarity score."""
        return f"{similarity:.3f}"
        
    @classmethod
    def truncate(cls, text: str, max_length: int, suffix: str = '...') -> str:
        """Truncate text to specified length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix