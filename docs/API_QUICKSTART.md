# Enginel API Quick Start Guide

Get started with the Enginel API in 5 minutes.

## Prerequisites

- Python 3.13+ (for examples)
- curl or HTTP client
- Access to Enginel instance (development or production)

## Step 1: Authentication

### Get Your Access Token

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'
```

**Response:**
```json
{
  "access_token": "abc123def456...",
  "refresh_token": "xyz789uvw012...",
  "expires_in": 86400,
  "token_type": "Bearer",
  "user": {
    "id": 1,
    "username": "your-username",
    "email": "you@example.com"
  }
}
```

**Save your token:**
```bash
export ENGINEL_TOKEN="abc123def456..."
```

### Using Python

```python
import requests

# Login
response = requests.post(
    'http://localhost:8000/api/auth/login/',
    json={
        'username': 'your-username',
        'password': 'your-password'
    }
)

data = response.json()
token = data['access_token']
print(f"Got token: {token}")

# Use token for authenticated requests
headers = {'Authorization': f'Token {token}'}
```

## Step 2: Create a Design Series

Design series are containers for part numbers and their versions.

**curl:**
```bash
curl -X POST http://localhost:8000/api/series/ \
  -H "Authorization: Token $ENGINEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "part_number": "TB-001",
    "name": "Turbine Blade Assembly",
    "description": "High-temperature titanium blade"
  }'
```

**Python:**
```python
response = requests.post(
    'http://localhost:8000/api/series/',
    headers=headers,
    json={
        'part_number': 'TB-001',
        'name': 'Turbine Blade Assembly',
        'description': 'High-temperature titanium blade'
    }
)

series = response.json()
series_id = series['id']
print(f"Created series: {series['part_number']} - {series['name']}")
```
print(f"Created organization: {org_id}")
```

## Step 2: Create a Design Series

Design series represent part numbers (e.g., "TB-001").

**curl:**
```bash
curl -X POST http://localhost:8000/api/series/ \
  -H "Authorization: Token $ENGINEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "part_number": "PART-001",
    "name": "Sample Part",
    "description": "Test component"
  }'
```

**Python:**
```python
response = requests.post(
    'http://localhost:8000/api/series/',
    headers=headers,
    json={
        'part_number': 'PART-001',
        'name': 'Sample Part',
        'description': 'Test component'
    }
)

series = response.json()
series_id = series['id']
print(f"Created series: {series['part_number']}")
```

## Step 3: Upload a CAD File

### Method 1: Direct Upload (Simple)

**curl:**
```bash
curl -X POST http://localhost:8000/api/designs/ \
  -H "Authorization: Token $ENGINEL_TOKEN" \
  -F "file=@/path/to/design.step" \
  -F "series=$SERIES_ID" \
  -F "filename=design_v1.step" \
  -F "classification=UNCLASSIFIED" \
  -F "material=Aluminum 6061"
```

**Python:**
```python
with open('design.step', 'rb') as f:
    files = {'file': f}
    data = {
        'series': series_id,
        'filename': 'design_v1.step',
        'classification': 'UNCLASSIFIED',
        'material': 'Aluminum 6061'
    }
    
    response = requests.post(
        'http://localhost:8000/api/designs/',
        headers=headers,
        files=files,
        data=data
    )

design = response.json()
print(f"Created design: {design['id']}")
```

### Method 2: Pre-Signed Upload (Production)

**Step 1 - Get upload URL:**
```python
response = requests.post(
    'http://localhost:8000/api/designs/upload-url/',
    headers=headers,
    json={
        'filename': 'design_v1.step',
        'file_size': 16777216,
        'content_type': 'application/step'
    }
)

upload_data = response.json()
upload_url = upload_data['upload_url']
upload_id = upload_data['upload_id']
```

**Step 2 - Upload file:**
```python
with open('design.step', 'rb') as f:
    requests.put(upload_url, data=f)
```

