# CSV Type Registry Structure Specification - Drupal Ticket Generator

## Overview
Unified specification for CSV type registry structure to resolve conflicting approaches across documentation and establish a single, implementable pattern.

## Conflicting Specifications Identified

### **Conflict 1: Registry Structure**
- **`missing_implementation_decisions.md`**: Nested dictionary with validation rules
- **`upload_service_architecture.md`**: Dataclass with CSVTypeDefinition
- **`fastapi_upload_endpoints.md`**: Processor-based registry

### **Conflict 2: Validation Approach**
- **Rules-based**: Validation rules embedded in registry
- **Processor-based**: Separate processor classes for each CSV type
- **Schema-based**: Dataclass definitions with detection patterns

### **Conflict 3: Detection Strategy**
- **Column-based**: Detect by required/optional columns
- **Pattern-based**: Detect by filename patterns
- **Content-based**: Detect by analyzing actual CSV content

## Decision: Unified Registry with Embedded Validation

### **Registry Structure: Comprehensive Dictionary Approach**
```python
# /backend/app/utils/csv/registry.py
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

@dataclass
class ValidationRule:
    """Individual column validation rule"""
    type: str  # "machine_name", "number", "choice", "reference", "text", "email"
    required: bool = True
    allow_empty: bool = False
    pattern: Optional[str] = None
    choices: Optional[List[str]] = None
    references_csv: Optional[str] = None
    references_column: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class CSVTypeDefinition:
    """Complete CSV type definition"""
    label: str
    required_columns: List[str]
    optional_columns: List[str]
    validation_rules: Dict[str, ValidationRule]
    detection_patterns: Dict[str, Any]
    entity_group: str  # "Content", "Media", "Views", "Migration", "Workflow", "User Roles", "Custom"
    
    def validate_column(self, column_name: str, value: Any, context: Dict) -> Optional[str]:
        """Validate individual column value, return error message if invalid"""
        pass
    
    def detect_from_filename(self, filename: str) -> float:
        """Return confidence score (0.0-1.0) for filename match"""
        pass
    
    def detect_from_content(self, headers: List[str], sample_rows: List[Dict]) -> float:
        """Return confidence score (0.0-1.0) for content match"""
        pass

# Main registry - Each CSV type has completely different column structures
CSV_TYPE_REGISTRY: Dict[str, CSVTypeDefinition] = {
    "bundles": CSVTypeDefinition(
        label="Content Types (Bundles)",
        required_columns=["Machine name", "Name"],
        optional_columns=["Description", "Type", "Settings/notes", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "Name": ValidationRule(
                type="text",
                error_message="Bundle name is required"
            ),
            "Type": ValidationRule(
                type="choice",
                choices=["node", "media", "taxonomy"],
                allow_empty=True,
                error_message="Type must be one of: node, media, taxonomy"
            ),
            "Dev": ValidationRule(
                type="number",
                allow_empty=True,
                error_message="Dev count must be a number"
            ),
            "QA": ValidationRule(
                type="number", 
                allow_empty=True,
                error_message="QA count must be a number"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*bundle.*\.csv$", r".*content.*type.*\.csv$"],
            "header_keywords": ["Machine name", "Bundle", "Content Type"],
            "content_indicators": ["node", "media", "taxonomy"]
        },
        entity_group="Content"
    ),
    
    "fields": CSVTypeDefinition(
        label="Fields",
        required_columns=["Machine name", "Field label", "Bundle"],
        optional_columns=["Field type", "Description", "Required", "Widget", "Formatter", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "Field label": ValidationRule(
                type="text",
                error_message="Field label is required"
            ),
            "Bundle": ValidationRule(
                type="reference",
                references_csv="bundles",
                references_column="Machine name",
                error_message="Bundle must reference an existing bundle machine name"
            ),
            "Field type": ValidationRule(
                type="choice",
                choices=["text", "number", "email", "entity_reference", "image", "file", "datetime", "boolean"],
                allow_empty=True,
                error_message="Field type must be a valid Drupal field type"
            ),
            "Required": ValidationRule(
                type="choice",
                choices=["Yes", "No", "1", "0", "true", "false"],
                allow_empty=True,
                error_message="Required must be Yes/No or 1/0 or true/false"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*field.*\.csv$"],
            "header_keywords": ["Field label", "Bundle", "Field type"],
            "content_indicators": ["text", "number", "entity_reference"]
        },
        entity_group="Content"
    ),
    
    "views": CSVTypeDefinition(
        label="Custom Views",
        required_columns=["Machine name", "View name"],
        optional_columns=["Description", "Type", "Path", "Menu", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "View name": ValidationRule(
                type="text",
                error_message="View name is required"
            ),
            "Type": ValidationRule(
                type="choice",
                choices=["page", "block", "feed", "embed"],
                allow_empty=True,
                error_message="View type must be one of: page, block, feed, embed"
            ),
            "Path": ValidationRule(
                type="text",
                pattern=r"^[a-zA-Z0-9/_-]*$",
                allow_empty=True,
                error_message="Path must contain only letters, numbers, slashes, underscores, and hyphens"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*view.*\.csv$"],
            "header_keywords": ["View name", "Machine name"],
            "content_indicators": ["page", "block", "feed"]
        },
        entity_group="Views"
    ),
    
    "view_displays": CSVTypeDefinition(
        label="Custom Views Displays",
        required_columns=["View", "Display name", "Display type"],
        optional_columns=["Description", "Settings", "Dev", "QA"],
        validation_rules={
            "View": ValidationRule(
                type="reference",
                references_csv="views",
                references_column="Machine name",
                error_message="View must reference an existing view machine name"
            ),
            "Display name": ValidationRule(
                type="text",
                error_message="Display name is required"
            ),
            "Display type": ValidationRule(
                type="choice",
                choices=["page", "block", "attachment", "feed", "embed"],
                error_message="Display type must be one of: page, block, attachment, feed, embed"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*view.*display.*\.csv$", r".*display.*\.csv$"],
            "header_keywords": ["View", "Display name", "Display type"],
            "content_indicators": ["page", "block", "attachment"]
        },
        entity_group="Views"
    ),
    
    "image_styles": CSVTypeDefinition(
        label="Image Styles",
        required_columns=["Machine name", "Style name"],
        optional_columns=["Description", "Width", "Height", "Effect", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "Style name": ValidationRule(
                type="text",
                error_message="Style name is required"
            ),
            "Width": ValidationRule(
                type="number",
                allow_empty=True,
                error_message="Width must be a number"
            ),
            "Height": ValidationRule(
                type="number",
                allow_empty=True,
                error_message="Height must be a number"
            ),
            "Effect": ValidationRule(
                type="choice",
                choices=["scale", "crop", "resize", "rotate", "desaturate"],
                allow_empty=True,
                error_message="Effect must be one of: scale, crop, resize, rotate, desaturate"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*image.*style.*\.csv$"],
            "header_keywords": ["Style name", "Width", "Height", "Effect"],
            "content_indicators": ["scale", "crop", "resize"]
        },
        entity_group="Media"
    ),
    
    "user_roles": CSVTypeDefinition(
        label="User Roles",
        required_columns=["Machine name", "Role name"],
        optional_columns=["Description", "Permissions", "Weight", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "Role name": ValidationRule(
                type="text",
                error_message="Role name is required"
            ),
            "Weight": ValidationRule(
                type="number",
                allow_empty=True,
                error_message="Weight must be a number"
            ),
            "Permissions": ValidationRule(
                type="text",
                allow_empty=True,
                error_message="Permissions should be a comma-separated list"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*user.*role.*\.csv$", r".*role.*\.csv$"],
            "header_keywords": ["Role name", "Permissions", "Weight"],
            "content_indicators": ["authenticated", "administrator", "editor"]
        },
        entity_group="User Roles"
    ),
    
    "workflows": CSVTypeDefinition(
        label="Workflows",
        required_columns=["Machine name", "Workflow name"],
        optional_columns=["Description", "Bundle", "Default state", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "Workflow name": ValidationRule(
                type="text",
                error_message="Workflow name is required"
            ),
            "Bundle": ValidationRule(
                type="reference",
                references_csv="bundles",
                references_column="Machine name",
                allow_empty=True,
                error_message="Bundle must reference an existing bundle machine name"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*workflow.*\.csv$"],
            "header_keywords": ["Workflow name", "Default state"],
            "content_indicators": ["draft", "published", "archived"]
        },
        entity_group="Workflow"
    ),
    
    "workflow_states": CSVTypeDefinition(
        label="Workflow States",
        required_columns=["Machine name", "State name", "Workflow"],
        optional_columns=["Description", "Weight", "Default", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "State name": ValidationRule(
                type="text",
                error_message="State name is required"
            ),
            "Workflow": ValidationRule(
                type="reference",
                references_csv="workflows",
                references_column="Machine name",
                error_message="Workflow must reference an existing workflow machine name"
            ),
            "Weight": ValidationRule(
                type="number",
                allow_empty=True,
                error_message="Weight must be a number"
            ),
            "Default": ValidationRule(
                type="choice",
                choices=["Yes", "No", "1", "0", "true", "false"],
                allow_empty=True,
                error_message="Default must be Yes/No or 1/0 or true/false"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*workflow.*state.*\.csv$", r".*state.*\.csv$"],
            "header_keywords": ["State name", "Workflow", "Weight"],
            "content_indicators": ["draft", "review", "published"]
        },
        entity_group="Workflow"
    ),
    
    "migrations": CSVTypeDefinition(
        label="Migrations",
        required_columns=["Migration name", "Source", "Destination"],
        optional_columns=["Description", "Bundle", "Status", "Dependencies", "Dev", "QA"],
        validation_rules={
            "Migration name": ValidationRule(
                type="text",
                error_message="Migration name is required"
            ),
            "Source": ValidationRule(
                type="text",
                error_message="Source is required"
            ),
            "Destination": ValidationRule(
                type="text",
                error_message="Destination is required"
            ),
            "Bundle": ValidationRule(
                type="reference",
                references_csv="bundles",
                references_column="Machine name",
                allow_empty=True,
                error_message="Bundle must reference an existing bundle machine name"
            ),
            "Status": ValidationRule(
                type="choice",
                choices=["pending", "in_progress", "completed", "failed"],
                allow_empty=True,
                error_message="Status must be one of: pending, in_progress, completed, failed"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*migration.*\.csv$"],
            "header_keywords": ["Migration name", "Source", "Destination"],
            "content_indicators": ["database", "file", "url"]
        },
        entity_group="Migration"
    ),
    
    "custom": CSVTypeDefinition(
        label="Custom Entity",
        required_columns=["Machine name", "Name"],
        optional_columns=["Description", "Type", "Dev", "QA"],
        validation_rules={
            "Machine name": ValidationRule(
                type="machine_name",
                pattern=r"^[a-z][a-z0-9_]*$",
                error_message="Must be lowercase letters, numbers, and underscores only"
            ),
            "Name": ValidationRule(
                type="text",
                error_message="Name is required"
            )
        },
        detection_patterns={
            "filename_patterns": [r".*custom.*\.csv$"],
            "header_keywords": ["Machine name", "Name"],
            "content_indicators": []
        },
        entity_group="Custom"
    )
}
```

