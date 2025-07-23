"""Visitor for class-related AST nodes."""
import ast
from .base import BaseStructureVisitor


class ClassVisitor(BaseStructureVisitor):
    """
    Specializes in extracting class-related structural information.
    Handles class definitions, inheritance, decorators, and methods.
    """
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.structure_tokens.append(f"CLASS:{len(node.bases)}")
        self.complexity += 1
        
        # Delegate specific processing to dedicated methods
        self._process_decorators(node.decorator_list)
        self._process_base_classes(node.bases)
        self._process_keywords(node.keywords)
        self._process_methods(node.body)
        
        self.generic_visit(node)
    
    def _process_decorators(self, decorator_list):
        """Process class decorators."""
        self.structure_tokens.append(f"CLASS_DECORATOR:{len(decorator_list)}")
        for decorator in decorator_list:
            self._process_single_decorator(decorator)
    
    def _process_single_decorator(self, decorator):
        """Process a single decorator."""
        if isinstance(decorator, ast.Name):
            self.structure_tokens.append(f"DECORATOR_NAME:{decorator.id}")
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            self.structure_tokens.append(f"DECORATOR_CALL:{decorator.func.id}")
    
    def _process_base_classes(self, bases):
        """Process base classes (inheritance)."""
        for base in bases:
            if isinstance(base, ast.Name):
                self.structure_tokens.append(f"BASE:{base.id}")
                self.dependencies.add(base.id)
            elif isinstance(base, ast.Attribute):
                self._process_attribute_base(base)
    
    def _process_attribute_base(self, base):
        """Process attribute-style base class (e.g., module.Class)."""
        if isinstance(base.value, ast.Name):
            self.structure_tokens.append(f"BASE_ATTR:{base.value.id}.{base.attr}")
            self.dependencies.add(base.value.id)
    
    def _process_keywords(self, keywords):
        """Process class keywords (e.g., metaclass)."""
        for keyword in keywords:
            if keyword.arg == "metaclass":
                self.structure_tokens.append("METACLASS")
                if isinstance(keyword.value, ast.Name):
                    self.structure_tokens.append(f"METACLASS_NAME:{keyword.value.id}")
    
    def _process_methods(self, body):
        """Process class methods and attributes."""
        method_count = 0
        property_count = 0
        static_method_count = 0
        class_method_count = 0
        
        for item in body:
            if isinstance(item, ast.FunctionDef):
                method_count += 1
                self._categorize_method(item, property_count, static_method_count, class_method_count)
            elif isinstance(item, ast.AnnAssign):
                # Class attribute with type annotation
                self.structure_tokens.append("CLASS_ATTR_ANNOTATED")
            elif isinstance(item, ast.Assign):
                # Class attribute
                self.structure_tokens.append("CLASS_ATTR")
        
        self.structure_tokens.append(f"METHODS:{method_count}")
        if property_count > 0:
            self.structure_tokens.append(f"PROPERTIES:{property_count}")
        if static_method_count > 0:
            self.structure_tokens.append(f"STATIC_METHODS:{static_method_count}")
        if class_method_count > 0:
            self.structure_tokens.append(f"CLASS_METHODS:{class_method_count}")
    
    def _categorize_method(self, method, property_count, static_method_count, class_method_count):
        """Categorize a method based on its decorators."""
        for decorator in method.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name == "property":
                property_count += 1
            elif decorator_name == "staticmethod":
                static_method_count += 1
            elif decorator_name == "classmethod":
                class_method_count += 1
        
        # Check for special method names
        if method.name.startswith("__") and method.name.endswith("__"):
            self.structure_tokens.append(f"DUNDER:{method.name}")
    
    def _get_decorator_name(self, decorator):
        """Extract decorator name from decorator node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr
        return None
    
    def visit_Attribute(self, node):
        """Visit attribute access (e.g., self.attr, obj.method)."""
        if isinstance(node.value, ast.Name):
            if node.value.id == "self":
                self.structure_tokens.append(f"SELF_ATTR:{node.attr}")
            elif node.value.id == "cls":
                self.structure_tokens.append(f"CLS_ATTR:{node.attr}")
            else:
                self.structure_tokens.append(f"ATTR:{node.value.id}.{node.attr}")
        self.generic_visit(node)