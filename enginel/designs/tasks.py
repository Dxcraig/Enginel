"""
Celery tasks for Enginel.

Handles asynchronous processing of design assets:
- File hash calculation
- Geometry extraction (STEP/IGES parsing)
- Design rule checks (DRC)
- BOM extraction
- Unit normalization

Integrated with task monitoring for progress tracking and metrics.
"""
import hashlib
import logging
import os
import time
from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone
from django.db import models
from .models import DesignAsset, AnalysisJob, AssemblyNode
from .geometry_processor import GeometryProcessor, GEOMETRY_AVAILABLE
from .unit_converter import (
    convert_length, convert_area, convert_volume,
    detect_unit_from_filename, get_scale_factor, BASE_UNIT
)
from .monitoring import PerformanceMonitor, ErrorTracker, MetricsCollector
from .task_monitor import task_metrics, TaskProgressTracker
from .exceptions import (
    GeometryProcessingError,
    BOMExtractionError,
    UnitConversionError,
    raise_geometry_error
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_design_asset(self, design_asset_id):
    """
    Main task to process uploaded design asset.
    
    Args:
        design_asset_id: UUID of the DesignAsset to process
    
    Flow:
        1. Calculate file hash (SHA-256)
        2. Extract geometry metadata (volume, area, mass properties)
        3. Run design rule checks (DRC)
        4. Extract BOM if assembly
        5. Update status to COMPLETED or FAILED
    """
    task_id = self.request.id
    task_metrics.record_task_start(task_id, 'process_design_asset', 'PROCESSING')
    
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Processing design asset: {design_asset.filename}")
        
        # Update status
        # Step 1: Calculate file hash
        TaskProgressTracker.update_progress(task_id, 1, 5, 'Calculating file hash...')
        hash_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='HASH_CALCULATION',
            status='RUNNING',
            celery_task_id=self.request.id,
            started_at=timezone.now()
        )
        
        # Step 1: Calculate file hash (run inline, quick operation)
        file_hash = calculate_file_hash(design_asset_id)
        design_asset.file_hash = file_hash
        design_asset.save()
        
        hash_job.status = 'SUCCESS'
        hash_job.result = {'file_hash': file_hash}
        hash_job.completed_at = timezone.now()
        hash_job.save()
        
        # Step 2: Extract geometry metadata (run inline)
        TaskProgressTracker.update_progress(task_id, 2, 5, 'Extracting geometry metadata...')
        metadata_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='GEOMETRY_EXTRACTION',
            status='RUNNING',
            started_at=timezone.now()
        )
        
        metadata = extract_geometry_metadata(design_asset_id)
        design_asset.metadata = metadata
        design_asset.save()
        
        metadata_job.status = 'SUCCESS'
        metadata_job.result = metadata
        metadata_job.completed_at = timezone.now()
        metadata_job.save()
        
        # Step 2.5: Generate web preview (STL) for STEP/IGES files
        file_ext = os.path.splitext(design_asset.filename)[1].lower()
        if file_ext in ['.step', '.stp', '.iges', '.igs']:
            TaskProgressTracker.update_progress(task_id, 2.5, 5, 'Generating web preview...')
            try:
                generate_web_preview(design_asset_id)
                logger.info(f"Web preview generated for {design_asset.filename}")
            except Exception as preview_error:
                logger.warning(f"Preview generation failed (non-critical): {preview_error}")
        
        # Step 3: Run design rule checks (run inline)
        TaskProgressTracker.update_progress(task_id, 3, 5, 'Running design rule checks...')
        validation_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='VALIDATION',
            status='RUNNING',
            started_at=timezone.now()
        )
        
        validation_result = run_design_rule_checks(design_asset_id)
        design_asset.is_valid_geometry = validation_result['is_valid']
        design_asset.validation_report = validation_result
        design_asset.save()
        
        validation_job.status = 'SUCCESS'
        validation_job.result = validation_result
        validation_job.completed_at = timezone.now()
        validation_job.save()
        
        # Step 4: Extract BOM (if assembly file)
        TaskProgressTracker.update_progress(task_id, 4, 5, 'Extracting BOM structure...')
        try:
            bom_result = extract_bom_from_assembly(design_asset_id)
            logger.info(f"BOM extraction result: {bom_result.get('bom_nodes_created', 0)} nodes created")
        except Exception as bom_error:
            logger.warning(f"BOM extraction failed (non-critical): {bom_error}")
        
        # Step 5: Normalize units
        try:
            unit_result = normalize_units(design_asset_id)
            logger.info(f"Unit normalization: {unit_result.get('original_unit', 'N/A')} → {unit_result.get('target_unit', 'N/A')}")
        except Exception as unit_error:
            logger.warning(f"Unit normalization failed (non-critical): {unit_error}")
        
        # Mark as completed
        TaskProgressTracker.update_progress(task_id, 5, 5, 'Processing complete!')
        design_asset.status = 'COMPLETED'
        design_asset.processed_at = timezone.now()
        design_asset.save()
        
        task_metrics.record_task_completion(task_id, success=True)
        logger.info(f"Successfully processed design asset: {design_asset.filename}")
        return {'status': 'success', 'design_asset_id': str(design_asset_id)}
        
    except DesignAsset.DoesNotExist:
        logger.error(f"DesignAsset {design_asset_id} not found")
        ErrorTracker.log_error(
            Exception(f"DesignAsset {design_asset_id} not found"),
            context={'design_asset_id': str(design_asset_id), 'task': 'process_design_asset'},
            severity='ERROR'
        )
        task_metrics.record_task_completion(task_id, success=False, error='DesignAsset not found')
        raise
    
    except Exception as exc:
        logger.error(f"Error processing design asset {design_asset_id}: {exc}")
        
        # Track error
        ErrorTracker.log_error(
            exc,
            context={'design_asset_id': str(design_asset_id), 'task': 'process_design_asset'},
            severity='ERROR'
        )
        
        # Record task failure
        task_metrics.record_task_completion(task_id, success=False, error=str(exc))
        
        # Update status to failed
        try:
            design_asset = DesignAsset.objects.get(id=design_asset_id)
            design_asset.status = 'FAILED'
            design_asset.processing_error = str(exc)
            design_asset.save()
        except Exception:
            pass
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
@PerformanceMonitor.track_duration('file_hash_calculation')
def calculate_file_hash(design_asset_id):
    """
    Calculate SHA-256 hash of uploaded file.
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        str: Hexadecimal SHA-256 hash
    """
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        
        if not design_asset.file:
            logger.warning(f"No file attached to {design_asset_id}")
            return None
        
        logger.info(f"Calculating hash for: {design_asset.filename}")
        logger.info(f"Storage backend: {design_asset.file.storage.__class__.__name__}")
        logger.info(f"File path: {design_asset.file.name}")
        
        hasher = hashlib.sha256()
        
        # Read file in chunks to handle large files
        with design_asset.file.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        file_hash = hasher.hexdigest()
        logger.info(f"Hash calculated: {file_hash}")
        return file_hash
        
    except Exception as exc:
        logger.error(f"Error calculating hash: {exc}")
        raise


