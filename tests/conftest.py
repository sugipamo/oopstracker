"""Fixtures for oopstracker tests."""

import pytest
from oopstracker.ast_analyzer import ASTAnalyzer
from oopstracker.core.simhash import SimHashCalculator
from oopstracker.core.analyzer.code_analyzer import CodeAnalyzer


@pytest.fixture
def ast_analyzer():
    """Create an ASTAnalyzer instance."""
    return ASTAnalyzer()


@pytest.fixture
def simhash_calculator():
    """Create a SimHashCalculator instance."""
    return SimHashCalculator()


@pytest.fixture
def code_analyzer(ast_analyzer, simhash_calculator):
    """Create a CodeAnalyzer instance with required dependencies."""
    return CodeAnalyzer(ast_analyzer, simhash_calculator)