"""
AST analysis module for structural code analysis.
Provides modular components for AST parsing and structure extraction.
"""

from .models import CodeUnit, ASTFeatures
from .extractors import (
    StructureExtractor,
    ComplexityExtractor,
    DependencyExtractor,
    TypeExtractor
)
from .visitors import (
    FunctionVisitor,
    ClassVisitor,
    ControlFlowVisitor,
    ExpressionVisitor
)
from .analyzer import ASTAnalyzer
from .similarity import SimilarityCalculator

__all__ = [
    'CodeUnit',
    'ASTFeatures',
    'StructureExtractor',
    'ComplexityExtractor',
    'DependencyExtractor',
    'TypeExtractor',
    'FunctionVisitor',
    'ClassVisitor',
    'ControlFlowVisitor',
    'ExpressionVisitor',
    'ASTAnalyzer',
    'SimilarityCalculator'
]