**Step 3 - Create design record:**
```python
response = requests.post(
    'http://localhost:8000/api/designs/',
    headers=headers,
    json={
        'series': series_id,
        'filename': 'design_v1.step',
        'upload_id': upload_id,
        'classification': 'UNCLASSIFIED',
        'material': 'Aluminum 6061'
    }
)

design = response.json()
design_id = design['id']
```

**Step 4 - Finalize and process:**
```python
response = requests.post(
    f'http://localhost:8000/api/designs/{design_id}/finalize_upload/',
    headers=headers,
    json={'file_hash': 'sha256:calculated-hash'}
)

print("Processing started:", response.json())
```

## Step 4: Monitor Processing

After upload, files are processed asynchronously:

**Check analysis job status:**
```python
import time

job_id = design['analysis_job']

while True:
    response = requests.get(
        f'http://localhost:8000/api/analysis-jobs/{job_id}/',
        headers=headers
    )
    
    job = response.json()
    status = job['status']
    
    print(f"Job status: {status}")
    
    if status in ['SUCCESS', 'FAILURE']:
        break
    
    time.sleep(2)

if status == 'SUCCESS':
    print("Processing complete!")
    print(f"Result: {job['result']}")
else:
    print(f"Processing failed: {job['error_message']}")
```

**Monitor progress in real-time:**
```python
response = requests.get(
    f'http://localhost:8000/api/analysis-jobs/{job_id}/progress/',
    headers=headers
)

progress = response.json()
print(f"Progress: {progress['percent']}% - {progress['status_message']}")
```

## Step 5: Query Designs

**List all designs:**
```bash
curl http://localhost:8000/api/designs/ \
  -H "Authorization: Token $ENGINEL_TOKEN"
```

**Python:**
```python
response = requests.get(
    'http://localhost:8000/api/designs/',
    headers=headers
)

designs = response.json()
print(f"Total designs: {designs['count']}")

for design in designs['results']:
    print(f"- {design['filename']} ({design['status']})")
```

**Filter by status:**
```python
response = requests.get(
    'http://localhost:8000/api/designs/',
    headers=headers,
    params={'status': 'APPROVED', 'classification': 'UNCLASSIFIED'}
)
```

**Search designs:**
```python
response = requests.get(
    'http://localhost:8000/api/designs/',
    headers=headers,
    params={'search': 'turbine'}
)
```

## Step 7: Download a Design

```python
response = requests.get(
    f'http://localhost:8000/api/designs/{design_id}/download/',
    headers=headers
)

with open('downloaded_design.step', 'wb') as f:
    f.write(response.content)

print("Design downloaded!")
```

## Step 8: Get Design Metadata

```python
response = requests.get(
    f'http://localhost:8000/api/designs/{design_id}/metadata/',
    headers=headers
)

metadata = response.json()

print(f"Volume: {metadata['geometry']['volume_cubic_mm']} mm³")
print(f"Mass: {metadata['material']['mass_kg']} kg")
print(f"Valid: {metadata['validation']['is_valid']}")
```

## Complete Example Script