## CSV Structure Flexibility

### **Each CSV Type Has Completely Different Column Requirements**

The registry accommodates the fact that each CSV file has a unique structure by defining type-specific column requirements:

#### **Example Column Structure Differences:**
```
UWEC_Bundles.csv:
├── Machine name (required)
├── Name (required)  
├── Description (optional)
├── Type (optional: node|media|taxonomy)
└── Dev, QA (optional: numbers)

UWEC_Fields.csv:
├── Machine name (required)
├── Field label (required)
├── Bundle (required: references bundles.csv)
├── Field type (optional: text|number|email|etc.)
├── Widget, Formatter (optional)
└── Dev, QA (optional: numbers)

UWEC_CustomViews.csv:
├── Machine name (required)
├── View name (required)
├── Path (optional: URL path)
├── Menu (optional)
└── Type (optional: page|block|feed|embed)

UWEC_ImageStyles.csv:
├── Machine name (required)
├── Style name (required)
├── Width, Height (optional: numbers)
├── Effect (optional: scale|crop|resize)
└── Description (optional)

UWEC_UserRoles.csv:
├── Machine name (required)
├── Role name (required)
├── Permissions (optional: comma-separated)
├── Weight (optional: number)
└── Description (optional)
```

#### **How the Registry Handles Structural Differences:**

