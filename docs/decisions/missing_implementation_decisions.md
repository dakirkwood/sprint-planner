# Missing Implementation Items - Phase 1 Decisions

## Overview
Decisions made for three implementation items that needed clarification for Claude Code's first phase implementation.

## 1. On-Demand "Explain this error" LLM Calls

### Decision: Dedicated Provider with Placeholder Implementation
- **Provider Strategy**: Use dedicated `LLM_ERROR_EXPLANATION_PROVIDER` environment variable
- **Default**: Same as `LLM_DEFAULT_PROVIDER` but allows future divergence for A/B testing
- **Phase 1 Scope**: Interface/placeholder only, no full implementation

### LLM Service Interface
```python
class LLMService:
    async def explain_error(self, error_context: dict) -> str:
        # Placeholder - just return the original error message
        return error_context.get('user_message', 'Error explanation not available')
```

### Rationale
- Enables future A/B testing of error explanation quality
- Consistent experience can be optimized independently from ticket generation
- Placeholder allows API contract to be established without full implementation

## 2. Hard-coded Relationship/Dependency Definitions

### Decision: Infer from Sample Data Analysis
- **Approach**: Claude Code analyzes UWEC sample CSV files to discover relationships
- **Pattern Recognition**: Standard Drupal entity relationships (linear dependencies)
- **Auto-generate**: Both cross-file validation rules and dependency ordering

### Expected Relationships (to be discovered)
- **Fields** → **Bundles** (via "Bundle" column → "Machine name")
- **Custom Views Displays** → **Custom Views** (via "View" column → "View name")
- **Workflow States** → **Workflows** (via "Workflow" column → "Machine name")
- **Workflow Transitions** → **Workflows + States** (via workflow and state references)
- **Responsive Image Styles** → **Image Styles** (via "Fallback Style" → "Machine name")

### Dependency Ordering Pattern
- Content Types (Bundles) → Fields
- Views → View Displays
- Workflows → Workflow States → Workflow Transitions
- Image Styles → Responsive Image Styles

### Rationale
- Drupal relationships follow established, discoverable patterns
- Sample data contains sufficient information for relationship inference
- Reduces manual configuration while maintaining accuracy

## 3. Rules for CSV Validation

### Decision: Build Modifiable Dictionary-Based Validation System
- **Approach**: Claude Code analyzes UWEC sample data to build validation rule registry
- **Structure**: Dictionary/list format for easy manual modification
- **Scope**: Reasonable rules from observed patterns, refineable afterward

### CSV Type Registry Structure
```python
CSV_TYPE_REGISTRY = {
    "bundles": {
        "label": "Content Types (Bundles)",
        "required_columns": ["Machine name", "Name"],
        "optional_columns": ["Description", "Type", "Settings/notes"],
        "validation_rules": {
            "Machine name": {
                "type": "machine_name",
                "pattern": r"^[a-z][a-z0-9_]*$",
                "error_msg": "Must be lowercase letters, numbers, and underscores only"
            },
            "Dev": {"type": "number", "allow_empty": True},
            "QA": {"type": "number", "allow_empty": True},
            "Type": {"type": "choice", "choices": ["node", "media", "taxonomy"], "allow_empty": True}
        }
    },
    "fields": {
        "required_columns": ["Machine name", "Field label", "Bundle"],
        "validation_rules": {
            "Bundle": {
                "type": "reference",
                "references_csv": "bundles", 
                "references_column": "Machine name"
            },
            "Field type": {
                "type": "choice",
                "choices": ["text", "number", "email", "entity_reference"],
                "allow_empty": True
            }
        }
    }
}
```

### Validation Rule Types
- **machine_name**: Lowercase letters, numbers, underscores
- **number**: Numeric values, empty allowed
- **choice**: Predefined list of valid values
- **reference**: Cross-file relationship validation

### Rationale
- Data structure format enables easy manual refinement
- Rules built from actual sample data patterns
- Covers common Drupal validation needs
- Extensible for future CSV types and validation requirements

## Implementation Impact for Claude Code

### Phase 1 Deliverables
1. **LLM Service Interface**: Placeholder method with proper signature
2. **Relationship Discovery**: Auto-built mapping from UWEC CSV analysis
3. **Validation Registry**: Complete dictionary-based validation system
4. **Easy Modification**: All rules in easily editable data structures

### Future Enhancement Path
- LLM error explanations can be implemented by replacing placeholder
- Relationship mappings can be adjusted by modifying discovered dictionary
- Validation rules can be refined by updating registry entries
- New CSV types can be added by extending registry structure

## Success Criteria
- ✅ Error explanation API endpoint works with placeholder responses
- ✅ Cross-file validation catches relationship violations using discovered mappings
- ✅ CSV validation provides meaningful error messages using generated rules
- ✅ All validation logic easily modifiable through dictionary updates
- ✅ System extensible for future CSV types and validation patterns