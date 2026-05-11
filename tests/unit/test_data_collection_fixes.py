"""
Testes unitários para as correções de coleta e gravação de dados:
- NVD: description_lang no upsert
- EUVD: _parse_date, is_eu_csirt_coordinated, vuln_status, vendor→produto, sync_latest endpoints, sync_by_date status
- MITRE: _save_weaknesses indentation, container adp, loop infinito no enriquecimento
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call


# ─────────────────────────────────────────────────────────────────────────────
# NVD
# ─────────────────────────────────────────────────────────────────────────────

class TestNVDBulkDatabaseService:

    def _make_cve_item(self, overrides=None):
        """CVE mínimo válido da NVD API."""
        item = {
            'id': 'CVE-2024-9999',
            'descriptions': [{'lang': 'en', 'value': 'Test vuln'}],
            'published': '2024-01-01T00:00:00.000',
            'lastModified': '2024-01-02T00:00:00.000',
            'vulnStatus': 'Analyzed',
            'metrics': {},
            'weaknesses': [],
            'references': [],
            'credits': [],
            'configurations': [],
        }
        if overrides:
            item.update(overrides)
        return item

    def test_description_lang_extracted(self):
        """description_lang deve ser 'en' no registro extraído."""
        from app.services.nvd.bulk_database_service import BulkDatabaseService
        svc = BulkDatabaseService()
        data = svc._extract_vulnerability_data(self._make_cve_item())
        assert data['description_lang'] == 'en'

    def test_description_lang_in_upsert_dict(self):
        """description_lang deve constar no update_dict do upsert."""
        # Verificação estática: garante que o campo está no código de upsert
        import inspect
        from app.services.nvd.bulk_database_service import BulkDatabaseService
        source = inspect.getsource(BulkDatabaseService._upsert_vulnerabilities)
        assert 'description_lang' in source


# ─────────────────────────────────────────────────────────────────────────────
# EUVD — _parse_date
# ─────────────────────────────────────────────────────────────────────────────

class TestEUVDParseDate:

    @pytest.fixture
    def service(self):
        from app.services.euvd.euvd_service import EUVDService
        svc = EUVDService.__new__(EUVDService)
        return svc

    def test_iso_format(self, service):
        from datetime import timezone
        result = service._parse_date('2024-04-01T10:30:00.000Z')
        assert result == datetime(2024, 4, 1, 10, 30, 0, tzinfo=timezone.utc)

    def test_iso_without_z(self, service):
        result = service._parse_date('2024-04-01T10:30:00')
        assert result == datetime(2024, 4, 1, 10, 30, 0)

    def test_legacy_format_fallback(self, service):
        """Formato legado ainda deve funcionar como fallback."""
        result = service._parse_date('Apr 15, 2025, 8:30:58 PM')
        assert result == datetime(2025, 4, 15, 20, 30, 58)

    def test_none_input(self, service):
        assert service._parse_date(None) is None

    def test_empty_string(self, service):
        assert service._parse_date('') is None

    def test_invalid_string(self, service):
        assert service._parse_date('not-a-date') is None


# ─────────────────────────────────────────────────────────────────────────────
# EUVD — is_eu_csirt_coordinated
# ─────────────────────────────────────────────────────────────────────────────

class TestEUVDIsEuCsirtCoordinated:

    def _make_service(self):
        from app.services.euvd.euvd_service import EUVDService
        svc = EUVDService.__new__(EUVDService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}
        return svc

    def test_updates_to_false(self):
        """Campo deve ser atualizado para False quando não é coordenado."""
        svc = self._make_service()

        existing = MagicMock()
        existing.description = 'desc'
        existing.cvss_score = 9.0
        existing.euvd_id = None
        existing.enisa_alternative_id = None
        existing.enisa_exploitation_status = None
        existing.enisa_source = None
        existing.enisa_last_changed = None
        existing.is_eu_csirt_coordinated = True  # era True

        data = {
            'cve_id': 'CVE-2024-1234',
            'euvd_id': 'EUVD-2024-1234',
            'enisa_alternative_id': None,
            'enisa_exploitation_status': None,
            'enisa_source': 'Other Source',
            'enisa_last_changed': None,
            'is_eu_csirt_coordinated': False,  # agora False
            'description': None,
            'cvss_score': None,
        }

        with patch.object(svc, '_save_cvss_metric'):
            with patch('app.services.euvd.euvd_service.Vulnerability') as MockVuln:
                MockVuln.query.filter_by.return_value.first.return_value = existing
                svc._process_single_item({'id': 'EUVD-2024-1234', 'aliases': 'CVE-2024-1234'})

        assert existing.is_eu_csirt_coordinated == False

    def test_updates_to_true(self):
        """Campo deve ser atualizado para True quando passa a ser coordenado."""
        svc = self._make_service()

        existing = MagicMock()
        existing.description = 'desc'
        existing.cvss_score = 9.0
        existing.euvd_id = None
        existing.enisa_alternative_id = None
        existing.enisa_exploitation_status = None
        existing.enisa_source = None
        existing.enisa_last_changed = None
        existing.is_eu_csirt_coordinated = False  # era False

        with patch.object(svc, '_save_cvss_metric'):
            with patch.object(svc, '_map_to_model') as mock_map:
                mock_map.return_value = {
                    'cve_id': 'CVE-2024-1234',
                    'euvd_id': 'EUVD-2024-1234',
                    'enisa_alternative_id': None,
                    'enisa_exploitation_status': None,
                    'enisa_source': 'EU CSIRT',
                    'enisa_last_changed': None,
                    'is_eu_csirt_coordinated': True,
                    'description': None,
                    'cvss_score': None,
                }
                with patch('app.services.euvd.euvd_service.Vulnerability') as MockVuln:
                    MockVuln.query.filter_by.return_value.first.return_value = existing
                    with patch.object(svc, '_extract_cve_id', return_value='CVE-2024-1234'):
                        svc._process_single_item({'id': 'EUVD-2024-1234'})

        assert existing.is_eu_csirt_coordinated == True


# ─────────────────────────────────────────────────────────────────────────────
# EUVD — vuln_status não hardcoded
# ─────────────────────────────────────────────────────────────────────────────

class TestEUVDVulnStatus:

    def test_vuln_status_not_in_map_to_model(self):
        """_map_to_model não deve mais retornar vuln_status hardcoded como 'Analyzed'."""
        from app.services.euvd.euvd_service import EUVDService
        svc = EUVDService.__new__(EUVDService)
        item = {
            'id': 'EUVD-2024-1',
            'description': 'test',
            'datePublished': '2024-01-01T00:00:00Z',
            'dateUpdated': '2024-01-02T00:00:00Z',
            'baseScore': None,
            'enisaIdVendor': [],
            'enisaIdProduct': [],
        }
        result = svc._map_to_model(item, 'EUVD-2024-1')
        assert result.get('vuln_status') != 'Analyzed'


# ─────────────────────────────────────────────────────────────────────────────
# EUVD — vendor→produto
# ─────────────────────────────────────────────────────────────────────────────

class TestEUVDVendorProductMapping:

    def _make_service(self):
        from app.services.euvd.euvd_service import EUVDService
        return EUVDService.__new__(EUVDService)

    def test_product_assigned_to_all_vendors_when_no_vendor_in_product(self):
        """Se produto não tem vendor próprio, atribui a todos os vendors."""
        svc = self._make_service()
        item = {
            'id': 'EUVD-2024-1',
            'description': '',
            'datePublished': None,
            'dateUpdated': None,
            'baseScore': None,
            'enisaIdVendor': [
                {'vendor': {'name': 'VendorA'}},
                {'vendor': {'name': 'VendorB'}},
            ],
            'enisaIdProduct': [
                {'product': {'name': 'ProductX'}},
            ],
        }
        result = svc._map_to_model(item, 'EUVD-2024-1')
        products = result['nvd_products_data']
        # ProductX deve estar em ambos os vendors
        assert 'ProductX' in products.get('VendorA', [])
        assert 'ProductX' in products.get('VendorB', [])

    def test_product_assigned_to_specific_vendor(self):
        """Se produto tem vendor próprio, usa apenas esse vendor."""
        svc = self._make_service()
        item = {
            'id': 'EUVD-2024-1',
            'description': '',
            'datePublished': None,
            'dateUpdated': None,
            'baseScore': None,
            'enisaIdVendor': [
                {'vendor': {'name': 'VendorA'}},
                {'vendor': {'name': 'VendorB'}},
            ],
            'enisaIdProduct': [
                {'vendor': {'name': 'VendorA'}, 'product': {'name': 'ProductX'}},
            ],
        }
        result = svc._map_to_model(item, 'EUVD-2024-1')
        products = result['nvd_products_data']
        assert 'ProductX' in products.get('VendorA', [])
        assert 'ProductX' not in products.get('VendorB', [])


# ─────────────────────────────────────────────────────────────────────────────
# EUVD — sync_latest chama todos os endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestEUVDSyncLatestEndpoints:

    def test_all_four_endpoints_called(self):
        """sync_latest deve chamar fetch_latest, fetch_exploited, fetch_eu_csirt, fetch_critical."""
        from app.services.euvd.euvd_service import EUVDService

        svc = EUVDService.__new__(EUVDService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.return_value = [{'id': 'EUVD-1', 'aliases': ''}]
        mock_fetcher.fetch_exploited.return_value = [{'id': 'EUVD-2', 'aliases': ''}]
        mock_fetcher.fetch_eu_csirt.return_value = [{'id': 'EUVD-3', 'aliases': ''}]
        mock_fetcher.fetch_critical.return_value = [{'id': 'EUVD-4', 'aliases': ''}]
        svc.fetcher = mock_fetcher

        with patch.object(svc, 'start_sync'), \
             patch.object(svc, '_update_progress'), \
             patch.object(svc, '_process_items') as mock_process, \
             patch.object(svc, 'complete_sync'):
            svc.sync_latest()

        mock_fetcher.fetch_latest.assert_called_once()
        mock_fetcher.fetch_exploited.assert_called_once()
        mock_fetcher.fetch_eu_csirt.assert_called_once()
        mock_fetcher.fetch_critical.assert_called_once()

        # Deve processar 4 itens únicos
        processed_items = mock_process.call_args[0][0]
        assert len(processed_items) == 4

    def test_duplicates_deduplicated(self):
        """Itens com mesmo ID de múltiplos endpoints não devem ser duplicados."""
        from app.services.euvd.euvd_service import EUVDService

        svc = EUVDService.__new__(EUVDService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}

        dup_item = {'id': 'EUVD-1', 'aliases': ''}
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.return_value = [dup_item]
        mock_fetcher.fetch_exploited.return_value = [dup_item]  # mesmo ID
        mock_fetcher.fetch_eu_csirt.return_value = []
        mock_fetcher.fetch_critical.return_value = []
        svc.fetcher = mock_fetcher

        with patch.object(svc, 'start_sync'), \
             patch.object(svc, '_update_progress'), \
             patch.object(svc, '_process_items') as mock_process, \
             patch.object(svc, 'complete_sync'):
            svc.sync_latest()

        processed_items = mock_process.call_args[0][0]
        assert len(processed_items) == 1

    def test_endpoint_failure_does_not_abort_sync(self):
        """Falha em um endpoint não deve abortar os demais."""
        from app.services.euvd.euvd_service import EUVDService

        svc = EUVDService.__new__(EUVDService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest.side_effect = Exception('Network error')
        mock_fetcher.fetch_exploited.return_value = [{'id': 'EUVD-2', 'aliases': ''}]
        mock_fetcher.fetch_eu_csirt.return_value = []
        mock_fetcher.fetch_critical.return_value = []
        svc.fetcher = mock_fetcher

        with patch.object(svc, 'start_sync'), \
             patch.object(svc, '_update_progress'), \
             patch.object(svc, '_process_items') as mock_process, \
             patch.object(svc, 'complete_sync'):
            svc.sync_latest()

        # Deve ter processado o item do fetch_exploited apesar da falha no fetch_latest
        processed_items = mock_process.call_args[0][0]
        assert len(processed_items) == 1


# ─────────────────────────────────────────────────────────────────────────────
# EUVD — sync_by_date gerencia status
# ─────────────────────────────────────────────────────────────────────────────

class TestEUVDSyncByDateStatus:

    def test_calls_start_and_complete_sync(self):
        """sync_by_date deve chamar start_sync e complete_sync."""
        from app.services.euvd.euvd_service import EUVDService

        svc = EUVDService.__new__(EUVDService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_search.return_value = {'items': [], 'total': 0}
        svc.fetcher = mock_fetcher

        with patch.object(svc, 'start_sync') as mock_start, \
             patch.object(svc, '_update_progress'), \
             patch.object(svc, '_process_items'), \
             patch.object(svc, 'complete_sync') as mock_complete:
            svc.sync_by_date('2024-01-01', '2024-01-31')

        mock_start.assert_called_once()
        mock_complete.assert_called_once()

    def test_calls_fail_sync_on_error(self):
        """sync_by_date deve chamar fail_sync em caso de exceção."""
        from app.services.euvd.euvd_service import EUVDService

        svc = EUVDService.__new__(EUVDService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_search.side_effect = Exception('API down')
        svc.fetcher = mock_fetcher

        with patch.object(svc, 'start_sync'), \
             patch.object(svc, 'fail_sync') as mock_fail:
            with pytest.raises(Exception):
                svc.sync_by_date('2024-01-01', '2024-01-31')

        mock_fail.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# MITRE — _save_weaknesses indentação
# ─────────────────────────────────────────────────────────────────────────────

class TestMitreSaveWeaknessesIndentation:

    def test_weakness_data_built_correctly(self):
        """_save_weaknesses deve construir weakness_data com todos os campos."""
        from app.services.mitre.mitre_service import MitreService
        svc = MitreService.__new__(MitreService)
        svc.stats = {}

        cna = {
            'problemTypes': [{
                'descriptions': [
                    {'cweId': 'CWE-79', 'description': 'Cross-site Scripting'},
                    {'cweId': 'NVD-CWE-Other', 'description': 'Other'},  # deve ser ignorado
                ]
            }]
        }

        executed_values = []

        class FakeStmt:
            def on_conflict_do_nothing(self, **kwargs):
                return self

        def fake_execute(stmt):
            pass

        with patch('app.services.mitre.mitre_service.insert') as mock_insert, \
             patch('app.services.mitre.mitre_service.db') as mock_db:
            captured = {}

            def capture_insert(model):
                class Stmt:
                    def values(self, data):
                        captured.update(data)
                        return FakeStmt()
                return Stmt()

            mock_insert.side_effect = capture_insert
            mock_db.session.execute = fake_execute

            svc._save_weaknesses('CVE-2024-1', cna)

        # Deve ter capturado weakness_data para CWE-79
        assert captured.get('cve_id') == 'CVE-2024-1'
        assert captured.get('cwe_id') == 'CWE-79'
        assert captured.get('source') == 'mitre'


# ─────────────────────────────────────────────────────────────────────────────
# MITRE — container adp processado
# ─────────────────────────────────────────────────────────────────────────────

class TestMitreADPProcessing:

    def _make_mitre_json(self, with_adp=True):
        data = {
            'cveMetadata': {'cveId': 'CVE-2024-1234'},
            'containers': {
                'cna': {
                    'descriptions': [{'lang': 'en', 'value': 'Test vuln'}],
                    'metrics': [],
                    'problemTypes': [],
                    'references': [],
                    'solutions': [],
                    'workarounds': [],
                    'credits': [],
                    'affected': [],
                },
            }
        }
        if with_adp:
            data['containers']['adp'] = [{
                'metrics': [{
                    'cvssV3_1': {
                        'baseScore': 9.8,
                        'baseSeverity': 'CRITICAL',
                        'vectorString': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
                    }
                }],
                'problemTypes': [],
                'references': [{'url': 'https://adp.example.com/advisory'}],
            }]
        return data

    def test_adp_cvss_metrics_saved(self):
        """Métricas CVSS do container adp devem ser salvas."""
        from app.services.mitre.mitre_service import MitreService
        svc = MitreService.__new__(MitreService)
        svc.stats = {'updated': 0}

        mock_vuln = MagicMock()
        mock_vuln.description = 'existing'
        mock_vuln.vuln_status = 'Analyzed'

        adp_metrics_calls = []

        original_save_cvss = MitreService._save_cvss_metrics

        def tracking_save_cvss(self_inner, cve_id, container):
            adp_metrics_calls.append(container)

        with patch('app.services.mitre.mitre_service.Vulnerability') as MockVuln, \
             patch.object(MitreService, '_save_cvss_metrics', tracking_save_cvss), \
             patch.object(svc, '_save_weaknesses'), \
             patch.object(svc, '_save_references'), \
             patch.object(svc, '_save_mitigations'), \
             patch.object(svc, '_save_credits'), \
             patch.object(svc, '_save_affected_products'), \
             patch('app.services.mitre.mitre_service.AlertService'):
            MockVuln.query.filter_by.return_value.first.return_value = mock_vuln
            svc._process_mitre_data(self._make_mitre_json(with_adp=True))

        # Deve ter chamado _save_cvss_metrics para CNA + 1 ADP = 2 vezes
        assert len(adp_metrics_calls) == 2

    def test_no_adp_processes_only_cna(self):
        """Sem container adp, só o cna é processado."""
        from app.services.mitre.mitre_service import MitreService
        svc = MitreService.__new__(MitreService)
        svc.stats = {'updated': 0}

        mock_vuln = MagicMock()
        mock_vuln.description = 'existing'
        mock_vuln.vuln_status = 'Analyzed'

        cvss_calls = []

        def tracking_save_cvss(self_inner, cve_id, container):
            cvss_calls.append(container)

        with patch('app.services.mitre.mitre_service.Vulnerability') as MockVuln, \
             patch.object(MitreService, '_save_cvss_metrics', tracking_save_cvss), \
             patch.object(svc, '_save_weaknesses'), \
             patch.object(svc, '_save_references'), \
             patch.object(svc, '_save_mitigations'), \
             patch.object(svc, '_save_credits'), \
             patch.object(svc, '_save_affected_products'), \
             patch('app.services.mitre.mitre_service.AlertService'):
            MockVuln.query.filter_by.return_value.first.return_value = mock_vuln
            svc._process_mitre_data(self._make_mitre_json(with_adp=False))

        assert len(cvss_calls) == 1


# ─────────────────────────────────────────────────────────────────────────────
# MITRE — loop infinito no enriquecimento
# ─────────────────────────────────────────────────────────────────────────────

class TestMitreEnrichmentNoLoop:

    def test_failed_cve_not_retried(self):
        """CVE que falha na MITRE não deve ser tentada novamente (evita loop infinito)."""
        from app.services.mitre.mitre_service import MitreService
        from app.models.nvd import Vulnerability as VulnModel

        svc = MitreService.__new__(MitreService)
        svc.stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'errors': 0, 'total': 0}
        svc.fetcher = MagicMock()

        # Simula 1 vulnerabilidade que sempre falha
        vuln_mock = MagicMock()
        vuln_mock.cve_id = 'CVE-2024-FAIL'
        vuln_mock.published_date = datetime(2024, 1, 1)

        call_count = {'n': 0}

        def mock_sync_cve(cve_id, force):
            call_count['n'] += 1
            raise Exception('MITRE not found')

        svc.sync_cve = mock_sync_cve

        with patch('app.services.mitre.mitre_service.Vulnerability') as MockVuln, \
             patch('app.services.mitre.mitre_service.SyncMetadata'), \
             patch.object(svc, '_update_status'):
            # Fila dinâmica: filtra sem description ou Awaiting Analysis
            # Primeiro call retorna o vuln, depois (com failed_ids) retorna lista vazia
            call_sequence = [
                [vuln_mock],  # primeiro batch
                [],           # segundo (após exclusão do failed_id)
            ]
            call_iter = iter(call_sequence)

            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.order_by.return_value = mock_query

            def mock_limit(n):
                try:
                    return MagicMock(all=lambda: next(call_iter))
                except StopIteration:
                    return MagicMock(all=lambda: [])

            mock_query.limit.side_effect = mock_limit
            MockVuln.query = mock_query
            MockVuln.cve_id = VulnModel.cve_id

            svc.enrich_existing_vulnerabilities(limit=0, force=False)

        # CVE deve ter sido tentada exatamente 1 vez, não em loop
        assert call_count['n'] == 1
        assert svc.stats['errors'] == 1
