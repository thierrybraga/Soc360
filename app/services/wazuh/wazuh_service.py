"""
Wazuh SIEM integration service.

Talks to the Wazuh Indexer (OpenSearch-compatible, default port 9200) to
pull alerts from the ``wazuh-alerts-*`` index pattern. The Manager API
(port 55000) is not used here — for SOC alert triage we only need the
data-plane (Indexer).

Design notes
------------
* Config lives in ``SyncMetadata`` (key/value) — no schema migration
  required. The password is encrypted with Fernet keyed off Flask
  ``SECRET_KEY`` (same pattern as the TACACS integration).
* Alert sync is watermark-based: we persist the highest ``timestamp``
  successfully ingested as ``wazuh_last_watermark``. On each poll we
  request ``timestamp > watermark`` sorted ``[timestamp asc, _id asc]``
  and upsert by composite ``<index>:<_id>`` to avoid duplicates during
  rolling-index hand-offs.
* The client uses plain ``requests`` — no new dependency. OpenSearch
  reachable over HTTP(S) with Basic auth is the documented contract.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Iterable, Optional, Tuple, List, Dict, Any

import requests
from flask import current_app

from app.extensions.db import db
from app.models.system import SyncMetadata
from app.models.wazuh import WazuhAlert, WazuhTreatmentNote
from app.models.wazuh.wazuh_alert import severity_from_level

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Config keys (sync_metadata key/value table)
# ─────────────────────────────────────────────────────────────────────────────

KEY_ENABLED           = 'wazuh_enabled'
KEY_URL               = 'wazuh_indexer_url'
KEY_USERNAME          = 'wazuh_indexer_username'
KEY_PASSWORD_ENC      = 'wazuh_indexer_password_enc'
KEY_VERIFY_TLS        = 'wazuh_verify_tls'
KEY_INDEX_PATTERN     = 'wazuh_index_pattern'
KEY_MIN_RULE_LEVEL    = 'wazuh_min_rule_level'
KEY_POLL_INTERVAL     = 'wazuh_poll_interval_seconds'
KEY_LAST_WATERMARK    = 'wazuh_last_watermark'          # ISO8601 UTC
KEY_LAST_WATERMARK_ID = 'wazuh_last_watermark_id'       # tie-breaker _id
KEY_LAST_SYNC_AT      = 'wazuh_last_sync_at'
KEY_LAST_SYNC_OK      = 'wazuh_last_sync_ok'
KEY_LAST_SYNC_MSG     = 'wazuh_last_sync_message'
KEY_LAST_SYNC_COUNT   = 'wazuh_last_sync_count'

DEFAULT_INDEX_PATTERN = 'wazuh-alerts-*'
DEFAULT_MIN_RULE_LEVEL = 0
DEFAULT_POLL_INTERVAL = 60
FETCH_PAGE_SIZE = 500

HTTP_DEFAULT_TIMEOUT = 15  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# Config dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WazuhConfig:
    enabled: bool = False
    url: str = ''                       # e.g. https://wazuh-indexer:9200
    username: str = ''
    password: str = ''                  # plaintext only in form / in-memory
    verify_tls: bool = True
    index_pattern: str = DEFAULT_INDEX_PATTERN
    min_rule_level: int = DEFAULT_MIN_RULE_LEVEL
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL
    has_password: bool = field(default=False)

    # ── Persistence ─────────────────────────────────────────────────────
    @classmethod
    def load(cls) -> 'WazuhConfig':
        def _b(v, default=False):
            if v is None:
                return default
            return str(v).strip().lower() in ('1', 'true', 'yes', 'on')

        def _i(v, default):
            try:
                return int(v) if v not in (None, '') else default
            except (TypeError, ValueError):
                return default

        pwd_enc = SyncMetadata.get(KEY_PASSWORD_ENC) or ''
        return cls(
            enabled=_b(SyncMetadata.get(KEY_ENABLED)),
            url=(SyncMetadata.get(KEY_URL) or '').rstrip('/'),
            username=SyncMetadata.get(KEY_USERNAME) or '',
            password='',
            verify_tls=_b(SyncMetadata.get(KEY_VERIFY_TLS), default=True),
            index_pattern=SyncMetadata.get(KEY_INDEX_PATTERN) or DEFAULT_INDEX_PATTERN,
            min_rule_level=_i(SyncMetadata.get(KEY_MIN_RULE_LEVEL), DEFAULT_MIN_RULE_LEVEL),
            poll_interval_seconds=_i(SyncMetadata.get(KEY_POLL_INTERVAL), DEFAULT_POLL_INTERVAL),
            has_password=bool(pwd_enc),
        )

    def save(self) -> None:
        if self.url and not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        if self.min_rule_level < 0 or self.min_rule_level > 15:
            raise ValueError('min_rule_level must be between 0 and 15')
        if self.poll_interval_seconds < 10 or self.poll_interval_seconds > 3600:
            raise ValueError('poll_interval_seconds must be between 10 and 3600')

        payload = {
            KEY_ENABLED: 'true' if self.enabled else 'false',
            KEY_URL: (self.url or '').rstrip('/'),
            KEY_USERNAME: (self.username or '').strip(),
            KEY_VERIFY_TLS: 'true' if self.verify_tls else 'false',
            KEY_INDEX_PATTERN: (self.index_pattern or DEFAULT_INDEX_PATTERN).strip(),
            KEY_MIN_RULE_LEVEL: str(int(self.min_rule_level)),
            KEY_POLL_INTERVAL: str(int(self.poll_interval_seconds)),
        }
        if self.password:
            payload[KEY_PASSWORD_ENC] = _encrypt_secret(self.password)
        SyncMetadata.set_multi(payload)
        logger.info('Wazuh config saved (enabled=%s url=%s)', self.enabled, self.url)


# ─────────────────────────────────────────────────────────────────────────────
# Fernet helpers — same SECRET_KEY-derived key as TACACS service
# ─────────────────────────────────────────────────────────────────────────────

def _fernet():
    from cryptography.fernet import Fernet
    secret_key = current_app.config.get('SECRET_KEY') or ''
    if not secret_key:
        raise RuntimeError('SECRET_KEY not configured; cannot encrypt Wazuh password')
    digest = hashlib.sha256(secret_key.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def _decrypt_secret(token: str) -> str:
    if not token:
        return ''
    try:
        return _fernet().decrypt(token.encode('ascii')).decode('utf-8')
    except Exception as exc:  # noqa: BLE001 — do not leak internals
        logger.error('Failed to decrypt Wazuh password (SECRET_KEY rotated?): %s', exc)
        return ''


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class WazuhService:
    """Stateless helper around the Wazuh Indexer."""

    # ── Config helpers ─────────────────────────────────────────────────
    @staticmethod
    def load_config() -> WazuhConfig:
        return WazuhConfig.load()

    @staticmethod
    def is_configured() -> bool:
        cfg = WazuhConfig.load()
        return bool(cfg.enabled and cfg.url and cfg.username and cfg.has_password)

    # ── HTTP internals ─────────────────────────────────────────────────
    @staticmethod
    def _auth(cfg: WazuhConfig) -> Optional[Tuple[str, str]]:
        if not cfg.username:
            return None
        pwd = _decrypt_secret(SyncMetadata.get(KEY_PASSWORD_ENC) or '')
        return (cfg.username, pwd) if pwd else None

    @classmethod
    def _request(cls, method: str, path: str, cfg: Optional[WazuhConfig] = None,
                 json_body: Optional[dict] = None, *, timeout: int = HTTP_DEFAULT_TIMEOUT):
        cfg = cfg or WazuhConfig.load()
        if not cfg.url:
            raise RuntimeError('Wazuh Indexer URL not configured')
        auth = cls._auth(cfg)
        if auth is None:
            raise RuntimeError('Wazuh credentials not configured')

        url = f"{cfg.url.rstrip('/')}/{path.lstrip('/')}"
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        return requests.request(
            method,
            url,
            headers=headers,
            auth=auth,
            data=json.dumps(json_body) if json_body is not None else None,
            verify=cfg.verify_tls,
            timeout=timeout,
        )

    # ── Operations ─────────────────────────────────────────────────────
    @classmethod
    def test_connection(cls) -> dict:
        """Ping the Indexer's cluster health endpoint and record the result."""
        now_iso = datetime.now(timezone.utc).isoformat()
        result: Dict[str, Any] = {
            'timestamp': now_iso,
            'ok': False,
            'status_code': None,
            'cluster_status': None,
            'message': '',
        }
        try:
            cfg = WazuhConfig.load()
            if not cfg.url or not cfg.has_password:
                result['message'] = 'URL ou credenciais do Wazuh não configurados.'
                cls._record_sync(False, result['message'], now_iso, count=0)
                return result
            r = cls._request('GET', '/_cluster/health', cfg=cfg, timeout=10)
            result['status_code'] = r.status_code
            if r.status_code == 200:
                body = r.json()
                result['cluster_status'] = body.get('status')
                result['ok'] = body.get('status') in ('green', 'yellow')
                result['message'] = f"Cluster {body.get('cluster_name', '?')}: {body.get('status')}"
            else:
                result['message'] = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.exceptions.SSLError as exc:
            result['message'] = f'Erro TLS: {exc}. Desabilite verify_tls se usar certificado auto-assinado.'
        except requests.exceptions.ConnectionError as exc:
            result['message'] = f'Falha de conexão: {exc}'
        except requests.exceptions.Timeout:
            result['message'] = 'Timeout ao conectar ao Wazuh Indexer.'
        except Exception as exc:  # noqa: BLE001
            logger.exception('Wazuh test_connection failed')
            result['message'] = f'Erro: {exc}'

        cls._record_sync(result['ok'], result['message'], now_iso, count=0)
        return result

    @staticmethod
    def _record_sync(ok: bool, message: str, now_iso: str, *, count: int) -> None:
        SyncMetadata.set_multi({
            KEY_LAST_SYNC_AT: now_iso,
            KEY_LAST_SYNC_OK: 'true' if ok else 'false',
            KEY_LAST_SYNC_MSG: (message or '')[:500],
            KEY_LAST_SYNC_COUNT: str(int(count)),
        })

    @staticmethod
    def last_sync_status() -> dict:
        return {
            'at': SyncMetadata.get(KEY_LAST_SYNC_AT),
            'ok': (SyncMetadata.get(KEY_LAST_SYNC_OK) or '').lower() == 'true',
            'message': SyncMetadata.get(KEY_LAST_SYNC_MSG) or '',
            'count': int(SyncMetadata.get(KEY_LAST_SYNC_COUNT) or 0),
            'watermark': SyncMetadata.get(KEY_LAST_WATERMARK),
        }

    # ── Alert fetch + persist ──────────────────────────────────────────
    @classmethod
    def sync_alerts(cls, *, max_pages: int = 10) -> dict:
        """Fetch new alerts since the last watermark and upsert them locally.

        Uses ``search_after`` pagination (stable under concurrent writes on
        the Indexer) and advances the watermark only after a successful
        commit. Bounded by ``max_pages`` to avoid unbounded work per call.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        cfg = WazuhConfig.load()

        if not cfg.enabled:
            msg = 'Wazuh integration disabled.'
            cls._record_sync(False, msg, now_iso, count=0)
            return {'ok': False, 'message': msg, 'count': 0}

        if not cfg.url or not cfg.has_password:
            msg = 'Wazuh credentials missing.'
            cls._record_sync(False, msg, now_iso, count=0)
            return {'ok': False, 'message': msg, 'count': 0}

        watermark = SyncMetadata.get(KEY_LAST_WATERMARK)
        watermark_id = SyncMetadata.get(KEY_LAST_WATERMARK_ID)

        # First-run default: last 24h so we don't try to replay all history.
        if not watermark:
            watermark = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            watermark_id = None

        total_ingested = 0
        search_after: Optional[list] = [watermark, watermark_id] if watermark_id else [watermark]

        try:
            for _ in range(max_pages):
                body = {
                    'size': FETCH_PAGE_SIZE,
                    'sort': [
                        {'timestamp': 'asc'},
                        {'_id': 'asc'},
                    ],
                    'query': {
                        'bool': {
                            'filter': [
                                {'range': {'timestamp': {'gt': watermark}}},
                                {'range': {'rule.level': {'gte': int(cfg.min_rule_level)}}},
                            ]
                        }
                    },
                    'search_after': search_after,
                }
                # search_after for the very first page with only timestamp needs
                # both tiebreakers to be valid — if we only have watermark, we
                # drop search_after and rely on the range filter.
                if len(search_after) < 2:
                    body.pop('search_after', None)

                path = f"/{cfg.index_pattern.lstrip('/')}/_search"
                r = cls._request('POST', path, cfg=cfg, json_body=body, timeout=30)
                if r.status_code != 200:
                    raise RuntimeError(f'Indexer responded {r.status_code}: {r.text[:300]}')
                hits = (r.json() or {}).get('hits', {}).get('hits', [])
                if not hits:
                    break

                for hit in hits:
                    saved = cls._upsert_hit(hit)
                    if saved:
                        total_ingested += 1

                # Advance watermark from the last hit
                last = hits[-1]
                last_sort = last.get('sort') or []
                if len(last_sort) >= 1:
                    watermark = last_sort[0] if isinstance(last_sort[0], str) else watermark
                if len(last_sort) >= 2:
                    watermark_id = str(last_sort[1])
                search_after = last_sort or search_after

                db.session.commit()

                if len(hits) < FETCH_PAGE_SIZE:
                    break

            SyncMetadata.set_multi({
                KEY_LAST_WATERMARK: watermark,
                KEY_LAST_WATERMARK_ID: watermark_id or '',
            })
            msg = f'Ingested {total_ingested} alert(s).'
            cls._record_sync(True, msg, now_iso, count=total_ingested)
            return {'ok': True, 'message': msg, 'count': total_ingested}

        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            logger.exception('Wazuh sync_alerts failed')
            cls._record_sync(False, str(exc)[:500], now_iso, count=total_ingested)
            return {'ok': False, 'message': str(exc), 'count': total_ingested}

    @staticmethod
    def _upsert_hit(hit: dict) -> bool:
        """Insert an alert if unseen; return True on insert, False on skip."""
        src = hit.get('_source') or {}
        index = hit.get('_index') or ''
        wid = hit.get('_id') or ''
        if not wid:
            return False

        uid = f"{index}:{wid}"
        existing = WazuhAlert.query.filter_by(alert_uid=uid).first()
        if existing:
            return False  # idempotent — never overwrite user treatment fields

        ts_raw = src.get('timestamp') or src.get('@timestamp')
        try:
            # ISO8601 w/ timezone — fallback to now() on malformed
            ts = datetime.fromisoformat(ts_raw.replace('Z', '+00:00')) if ts_raw else datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001
            ts = datetime.now(timezone.utc)

        rule = src.get('rule') or {}
        agent = src.get('agent') or {}
        manager = src.get('manager') or {}
        decoder = src.get('decoder') or {}
        data = src.get('data') or {}
        mitre = rule.get('mitre') or {}

        def _as_list(v):
            if v is None:
                return []
            return v if isinstance(v, list) else [v]

        level = rule.get('level')
        alert = WazuhAlert(
            alert_uid=uid,
            wazuh_id=wid,
            wazuh_index=index,
            timestamp=ts,
            rule_id=str(rule.get('id') or '')[:32] or None,
            rule_level=int(level) if isinstance(level, (int, str)) and str(level).isdigit() else None,
            rule_description=(rule.get('description') or '')[:4000] or None,
            rule_groups=_as_list(rule.get('groups')),
            rule_mitre_ids=_as_list(mitre.get('id')),
            rule_mitre_tactics=_as_list(mitre.get('tactic')),
            rule_mitre_techniques=_as_list(mitre.get('technique')),
            agent_id=str(agent.get('id') or '')[:32] or None,
            agent_name=(agent.get('name') or '')[:255] or None,
            agent_ip=(agent.get('ip') or '')[:64] or None,
            manager_name=(manager.get('name') or '')[:255] or None,
            decoder_name=(decoder.get('name') or '')[:128] or None,
            location=(src.get('location') or '')[:2000] or None,
            full_log=(src.get('full_log') or '')[:10000] or None,
            src_ip=(data.get('srcip') or '')[:64] or None,
            dst_ip=(data.get('dstip') or '')[:64] or None,
            severity=severity_from_level(level),
            raw=src,
            status='NEW',
        )
        db.session.add(alert)
        return True

    # ── AI analysis ────────────────────────────────────────────────────
    @staticmethod
    def ai_analyze(alert: WazuhAlert) -> dict:
        """Produce a short triage summary and a list of recommended actions.

        Uses whichever provider ``AI_PROVIDER`` selects. The caller is
        responsible for persisting the returned fields onto the alert.
        """
        from app.services.core.ai_service import get_ai_service

        mitre_part = ''
        if alert.rule_mitre_ids:
            mitre_part = (
                f"\nMITRE ATT&CK: IDs={alert.rule_mitre_ids}"
                f" tactics={alert.rule_mitre_tactics}"
                f" techniques={alert.rule_mitre_techniques}"
            )

        prompt = (
            "Você é um analista de SOC. Analise o alerta Wazuh abaixo e responda "
            "em JSON estrito com as chaves `summary` (string curta em português, "
            "máx 600 chars, explicando o que aconteceu e o risco) e "
            "`recommendations` (lista de 3 a 6 strings em português com ações "
            "concretas e priorizadas para triagem/contenção).\n\n"
            f"Alerta:\n"
            f"- Regra {alert.rule_id} (nível {alert.rule_level}, severidade {alert.severity}): {alert.rule_description}\n"
            f"- Agente: {alert.agent_name} ({alert.agent_ip})\n"
            f"- Decoder: {alert.decoder_name} | Location: {alert.location}\n"
            f"- Grupos: {alert.rule_groups}"
            f"{mitre_part}\n"
            f"- Log: {(alert.full_log or '')[:1500]}\n"
            f"- src_ip={alert.src_ip} dst_ip={alert.dst_ip}\n\n"
            "Retorne APENAS JSON, sem markdown nem comentários."
        )

        service = get_ai_service()
        try:
            raw = service.generate_chat_response(prompt, context='wazuh_soc_triage')
        except Exception as exc:  # noqa: BLE001
            logger.exception('AI analysis failed')
            return {
                'summary': f'Falha na análise de IA: {exc}',
                'recommendations': [],
                'ok': False,
            }

        summary, recs = _parse_ai_json(raw)
        return {'summary': summary, 'recommendations': recs, 'ok': True, 'raw': raw}


def _parse_ai_json(raw: str) -> Tuple[str, List[str]]:
    """Best-effort extraction of {summary, recommendations} from AI output."""
    if not raw:
        return '', []
    text = raw.strip()

    # Strip ```json fences if the model added them
    if text.startswith('```'):
        text = text.strip('`')
        # drop leading "json" language marker if present
        if text.lower().startswith('json'):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        # Fallback: treat the whole thing as the summary.
        return text[:600], []

    summary = str(data.get('summary', '') or '')[:2000]
    recs_raw = data.get('recommendations') or []
    if isinstance(recs_raw, str):
        recs = [recs_raw]
    elif isinstance(recs_raw, list):
        recs = [str(r) for r in recs_raw if str(r).strip()]
    else:
        recs = []
    return summary, recs[:10]
