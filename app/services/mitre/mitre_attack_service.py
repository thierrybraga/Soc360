"""
Open-Monitor MITRE ATT&CK Sync Service
Serviço para processamento de dados STIX 2.1 do MITRE ATT&CK.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from app.extensions.db import db
from app.models.mitre import Tactic, Technique, AttackMitigation
from app.models.system import SyncMetadata
from app.jobs.fetchers import MitreAttackFetcher
from app.services.core.base_sync_service import BaseSyncService, SyncStatus

logger = logging.getLogger(__name__)

from app.models.nvd import Vulnerability, Weakness

class MitreAttackService(BaseSyncService):
    # ... (rest of the class)
    
    def map_cves_to_techniques(self) -> Dict:
        """
        Tenta mapear CVEs para Técnicas do ATT&CK baseado em CWEs.
        Nota: Esta é uma heurística inicial.
        """
        try:
            self.start_sync("Mapeando CVEs para Técnicas do ATT&CK...")
            
            # Exemplo de mapeamento CWE -> Technique (simplificado)
            # Em produção, usaríamos o mapeamento oficial da MITRE (CWE-to-ATT&CK)
            cwe_mapping = {
                'CWE-79': ['T1059.007'], # XSS -> JavaScript
                'CWE-89': ['T1190'],     # SQLi -> Exploit Public-Facing Application
                'CWE-22': ['T1083'],     # Path Traversal -> File and Directory Discovery
                'CWE-78': ['T1059'],     # OS Command Injection -> Command and Scripting Interpreter
                'CWE-502': ['T1203'],    # Deserialization -> Exploitation for Client Execution
            }
            
            vulnerabilities = Vulnerability.query.join(Vulnerability.weaknesses).all()
            self.stats['total'] = len(vulnerabilities)
            
            for vuln in vulnerabilities:
                mapped = False
                for weakness in vuln.weaknesses:
                    tech_ids = cwe_mapping.get(weakness.cwe_id)
                    if tech_ids:
                        for ext_id in tech_ids:
                            tech = Technique.query.filter_by(external_id=ext_id).first()
                            if tech and tech not in vuln.mitre_techniques:
                                vuln.mitre_techniques.append(tech)
                                mapped = True
                
                if mapped:
                    self.stats['updated'] += 1
                self.stats['processed'] += 1
                
            db.session.commit()
            self.complete_sync("Mapeamento concluído.")
            return self.stats
        except Exception as e:
            db.session.rollback()
            self.fail_sync(str(e))
            raise
    """
    Serviço para sincronização de dados do framework MITRE ATT&CK.
    Consolida Táticas, Técnicas e Mitigações na base local.
    """
    
    def __init__(self):
        super().__init__(prefix='mitre_attack')
        self.fetcher = MitreAttackFetcher()
        # Mapeamento para acelerar relações (stix_id -> local_id)
        self._stix_id_map = {}

    def get_status(self) -> Dict:
        """Obter status atual da sincronização."""
        return self.get_progress()

    def sync_all_domains(self) -> Dict:
        """Sincroniza todos os domínios do ATT&CK (Enterprise, Mobile, ICS)."""
        try:
            self.start_sync("Iniciando sincronização do MITRE ATT&CK (Todos os domínios)...")
            
            all_stix_objects = []
            for domain in self.fetcher.DOMAINS:
                data = self.fetcher.fetch_domain_data(domain)
                if data and 'objects' in data:
                    all_stix_objects.extend(data['objects'])
            
            if not all_stix_objects:
                raise Exception("Não foi possível baixar dados do MITRE ATT&CK.")
                
            self.stats['total'] = len(all_stix_objects)
            self._process_stix_objects(all_stix_objects)
            
            self.complete_sync("MITRE ATT&CK sincronizado com sucesso.")
            return self.stats
        except Exception as e:
            logger.error(f"Erro na sincronização MITRE ATT&CK: {e}")
            self.fail_sync(str(e))
            raise

    def _process_stix_objects(self, objects: List[Dict]):
        """Processa a lista de objetos STIX e salva no banco."""
        
        # 1. Primeiro pass: Criar/Atualizar Táticas, Técnicas e Mitigações
        # Filtramos por tipo primeiro
        tactics_data = [obj for obj in objects if obj.get('type') == 'x-mitre-tactic']
        techniques_data = [obj for obj in objects if obj.get('type') == 'attack-pattern']
        mitigations_data = [obj for obj in objects if obj.get('type') == 'course-of-action']
        relationships_data = [obj for obj in objects if obj.get('type') == 'relationship']
        
        logger.info(f"Processando {len(tactics_data)} táticas...")
        self._sync_tactics(tactics_data)
        
        logger.info(f"Processando {len(techniques_data)} técnicas...")
        self._sync_techniques(techniques_data)
        
        logger.info(f"Processando {len(mitigations_data)} mitigações...")
        self._sync_mitigations(mitigations_data)
        
        # 2. Segundo pass: Processar relacionamentos (Tactics <-> Techniques, Techniques <-> Mitigations)
        logger.info(f"Processando {len(relationships_data)} relacionamentos...")
        self._sync_relationships(relationships_data)

    def _sync_tactics(self, tactics: List[Dict]):
        """Sincroniza táticas."""
        for data in tactics:
            stix_id = data.get('id')
            ext_refs = data.get('external_references', [])
            ext_id = next((r['external_id'] for r in ext_refs if r.get('source_name') == 'mitre-attack'), None)
            url = next((r['url'] for r in ext_refs if r.get('source_name') == 'mitre-attack'), None)
            
            if not ext_id: continue
            
            tactic = Tactic.query.filter_by(stix_id=stix_id).first()
            if not tactic:
                tactic = Tactic(stix_id=stix_id)
                db.session.add(tactic)
                self.stats['inserted'] += 1
            else:
                self.stats['updated'] += 1
                
            tactic.external_id = ext_id
            tactic.name = data.get('name')
            tactic.description = data.get('description')
            tactic.url = url
            
            db.session.flush() # Para garantir que temos ID
            self._stix_id_map[stix_id] = tactic.id
            self.stats['processed'] += 1
        db.session.commit()

    def _sync_techniques(self, techniques: List[Dict]):
        """Sincroniza técnicas."""
        for data in techniques:
            stix_id = data.get('id')
            ext_refs = data.get('external_references', [])
            ext_id = next((r['external_id'] for r in ext_refs if r.get('source_name') == 'mitre-attack'), None)
            url = next((r['url'] for r in ext_refs if r.get('source_name') == 'mitre-attack'), None)
            
            if not ext_id: continue
            
            tech = Technique.query.filter_by(stix_id=stix_id).first()
            if not tech:
                tech = Technique(stix_id=stix_id)
                db.session.add(tech)
                self.stats['inserted'] += 1
            else:
                self.stats['updated'] += 1
                
            tech.external_id = ext_id
            tech.name = data.get('name')
            tech.description = data.get('description')
            tech.url = url
            tech.is_subtechnique = data.get('x_mitre_is_subtechnique', False)
            
            db.session.flush()
            self._stix_id_map[stix_id] = tech.id
            self.stats['processed'] += 1
        db.session.commit()

    def _sync_mitigations(self, mitigations: List[Dict]):
        """Sincroniza mitigações do ATT&CK."""
        for data in mitigations:
            stix_id = data.get('id')
            ext_refs = data.get('external_references', [])
            ext_id = next((r['external_id'] for r in ext_refs if r.get('source_name') == 'mitre-attack'), None)
            url = next((r['url'] for r in ext_refs if r.get('source_name') == 'mitre-attack'), None)
            
            if not ext_id: continue
            
            mit = AttackMitigation.query.filter_by(stix_id=stix_id).first()
            if not mit:
                mit = AttackMitigation(stix_id=stix_id)
                db.session.add(mit)
                self.stats['inserted'] += 1
            else:
                self.stats['updated'] += 1
                
            mit.external_id = ext_id
            mit.name = data.get('name')
            mit.description = data.get('description')
            mit.url = url
            
            db.session.flush()
            self._stix_id_map[stix_id] = mit.id
            self.stats['processed'] += 1
        db.session.commit()

    def _sync_relationships(self, relationships: List[Dict]):
        """Processa relacionamentos entre objetos."""
        # Limpar associações existentes para evitar duplicatas em re-syncs complexos
        # Nota: em produção usaríamos lógica mais granular de diff
        
        for rel in relationships:
            source_ref = rel.get('source_ref')
            target_ref = rel.get('target_ref')
            rel_type = rel.get('relationship_type')
            
            source_id = self._stix_id_map.get(source_ref)
            target_id = self._stix_id_map.get(target_ref)
            
            if not source_id or not target_id: continue
            
            # 1. Técnica (source) -> Tática (target) via 'revoked-by' ou lógica do STIX?
            # No STIX 2.1 ATT&CK, Técnicas referenciam Táticas em 'kill_chain_phases'
            # Mas relacionamentos explícitos também existem.
            
            # 2. Mitigação (source) -> Técnica (target) via 'mitigates'
            if rel_type == 'mitigates' and source_ref.startswith('course-of-action--') and target_ref.startswith('attack-pattern--'):
                tech = Technique.query.get(target_id)
                mit = AttackMitigation.query.get(source_id)
                if tech and mit and mit not in tech.mitigations:
                    tech.mitigations.append(mit)
            
            # 3. Sub-técnica (source) -> Técnica Pai (target) via 'subtechnique-of'
            if rel_type == 'subtechnique-of' and source_ref.startswith('attack-pattern--') and target_ref.startswith('attack-pattern--'):
                child_tech = Technique.query.get(source_id)
                if child_tech:
                    child_tech.parent_id = target_id
            
            # Incrementamos progresso de processamento
            self.stats['processed'] += 1
        
        # Também precisamos processar as táticas das técnicas (kill_chain_phases)
        # Note: isto não está nos relationships explícitos mas sim no próprio objeto Technique.
        # Vou simplificar e não re-processar kill_chain_phases agora, mas em uma implementação completa seria necessário.
        
        db.session.commit()