@shared_task
@PerformanceMonitor.track_duration('geometry_extraction')
def extract_geometry_metadata(design_asset_id):
    """
    Extract geometric metadata from CAD file.
    
    Uses OpenCASCADE to parse STEP/IGES and extract:
    - Volume
    - Surface area
    - Center of mass
    - Bounding box
    - Part count
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        dict: Metadata including volume, area, mass properties
    """
    start_time = time.time()
    
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Extracting geometry metadata for: {design_asset.filename}")
        
        # Check file format - only STEP/IGES supported for geometry extraction
        file_ext = os.path.splitext(design_asset.filename)[1].lower()
        if file_ext not in ['.step', '.stp', '.iges', '.igs']:
            logger.info(f"Skipping geometry extraction for unsupported format: {file_ext}")
            metadata = {
                'volume_mm3': 0.0,
                'surface_area_mm2': 0.0,
                'center_of_mass': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'bounding_box': {
                    'min': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                    'max': {'x': 0.0, 'y': 0.0, 'z': 0.0}
                },
                'part_count': 1,
                'unit': 'millimeters',
                'note': f'Geometry extraction not available for {file_ext} files'
            }
            return metadata
        
        if not GEOMETRY_AVAILABLE:
            logger.warning("CadQuery/OCP not available. Returning placeholder metadata.")
            metadata = {
                'volume_mm3': 0.0,
                'surface_area_mm2': 0.0,
                'center_of_mass': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'bounding_box': {
                    'min': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                    'max': {'x': 0.0, 'y': 0.0, 'z': 0.0}
                },
                'part_count': 1,
                'unit': 'millimeters',
                'note': 'Geometry processing unavailable - install cadquery'
            }
            return metadata
        
        if not design_asset.file:
            logger.warning(f"No file attached to {design_asset_id}")
            raise GeometryProcessingError("No file attached to design asset")
            return {'error': 'No file available for processing'}
        
        # Get file path (works with both local storage and S3)
        temp_file_path = None
        try:
            file_path = design_asset.file.path
        except (AttributeError, NotImplementedError):
            # For S3, download to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=design_asset.filename) as tmp_file:
                with design_asset.file.open('rb') as f:
                    tmp_file.write(f.read())
                file_path = tmp_file.name
                temp_file_path = tmp_file.name  # Track for cleanup
                logger.info(f"Downloaded S3 file to temp path: {file_path}")
        
        # Process with GeometryProcessor
        processor = GeometryProcessor(file_path)
        mass_props = processor.extract_mass_properties()
        topology = processor.extract_topology_info()
        
        # Clean up temp file if it was created
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temp file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {temp_file_path}: {cleanup_error}")
        
        metadata = {
            'volume_mm3': mass_props['volume'],
            'surface_area_mm2': mass_props['surface_area'],
            'center_of_mass': mass_props['center_of_mass'],
            'bounding_box': {
                'min': {
                    'x': mass_props['bounding_box']['xmin'],
                    'y': mass_props['bounding_box']['ymin'],
                    'z': mass_props['bounding_box']['zmin']
                },
                'max': {
                    'x': mass_props['bounding_box']['xmax'],
                    'y': mass_props['bounding_box']['ymax'],
                    'z': mass_props['bounding_box']['zmax']
                },
                'dimensions': mass_props['bounding_box']['dimensions']
            },
            'topology': topology,
            'unit': 'millimeters'
        }
        
        logger.info(f"Metadata extracted: volume={metadata['volume_mm3']:.2f} mm³")
        return metadata
        
    except Exception as exc:
        logger.error(f"Error extracting metadata: {exc}")
        raise