1. **Column Flexibility**: Each CSV type defines its own required/optional columns
   ```python
   "bundles": required_columns=["Machine name", "Name"]
   "fields": required_columns=["Machine name", "Field label", "Bundle"]  
   "user_roles": required_columns=["Machine name", "Role name"]
   ```

2. **Validation Rule Flexibility**: Each column can have completely different validation rules
   ```python
   # Bundles: Type column validates against Drupal entity types
   "Type": ValidationRule(choices=["node", "media", "taxonomy"])
   
   # Fields: Bundle column validates references to bundles.csv
   "Bundle": ValidationRule(type="reference", references_csv="bundles")
   
   # User Roles: Weight column validates as number
   "Weight": ValidationRule(type="number", allow_empty=True)
   ```

3. **Detection Pattern Flexibility**: Each type detected by its unique characteristics
   ```python
   # Image Styles detected by image-specific patterns
   "image_styles": detection_patterns={
       "filename_patterns": [r".*image.*style.*\.csv$"],
       "header_keywords": ["Style name", "Width", "Height", "Effect"],
       "content_indicators": ["scale", "crop", "resize"]
   }
   
   # Workflows detected by workflow-specific patterns  
   "workflows": detection_patterns={
       "filename_patterns": [r".*workflow.*\.csv$"],
       "header_keywords": ["Workflow name", "Default state"],
       "content_indicators": ["draft", "published", "archived"]
   }
   ```

