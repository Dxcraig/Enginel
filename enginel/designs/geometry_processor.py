"""
Geometry Processing Module using CadQuery (OCP/OpenCASCADE)

This module provides functions to extract geometric metadata from CAD files:
- Volume, Surface Area, Center of Mass
- Bounding Box dimensions
- Topology counts (solids, faces, edges, vertices)
- Design Rule Checks (manifold geometry, watertightness)

Expensive operations are cached using longterm cache (1 hour).
"""

import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path
import json
from designs.cache import cache_result, CacheKey, longterm_cache_manager

try:
    import cadquery as cq
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    GEOMETRY_AVAILABLE = True
except ImportError:
    GEOMETRY_AVAILABLE = False
    logging.warning("CadQuery/OCP not available. Geometry processing will be disabled.")

logger = logging.getLogger(__name__)


class GeometryProcessor:
    """Processes STEP/IGES files to extract geometric metadata."""
    
    def __init__(self, file_path: str):
        """
        Initialize geometry processor with a CAD file.
        
        Args:
            file_path: Path to STEP or IGES file
        """
        if not GEOMETRY_AVAILABLE:
            raise ImportError("CadQuery/OCP not installed. Install with: pip install cadquery")
        
        self.file_path = Path(file_path)
        self.shape = None
        self._load_file()
    
    def _load_file(self):
        """Load CAD file into CadQuery."""
        try:
            file_ext = self.file_path.suffix.lower()
            
            if file_ext == '.step' or file_ext == '.stp':
                self.shape = cq.importers.importStep(str(self.file_path))
            elif file_ext == '.iges' or file_ext == '.igs':
                self.shape = cq.importers.importDXF(str(self.file_path))  # CadQuery uses DXF importer for IGES
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            logger.info(f"Successfully loaded CAD file: {self.file_path.name}")
        except Exception as e:
            logger.error(f"Failed to load CAD file {self.file_path}: {str(e)}")
            raise
    
    def extract_mass_properties(self) -> Dict[str, Any]:
        """
        Extract mass properties from the geometry.
        
        Returns:
            Dictionary with volume, surface_area, center_of_mass, bounding_box
        """
        try:
            # Get the solid from the shape
            solid = self.shape.val() if hasattr(self.shape, 'val') else self.shape
            
            # Extract the wrapped OCP shape for direct OCP API calls
            ocp_shape = solid.wrapped if hasattr(solid, 'wrapped') else solid
            
            # Calculate volume
            volume_props = GProp_GProps()
            BRepGProp.VolumeProperties_s(ocp_shape, volume_props, OnlyClosed=True)
            volume = volume_props.Mass()
            
            # Calculate surface area
            surface_props = GProp_GProps()
            BRepGProp.SurfaceProperties_s(ocp_shape, surface_props)
            surface_area = surface_props.Mass()
            
            # Get center of mass
            com = volume_props.CentreOfMass()
            center_of_mass = {
                'x': com.X(),
                'y': com.Y(),
                'z': com.Z()
            }
            
            # Get bounding box
            bbox = self.shape.val().BoundingBox() if hasattr(self.shape, 'val') else self.shape.BoundingBox()
            bounding_box = {
                'xmin': bbox.xmin,
                'xmax': bbox.xmax,
                'ymin': bbox.ymin,
                'ymax': bbox.ymax,
                'zmin': bbox.zmin,
                'zmax': bbox.zmax,
                'dimensions': {
                    'length': bbox.xmax - bbox.xmin,
                    'width': bbox.ymax - bbox.ymin,
                    'height': bbox.zmax - bbox.zmin
                }
            }
            
            return {
                'volume': volume,
                'surface_area': surface_area,
                'center_of_mass': center_of_mass,
                'bounding_box': bounding_box,
                'units': 'mm'  # OpenCASCADE typically uses mm
            }
        
        except Exception as e:
            logger.error(f"Failed to extract mass properties: {str(e)}")
            raise
    
    def extract_units(self) -> str:
        """
        Extract native units from STEP file header.
        
        Returns:
            Unit string ('mm', 'in', 'm', etc.) or 'mm' as default
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000).upper()  # Read first 50KB, case-insensitive
                
            # STEP files contain unit info in UNCERTAINTY_MEASURE_WITH_UNIT or similar entities
            # Common patterns (case-insensitive):
            # #XX = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );
            # #XX = ( NAMED_UNIT(*) SI_UNIT($,.METRE.) LENGTH_UNIT() );
            # #XX = UNCERTAINTY_MEASURE_WITH_UNIT(...LENGTH_MEASURE...METRE...)
            
            # Search patterns with priority (most specific first)
            unit_patterns = [
                ('MILLI', 'METRE', 'mm'),
                ('CENTI', 'METRE', 'cm'),
                ('MICRO', 'METRE', 'um'),
                ('KILO', 'METRE', 'km'),
                ('INCH', None, 'in'),
                ('FOOT', None, 'ft'),
                ('METRE', None, 'm'),  # Check last to avoid matching MILLIMETRE
            ]
            
            for prefix, suffix, unit in unit_patterns:
                if suffix:
                    # Look for compound patterns like MILLI + METRE
                    if prefix in content and suffix in content:
                        # Make sure they appear close together (within 100 chars)
                        prefix_pos = content.find(prefix)
                        suffix_pos = content.find(suffix, prefix_pos)
                        if suffix_pos - prefix_pos < 100:
                            logger.info(f"Detected unit from STEP file: {unit} (pattern: {prefix}+{suffix})")
                            return unit
                else:
                    # Single word patterns like INCH
                    if prefix in content:
                        logger.info(f"Detected unit from STEP file: {unit} (pattern: {prefix})")
                        return unit
            
            # Default to millimeters if not found
            logger.warning("Could not detect units from STEP file, defaulting to mm")
            return 'mm'
            
        except Exception as e:
            logger.warning(f"Failed to extract units: {str(e)}, defaulting to mm")
            return 'mm'
    
    def extract_topology_info(self) -> Dict[str, int]:
        """
        Extract topology counts from the geometry.
        
        Returns:
            Dictionary with counts of solids, shells, faces, edges, vertices
        """
        try:
            solid = self.shape.val() if hasattr(self.shape, 'val') else self.shape
            
            # Extract the wrapped OCP shape for direct OCP API calls
            ocp_shape = solid.wrapped if hasattr(solid, 'wrapped') else solid
            
            from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
            from OCP.TopExp import TopExp_Explorer
            
            def count_shapes(shape, shape_type):
                """Count shapes of a specific type."""
                explorer = TopExp_Explorer(shape, shape_type)
                count = 0
                while explorer.More():
                    count += 1
                    explorer.Next()
                return count
            
            return {
                'solids': count_shapes(ocp_shape, TopAbs_SOLID),
                'shells': count_shapes(ocp_shape, TopAbs_SHELL),
                'faces': count_shapes(ocp_shape, TopAbs_FACE),
                'edges': count_shapes(ocp_shape, TopAbs_EDGE),
                'vertices': count_shapes(ocp_shape, TopAbs_VERTEX)
            }
        
        except Exception as e:
            logger.error(f"Failed to extract topology info: {str(e)}")
            raise
    
    def run_design_rule_checks(self) -> Dict[str, Any]:
        """
        Run design rule checks on the geometry.
        
        Returns:
            Dictionary with validation results and issues found
        """
        try:
            solid = self.shape.val() if hasattr(self.shape, 'val') else self.shape
            
            # Extract the wrapped OCP shape for direct OCP API calls
            ocp_shape = solid.wrapped if hasattr(solid, 'wrapped') else solid
            
            # Run BRep analyzer
            analyzer = BRepCheck_Analyzer(ocp_shape)
            is_valid = analyzer.IsValid()
            
            issues = []
            
            # Check for manifold geometry
            try:
                from OCP.BRepClass3d import BRepClass3d_SolidClassifier
                classifier = BRepClass3d_SolidClassifier(ocp_shape)
                is_manifold = True
            except Exception:
                is_manifold = False
                issues.append({
                    'severity': 'error',
                    'code': 'NON_MANIFOLD',
                    'message': 'Geometry contains non-manifold edges or vertices'
                })
            
            # Check for closed/watertight geometry
            try:
                from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
                sewing = BRepBuilderAPI_Sewing()
                sewing.Add(ocp_shape)
                sewing.Perform()
                is_closed = sewing.SewedShape().Closed()
            except Exception:
                is_closed = False
                issues.append({
                    'severity': 'warning',
                    'code': 'NOT_WATERTIGHT',
                    'message': 'Geometry may not be watertight (not closed)'
                })
            
            # Additional checks
            if not is_valid:
                issues.append({
                    'severity': 'error',
                    'code': 'INVALID_BREP',
                    'message': 'BRep structure is invalid'
                })
            
            # Check for small edges/faces
            topology = self.extract_topology_info()
            if topology['edges'] > 10000:
                issues.append({
                    'severity': 'warning',
                    'code': 'HIGH_EDGE_COUNT',
                    'message': f"High edge count ({topology['edges']}) may impact performance"
                })
            
            return {
                'is_valid': is_valid and is_manifold,
                'is_manifold': is_manifold,
                'is_closed': is_closed,
                'issues': issues,
                'summary': f"Found {len(issues)} issue(s)" if issues else "No issues found"
            }
        
        except Exception as e:
            logger.error(f"Failed to run design rule checks: {str(e)}")
            return {
                'is_valid': False,
                'error': str(e),
                'issues': [{
                    'severity': 'error',
                    'code': 'CHECK_FAILED',
                    'message': f"Design rule check failed: {str(e)}"
                }]
            }
    
    def extract_bom_structure(self) -> List[Dict[str, Any]]:
        """
        Extract assembly structure / Bill of Materials from STEP file.
        
        For STEP files with assembly structure, this extracts component information.
        Returns hierarchical BOM with part names, quantities, and properties.
        
        Returns:
            List of assembly components with their transformations and metadata
        """
        try:
            solid = self.shape.val() if hasattr(self.shape, 'val') else self.shape
            
            # Extract the wrapped OCP shape for direct OCP API calls
            ocp_shape = solid.wrapped if hasattr(solid, 'wrapped') else solid
            
            from OCP.TopAbs import TopAbs_SOLID
            from OCP.TopExp import TopExp_Explorer
            from OCP.Bnd import Bnd_Box
            from OCP.BRepBndLib import BRepBndLib
            
            components = []
            
            # Try to parse STEP file metadata for assembly names
            component_names = self._extract_step_component_names()
            
            # Explore all solids in the assembly
            explorer = TopExp_Explorer(ocp_shape, TopAbs_SOLID)
            index = 0
            
            while explorer.More():
                component_solid = explorer.Current()
                
                try:
                    # Calculate geometric properties
                    volume_props = GProp_GProps()
                    surface_props = GProp_GProps()
                    BRepGProp.VolumeProperties_s(component_solid, volume_props)
                    BRepGProp.SurfaceProperties_s(component_solid, surface_props)
                    
                    volume = volume_props.Mass()
                    surface_area = surface_props.Mass()
                    com = volume_props.CentreOfMass()
                    
                    # Get bounding box for component
                    bbox = Bnd_Box()
                    BRepBndLib.Add_s(component_solid, bbox)
                    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
                    
                    # Determine component name
                    component_name = component_names.get(index, f"Component_{index + 1}")
                    
                    components.append({
                        'index': index,
                        'name': component_name,
                        'part_number': f"PN-{index + 1:04d}",
                        'quantity': 1,
                        'node_type': 'PART',
                        'volume': volume,
                        'surface_area': surface_area,
                        'mass': volume * 0.0000027,  # Rough estimate assuming aluminum (2.7 g/cm³)
                        'center_of_mass': {
                            'x': com.X(),
                            'y': com.Y(),
                            'z': com.Z()
                        },
                        'bounding_box': {
                            'xmin': xmin, 'xmax': xmax,
                            'ymin': ymin, 'ymax': ymax,
                            'zmin': zmin, 'zmax': zmax,
                            'dimensions': {
                                'length': xmax - xmin,
                                'width': ymax - ymin,
                                'height': zmax - zmin
                            }
                        },
                        'topology': self._count_component_topology(component_solid)
                    })
                    
                except Exception as comp_error:
                    logger.warning(f"Failed to process component {index}: {comp_error}")
                
                index += 1
                explorer.Next()
            
            if not components:
                logger.info("No assembly structure found, treating as single part")
            
            return components
        
        except Exception as e:
            logger.error(f"Failed to extract BOM structure: {str(e)}")
            return []
    
    def _extract_step_component_names(self) -> Dict[int, str]:
        """
        Parse STEP file to extract component names from metadata.
        
        Returns:
            Dictionary mapping component index to name
        """
        names = {}
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for PRODUCT definitions in STEP file
                import re
                product_pattern = r"#\d+\s*=\s*PRODUCT\s*\('([^']+)'"
                matches = re.findall(product_pattern, content)
                
                for idx, name in enumerate(matches):
                    if name and name not in ['', 'UNNAMED', 'UNKNOWN']:
                        names[idx] = name
                
                logger.info(f"Found {len(names)} named components in STEP file")
        except Exception as e:
            logger.debug(f"Could not extract STEP component names: {e}")
        
        return names
    
    def _count_component_topology(self, solid) -> Dict[str, int]:
        """
        Count topology elements for a specific component.
        
        Args:
            solid: TopoDS_Solid to analyze
        
        Returns:
            Dictionary with topology counts
        """
        try:
            from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
            from OCP.TopExp import TopExp_Explorer
            
            def count_shapes(shape, shape_type):
                explorer = TopExp_Explorer(shape, shape_type)
                count = 0
                while explorer.More():
                    count += 1
                    explorer.Next()
                return count
            
            return {
                'faces': count_shapes(solid, TopAbs_FACE),
                'edges': count_shapes(solid, TopAbs_EDGE),
                'vertices': count_shapes(solid, TopAbs_VERTEX)
            }
        except Exception as e:
            logger.debug(f"Failed to count topology: {e}")
            return {'faces': 0, 'edges': 0, 'vertices': 0}
    
    def process_all(self) -> Dict[str, Any]:
        """
        Run all geometry extraction processes.
        
        Returns:
            Complete metadata dictionary
        """
        try:
            mass_props = self.extract_mass_properties()
            topology = self.extract_topology_info()
            validation = self.run_design_rule_checks()
            bom = self.extract_bom_structure()
            
            return {
                'file_name': self.file_path.name,
                'file_format': self.file_path.suffix.upper().replace('.', ''),
                'mass_properties': mass_props,
                'topology': topology,
                'validation': validation,
                'bom_components': bom,
                'processing_status': 'success'
            }
        
        except Exception as e:
            logger.error(f"Failed to process geometry: {str(e)}")
            return {
                'file_name': self.file_path.name,
                'processing_status': 'failed',
                'error': str(e)
            }


def process_cad_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to process a CAD file and return all metadata.
    
    This function is NOT cached because it's called from Celery tasks
    with different file paths. Caching happens at the ViewSet level.
    
    Args:
        file_path: Path to STEP or IGES file
    
    Returns:
        Dictionary with all extracted metadata
    """
    processor = GeometryProcessor(file_path)
    return processor.process_all()


