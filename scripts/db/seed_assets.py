# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from app import create_app, db
from app.models.inventory import Asset, Vendor, Product, AssetVulnerability
from app.models.auth import User
from app.models.system.enums import AssetType, AssetStatus, VulnerabilityStatus
from app.services.fortinet import get_fortinet_matching_service


def seed_assets():

    app = create_app()
    with app.app_context():
        print("Seeding assets...")

        # Get admin user as owner
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print(
                "Admin user not found. "
                "Run init_admin.py first."
            )
            return

        # 1. Create Vendors
        vendors_data = [
            {'name': 'Cisco', 'website': 'https://www.cisco.com'},
            {'name': 'Fortinet', 'website': 'https://www.fortinet.com'},
            {'name': 'Microsoft', 'website': 'https://www.microsoft.com'},
        ]

        vendors = {}
        for v_data in vendors_data:
            vendor, created = Vendor.get_or_create(name=v_data['name'])
            if created:
                vendor.website = v_data['website']
                db.session.add(vendor)
                print(f"Created vendor: {vendor.name}")
            else:
                print(f"Vendor exists: {vendor.name}")
            vendors[vendor.name] = vendor

        db.session.commit()

        # 2. Create Products
        products_data = [
            {
                'name': 'Meraki MX68',
                'vendor': vendors['Cisco'],
                'type': 'hardware',
                'version': '18.107',
                'cpe': 'cpe:2.3:h:cisco:meraki_mx68:-:*:*:*:*:*:*:*'
            },
            {
                'name': 'Fortigate 60F',
                'vendor': vendors['Fortinet'],
                'type': 'hardware',
                'version': '7.2.5',
                'cpe': 'cpe:2.3:h:fortinet:fortigate_60f:-:*:*:*:*:*:*:*'
            },
            {
                'name': 'FortiManager',
                'vendor': vendors['Fortinet'],
                'type': 'a',
                'version': '7.4.1',
                'cpe': (
                    'cpe:2.3:a:fortinet:' +
                    'fortimanager:7.4.1:*:*:*:*:*:*:*'
                )
            },
            {
                'name': 'FortiAnalyzer',
                'vendor': vendors['Fortinet'],
                'type': 'a',
                'version': '7.4.1',
                'cpe': (
                    'cpe:2.3:a:fortinet:' +
                    'fortianalyzer:7.4.1:*:*:*:*:*:*:*'
                )
            },
            {
                'name': 'Windows Server 2022',
                'vendor': vendors['Microsoft'],
                'type': 'os',
                'version': '21H2',
                'cpe': (
                    'cpe:2.3:o:microsoft:' +
                    'windows_server_2022:21h2:*:*:*:*:*:*:*'
                )
            }
        ]

        products = {}
        for p_data in products_data:
            product = Product.query.filter_by(
                name=p_data['name'],
                vendor_id=p_data['vendor'].id,
                version=p_data['version']
            ).first()

            if not product:
                product = Product(
                    name=p_data['name'],
                    vendor_id=p_data['vendor'].id
                )
                product.version = p_data['version']
                product.product_type = p_data['type']
                product.cpe_string = p_data['cpe']
                db.session.add(product)
                print(f"Created product: {product.name} ({product.version})")
            else:
                print(f"Product exists: {product.name}")
            products[p_data['name']] = product

        db.session.commit()

        # 3. Create Assets
        assets_data = [
            {
                'name': 'Headquarters Firewall',
                'hostname': 'fw-hq-01',
                'ip': '192.168.1.1',
                'type': AssetType.NETWORK_DEVICE.value,
                'criticality': 'CRITICAL',
                'product': products['Meraki MX68'],
                'vendor': vendors['Cisco'],
                'location': 'HQ Server Room',
                'rto': 4.0,
                'rpo': 1.0,
                'cost': 5000.0
            },
            {
                'name': 'Branch Office Firewall',
                'hostname': 'fw-branch-01',
                'ip': '192.168.2.1',
                'type': AssetType.NETWORK_DEVICE.value,
                'criticality': 'HIGH',
                'product': products['Fortigate 60F'],
                'vendor': vendors['Fortinet'],
                'location': 'Branch Office',
                'rto': 8.0,
                'rpo': 4.0,
                'cost': 2000.0
            },
            {
                'name': 'Fortinet Analyzer',
                'hostname': 'faz-01',
                'ip': '192.168.3.10',
                'type': AssetType.APPLICATION.value,
                'criticality': 'HIGH',
                'product': products['FortiAnalyzer'],
                'vendor': vendors['Fortinet'],
                'location': 'HQ SOC',
                'rto': 6.0,
                'rpo': 2.0,
                'cost': 3000.0
            },
            {
                'name': 'Fortinet Manager',
                'hostname': 'fmg-01',
                'ip': '192.168.3.11',
                'type': AssetType.APPLICATION.value,
                'criticality': 'CRITICAL',
                'product': products['FortiManager'],
                'vendor': vendors['Fortinet'],
                'location': 'HQ SOC',
                'rto': 4.0,
                'rpo': 1.0,
                'cost': 4000.0
            },
            {
                'name': 'FortiGate Edge',
                'hostname': 'fg-100f-01',
                'ip': '192.168.4.1',
                'type': AssetType.NETWORK_DEVICE.value,
                'criticality': 'CRITICAL',
                'product': products['Fortigate 60F'],
                'vendor': vendors['Fortinet'],
                'location': 'Edge Datacenter',
                'rto': 4.0,
                'rpo': 1.0,
                'cost': 6000.0
            },
            {
                'name': 'Primary Domain Controller',
                'hostname': 'dc-01',
                'ip': '192.168.1.10',
                'type': AssetType.SERVER.value,
                'criticality': 'CRITICAL',
                'product': products['Windows Server 2022'],
                'vendor': vendors['Microsoft'],
                'location': 'HQ Virtual Cluster',
                'rto': 2.0,
                'rpo': 0.5,
                'cost': 10000.0
            }
        ]

        created_assets = []
        for a_data in assets_data:
            asset = Asset.query.filter_by(ip_address=a_data['ip']).first()
            if not asset:
                asset = Asset(
                    name=a_data['name'],
                    hostname=a_data['hostname'],
                    ip_address=a_data['ip'],
                    asset_type=a_data['type'],
                    status=AssetStatus.ACTIVE.value,
                    criticality=a_data['criticality'],
                    owner_id=admin.id,
                    vendor_id=a_data['vendor'].id,
                    product_id=a_data['product'].id,
                    version=a_data['product'].version,
                    location=a_data['location'],
                    rto_hours=a_data['rto'],
                    rpo_hours=a_data['rpo'],
                    operational_cost_per_hour=a_data['cost']
                )
                db.session.add(asset)
                print(f"Created asset: {asset.name}")
                created_assets.append(asset)
            else:
                print(f"Asset exists: {asset.name}")

        db.session.commit()
        print("Asset seeding completed successfully.")

        # 4. Associar CVEs aos assets Fortinet recém-criados
        if created_assets:
            service = get_fortinet_matching_service()
            assoc_count = 0
            for asset in created_assets:
                # Apenas ativos Fortinet
                try:
                    vendor = Vendor.query.get(asset.vendor_id)
                    if not vendor or (vendor.name or '').lower() != 'fortinet':
                        continue
                except Exception:
                    continue

                matches = service.match_asset(asset)
                for match in matches:
                    exists = AssetVulnerability.query.filter_by(
                        asset_id=asset.id, cve_id=match.cve_id
                    ).first()
                    if not exists:
                        av = AssetVulnerability(
                            asset_id=asset.id,
                            cve_id=match.cve_id,
                            status=VulnerabilityStatus.OPEN.value,
                            discovered_at=None
                        )
                        db.session.add(av)
                        assoc_count += 1
            db.session.commit()
            print(f"Associated {assoc_count} CVEs to Fortinet assets.")


if __name__ == '__main__':
    seed_assets()