```python
#!/usr/bin/env python3
"""
Complete Enginel API workflow example.
"""
import requests
import time
from pathlib import Path

BASE_URL = 'http://localhost:8000/api'

def main():
    # 1. Login
    print("1. Logging in...")
    response = requests.post(
        f'{BASE_URL}/auth/login/',
        json={
            'username': 'your-username',
            'password': 'your-password'
        }
    )
    token = response.json()['access_token']
    headers = {'Authorization': f'Token {token}'}
    print("✓ Logged in")
    
    # 2. Create organization
    print("\n2. Creating organization...")
    response = requests.post(
        f'{BASE_URL}/organizations/',
        headers=headers,
        json={
            'name': 'Demo Company',
            'slug': 'demo-company',
            'is_us_organization': True
        }
    )
    org_id = response.json()['id']
    print(f"✓ Created organization: {org_id}")
    
    # 3. Create design series
    print("\n3. Creating design series...")
    response = requests.post(
        f'{BASE_URL}/series/',
        headers=headers,
        json={
            'organization': org_id,
            'part_number': 'DEMO-001',
            'name': 'Demo Part',
            'category': 'MECHANICAL'
        }
    )
    series_id = response.json()['id']
    print(f"✓ Created series: DEMO-001")
    
    # 4. Upload CAD file
    print("\n4. Uploading CAD file...")
    file_path = 'sample_design.step'
    
    with open(file_path, 'rb') as f:
        response = requests.post(
            f'{BASE_URL}/designs/',
            headers=headers,
            files={'file': f},
            data={
                'series': series_id,
                'filename': 'demo_v1.step',
                'classification': 'UNCLASSIFIED',
                'material': 'Aluminum 6061'
            }
        )
    
    design = response.json()
    design_id = design['id']
    job_id = design.get('analysis_job')
    print(f"✓ Uploaded design: {design_id}")
    
    # 5. Monitor processing
    if job_id:
        print("\n5. Monitoring processing...")
        while True:
            response = requests.get(
                f'{BASE_URL}/analysis-jobs/{job_id}/',
                headers=headers
            )
            job = response.json()
            status = job['status']
            
            # Get progress
            progress_response = requests.get(
                f'{BASE_URL}/analysis-jobs/{job_id}/progress/',
                headers=headers
            )
            progress = progress_response.json()
            
            print(f"   Status: {status} - {progress.get('percent', 0)}%")
            
            if status in ['SUCCESS', 'FAILURE']:
                break
            
            time.sleep(2)
        
        if status == 'SUCCESS':
            print("✓ Processing complete!")
        else:
            print(f"✗ Processing failed: {job['error_message']}")
    
    # 6. Get metadata
    print("\n6. Fetching design metadata...")
    response = requests.get(
        f'{BASE_URL}/designs/{design_id}/metadata/',
        headers=headers
    )
    metadata = response.json()
    
    print(f"✓ Metadata:")
    print(f"   Volume: {metadata['geometry']['volume_cubic_mm']:.2f} mm³")
    print(f"   Mass: {metadata['material']['mass_kg']:.3f} kg")
    print(f"   Valid: {metadata['validation']['is_valid']}")
    
    # 7. List all designs
    print("\n7. Listing designs...")
    response = requests.get(
        f'{BASE_URL}/designs/',
        headers=headers
    )
    designs = response.json()
    print(f"✓ Total designs: {designs['count']}")
    
    print("\n✅ Workflow complete!")

if __name__ == '__main__':
    main()
```

## Common Tasks

### Create API Key for CI/CD

```python
response = requests.post(
    'http://localhost:8000/api/auth/api-keys/',
    headers=headers,
    json={
        'name': 'Jenkins CI',
        'expires_in_days': 365,
        'scopes': 'read,write'
    }
)

api_key = response.json()['key']
print(f"API Key: {api_key}")
print("⚠️ Save this key! It won't be shown again.")

# Use API key
api_headers = {'Authorization': f'ApiKey {api_key}'}
```

### Batch Upload Designs

```python
import os

design_files = Path('designs/').glob('*.step')

for file_path in design_files:
    print(f"Uploading {file_path.name}...")
    
    with open(file_path, 'rb') as f:
        response = requests.post(
            f'{BASE_URL}/designs/',
            headers=headers,
            files={'file': f},
            data={
                'series': series_id,
                'filename': file_path.name,
                'classification': 'UNCLASSIFIED'
            }
        )
    
    if response.status_code == 201:
        print(f"✓ Uploaded {file_path.name}")
    else:
        print(f"✗ Failed: {response.json()}")
```

### Start Design Review

```python
response = requests.post(
    f'{BASE_URL}/designs/{design_id}/start_review/',
    headers=headers,
    json={
        'reviewer_ids': [5, 7, 12],
        'due_date': '2025-12-25T00:00:00Z',
        'notes': 'Please review before production'
    }
)

review = response.json()
print(f"Review started: {review['review_session_id']}")
```

### Add Markup to Design

