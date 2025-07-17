"""Test AST similarity calculation issues"""

from oopstracker.ast_analyzer import ASTAnalyzer

# Test case: Different Pydantic models that are incorrectly detected as identical
code1 = '''
class DeleteRequest(BaseModel):
    id: int = Field(..., description='ID of the record to delete')
'''

code2 = '''
class DeleteResponse(BaseModel):
    status: str = Field(..., description='Operation status')
'''

code3 = '''
class ListResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(..., description='List of all code records')
    total: int = Field(..., description='Total number of records')
'''

analyzer = ASTAnalyzer()

# Parse all three models
units = []
for i, code in enumerate([code1, code2, code3], 1):
    parsed = analyzer.parse_code(code)
    if parsed:
        units.append(parsed[0])
        print(f"\nCode {i} AST structure:")
        print(f"  Raw: {parsed[0].ast_structure}")
        print(f"  Tokens: {set(parsed[0].ast_structure.split('|'))}")

# Compare similarities
if len(units) == 3:
    print("\n\nSimilarity comparisons:")
    print(f"DeleteRequest vs DeleteResponse: {analyzer.calculate_structural_similarity(units[0], units[1]):.3f}")
    print(f"DeleteRequest vs ListResponse: {analyzer.calculate_structural_similarity(units[0], units[2]):.3f}")
    print(f"DeleteResponse vs ListResponse: {analyzer.calculate_structural_similarity(units[1], units[2]):.3f}")
    
    # Show why they're considered identical
    print("\n\nToken analysis:")
    tokens1 = set(units[0].ast_structure.split('|'))
    tokens2 = set(units[1].ast_structure.split('|'))
    tokens3 = set(units[2].ast_structure.split('|'))
    
    print(f"DeleteRequest unique tokens: {tokens1}")
    print(f"DeleteResponse unique tokens: {tokens2}")
    print(f"ListResponse unique tokens: {tokens3}")
    
    print(f"\nAre DeleteRequest and DeleteResponse token sets identical? {tokens1 == tokens2}")
    print(f"Jaccard similarity calculation: {len(tokens1 & tokens2)} / {len(tokens1 | tokens2)} = {len(tokens1 & tokens2) / len(tokens1 | tokens2):.3f}")