@shared_task
def generate_web_preview(design_asset_id):
    """
    Generate web-friendly preview file (STL) from STEP/IGES for Three.js viewing.
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        dict: Preview generation result with S3 key
    """
    try:
        from django.core.files.base import ContentFile
        from django.conf import settings
        import tempfile
        
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Generating web preview for: {design_asset.filename}")
        
        if not design_asset.file:
            logger.warning(f"No file attached to {design_asset_id}")
            return {'status': 'no_file'}
        
        # Check if already has preview
        if design_asset.preview_file:
            logger.info(f"Preview already exists: {design_asset.preview_file.name}")
            return {'status': 'exists', 'preview_key': design_asset.preview_file.name}
        
        # Get file path (download from S3 if needed)
        temp_input_path = None
        temp_output_path = None
        try:
            file_path = design_asset.file.path
        except (AttributeError, NotImplementedError):
            # For S3, download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=design_asset.filename) as tmp_file:
                with design_asset.file.open('rb') as f:
                    tmp_file.write(f.read())
                file_path = tmp_file.name
                temp_input_path = tmp_file.name
                logger.info(f"Downloaded S3 file to temp path: {file_path}")
        
        # Generate STL preview
        processor = GeometryProcessor(file_path)
        
        # Create temp file for STL output
        stl_filename = f"{design_asset.id}.stl"
        with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as tmp_stl:
            temp_output_path = tmp_stl.name
        
        # Export to STL
        processor.export_to_stl(temp_output_path, linear_deflection=0.1, angular_deflection=0.1)
        
        # Upload STL to storage
        with open(temp_output_path, 'rb') as stl_file:
            stl_content = stl_file.read()
            
            # Save to preview_file field
            design_asset.preview_file.save(
                stl_filename,
                ContentFile(stl_content),
                save=False
            )
            
            # Set S3 key
            if settings.USE_S3:
                design_asset.preview_s3_key = f"designs/{design_asset.id}/{stl_filename}"
            
            design_asset.save(update_fields=['preview_file', 'preview_s3_key'])
        
        logger.info(f"Preview generated and uploaded: {design_asset.preview_file.name}")
        
        # Cleanup temp files
        if temp_input_path:
            try:
                os.unlink(temp_input_path)
            except Exception:
                pass
        if temp_output_path:
            try:
                os.unlink(temp_output_path)
            except Exception:
                pass
        
        return {
            'status': 'success',
            'preview_key': design_asset.preview_file.name,
            'preview_s3_key': design_asset.preview_s3_key
        }
        
    except Exception as exc:
        logger.error(f"Error generating preview: {exc}")
        raise