#### **Cross-File Reference Accommodation:**

The registry handles that different CSV types reference each other through different column names:

```python
# Fields reference bundles through "Bundle" column
"fields" → "Bundle" column → references "bundles" → "Machine name" column

# View displays reference views through "View" column  
"view_displays" → "View" column → references "views" → "Machine name" column

# Workflow states reference workflows through "Workflow" column
"workflow_states" → "Workflow" column → references "workflows" → "Machine name" column
```

## Detection Strategy

### **Multi-Level Detection Process**
```python
# /backend/app/utils/csv/detector.py
class CSVTypeDetector:
    def __init__(self, registry: Dict[str, CSVTypeDefinition]):
        self.registry = registry
    
    def detect_csv_type(self, filename: str, headers: List[str], 
                       sample_rows: List[Dict]) -> Dict[str, float]:
        """
        Detect CSV type using multiple strategies, return confidence scores.
        
        Returns: {
            "bundles": 0.95,
            "fields": 0.15,
            "custom": 0.05
        }
        """
        scores = {}
        
        for csv_type, definition in self.registry.items():
            filename_score = definition.detect_from_filename(filename)
            content_score = definition.detect_from_content(headers, sample_rows)
            
            # Weighted combination: filename 30%, content 70%
            combined_score = (filename_score * 0.3) + (content_score * 0.7)
            scores[csv_type] = combined_score
        
        return scores
    
    def get_best_match(self, filename: str, headers: List[str], 
                      sample_rows: List[Dict]) -> Optional[str]:
        """Return best matching CSV type if confidence > 0.7"""
        scores = self.detect_csv_type(filename, headers, sample_rows)
        best_type = max(scores, key=scores.get)
        
        if scores[best_type] >= 0.7:
            return best_type
        return None
```

## Validation Engine

