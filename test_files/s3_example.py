"""
Example usage of S3 integration for Enginel design asset uploads/downloads.

This script demonstrates:
- Uploading a design asset to S3 via pre-signed URLs
- Downloading a design asset from S3
- Error handling
"""

import requests
import os
import json
from pathlib import Path


class EnginelS3Client:
    """
    Client for interacting with Enginel API with S3 integration.
    """
    
    def __init__(self, base_url, auth_token):
        """
        Initialize the Enginel S3 client.
        
        Args:
            base_url: Base URL of Enginel API (e.g., 'http://localhost:8000')
            auth_token: Authentication token for API access
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Token {auth_token}',
            'Content-Type': 'application/json'
        }
    
    def upload_design_asset(
        self,
        filepath,
        part_number,
        revision,
        classification='UNCLASSIFIED',
        description=None
    ):
        """
        Upload a design asset to Enginel via S3.
        
        Args:
            filepath: Path to the file to upload
            part_number: Part number for the design
            revision: Revision identifier (e.g., 'v1', 'A')
            classification: Security classification
            description: Optional description
        
        Returns:
            Dictionary with design asset details
        
        Raises:
            Exception: If upload fails
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        filename = filepath.name
        
        print(f"📤 Uploading: {filename}")
        
        # Step 1: Request pre-signed upload URL
        print("  1/3 Requesting upload URL...")
        
        payload = {
            'filename': filename,
            'part_number': part_number,
            'revision': revision,
            'classification': classification,
            'content_type': 'application/octet-stream'
        }
        
        if description:
            payload['description'] = description
        
        response = requests.post(
            f'{self.base_url}/api/designs/upload-url/',
            json=payload,
            headers=self.headers
        )
        
        if not response.ok:
            raise Exception(f"Failed to get upload URL: {response.text}")
        
        upload_data = response.json()
        design_asset_id = upload_data['design_asset_id']
        
        print(f"  ✓ Upload URL obtained (Asset ID: {design_asset_id})")
        
        # Step 2: Upload file to S3 using pre-signed POST
        print("  2/3 Uploading file to S3...")
        
        with open(filepath, 'rb') as f:
            # Prepare multipart form data
            files = {'file': (filename, f)}
            data = upload_data['fields']
            
            upload_response = requests.post(
                upload_data['upload_url'],
                data=data,
                files=files
            )
            
            if not upload_response.ok:
                raise Exception(f"S3 upload failed: {upload_response.text}")
        
        print(f"  ✓ File uploaded to S3")
        
        # Step 3: Finalize upload and trigger processing
        print("  3/3 Finalizing upload...")
        
        finalize_response = requests.post(
            f'{self.base_url}/api/designs/{design_asset_id}/finalize/',
            headers=self.headers
        )
        
        if not finalize_response.ok:
            raise Exception(f"Failed to finalize upload: {finalize_response.text}")
        
        result = finalize_response.json()
        
        print(f"  ✓ Upload finalized (Task ID: {result.get('task_id', 'N/A')})")
        print(f"✅ Upload complete! Asset ID: {design_asset_id}")
        
        return result
    
    def download_design_asset(self, asset_id, output_path=None):
        """
        Download a design asset from Enginel via S3.
        
        Args:
            asset_id: UUID of the design asset
            output_path: Optional output file path (default: use original filename)
        
        Returns:
            Path to downloaded file
        
        Raises:
            Exception: If download fails
        """
        print(f"📥 Downloading asset: {asset_id}")
        
        # Step 1: Request pre-signed download URL
        print("  1/2 Requesting download URL...")
        
        response = requests.get(
            f'{self.base_url}/api/designs/{asset_id}/download/',
            headers=self.headers
        )
        
        if not response.ok:
            raise Exception(f"Failed to get download URL: {response.text}")
        
        download_data = response.json()
        filename = download_data['filename']
        
        print(f"  ✓ Download URL obtained (expires in {download_data['expires_in_seconds']}s)")
        
        # Step 2: Download file from S3
        print("  2/2 Downloading file from S3...")
        
        file_response = requests.get(download_data['download_url'])
        
        if not file_response.ok:
            raise Exception(f"S3 download failed: {file_response.status_code}")
        
        # Determine output path
        if output_path is None:
            output_path = Path(filename)
        else:
            output_path = Path(output_path)
        
        # Save file
        with open(output_path, 'wb') as f:
            f.write(file_response.content)
        
        file_size_mb = len(file_response.content) / (1024 * 1024)
        
        print(f"  ✓ File downloaded ({file_size_mb:.2f} MB)")
        print(f"✅ Download complete! Saved to: {output_path}")
        
        return str(output_path)
    
    def get_design_asset_status(self, asset_id):
        """
        Check the processing status of a design asset.
        
        Args:
            asset_id: UUID of the design asset
        
        Returns:
            Dictionary with asset details
        """
        response = requests.get(
            f'{self.base_url}/api/designs/{asset_id}/',
            headers=self.headers
        )
        
        if not response.ok:
            raise Exception(f"Failed to get asset status: {response.text}")
        
        return response.json()


