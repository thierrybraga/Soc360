"""
SOC360 Alert Service
Serviço para geração e gerenciamento de alertas.
"""
import logging
from datetime import datetime, timedelta
from app.extensions import db
from app.models.monitoring import Alert, MonitoringRule
from app.models.system import AlertStatus, Severity, MonitoringRuleType

logger = logging.getLogger(__name__)

class AlertService:
    @staticmethod
    def create_alert(rule: MonitoringRule, title: str, description: str, 
                     severity: str = 'MEDIUM', cve_id: str = None, details: dict = None):
        """
        Cria um novo alerta baseado em uma regra.
        Verifica throttling e duplicação.
        """
        # Verificar cooldown
        if rule.last_triggered_at:
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            if datetime.utcnow() - rule.last_triggered_at < cooldown_delta:
                logger.info(f"Rule {rule.id} suppressed by cooldown")
                return None

        # Verificar limite diário
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = Alert.query.filter(
            Alert.rule_id == rule.id,
            Alert.created_at >= today_start
        ).count()
        
        if daily_count >= rule.max_alerts_per_day:
            logger.info(f"Rule {rule.id} reached daily limit")
            return None

        # Verificar se já existe alerta para este CVE e regra
        if cve_id:
            existing = Alert.query.filter(
                Alert.rule_id == rule.id,
                Alert.cve_id == cve_id,
                Alert.status.in_([AlertStatus.NEW.value, AlertStatus.ACKNOWLEDGED.value])
            ).first()
            if existing:
                logger.info(f"Alert already exists for Rule {rule.id} and CVE {cve_id}")
                return existing

        # Criar alerta
        alert = Alert(
            title=title,
            description=description,
            rule_id=rule.id,
            cve_id=cve_id,
            severity=severity,
            details=details or {},
            status=AlertStatus.NEW.value
        )
        
        db.session.add(alert)
        
        # Atualizar regra
        rule.last_triggered_at = datetime.utcnow()
        rule.trigger_count += 1
        
        db.session.commit()
        
        # TODO: Enviar notificações (Email, Webhook, etc)
        # AlertService.send_notifications(rule, alert)
        
        logger.info(f"Alert created: {title} (Rule {rule.id})")
        return alert

    @staticmethod
    def process_new_vulnerability(vulnerability):
        """
        Processa uma nova vulnerabilidade contra todas as regras ativas.
        """
        
        # Tipos de regras que se aplicam a novas vulnerabilidades
        applicable_types = [
            MonitoringRuleType.NEW_CVE.value,
            MonitoringRuleType.SEVERITY_THRESHOLD.value,
            MonitoringRuleType.VENDOR_SPECIFIC.value,
            MonitoringRuleType.PRODUCT_SPECIFIC.value,
            MonitoringRuleType.CISA_KEV.value
        ]
        
        rules = MonitoringRule.query.filter(
            MonitoringRule.enabled == True,
            MonitoringRule.rule_type.in_(applicable_types)
        ).all()
        
        alerts_created = 0
        for rule in rules:
            try:
                if rule.matches_vulnerability(vulnerability):
                    severity = vulnerability.base_severity or 'MEDIUM'
                    
                    alert = AlertService.create_alert(
                        rule=rule,
                        title=f"New Vulnerability: {vulnerability.cve_id}",
                        description=f"Rule '{rule.name}' matched vulnerability {vulnerability.cve_id}",
                        severity=severity,
                        cve_id=vulnerability.cve_id,
                        details={
                            'vulnerability_id': vulnerability.cve_id,
                            'cvss_score': vulnerability.cvss_score,
                            'vendors': vulnerability.vendors,
                            'matched_rule_type': rule.rule_type
                        }
                    )
                    if alert:
                        alerts_created += 1
            except Exception as e:
                logger.error(f"Error processing rule {rule.id} for vuln {vulnerability.cve_id}: {str(e)}")
                
        return alerts_created