### **Column-Level Validation**
```python
# /backend/app/utils/csv/validator.py
class CSVValidator:
    def __init__(self, registry: Dict[str, CSVTypeDefinition]):
        self.registry = registry
    
    def validate_file(self, csv_type: str, parsed_data: Dict) -> List[ValidationError]:
        """Validate entire CSV file against type definition"""
        definition = self.registry[csv_type]
        errors = []
        
        # Schema validation
        errors.extend(self._validate_schema(definition, parsed_data))
        
        # Content validation  
        errors.extend(self._validate_content(definition, parsed_data))
        
        return errors
    
    def _validate_schema(self, definition: CSVTypeDefinition, 
                        parsed_data: Dict) -> List[ValidationError]:
        """Validate headers and required columns"""
        errors = []
        headers = parsed_data.get('headers', [])
        
        # Check required columns
        for required_col in definition.required_columns:
            if required_col not in headers:
                errors.append(ValidationError(
                    type="missing_column",
                    message=f"Required column '{required_col}' not found",
                    column=required_col
                ))
        
        return errors
    
    def _validate_content(self, definition: CSVTypeDefinition,
                         parsed_data: Dict) -> List[ValidationError]:
        """Validate row content against validation rules"""
        errors = []
        rows = parsed_data.get('rows', [])
        
        for row_idx, row in enumerate(rows):
            for column, rule in definition.validation_rules.items():
                if column in row:
                    error = definition.validate_column(column, row[column], 
                                                     {"row_number": row_idx + 1})
                    if error:
                        errors.append(ValidationError(
                            type="validation_failed",
                            message=error,
                            column=column,
                            row_number=row_idx + 1,
                            current_value=row[column]
                        ))
        
        return errors
```

## Cross-File Relationship Validation

### **Relationship Mapping Accommodates Different CSV Structures**
```python
# /backend/app/utils/csv/relationships.py
CROSS_FILE_RELATIONSHIPS = {
    # Fields CSV references Bundles CSV
    "fields": [
        {
            "column": "Bundle",                    # Column in fields.csv
            "references_csv_type": "bundles",     # References bundles.csv
            "references_column": "Machine name",   # Specific column in bundles.csv
            "relationship_type": "bundle_references"
        }
    ],
    
    # View Displays CSV references Views CSV  
    "view_displays": [
        {
            "column": "View",                      # Column in view_displays.csv
            "references_csv_type": "views",       # References views.csv
            "references_column": "Machine name",   # Specific column in views.csv
            "relationship_type": "view_references"
        }
    ],
    
    # Workflow States CSV references Workflows CSV
    "workflow_states": [
        {
            "column": "Workflow",                  # Column in workflow_states.csv
            "references_csv_type": "workflows",   # References workflows.csv
            "references_column": "Machine name",   # Specific column in workflows.csv
            "relationship_type": "workflow_references"
        }
    ],
    
    # Multiple references - Fields can reference multiple CSV types
    "fields": [
        {
            "column": "Bundle",                    # Primary bundle reference
            "references_csv_type": "bundles",
            "references_column": "Machine name",
            "relationship_type": "bundle_references"
        },
        {
            "column": "Referenced bundle",         # For entity_reference fields
            "references_csv_type": "bundles", 
            "references_column": "Machine name",
            "relationship_type": "entity_references",
            "conditional": {"Field type": "entity_reference"}  # Only validate if field type is entity_reference
        }
    ],
    
    # Workflows can reference Bundles (workflow applies to specific content types)
    "workflows": [
        {
            "column": "Bundle",
            "references_csv_type": "bundles",
            "references_column": "Machine name", 
            "relationship_type": "workflow_bundle_references",
            "allow_empty": True  # Workflows can apply to all content types
        }
    ],
    
    # Migrations can reference Bundles (migration targets specific content types)
    "migrations": [
        {
            "column": "Bundle",
            "references_csv_type": "bundles",
            "references_column": "Machine name",
            "relationship_type": "migration_bundle_references",
            "allow_empty": True  # Migrations can be bundle-agnostic
        }
    ]
}

class RelationshipValidator:
    def validate_relationships(self, uploaded_files: List[UploadedFile]) -> List[RelationshipError]:
        """
        Validate cross-file references accounting for different CSV structures.
        
        Example validation scenarios:
        1. fields.csv "Bundle" column → bundles.csv "Machine name" column
        2. view_displays.csv "View" column → views.csv "Machine name" column  
        3. workflow_states.csv "Workflow" column → workflows.csv "Machine name" column
        """
        errors = []
        file_data = {file.csv_type: file.parsed_content for file in uploaded_files}
        
        for file in uploaded_files:
            if file.csv_type in CROSS_FILE_RELATIONSHIPS:
                relationships = CROSS_FILE_RELATIONSHIPS[file.csv_type]
                for relationship in relationships:
                    errors.extend(self._validate_relationship(
                        file, relationship, file_data
                    ))
        
        return errors
    
    def _validate_relationship(self, source_file: UploadedFile, 
                              relationship: dict, all_file_data: dict) -> List[RelationshipError]:
        """
        Validate that values in source_file[relationship.column] exist in 
        target_file[relationship.references_column], handling different CSV structures.
        """
        errors = []
        source_column = relationship["column"]
        target_csv_type = relationship["references_csv_type"]
        target_column = relationship["references_column"]
        
        # Check if target CSV type exists in uploaded files
        if target_csv_type not in all_file_data:
            if not relationship.get("allow_empty", False):
                errors.append(RelationshipError(
                    type="missing_reference_file",
                    message=f"Missing required {target_csv_type}.csv for {source_file.filename} references",
                    source_file=source_file.filename,
                    missing_csv_type=target_csv_type
                ))
            return errors
        
        # Get valid reference values from target CSV
        target_data = all_file_data[target_csv_type]
        valid_references = set()
        for row in target_data.get("rows", []):
            if target_column in row and row[target_column]:
                valid_references.add(row[target_column])
        
        # Validate each reference in source CSV
        source_data = source_file.parsed_content
        for row_idx, row in enumerate(source_data.get("rows", [])):
            if source_column in row and row[source_column]:
                # Handle conditional validation
                if "conditional" in relationship:
                    condition_met = all(
                        row.get(cond_col) == cond_val 
                        for cond_col, cond_val in relationship["conditional"].items()
                    )
                    if not condition_met:
                        continue  # Skip validation for this row
                
                reference_value = row[source_column]
                if reference_value not in valid_references:
                    errors.append(RelationshipError(
                        type="invalid_reference",
                        message=f"'{reference_value}' not found in {target_csv_type}.csv",
                        source_file=source_file.filename,
                        row_number=row_idx + 1,
                        column_name=source_column,
                        invalid_reference=reference_value,
                        available_options=list(valid_references)[:10]  # Show first 10 options
                    ))
        
        return errors
```