@shared_task
def run_design_rule_checks(design_asset_id):
    """
    Run design rule checks (DRC) on geometry.
    
    Validates:
    - Manifold geometry (watertight)
    - No self-intersections
    - Valid topology
    - Minimum feature sizes
    - Unit consistency
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        dict: Validation results with is_valid flag and error list
    """
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Running DRC for: {design_asset.filename}")
        
        if not GEOMETRY_AVAILABLE:
            logger.warning("CadQuery/OCP not available. Skipping validation.")
            validation_result = {
                'is_valid': True,
                'errors': {},
                'warnings': [{'message': 'Geometry validation unavailable - install cadquery'}],
                'checks_performed': []
            }
            return validation_result
        
        if not design_asset.file:
            logger.warning(f"No file attached to {design_asset_id}")
            return {'is_valid': False, 'errors': {'file': 'No file available for validation'}}
        
        # Get file path (handle both local and S3 storage)
        if hasattr(design_asset.file, 'path'):
            file_path = design_asset.file.path
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=design_asset.filename) as tmp_file:
                with design_asset.file.open('rb') as f:
                    tmp_file.write(f.read())
                file_path = tmp_file.name
        
        # Run validation with GeometryProcessor
        processor = GeometryProcessor(file_path)
        validation = processor.run_design_rule_checks()
        
        # Convert to expected format
        validation_result = {
            'is_valid': validation['is_valid'],
            'is_manifold': validation.get('is_manifold', False),
            'is_closed': validation.get('is_closed', False),
            'errors': {issue['code']: issue['message'] for issue in validation.get('issues', []) if issue['severity'] == 'error'},
            'warnings': [{'code': issue['code'], 'message': issue['message']} for issue in validation.get('issues', []) if issue['severity'] == 'warning'],
            'checks_performed': [
                'manifold_check',
                'watertight_check',
                'brep_validity_check',
                'topology_check'
            ],
            'summary': validation.get('summary', 'No issues found')
        }
        
        logger.info(f"DRC completed: {validation_result['summary']}")
        return validation_result
        
    except Exception as exc:
        logger.error(f"Error running DRC: {exc}")
        raise


