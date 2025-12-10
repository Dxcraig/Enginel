# Enginel
**Engineering Intelligence Kernel**

A secure, regulatory-compliant API that serves as a "Universal Translator" for engineering designs. Enginel accepts raw CAD files (STEP, IGES), cryptographically secures them, and computationally extracts "smart" data (Bill of Materials, Mass Properties, Validation Checks) for use in enterprise systems.

## 🎯 Core Value Proposition

Unlike standard file storage, Enginel treats CAD files as structured data sources, enabling non-engineering teams (procurement, compliance) to query engineering data without needing expensive CAD licenses, all while enforcing strict ITAR/CMMC security controls.

## ✨ Key Features

### Secure Ingestion
- **Direct-to-cloud upload** capability for gigabyte-scale files
- Bypasses application server to prevent bottlenecks
- Pre-signed URL mechanism for secure S3 uploads

### Deep Semantic Extraction
- Automated extraction of hierarchical Bills of Materials (BOM)
- Metadata extraction: volume, surface area, center of mass
- Leverages OpenCASCADE geometry kernel via PythonOCC/CadQuery

### Geometric Validation
- Automated Design Rule Checks (DRC) for file integrity
- Manifold geometry verification
- Watertightness checks before acceptance

### Regulatory Compliance
- **ITAR Locking**: Attribute-Based Access Control (ABAC) preventing non-US persons from accessing specific data objects
- **Immutable Auditing**: Tamper-evident log of every read/write action for CMMC Level 3 compliance
- **Unit Consistency**: Automated normalization of physical units to prevent engineering errors

## 🛠 Technology Stack

- **Web Framework**: Django (Python 3.13+) with Django REST Framework (DRF)
- **Geometry Kernel**: OpenCASCADE (OCCT) via PythonOCC or CadQuery
- **Asynchronous Engine**: Celery + Redis for offloading geometry processing
- **Database**: PostgreSQL 18 (JSONField and efficient tree storage)
- **Storage**: AWS S3 with django-storages and boto3 for presigned URLs

## 📦 Prerequisites

- Docker and Docker Compose
- Python 3.13+ (for local development)
- AWS S3 bucket (for production)
- Redis (for Celery task queue)

## 🚀 Getting Started

### Environment Setup

Create a `.env` file in the project root:

```env
# Database
POSTGRES_DB=enginel
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Django
SECRET_KEY=your_django_secret_key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# AWS S3
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-1

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Running with Docker

Start the application:

```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

To run in detached mode:

```bash
docker-compose up -d
```

Stop the application:

```bash
docker-compose down
```

### Database Migrations

Run migrations inside the container:

```bash
docker exec -it enginel_app python manage.py migrate
```

Create a superuser:

```bash
docker exec -it enginel_app python manage.py createsuperuser
```

## 📊 Data Models

### Core Django Models

#### CustomUser
Extends standard user with compliance flags:
- `is_us_person`: Boolean for ITAR compliance
- `security_clearance_level`: Integer (0-5)

#### DesignAsset
Main model for CAD file storage:
- `id`: UUID primary key
- `s3_key`: Path to raw file in secure storage
- `file_hash`: SHA-256 for integrity verification
- `classification`: Enum (UNCLASSIFIED, ITAR, EAR99)
- `metadata`: JSONField storing extracted physics data

#### AssemblyNode
Hierarchical BOM representation (using `treebeard.MP_Node`):
- `name`: Part/assembly name
- `part_number`: Engineering part number
- `quantity`: Count in parent assembly
- `reference_designator`: Position identifier

#### AuditEntry
Immutable audit log (via `django-auditlog`):
- `actor`: User who performed action
- `action`: Type (Read/Update/Delete)
- `resource_id`: Affected object
- `timestamp`: ISO 8601 timestamp
- `ip_address`: Source IP for compliance

## 🔌 API Endpoints

### Uploads

**Get Pre-signed Upload URL**
```
POST /api/designs/upload-url/
```
Returns a pre-signed S3 URL. Validates user clearance before issuing.

**Finalize Upload**
```
POST /api/designs/finalize/
```
Triggered after S3 upload completes; queues Celery analysis task.

### Data Retrieval

**Get Design Metadata**
```
GET /api/designs/{id}/
```
Returns metadata and validation status.

**Get Bill of Materials**
```
GET /api/designs/{id}/bom/
```
Returns full hierarchical BOM tree (using treebeard's `dump_bulk` method).

**Download Design File**
```
GET /api/designs/{id}/download/
```
Generates short-lived (60s) pre-signed download URL. Logs action to `AuditEntry`.

### Compliance

**View Audit Logs** (Superuser only)
```
GET /api/admin/audit-logs/
```
View immutable access history for compliance reporting.

## 📁 Project Structure

```
Enginel/
├── docker-compose.yml       # Multi-container orchestration
├── Dockerfile              # Application container definition
├── .env                    # Environment variables (create this)
└── enginel/
    ├── manage.py           # Django management script
    ├── requirements.txt    # Python dependencies
    ├── db.sqlite3          # Local SQLite (dev only)
    ├── designs/            # Main app (DesignAsset models)
    │   ├── models.py       # Data models
    │   ├── views.py        # API views
    │   └── migrations/     # Database migrations
    └── enginel/            # Project settings
        ├── settings.py     # Django configuration
        ├── urls.py         # URL routing
        └── wsgi.py         # WSGI entry point
```

## 🔒 Security Features

- **ITAR/CMMC Compliance**: Role-based access control with audit trails
- **Cryptographic Hashing**: SHA-256 verification for all file uploads
- **Pre-signed URLs**: Time-limited, secure file access (60s expiry)
- **Immutable Audit Logs**: Tamper-evident compliance logging
- **Attribute-Based Access Control**: Granular permissions based on user attributes

## 🧪 Development Roadmap

- [ ] Implement Celery workers for async geometry processing
- [ ] Integrate OpenCASCADE/PythonOCC for STEP file parsing
- [ ] Add Design Rule Check (DRC) validation engine
- [ ] Implement unit conversion/normalization system
- [ ] Deploy Redis for task queue management
- [ ] Configure AWS S3 integration with pre-signed URLs
- [ ] Add comprehensive audit logging middleware
- [ ] Implement ITAR access control decorators

## 📄 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]