def example_upload():
    """Example: Upload a design asset."""
    # Configuration
    BASE_URL = 'http://localhost:8000'
    AUTH_TOKEN = 'your-auth-token-here'  # Replace with actual token
    
    # Initialize client
    client = EnginelS3Client(BASE_URL, AUTH_TOKEN)
    
    # Upload a file
    try:
        result = client.upload_design_asset(
            filepath='bracket_v3.step',
            part_number='BRK-001',
            revision='v3',
            classification='UNCLASSIFIED',
            description='Mounting bracket for assembly XYZ'
        )
        
        print(f"\n📊 Asset Details:")
        print(f"  ID: {result['id']}")
        print(f"  Status: {result['status']}")
        print(f"  Filename: {result['filename']}")
        
        # Wait for processing
        import time
        print("\n⏳ Waiting for processing to complete...")
        
        for i in range(30):  # Poll for 30 seconds
            time.sleep(1)
            status_data = client.get_design_asset_status(result['id'])
            
            if status_data['status'] == 'COMPLETED':
                print("✅ Processing complete!")
                print(f"\n📊 Metadata:")
                print(json.dumps(status_data.get('metadata', {}), indent=2))
                break
            elif status_data['status'] == 'FAILED':
                print("❌ Processing failed!")
                break
            
            print(f"  Status: {status_data['status']} ({i+1}s)")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")


def example_download():
    """Example: Download a design asset."""
    # Configuration
    BASE_URL = 'http://localhost:8000'
    AUTH_TOKEN = 'your-auth-token-here'  # Replace with actual token
    ASSET_ID = '550e8400-e29b-41d4-a716-446655440000'  # Replace with actual ID
    
    # Initialize client
    client = EnginelS3Client(BASE_URL, AUTH_TOKEN)
    
    # Download a file
    try:
        output_path = client.download_design_asset(
            asset_id=ASSET_ID,
            output_path='downloaded_bracket.step'
        )
        
        print(f"\n✅ File saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")


def example_upload_multiple():
    """Example: Upload multiple design assets."""
    BASE_URL = 'http://localhost:8000'
    AUTH_TOKEN = 'your-auth-token-here'
    
    client = EnginelS3Client(BASE_URL, AUTH_TOKEN)
    
    # Files to upload
    files = [
        {
            'filepath': 'bracket_v1.step',
            'part_number': 'BRK-001',
            'revision': 'v1',
        },
        {
            'filepath': 'bracket_v2.step',
            'part_number': 'BRK-001',
            'revision': 'v2',
        },
        {
            'filepath': 'bracket_v3.step',
            'part_number': 'BRK-001',
            'revision': 'v3',
        },
    ]
    
    results = []
    
    for file_info in files:
        try:
            print(f"\n{'='*60}")
            result = client.upload_design_asset(**file_info)
            results.append({
                'success': True,
                'asset_id': result['id'],
                'filename': file_info['filepath']
            })
        except Exception as e:
            print(f"❌ Failed: {e}")
            results.append({
                'success': False,
                'error': str(e),
                'filename': file_info['filepath']
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Upload Summary:")
    successful = sum(1 for r in results if r['success'])
    print(f"  ✅ Successful: {successful}/{len(results)}")
    print(f"  ❌ Failed: {len(results) - successful}/{len(results)}")
    
    for result in results:
        if result['success']:
            print(f"  ✓ {result['filename']} → {result['asset_id']}")
        else:
            print(f"  ✗ {result['filename']} → {result['error']}")


if __name__ == '__main__':
    print("Enginel S3 Integration Example")
    print("=" * 60)
    
    # Uncomment the example you want to run:
    
    # Example 1: Upload a single file
    # example_upload()
    
    # Example 2: Download a file
    # example_download()
    
    # Example 3: Upload multiple files
    # example_upload_multiple()
    
    print("\nℹ️  Update AUTH_TOKEN and file paths before running examples.")
