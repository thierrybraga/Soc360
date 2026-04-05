from app.extensions.celery_extension import celery, CELERY_AVAILABLE
from app.services.nvd.nvd_sync_service import NVDSyncService, SyncMode


def _task(name):
    """Decorator that uses celery.task if available, otherwise a no-op."""
    def decorator(fn):
        if CELERY_AVAILABLE and celery is not None:
            return celery.task(name=name)(fn)
        return fn
    return decorator


@_task(name='nvd.sync')
def sync_nvd_task(mode='incremental'):
    """
    Tarefa Celery para sincronização NVD.
    
    Args:
        mode: Modo de sincronização ('incremental', 'full', 'initial')
    """
    service = NVDSyncService()
    # Executar sync sincronicamente pois já estamos em um worker assíncrono
    service.start_sync(mode=SyncMode(mode), async_mode=False)


@_task(name='nvd.bulk_import')
def bulk_import_task(file_path):
    """
    Tarefa Celery para importação em massa.
    
    Args:
        file_path: Caminho para o arquivo JSON (pode ser caminho local, URL HTTP/HTTPS, ou S3 URI)
    """
    # Importação aqui para evitar ciclos
    from app.services.nvd.bulk_database_service import BulkDatabaseService
    import json
    import os
    import requests
    from urllib.parse import urlparse
    
    service = BulkDatabaseService()
    
    try:
        if os.path.exists(file_path):
            # Arquivo local
            with open(file_path, 'r') as f:
                data = json.load(f)
        elif file_path.startswith(('http://', 'https://')):
            # URL HTTP/HTTPS
            response = requests.get(file_path, timeout=300)
            response.raise_for_status()
            data = response.json()
        elif file_path.startswith('s3://'):
            # S3 URI
            try:
                import boto3
                from botocore.exceptions import NoCredentialsError, ClientError
            except ImportError:
                raise ImportError("boto3 is required for S3 support. Install with: pip install boto3")
            
            # Parse S3 URI: s3://bucket/key
            parsed = urlparse(file_path)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            s3_client = boto3.client('s3')
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                data = json.loads(response['Body'].read().decode('utf-8'))
            except NoCredentialsError:
                raise Exception("AWS credentials not found for S3 access")
            except ClientError as e:
                raise Exception(f"S3 error: {e}")
        else:
            raise ValueError(f"Unsupported file path format: {file_path}")
        
        # Assumindo estrutura do NVD JSON
        vulnerabilities = data.get('CVE_Items', [])
        if not vulnerabilities:
            # Tentar outras estruturas possíveis
            vulnerabilities = data.get('vulnerabilities', data)
        
        service.process_vulnerabilities(vulnerabilities)
        
    except Exception as e:
        # Log error and re-raise
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bulk import failed for {file_path}: {e}")
        raise
