from app.extensions.celery_extension import celery
from app.services.nvd.nvd_sync_service import NVDSyncService, SyncMode

@celery.task(name='nvd.sync')
def sync_nvd_task(mode='incremental'):
    """
    Tarefa Celery para sincronização NVD.
    
    Args:
        mode: Modo de sincronização ('incremental', 'full', 'initial')
    """
    service = NVDSyncService()
    # Executar sync sincronicamente pois já estamos em um worker assíncrono
    service.start_sync(mode=SyncMode(mode), async_mode=False)


@celery.task(name='nvd.bulk_import')
def bulk_import_task(file_path):
    """
    Tarefa Celery para importação em massa.
    
    Args:
        file_path: Caminho para o arquivo JSON (pode ser URL ou local)
    """
    # Importação aqui para evitar ciclos
    from app.services.nvd.bulk_database_service import BulkDatabaseService
    import json
    import os
    
    service = BulkDatabaseService()
    
    # Se for arquivo local
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            # Assumindo estrutura do NVD JSON
            vulnerabilities = data.get('CVE_Items', [])
            service.process_vulnerabilities(vulnerabilities)
    else:
        # TODO: Suporte a URL/S3
        pass