## Sample Data Integration

### **Registry Accommodates Real UWEC CSV Structures**

The registry is designed to handle the actual sample CSV files mentioned in the specifications, each with completely different column structures:

#### **UWEC Sample Files Mapping:**
```python
# Real sample files → Registry types
"UWEC_Bundles.csv"           → "bundles" type
"UWEC_Fields.csv"            → "fields" type  
"UWEC_CustomViews.csv"       → "views" type
"UWEC_CustomViewsDisplays.csv" → "view_displays" type
"UWEC_Imagestyles.csv"       → "image_styles" type
"UWEC_Userroles.csv"         → "user_roles" type
"UWEC_Workflows.csv"         → "workflows" type

# Plus test case files
"UWEC_Fields_BROKEN.csv"     → "fields" type (for validation testing)
```

#### **How Each UWEC File Maps to Different Column Structures:**

**UWEC_Bundles.csv Structure:**
```
Machine name | Name | Description | Type | Settings/notes | Dev | QA
product      | Product | Product content | node | {...} | 5 | 3
event        | Event | Event content | node | {...} | 2 | 1
```
→ Registry: `required_columns=["Machine name", "Name"]`

**UWEC_Fields.csv Structure:**  
```
Machine name | Field label | Bundle | Field type | Widget | Formatter | Dev | QA
field_price  | Price | product | number | number | default | 1 | 1
field_date   | Event Date | event | datetime | datetime | default | 1 | 1
```
→ Registry: `required_columns=["Machine name", "Field label", "Bundle"]`

**UWEC_CustomViews.csv Structure:**
```
Machine name | View name | Description | Type | Path | Menu | Dev | QA
product_list | Product List | Lists all products | page | /products | main | 2 | 1
events_block | Events Block | Recent events | block | | | 1 | 1
```
→ Registry: `required_columns=["Machine name", "View name"]`

**UWEC_ImageStyles.csv Structure:**
```
Machine name | Style name | Description | Width | Height | Effect | Dev | QA
thumbnail    | Thumbnail | Small image | 150 | 150 | scale | 1 | 1
hero_banner  | Hero Banner | Large banner | 1200 | 400 | crop | 1 | 1
```
→ Registry: `required_columns=["Machine name", "Style name"]`