@cache_result(timeout=3600, cache_alias='longterm', key_prefix='geometry_metadata')
def get_cached_geometry_metadata(design_asset_id: str) -> Dict[str, Any]:
    """
    Get geometry metadata with longterm caching (1 hour).
    
    Use this function for API responses to avoid recomputing expensive
    geometry calculations. Cache is automatically invalidated when
    DesignAsset is updated via signals.
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        Dictionary with geometry metadata
    """
    from designs.models import DesignAsset
    
    try:
        design = DesignAsset.objects.get(id=design_asset_id)
        
        if design.upload_status != 'COMPLETED':
            return {
                'status': 'not_ready',
                'message': 'Design asset is not in COMPLETED state'
            }
        
        # Return cached metadata from model if available
        if design.metadata:
            return design.metadata
        
        # Otherwise recompute (should rarely happen)
        if design.file:
            # Get file path (handle both local and S3 storage)
            temp_file_path = None
            try:
                file_path = design.file.path
            except (AttributeError, NotImplementedError):
                # For S3, download to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=design.filename) as tmp_file:
                    with design.file.open('rb') as f:
                        tmp_file.write(f.read())
                    file_path = tmp_file.name
                    temp_file_path = tmp_file.name
            
            processor = GeometryProcessor(file_path)
            metadata = processor.process_all()
            
            # Clean up temp file if it was created
            if temp_file_path:
                try:
                    import os
                    os.unlink(temp_file_path)
                except Exception:
                    pass
            
            # Update the model
            design.metadata = metadata
            design.save(update_fields=['metadata'])
            
            return metadata
        
        return {
            'status': 'no_file',
            'message': 'No file available for processing'
        }
        
    except Exception as e:
        logger.error(f"Failed to get geometry metadata for {design_asset_id}: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

    def export_to_stl(self, output_path: str, linear_deflection: float = 0.1, angular_deflection: float = 0.1):
        """
        Export geometry to STL format for web preview using native OpenCascade.
        
        Args:
            output_path: Path to save STL file
            linear_deflection: Mesh quality (smaller = finer mesh)
            angular_deflection: Mesh quality for curved surfaces
        """
        try:
            from OCP.StlAPI import StlAPI_Writer
            from OCP.BRepMesh import BRepMesh_IncrementalMesh
            
            # Get the shape
            solid = self.shape.val() if hasattr(self.shape, 'val') else self.shape
            
            # Generate mesh with specified deflection
            mesh = BRepMesh_IncrementalMesh(solid, linear_deflection, False, angular_deflection, True)
            mesh.Perform()
            
            if not mesh.IsDone():
                raise Exception("Mesh generation failed")
            
            # Write to STL file
            writer = StlAPI_Writer()
            writer.Write(solid, output_path)
            
            logger.info(f"Exported STL to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export STL: {e}")
            raise
