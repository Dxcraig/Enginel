# Enginel BOM (Bill of Materials) Extraction

## Overview
Automated BOM extraction from CAD assembly files (STEP/IGES) with hierarchical tree structure, mass properties, and component metadata.

## Features

### 1. **Automatic BOM Extraction**
- Triggered automatically during file upload processing
- Parses STEP file assembly structure
- Extracts component names from STEP metadata
- Calculates geometric properties per component
- Builds hierarchical tree using Django Treebeard

### 2. **Component Data Extracted**
- **Identification**: Name, part number, quantity
- **Geometry**: Volume, surface area, bounding box
- **Mass Properties**: Estimated mass (aluminum default)
- **Topology**: Face, edge, vertex counts
- **Position**: Center of mass coordinates
- **Hierarchy**: Parent-child relationships

### 3. **BOM Tree Structure**
Uses Django Treebeard's Materialized Path for efficient hierarchical queries:
- Root assemblies at depth 0
- Nested sub-assemblies and parts
- Quantity tracking at each level
- Recursive mass/volume calculations

## API Endpoints

### Get BOM Tree
```http
GET /api/designs/{id}/bom/
```

**Response:**
```json
{
  "design_asset_id": "uuid",
  "filename": "assembly.step",
  "root_nodes": [
    {
      "id": 1,
      "name": "Assembly_Root",
      "part_number": "PN-0001",
      "node_type": "ASSEMBLY",
      "quantity": 1,
      "mass": 0.0135,
      "volume": 5000.0,
      "children": [
        {
          "id": 2,
          "name": "Base_Plate",
          "part_number": "PN-0001",
          "node_type": "PART",
          "quantity": 1,
          "mass": 0.0054,
          "volume": 2000.0,
          "topology": {"faces": 6, "edges": 12, "vertices": 8},
          "children": []
        }
      ]
    }
  ],
  "total_nodes": 4,
  "total_parts": 3,
  "total_assemblies": 1,
  "max_depth": 2,
  "total_mass_kg": 0.0135
}
```

### Manually Trigger BOM Extraction
```http
POST /api/designs/{id}/extract_bom/
```

Useful for:
- Re-extracting BOM after file changes
- Recovering from failed automatic extraction
- Processing uploads that skipped BOM extraction

**Response:**
```json
{
  "message": "BOM extraction started",
  "task_id": "celery-task-uuid",
  "design_asset_id": "design-uuid"
}
```

### List BOM Nodes
```http
GET /api/bom-nodes/
GET /api/bom-nodes/?design_asset={uuid}
```

## Architecture

### Geometry Processor
`geometry_processor.py` handles CAD file parsing:

```python
processor = GeometryProcessor('assembly.step')
components = processor.extract_bom_structure()

# Returns:
# [
#   {
#     'index': 0,
#     'name': 'Component_1',
#     'part_number': 'PN-0001',
#     'quantity': 1,
#     'volume': 1000.0,
#     'surface_area': 600.0,
#     'mass': 0.0027,  # kg (aluminum)
#     'center_of_mass': {'x': 0, 'y': 0, 'z': 0},
#     'bounding_box': {...},
#     'topology': {'faces': 6, 'edges': 12, 'vertices': 8}
#   }
# ]
```

**Key Methods:**
- `extract_bom_structure()` - Main BOM extraction
- `_extract_step_component_names()` - Parse STEP file for product names
- `_count_component_topology()` - Count faces/edges/vertices

### Celery Task
`extract_bom_from_assembly()` task orchestrates extraction:

1. Load design asset from database
2. Get file path (local or S3)
3. Call GeometryProcessor
4. Clear existing BOM nodes
5. Create root assembly node
6. Add child components recursively
7. Calculate total mass/volume
8. Update AnalysisJob status

### Database Model
`AssemblyNode` uses Django Treebeard:

```python
class AssemblyNode(MP_Node):
    design_asset = ForeignKey(DesignAsset)
    name = CharField()
    part_number = CharField()
    quantity = IntegerField()
    node_type = CharField(choices=['ASSEMBLY', 'PART'])
    mass = FloatField()  # kg
    volume = FloatField()  # mm³
    component_metadata = JSONField()
    
    def get_total_mass(self):
        """Recursively calculate mass including children."""
        total = self.mass or 0
        for child in self.get_children():
            total += (child.get_total_mass() * child.quantity)
        return total
```

## Processing Workflow

### Automatic Processing (on upload)
```
1. File Upload
   └─→ process_design_asset.delay()
       ├─→ calculate_file_hash()
       ├─→ extract_geometry_metadata()
       ├─→ run_design_rule_checks()
       └─→ extract_bom_from_assembly() ← BOM EXTRACTION
```

### Manual Triggering
```
POST /api/designs/{id}/extract_bom/
  └─→ extract_bom_from_assembly.delay()
      └─→ Creates AnalysisJob (BOM_PARSING)
          └─→ Updates job status (RUNNING → SUCCESS/FAILED)
```

## STEP File Parsing

### Component Name Extraction
Regex pattern searches for PRODUCT entities:
```regex
#\d+\s*=\s*PRODUCT\s*\('([^']+)'
```

Example STEP content:
```step
#10 = PRODUCT('Base_Plate','Mounting Base','',());
#20 = PRODUCT('Bracket_Left','Left Support Bracket','',());
```