@shared_task
def extract_bom_from_assembly(design_asset_id):
    """
    Extract Bill of Materials from assembly file.
    
    Parses assembly structure and creates AssemblyNode tree.
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        dict: BOM extraction results
    """
    bom_job = None
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Extracting BOM for: {design_asset.filename}")
        
        # Create analysis job
        bom_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='BOM_PARSING',
            status='RUNNING',
            started_at=timezone.now()
        )
        
        if not GEOMETRY_AVAILABLE:
            logger.warning("CadQuery/OCP not available. Skipping BOM extraction.")
            bom_job.status = 'SUCCESS'
            bom_job.result = {'components': [], 'note': 'BOM extraction unavailable - install cadquery'}
            bom_job.completed_at = timezone.now()
            bom_job.save()
            return {'components': []}
        
        if not design_asset.file:
            logger.warning(f"No file attached to {design_asset_id}")
            bom_job.status = 'FAILED'
            bom_job.result = {'error': 'No file available'}
            bom_job.completed_at = timezone.now()
            bom_job.save()
            return {'error': 'No file available'}
        
        # Get file path (handle both local and S3 storage)
        if hasattr(design_asset.file, 'path'):
            file_path = design_asset.file.path
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=design_asset.filename) as tmp_file:
                with design_asset.file.open('rb') as f:
                    tmp_file.write(f.read())
                file_path = tmp_file.name
        
        # Extract BOM using GeometryProcessor
        processor = GeometryProcessor(file_path)
        components = processor.extract_bom_structure()
        
        # Clear existing BOM nodes for this design
        AssemblyNode.objects.filter(design_asset=design_asset).delete()
        
        # Create AssemblyNode tree from extracted components
        if components:
            # Create root assembly node
            root = AssemblyNode.add_root(
                design_asset=design_asset,
                name=design_asset.filename.rsplit('.', 1)[0],  # Remove extension
                part_number=design_asset.series.part_number,
                node_type='ASSEMBLY',
                quantity=1,
                mass=sum(comp.get('mass', 0) for comp in components),
                volume=sum(comp.get('volume', 0) for comp in components),
                component_metadata={
                    'is_root': True,
                    'component_count': len(components),
                    'file_format': design_asset.filename.rsplit('.', 1)[-1].upper()
                }
            )
            
            # Add component nodes as children
            for comp in components:
                child = root.add_child(
                    design_asset=design_asset,
                    name=comp['name'],
                    part_number=comp['part_number'],
                    node_type=comp.get('node_type', 'PART'),
                    quantity=comp.get('quantity', 1),
                    mass=comp.get('mass'),
                    volume=comp.get('volume'),
                    component_metadata={
                        'index': comp['index'],
                        'surface_area': comp.get('surface_area', 0),
                        'center_of_mass': comp.get('center_of_mass', {}),
                        'bounding_box': comp.get('bounding_box', {}),
                        'topology': comp.get('topology', {})
                    }
                )
                logger.debug(f"Created BOM node: {child.name} ({child.part_number})")
            
            result = {
                'bom_nodes_created': len(components) + 1,  # +1 for root
                'root_assemblies': 1,
                'total_parts': len(components),
                'total_mass': root.mass,
                'total_volume': root.volume,
                'components': components[:10]  # Only include first 10 for result summary
            }
        else:
            # Single part, no assembly - create single node
            root = AssemblyNode.add_root(
                design_asset=design_asset,
                name=design_asset.filename.rsplit('.', 1)[0],
                part_number=design_asset.series.part_number,
                node_type='PART',
                quantity=1,
                mass=design_asset.metadata.get('mass_properties', {}).get('mass', 0) if design_asset.metadata else 0,
                volume=design_asset.metadata.get('volume_mm3', 0) if design_asset.metadata else 0,
                component_metadata={
                    'is_root': True,
                    'single_part': True
                }
            )
            
            result = {
                'bom_nodes_created': 1,
                'root_assemblies': 1,
                'total_parts': 1,
                'note': 'Single part file, no assembly structure'
            }
        
        bom_job.status = 'SUCCESS'
        bom_job.result = result
        bom_job.completed_at = timezone.now()
        bom_job.save()
        
        logger.info(f"BOM extraction completed: {result['total_parts']} parts")
        return result
        
    except Exception as exc:
        logger.error(f"Error extracting BOM: {exc}")
        
        if bom_job:
            bom_job.status = 'FAILED'
            bom_job.error_message = str(exc)
            bom_job.completed_at = timezone.now()
            bom_job.save()
        
        raise


