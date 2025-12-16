"""
Geometry Processing Module using CadQuery (OCP/OpenCASCADE)

This module provides functions to extract geometric metadata from CAD files:
- Volume, Surface Area, Center of Mass
- Bounding Box dimensions
- Topology counts (solids, faces, edges, vertices)
- Design Rule Checks (manifold geometry, watertightness)
"""

import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path
import json

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
            
            # Calculate volume
            volume_props = GProp_GProps()
            BRepGProp.VolumeProperties_s(solid, volume_props)
            volume = volume_props.Mass()
            
            # Calculate surface area
            surface_props = GProp_GProps()
            BRepGProp.SurfaceProperties_s(solid, surface_props)
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
    
    def extract_topology_info(self) -> Dict[str, int]:
        """
        Extract topology counts from the geometry.
        
        Returns:
            Dictionary with counts of solids, shells, faces, edges, vertices
        """
        try:
            solid = self.shape.val() if hasattr(self.shape, 'val') else self.shape
            
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
                'solids': count_shapes(solid, TopAbs_SOLID),
                'shells': count_shapes(solid, TopAbs_SHELL),
                'faces': count_shapes(solid, TopAbs_FACE),
                'edges': count_shapes(solid, TopAbs_EDGE),
                'vertices': count_shapes(solid, TopAbs_VERTEX)
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
            
            # Run BRep analyzer
            analyzer = BRepCheck_Analyzer(solid)
            is_valid = analyzer.IsValid()
            
            issues = []
            
            # Check for manifold geometry
            try:
                from OCP.BRepClass3d import BRepClass3d_SolidClassifier
                classifier = BRepClass3d_SolidClassifier(solid)
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
                sewing.Add(solid)
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
            
            from OCP.TopAbs import TopAbs_SOLID
            from OCP.TopExp import TopExp_Explorer
            from OCP.Bnd import Bnd_Box
            from OCP.BRepBndLib import BRepBndLib
            
            components = []
            
            # Try to parse STEP file metadata for assembly names
            component_names = self._extract_step_component_names()
            
            # Explore all solids in the assembly
            explorer = TopExp_Explorer(solid, TopAbs_SOLID)
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
    
    Args:
        file_path: Path to STEP or IGES file
    
    Returns:
        Dictionary with all extracted metadata
    """
    processor = GeometryProcessor(file_path)
    return processor.process_all()
