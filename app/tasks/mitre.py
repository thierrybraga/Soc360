from app.extensions.celery_extension import celery, CELERY_AVAILABLE
from app.services.mitre.mitre_service import MitreService
from app.services.mitre.mitre_attack_service import MitreAttackService


def _task(name):
    """Decorator that uses celery.task if available, otherwise a no-op."""
    def decorator(fn):
        if CELERY_AVAILABLE and celery is not None:
            return celery.task(name=name)(fn)
        return fn
    return decorator


# MITRE CVE Services Tasks

@_task(name='mitre.sync_cve')
def sync_mitre_cve_task(cve_id: str, force: bool = False):
    """
    Tarefa Celery para sincronização de um CVE específico da MITRE.
    
    Args:
        cve_id: ID do CVE (ex: CVE-2021-44228)
        force: Forçar atualização mesmo se já existir
    """
    service = MitreService()
    return service.sync_cve(cve_id, force)


@_task(name='mitre.enrich_vulnerabilities')
def enrich_mitre_vulnerabilities_task(limit: int = 0, force: bool = False):
    """
    Tarefa Celery para enriquecimento de vulnerabilidades com dados MITRE.
    
    Args:
        limit: Número máximo de vulnerabilidades para processar (0 = todas)
        force: Forçar reprocessamento
    """
    service = MitreService()
    return service.start_enrichment_task(limit, force)


# MITRE ATT&CK Tasks

@_task(name='mitre_attack.sync')
def sync_mitre_attack_task(domain: str = "enterprise-attack"):
    """
    Tarefa Celery para sincronização de dados MITRE ATT&CK.
    
    Args:
        domain: Domínio ATT&CK ('enterprise-attack', 'mobile-attack', 'ics-attack')
    """
    service = MitreAttackService()
    return service.sync_attack_data(domain)


@_task(name='mitre_attack.map_cves')
def map_cves_to_techniques_task():
    """
    Tarefa Celery para mapear CVEs para técnicas ATT&CK baseado em CWEs.
    """
    service = MitreAttackService()
    return service.map_cves_to_techniques()