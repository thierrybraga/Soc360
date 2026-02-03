
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models.nvd import Vulnerability
from app.models.inventory import Asset, AssetVulnerability
from app.models.system.enums import VulnerabilityStatus

def seed_vulns():
    app = create_app()
    with app.app_context():
        print("Seeding mock vulnerabilities...")
        
        # 1. Windows Server 2022 Vulns
        vulns_data = [
            {
                'cve_id': 'CVE-2023-9999',
                'description': 'Critical RCE in Windows Server 2022',
                'severity': 'CRITICAL',
                'score': 9.8,
                'vendor': 'microsoft',
                'product': 'windows_server_2022',
                'published': datetime.now() - timedelta(days=10)
            },
            {
                'cve_id': 'CVE-2023-9998',
                'description': 'Privilege Escalation in Windows Server',
                'severity': 'HIGH',
                'score': 7.5,
                'vendor': 'microsoft',
                'product': 'windows_server_2022',
                'published': datetime.now() - timedelta(days=20)
            },
            # Fortinet
            {
                'cve_id': 'CVE-2023-8888',
                'description': 'Authentication Bypass in Fortigate',
                'severity': 'CRITICAL',
                'score': 9.1,
                'vendor': 'fortinet',
                'product': 'fortigate_60f',
                'published': datetime.now() - timedelta(days=5)
            },
            # Meraki
            {
                'cve_id': 'CVE-2023-7777',
                'description': 'Information Disclosure in Meraki MX',
                'severity': 'MEDIUM',
                'score': 5.3,
                'vendor': 'cisco',
                'product': 'meraki_mx68',
                'published': datetime.now() - timedelta(days=30)
            }
        ]
        
        created_count = 0
        for v_data in vulns_data:
            existing = Vulnerability.query.filter_by(cve_id=v_data['cve_id']).first()
            if not existing:
                vuln = Vulnerability(
                    cve_id=v_data['cve_id'],
                    description=v_data['description'],
                    base_severity=v_data['severity'],
                    cvss_score=v_data['score'],
                    nvd_vendors_data=[v_data['vendor']],
                    nvd_products_data={v_data['vendor']: [v_data['product']]},
                    published_date=v_data['published'],
                    last_modified_date=datetime.now()
                )
                db.session.add(vuln)
                created_count += 1
                print(f"Created {v_data['cve_id']}")
            else:
                print(f"Vuln {v_data['cve_id']} exists")
                
        db.session.commit()
        print(f"Created {created_count} vulnerabilities.")
        
        # Now run the matcher again
        print("Running matcher...")
        # We can import match_assets or just run the logic here
        
if __name__ == "__main__":
    seed_vulns()