```python
response = requests.post(
    f'{BASE_URL}/markups/',
    headers=headers,
    json={
        'design_asset': design_id,
        'position': {'x': 25.5, 'y': 12.3, 'z': 8.7},
        'annotation_text': 'Check wall thickness here',
        'severity': 'MAJOR'
    }
)

markup = response.json()
print(f"Markup created: {markup['id']}")
```

### Convert Units

```python
response = requests.get(
    f'{BASE_URL}/designs/convert-units/',
    headers=headers,
    params={
        'value': 100,
        'from_unit': 'mm',
        'to_unit': 'in'
    }
)

result = response.json()
print(f"{result['original_value']} {result['from_unit']} = {result['converted_value']} {result['to_unit']}")
```

### Get Audit Trail

```python
response = requests.get(
    f'{BASE_URL}/audit-logs/',
    headers=headers,
    params={
        'resource_type': 'DesignAsset',
        'resource_id': design_id
    }
)

logs = response.json()
for log in logs['results']:
    print(f"{log['timestamp']}: {log['actor_username']} - {log['action_display']}")
```

## Error Handling

```python
def safe_api_call(method, url, **kwargs):
    """Make API call with error handling."""
    try:
        response = method(url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed. Check your token.")
        elif e.response.status_code == 403:
            print("❌ Permission denied.")
        elif e.response.status_code == 404:
            print("❌ Resource not found.")
        else:
            print(f"❌ HTTP Error: {e.response.status_code}")
            print(e.response.json())
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    return None

# Usage
data = safe_api_call(
    requests.get,
    f'{BASE_URL}/designs/{design_id}/',
    headers=headers
)

if data:
    print(f"Design: {data['filename']}")
```

## Pagination Helper

```python
def get_all_pages(url, headers, params=None):
    """Fetch all pages from a paginated endpoint."""
    all_results = []
    next_url = url
    
    while next_url:
        response = requests.get(next_url, headers=headers, params=params)
        data = response.json()
        
        all_results.extend(data['results'])
        next_url = data.get('next')
        params = None  # Only use params on first request
    
    return all_results

# Usage
all_designs = get_all_pages(
    f'{BASE_URL}/designs/',
    headers=headers,
    params={'status': 'APPROVED'}
)

print(f"Found {len(all_designs)} approved designs")
```

## Refresh Token Automatically

```python
class EnginelClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.login()
    
    def login(self):
        """Login and store tokens."""
        response = requests.post(
            f'{self.base_url}/auth/login/',
            json={'username': self.username, 'password': self.password}
        )
        data = response.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
    
    def refresh_access_token(self):
        """Refresh the access token."""
        response = requests.post(
            f'{self.base_url}/auth/refresh/',
            json={'refresh_token': self.refresh_token}
        )
        data = response.json()
        self.access_token = data['access_token']
    
    def request(self, method, endpoint, **kwargs):
        """Make authenticated request with automatic token refresh."""
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Token {self.access_token}'
        kwargs['headers'] = headers
        
        url = f'{self.base_url}/{endpoint.lstrip("/")}'
        response = method(url, **kwargs)
        
        # If token expired, refresh and retry
        if response.status_code == 401:
            self.refresh_access_token()
            headers['Authorization'] = f'Token {self.access_token}'
            response = method(url, **kwargs)
        
        return response

# Usage
client = EnginelClient('http://localhost:8000/api', 'user', 'pass')

response = client.request(requests.get, '/designs/')
designs = response.json()
```

## Next Steps

- Read the [API Reference](./API_REFERENCE.md) for complete endpoint documentation
- Review [Authentication Guide](./AUTHENTICATION.md) for security best practices
- Check [Search & Filtering](./SEARCH_FILTERING.md) for advanced queries
- See [Error Handling](./ERROR_HANDLING.md) for error codes and troubleshooting

## Support

- **Documentation:** Check the `/docs` folder
- **Health Status:** `GET /api/health/detailed/`
- **Error Logs:** `GET /api/monitoring/errors/` (admin only)
- **API Version:** Check response headers for `X-API-Version`

---

**Quick Start Version:** 1.0  
**Last Updated:** December 16, 2025
