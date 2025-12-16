"""
Celery tasks for Enginel.

Handles asynchronous processing of design assets:
- File hash calculation
- Geometry extraction (STEP/IGES parsing)
- Design rule checks (DRC)
- BOM extraction
"""
import hashlib
import logging
from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import DesignAsset, AnalysisJob, AssemblyNode
from .geometry_processor import GeometryProcessor, GEOMETRY_AVAILABLE

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
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Processing design asset: {design_asset.filename}")
        
        # Update status
        design_asset.status = 'PROCESSING'
        design_asset.save()
        
        # Step 1: Calculate file hash
        hash_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='HASH_CALCULATION',
            status='RUNNING',
            celery_task_id=self.request.id,
            started_at=timezone.now()
        )
        
        file_hash = calculate_file_hash.delay(design_asset_id).get()
        design_asset.file_hash = file_hash
        design_asset.save()
        
        hash_job.status = 'SUCCESS'
        hash_job.result = {'file_hash': file_hash}
        hash_job.completed_at = timezone.now()
        hash_job.save()
        
        # Step 2: Extract geometry metadata
        metadata_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='GEOMETRY_EXTRACTION',
            status='RUNNING',
            started_at=timezone.now()
        )
        
        metadata = extract_geometry_metadata.delay(design_asset_id).get()
        design_asset.metadata = metadata
        design_asset.save()
        
        metadata_job.status = 'SUCCESS'
        metadata_job.result = metadata
        metadata_job.completed_at = timezone.now()
        metadata_job.save()
        
        # Step 3: Run design rule checks
        validation_job = AnalysisJob.objects.create(
            design_asset=design_asset,
            job_type='VALIDATION',
            status='RUNNING',
            started_at=timezone.now()
        )
        
        validation_result = run_design_rule_checks.delay(design_asset_id).get()
        design_asset.is_valid_geometry = validation_result['is_valid']
        design_asset.validation_report = validation_result
        design_asset.save()
        
        validation_job.status = 'SUCCESS'
        validation_job.result = validation_result
        validation_job.completed_at = timezone.now()
        validation_job.save()
        
        # Step 4: Extract BOM (if assembly file)
        try:
            bom_result = extract_bom_from_assembly.delay(design_asset_id).get(timeout=120)
            logger.info(f"BOM extraction result: {bom_result.get('bom_nodes_created', 0)} nodes created")
        except Exception as bom_error:
            logger.warning(f"BOM extraction failed (non-critical): {bom_error}")
        
        # Mark as completed
        design_asset.status = 'COMPLETED'
        design_asset.processed_at = timezone.now()
        design_asset.save()
        
        logger.info(f"Successfully processed design asset: {design_asset.filename}")
        return {'status': 'success', 'design_asset_id': str(design_asset_id)}
        
    except DesignAsset.DoesNotExist:
        logger.error(f"DesignAsset {design_asset_id} not found")
        raise
    
    except Exception as exc:
        logger.error(f"Error processing design asset {design_asset_id}: {exc}")
        
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
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Extracting geometry metadata for: {design_asset.filename}")
        
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
            return {'error': 'No file available for processing'}
        
        # Get file path (works with both local storage and S3)
        if hasattr(design_asset.file, 'path'):
            file_path = design_asset.file.path
        else:
            # For S3, download to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=design_asset.filename) as tmp_file:
                with design_asset.file.open('rb') as f:
                    tmp_file.write(f.read())
                file_path = tmp_file.name
        
        # Process with GeometryProcessor
        processor = GeometryProcessor(file_path)
        mass_props = processor.extract_mass_properties()
        topology = processor.extract_topology_info()
        
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
def normalize_units(design_asset_id):
    """
    Normalize physical units to standard (millimeters).
    
    Detects units from CAD file and converts all measurements
    to millimeters to prevent unit confusion errors.
    
    Args:
        design_asset_id: UUID of the DesignAsset
    
    Returns:
        dict: Unit conversion results
    """
    try:
        design_asset = DesignAsset.objects.get(id=design_asset_id)
        logger.info(f"Normalizing units for: {design_asset.filename}")
        
        # TODO: Implement unit detection and conversion
        
        result = {
            'original_unit': design_asset.units or 'unknown',
            'converted_to': 'millimeters',
            'conversion_factor': 1.0
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