@shared_task
def normalize_units(design_asset_id, unit_override=None):
    """
    Normalize physical units to standard (millimeters).
    
    Detects units from CAD file and converts all measurements
    to millimeters to prevent unit confusion errors.
    
    Args:
        design_asset_id: UUID of the DesignAsset
        unit_override: Optional unit to use instead of auto-detection
    
    Returns:
        dict: Unit conversion results
    """
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Normalizing units for: {design_asset.filename}")
        
        # Determine original unit (priority: override > stored > auto-detect)
        original_unit = unit_override or design_asset.units
        if not original_unit or original_unit == 'unknown':
            original_unit = detect_unit_from_filename(design_asset.filename)
            logger.info(f"Auto-detected unit: {original_unit}")
        
        # If already in base unit, no conversion needed
        if original_unit == BASE_UNIT:
            logger.info(f"Already in base unit ({BASE_UNIT}), no conversion needed")
            return {
                'original_unit': original_unit,
                'target_unit': BASE_UNIT,
                'conversion_factor': 1.0,
                'converted': False
            }
        
        # Get metadata to convert
        metadata = design_asset.metadata or {}
        
        # Convert geometric measurements
        conversions = {}
        
        if 'volume' in metadata:
            original_volume = metadata['volume']
            converted_volume = convert_volume(original_volume, original_unit, BASE_UNIT)
            conversions['volume'] = {
                'original': original_volume,
                'converted': converted_volume,
                'unit': f'{BASE_UNIT}³'
            }
            metadata['volume_mm3'] = converted_volume
        
        if 'surface_area' in metadata:
            original_area = metadata['surface_area']
            converted_area = convert_area(original_area, original_unit, BASE_UNIT)
            conversions['surface_area'] = {
                'original': original_area,
                'converted': converted_area,
                'unit': f'{BASE_UNIT}²'
            }
            metadata['surface_area_mm2'] = converted_area
        
        # Convert bounding box
        if 'bounding_box' in metadata:
            bbox = metadata['bounding_box']
            for key in ['xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax']:
                if key in bbox:
                    bbox[key] = convert_length(bbox[key], original_unit, BASE_UNIT)
            
            if 'dimensions' in bbox:
                dims = bbox['dimensions']
                for key in ['length', 'width', 'height']:
                    if key in dims:
                        dims[key] = convert_length(dims[key], original_unit, BASE_UNIT)
        
        # Convert center of mass
        if 'center_of_mass' in metadata:
            com = metadata['center_of_mass']
            for key in ['x', 'y', 'z']:
                if key in com:
                    com[key] = convert_length(com[key], original_unit, BASE_UNIT)
        
        # Add conversion metadata
        metadata['unit_conversion'] = {
            'original_unit': original_unit,
            'target_unit': BASE_UNIT,
            'conversions': conversions,
            'timestamp': timezone.now().isoformat()
        }
        
        # Update design asset
        design_asset.metadata = metadata
        design_asset.units = BASE_UNIT
        design_asset.save()
        
        logger.info(f"Unit conversion complete: {original_unit} → {BASE_UNIT}")
        
        result = {
            'original_unit': original_unit,
            'target_unit': BASE_UNIT,
            'conversion_factor': convert_length(1.0, original_unit, BASE_UNIT),
            'converted': True,
            'conversions': conversions
        }
        
        return result
        
    except Exception as exc:
        logger.error(f"Error normalizing units: {exc}")
        raise


@shared_task(bind=True)
def create_analysis_job(self, design_asset_id, job_type):
    """
    Create and track a new analysis job.
    
    Args:
        design_asset_id: UUID of the DesignAsset
        job_type: Type of analysis (e.g., 'MASS_PROPERTIES', 'INTERFERENCE_CHECK')
    
    Returns:
        dict: Job creation results
    """
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        
        job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type=job_type,
            status='PENDING',
            celery_task_id=self.request.id,
            created_at=timezone.now()
        )
        
        logger.info(f"Created analysis job {job.id} for {design_asset.filename}")
        
        return {
            'job_id': str(job.id),
            'design_asset_id': str(design_asset_id),
            'job_type': job_type,
            'status': 'PENDING'
        }
        
    except Exception as exc:
        logger.error(f"Error creating analysis job: {exc}")
        raise


# Email Notification Tasks