Maps to:
```python
{
  0: 'Base_Plate',
  1: 'Bracket_Left'
}
```

### Assembly Hierarchy
Current implementation:
- Flat structure (all components as children of root)
- Future: Parse `NEXT_ASSEMBLY_USAGE_OCCURRENCE` for true hierarchy

## Testing

### Test Script
```bash
# Upload assembly file and view BOM
python test_files/test_bom.py admin admin123 1 test_files/test_assembly.step
```

**Tests performed:**
1. Upload assembly STEP file
2. Wait for automatic processing
3. View BOM tree structure
4. Manually trigger re-extraction
5. Check analysis job statuses

### Sample Assembly File
`test_assembly.step` contains:
- 1 root assembly
- 3 components (Base_Plate, Bracket_Left, Bracket_Right)
- PRODUCT metadata with names
- Assembly structure with NEXT_ASSEMBLY_USAGE_OCCURRENCE

### Expected Output
```
✅ Uploaded assembly: <uuid>
✅ Processing completed in 15 seconds
✅ BOM extracted successfully!
   Total nodes: 4
   Total parts: 3
   Total assemblies: 1
   Max depth: 1
   Total mass: 0.0135 kg

   BOM Tree Structure:
   ├─ [ASSEMBLY] Assembly_Root (PN-0001) x1 - 0.0135kg
      ├─ [PART] Base_Plate (PN-0001) x1 - 0.0054kg
      ├─ [PART] Bracket_Left (PN-0002) x1 - 0.0041kg
      ├─ [PART] Bracket_Right (PN-0003) x1 - 0.0040kg
```

## Configuration

### Material Density (for mass estimation)
Default: Aluminum (2.7 g/cm³)
```python
# In geometry_processor.py
mass = volume * 0.0000027  # volume in mm³, mass in kg
```

To customize:
```python
# Add material field to AssemblyNode
material_density = {
    'aluminum': 0.0000027,
    'steel': 0.0000078,
    'titanium': 0.0000045,
    'plastic': 0.0000012
}
```

### Part Number Format
Default: `PN-{index:04d}` (e.g., PN-0001, PN-0002)

Customize in `extract_bom_structure()`:
```python
'part_number': f"{design_asset.series.part_number}-{index + 1:03d}"
```

## Limitations & Future Enhancements

### Current Limitations
- ❌ Flat BOM (no nested assemblies beyond root)
- ❌ No duplicate detection (same part appearing multiple times)
- ❌ Fixed material density (aluminum)
- ❌ Limited STEP metadata parsing
- ❌ No IGES assembly support

### Planned Features
- [ ] True hierarchical BOM from STEP assembly structure
- [ ] Duplicate part consolidation with quantity rollup
- [ ] Material property extraction from STEP
- [ ] Custom material database integration
- [ ] BOM export (CSV, Excel, PDF)
- [ ] BOM comparison between versions
- [ ] Cost rollup from component pricing
- [ ] Supplier data integration
- [ ] IGES assembly parsing

## Troubleshooting

### BOM Not Appearing
1. Check design status: `GET /api/designs/{id}/`
2. Verify file has assembly structure (multiple solids)
3. Check analysis jobs: `GET /api/analysis-jobs/?design_asset={id}`
4. Manually trigger: `POST /api/designs/{id}/extract_bom/`

### Single Part Showing as Assembly
- Normal behavior - creates single root node
- Check `component_metadata.single_part = true`

### Missing Component Names
- STEP file may lack PRODUCT entities
- Falls back to `Component_{N}` naming
- Check file with `_extract_step_component_names()`

### Incorrect Mass Values
- Default aluminum density used
- Verify volume calculation in mm³
- Override with actual material density

## Database Queries

### Get all parts for a design
```python
parts = AssemblyNode.objects.filter(
    design_asset=design,
    node_type='PART'
)
```

### Get BOM tree with descendants
```python
root = AssemblyNode.get_root_nodes().filter(design_asset=design).first()
descendants = root.get_descendants()
```

### Calculate total mass
```python
total_mass = sum(node.get_total_mass() for node in root_nodes)
```

### Find specific component
```python
component = AssemblyNode.objects.get(
    design_asset=design,
    part_number='PN-0005'
)
```

## Performance

### Extraction Time
- Single part: ~1-2 seconds
- Small assembly (5-10 parts): ~5-10 seconds
- Medium assembly (50-100 parts): ~30-60 seconds
- Large assembly (500+ parts): ~5-10 minutes

### Optimization Tips
- Use `select_related()` for design_asset queries
- Cache BOM tree in Redis for frequently accessed designs
- Paginate large BOMs in API responses
- Index part_number and node_type fields

## Integration

### With Geometry Extraction
BOM extraction reuses geometry data:
```python
metadata = design_asset.metadata
volume = metadata.get('volume_mm3', 0)
```

### With Audit Logging
BOM operations are automatically logged:
- CREATE when BOM nodes added
- UPDATE when BOM re-extracted
- READ when BOM viewed

### With File Upload
Seamlessly integrated into upload workflow:
```python
# In DesignAssetCreateSerializer.create()
if file_data:
    process_design_asset.delay(instance.id)
    # ^ Includes BOM extraction
```
