#!/usr/bin/env python3
"""
Open-Monitor Fortinet Seed Script
Popula o banco de dados com vendor e produtos Fortinet.
"""
import sys
import os
import logging

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models.inventory import Vendor, Product
from app.services.fortinet import (
    FORTINET_PRODUCTS,
    FORTIOS_VERSIONS,
    generate_vendor_product_seeds
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def seed_fortinet_vendor():
    """Cria ou atualiza vendor Fortinet."""
    vendor = Vendor.query.filter_by(normalized_name='fortinet').first()

    if vendor:
        logger.info(f"Vendor Fortinet ja existe (ID: {vendor.id})")
        return vendor

    vendor = Vendor(
        name='Fortinet',
        website='https://www.fortinet.com',
        support_url='https://support.fortinet.com',
        security_contact='psirt@fortinet.com',
        description='Fortinet, Inc. - Cybersecurity Solutions Provider'
    )

    db.session.add(vendor)
    db.session.commit()

    logger.info(f"Vendor Fortinet criado (ID: {vendor.id})")
    return vendor


def seed_fortinet_products(vendor: Vendor):
    """Cria ou atualiza produtos Fortinet."""
    created = 0
    updated = 0

    for key, product_def in FORTINET_PRODUCTS.items():
        existing = Product.query.filter_by(
            vendor_id=vendor.id,
            normalized_name=product_def.cpe_product
        ).first()

        if existing:
            existing.name = product_def.name
            existing.cpe_string = product_def.build_cpe()
            existing.product_type = product_def.cpe_part
            existing.description = product_def.description
            updated += 1
        else:
            product = Product(
                name=product_def.name,
                vendor_id=vendor.id,
                cpe_string=product_def.build_cpe(),
                product_type=product_def.cpe_part,
                description=product_def.description
            )
            product.normalized_name = product_def.cpe_product
            db.session.add(product)
            created += 1

    db.session.commit()

    logger.info(f"Produtos Fortinet: {created} criados, {updated} atualizados")
    return created, updated


def seed_fortios_versions(vendor: Vendor):
    """Cria produtos para versoes especificas de FortiOS."""
    base_product = Product.query.filter_by(
        vendor_id=vendor.id,
        normalized_name='fortios'
    ).first()

    if not base_product:
        logger.warning("Produto FortiOS base nao encontrado")
        return 0

    created = 0

    for branch, versions in FORTIOS_VERSIONS.items():
        for version in versions:
            existing = Product.query.filter_by(
                vendor_id=vendor.id,
                name=f'FortiOS {version}'
            ).first()

            if existing:
                continue

            product = Product(
                name=f'FortiOS {version}',
                vendor_id=vendor.id,
                version=version,
                cpe_string=f'cpe:2.3:o:fortinet:fortios:{version}:*:*:*:*:*:*:*',
                product_type='o',
                description=f'FortiOS version {version} (Branch {branch})'
            )
            product.normalized_name = f'fortios_{version}'
            db.session.add(product)
            created += 1

    if created > 0:
        db.session.commit()

    logger.info(f"Versoes FortiOS: {created} criadas")
    return created


def print_summary():
    """Imprime resumo dos dados Fortinet."""
    vendor = Vendor.query.filter_by(normalized_name='fortinet').first()

    if not vendor:
        logger.warning("Vendor Fortinet nao encontrado")
        return

    print("\n" + "=" * 60)
    print("RESUMO - DADOS FORTINET")
    print("=" * 60)

    print(f"\nVendor: {vendor.name}")
    print(f"  ID: {vendor.id}")
    print(f"  Website: {vendor.website}")
    print(f"  Total de produtos: {len(vendor.products)}")

    print("\nProdutos por tipo:")

    type_counts = {}
    for product in vendor.products:
        ptype = product.product_type or 'unknown'
        type_counts[ptype] = type_counts.get(ptype, 0) + 1

    type_names = {
        'a': 'Application',
        'o': 'Operating System',
        'h': 'Hardware',
    }

    for ptype, count in sorted(type_counts.items()):
        type_name = type_names.get(ptype, ptype)
        print(f"  {type_name}: {count}")

    print("\n" + "=" * 60)


def main():
    """Funcao principal."""
    app = create_app()

    with app.app_context():
        logger.info("Iniciando seed de dados Fortinet...")

        # 1. Cria vendor
        vendor = seed_fortinet_vendor()

        # 2. Cria produtos base
        created, updated = seed_fortinet_products(vendor)

        # 3. Cria versoes FortiOS
        versions_created = seed_fortios_versions(vendor)

        # 4. Imprime resumo
        print_summary()

        logger.info("Seed Fortinet concluido!")

        return {
            'vendor_id': vendor.id,
            'products_created': created,
            'products_updated': updated,
            'versions_created': versions_created
        }


if __name__ == '__main__':
    result = main()
    print(f"\nResultado: {result}")