@shared_task(bind=True, max_retries=3)
def send_email_notification(self, notification_id):
    """
    Send a single email notification.
    
    Args:
        notification_id: UUID of the EmailNotification to send
    
    Returns:
        Dict with status and details
    """
    from .models import EmailNotification
    from .notifications import EmailSender
    
    try:
        notification = EmailNotification.objects.get(id=notification_id)
        
        # Check if notification can be sent
        if not notification.can_send_now():
            logger.info(f"Notification {notification_id} cannot be sent now")
            return {
                'notification_id': str(notification_id),
                'status': 'SKIPPED',
                'reason': 'Cannot send now (retry scheduled or max retries exceeded)'
            }
        
        # Send notification
        success = EmailSender.send_notification(notification)
        
        return {
            'notification_id': str(notification_id),
            'status': 'SENT' if success else 'FAILED',
            'recipient': notification.recipient.email,
            'type': notification.notification_type,
        }
        
    except EmailNotification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        raise
    except Exception as exc:
        logger.error(f"Error sending notification {notification_id}: {exc}")
        
        # Retry with exponential backoff
        try:
            notification = EmailNotification.objects.get(id=notification_id)
            notification.mark_failed(str(exc))
        except:
            pass
        
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def process_pending_notifications():
    """
    Process all pending email notifications in batch.
    
    This task runs periodically (e.g., every 5 minutes) to process
    notifications based on user delivery preferences (immediate, digest).
    
    Returns:
        Dict with processing statistics
    """
    from django.conf import settings
    from .models import EmailNotification
    from .notifications import EmailSender
    
    # Get pending notifications, prioritized
    pending = EmailNotification.objects.filter(
        status='PENDING'
    ).filter(
        models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=timezone.now())
    ).order_by(
        '-priority',  # HIGH before NORMAL
        'queued_at'   # Oldest first
    )[:settings.NOTIFICATION_BATCH_SIZE]
    
    if not pending:
        logger.info("No pending notifications to process")
        return {'processed': 0, 'sent': 0, 'failed': 0}
    
    logger.info(f"Processing {len(pending)} pending notifications")
    
    # Send in batch
    results = EmailSender.send_batch(pending)
    
    return {
        'processed': len(pending),
        'sent': results['sent'],
        'failed': results['failed'],
    }


@shared_task
def send_digest_notifications():
    """
    Send digest emails for users who prefer batched notifications.
    
    This task runs hourly/daily/weekly based on user preferences
    and bundles multiple notifications into a single email.
    """
    from django.conf import settings
    from django.db.models import Q
    from .models import EmailNotification, NotificationPreference, CustomUser
    from .notifications import EmailSender
    
    # For now, we'll just handle hourly digests
    # You can expand this to handle daily/weekly
    
    # Get users with digest preference
    digest_users = CustomUser.objects.filter(
        notification_preferences__delivery_method='HOURLY',
        notification_preferences__email_enabled=True
    )
    
    results = {'users_processed': 0, 'digests_sent': 0}
    
    for user in digest_users:
        # Get pending notifications for this user
        notifications = EmailNotification.objects.filter(
            recipient=user,
            status='PENDING',
            queued_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).order_by('-priority', 'queued_at')
        
        if not notifications:
            continue
        
        # Create digest email
        subject = f"Enginel Digest - {notifications.count()} notifications"
        
        message_parts = [
            f"Hello {user.first_name or user.username},",
            "",
            f"You have {notifications.count()} new notifications:",
            "",
        ]
        
        for notif in notifications:
            message_parts.append(f"• {notif.subject}")
            message_parts.append(f"  {notif.message_plain[:100]}...")
            message_parts.append("")
        
        message_parts.extend([
            "Log in to Enginel to view all notifications.",
            "",
            "Best regards,",
            "The Enginel Team"
        ])
        
        message = "\n".join(message_parts)
        
        # Create and send digest notification
        digest_notif = EmailNotification.objects.create(
            recipient=user,
            notification_type='DIGEST',
            subject=subject,
            message_plain=message,
            priority='NORMAL',
            status='PENDING',
        )
        
        if EmailSender.send_notification(digest_notif):
            # Mark bundled notifications as sent
            notifications.update(status='SENT', sent_at=timezone.now())
            results['digests_sent'] += 1
        
        results['users_processed'] += 1
    
    return results


@shared_task
def cleanup_old_notifications():
    """
    Clean up old sent/failed notifications to keep database clean.
    
    Removes notifications older than 30 days (configurable).
    """
    from .models import EmailNotification
    
    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    
    deleted_count, _ = EmailNotification.objects.filter(
        status__in=['SENT', 'CANCELLED'],
        queued_at__lt=cutoff_date
    ).delete()
    
    logger.info(f"Cleaned up {deleted_count} old notifications")
    
    return {'deleted': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
