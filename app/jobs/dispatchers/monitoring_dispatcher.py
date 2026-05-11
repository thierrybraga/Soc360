"""
SOC360 Monitoring Dispatcher Job
Responsavel por encontrar vulnerabilidades correspondentes a regras
de monitoramento ativas e despachar alertas.
"""
import logging
from typing import List
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask
from app.extensions.db import db
from app.models.monitoring.monitoring_rule import MonitoringRule
from app.models.nvd.vulnerability import Vulnerability
from app.models.inventory.vendor import Vendor

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_email(to: str, subject: str, content: str) -> None:
        """Placeholder para enviar e-mail."""
        logger.info(f"Simulating sending email to {to}:\nSubject: {subject}\n{content}")
        pass


class MonitoringDispatcher:
    """
    Dispatcher responsavel por encontrar vulnerabilidades correspondentes a regras
    de monitoramento ativas e despachar alertas.
    """

    def __init__(self, email_service: EmailService = None):
        self.email_service = email_service or EmailService()

    def dispatch_alerts(self, db_session: Session) -> int:
        """
        Busca regras de monitoramento ativas, encontra vulnerabilidades correspondentes
        e despacha alertas.

        Retorna o numero total de alertas despachados.
        """
        alerts_dispatched_count = 0
        logger.info("Starting monitoring alert dispatch.")
        try:
            rules = db_session.query(MonitoringRule)\
                               .filter_by(is_active=True)\
                               .options(joinedload(MonitoringRule.user))\
                               .all()
            logger.info(f"Found {len(rules)} active monitoring rules.")

            for rule in rules:
                try:
                    vulnerabilities = self.fetch_vulnerabilities(db_session, rule)
                    if vulnerabilities:
                        logger.info(f"Rule '{rule.name}' (user={rule.user.username}) found {len(vulnerabilities)} new vulnerabilities.")
                        self.send_alert(rule, vulnerabilities)
                        alerts_dispatched_count += 1
                    else:
                        logger.debug(f"Rule '{rule.name}' (user={rule.user.username}) found no new vulnerabilities.")
                except SQLAlchemyError as db_err:
                    logger.error(f"DB error processing rule {rule.id} (user={rule.user.username}).", exc_info=db_err)
                except Exception as e:
                    logger.error(f"Error processing rule {rule.id} (user={rule.user.username}).", exc_info=e)

        except SQLAlchemyError as e:
            logger.error("DB error fetching active monitoring rules.", exc_info=e)
        except Exception as e:
            logger.error("An unexpected error occurred during dispatch_alerts.", exc_info=e)

        logger.info(f"Monitoring alert dispatch finished. Total alerts dispatched: {alerts_dispatched_count}.")
        return alerts_dispatched_count

    def fetch_vulnerabilities(self, db_session: Session, rule: MonitoringRule) -> List['Vulnerability']:
        """
        Busca vulnerabilidades do banco de dados que correspondem aos criterios de uma regra.
        """
        query = db_session.query(Vulnerability)

        if rule.vendor_id:
            query = query.join(Vulnerability.vendors).filter(Vendor.id == rule.vendor_id)

        if rule.severity_filter:
            query = query.filter(Vulnerability.base_severity == rule.severity_filter)

        if rule.query:
            query = query.filter(Vulnerability.description.ilike(f"%{rule.query}%"))

        try:
            vulnerabilities = query.order_by(Vulnerability.published_date.desc()).limit(10).all()
            return vulnerabilities
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching vulnerabilities for rule {rule.id}.", exc_info=e)
            return []

    def send_alert(self, rule: MonitoringRule, vulnerabilities: List['Vulnerability']) -> None:
        """
        Prepara e envia um alerta (e-mail) para o usuario associado a regra.
        """
        if not rule.user or not rule.user.email:
            logger.warning(f"Rule {rule.id} has no associated user or email. Cannot send alert.")
            return

        user_email = rule.user.email
        subject = f"Alert: New vulnerabilities matching your rule ({rule.name or rule.query})"
        content = "Recent vulnerabilities found for your monitoring rule:\n\n" + "\n".join(
            f"- {v.cve_id}: {v.description[:150]}... Severity: {v.base_severity} (Published: {v.published_date.strftime('%Y-%m-%d')})"
            for v in vulnerabilities
        ) + "\n\nView all matching vulnerabilities on the platform."

        try:
            self.email_service.send_email(user_email, subject, content)
            logger.info(f"Alert sent successfully for rule {rule.id} to {user_email}.")
        except Exception as e:
            logger.error(f"Failed to send alert email for rule {rule.id} to {user_email}.", exc_info=e)


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        dispatcher = MonitoringDispatcher()
        alerts_sent = dispatcher.dispatch_alerts(db.session)
        logger.info(f"Monitoring dispatch job finished. Sent {alerts_sent} alerts.")