#### **Cross-File Reference Handling in Sample Data:**

The registry handles how UWEC files reference each other:

```python
# UWEC_Fields.csv references UWEC_Bundles.csv
fields.csv "Bundle" column → bundles.csv "Machine name" column
"product" → must exist in bundles.csv
"event" → must exist in bundles.csv

# UWEC_CustomViewsDisplays.csv references UWEC_CustomViews.csv  
view_displays.csv "View" column → views.csv "Machine name" column
"product_list" → must exist in views.csv
"events_block" → must exist in views.csv
```

#### **Test Case Integration:**

**UWEC_Fields_BROKEN.csv** (for validation testing):
```python
# Example broken data the registry would catch:
Row 3: Bundle = "invalid_bundle"     # ← Not found in bundles.csv
Row 5: Field type = "invalid_type"   # ← Not in allowed choices  
Row 7: Machine name = "Invalid Name" # ← Doesn't match machine_name pattern
```

The registry's validation rules would catch all these issues and provide specific error messages pointing to the exact row and column with the problem.

## Service Integration

### **UploadService Integration**
```python
# /backend/app/services/upload_service.py
class UploadService:
    def __init__(self, upload_repo: UploadRepositoryInterface,
                 session_repo: SessionRepositoryInterface,
                 error_repo: ErrorRepositoryInterface):
        self.csv_detector = CSVTypeDetector(CSV_TYPE_REGISTRY)
        self.csv_validator = CSVValidator(CSV_TYPE_REGISTRY)
        self.relationship_validator = RelationshipValidator()
    
    async def upload_files(self, session_id: UUID, files: List[UploadFile]) -> FileUploadResponse:
        # 1. Parse CSV files
        # 2. Auto-detect types using detector
        # 3. Validate using validator
        # 4. Store results
        pass
    
    async def validate_files(self, session_id: UUID) -> ValidationResponse:
        # 1. Get all files for session
        # 2. Validate individual files
        # 3. Validate cross-file relationships
        # 4. Return comprehensive results
        pass
```

## Benefits of Unified Approach

### **1. Comprehensive Detection**
- **Multi-strategy**: Filename patterns + content analysis + header matching
- **Confidence scoring**: Quantified confidence levels for auto-detection
- **Fallback handling**: Custom classification when auto-detection fails

### **2. Flexible Validation**
- **Rule-based**: Simple validation rules for common patterns
- **Extensible**: Easy to add new CSV types and validation rules
- **Context-aware**: Validation rules can access row context and cross-references

### **3. Cross-File Relationships**
- **Mapping-based**: Clear relationship definitions between CSV types
- **Validation integration**: Automatic cross-file reference checking
- **Error reporting**: Specific guidance for relationship violations

### **4. Maintainable Structure**
- **Single source**: One registry contains all CSV type definitions
- **Modifiable**: Easy to update validation rules and detection patterns
- **Testable**: Clear interfaces for testing detection and validation logic

## Implementation Priority

### **Phase 1: Core Registry (MVP)**
1. **Basic CSV types**: bundles, fields, views, custom
2. **Simple detection**: Filename + required column matching
3. **Schema validation**: Required columns and basic data types
4. **Cross-file validation**: Standard Drupal relationships

### **Phase 2: Enhanced Detection (Future)**
1. **Advanced content analysis**: Machine learning-based detection
2. **Smart suggestions**: Recommend CSV type based on content patterns
3. **Validation improvements**: More sophisticated validation rules
4. **Custom relationship mapping**: User-defined cross-file relationships

## Success Criteria

- ✅ Single registry structure supports all CSV type definitions
- ✅ Auto-detection works reliably for standard Drupal CSV exports
- ✅ Validation provides specific, actionable error messages
- ✅ Cross-file relationship validation catches reference errors
- ✅ Registry is easily extendable for new CSV types
- ✅ Detection confidence scoring enables smart UI suggestions
- ✅ Validation rules are maintainable and well-documented

This unified registry approach combines the best aspects of all three conflicting specifications while providing a clear, implementable structure for Claude Code.