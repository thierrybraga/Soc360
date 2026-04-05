#!/usr/bin/env python3
"""
Script para gerar API keys para usuários existentes.
Executar após implementar as melhorias de segurança.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import current_app


def generate_api_keys_for_existing_users():
    """Gera API keys para usuários que não têm uma."""

    app = create_app()

    with app.app_context():
        from models.user import User
        db = current_app.extensions['sqlalchemy']
        
        # Check if tables exist, if not exit gracefully
        try:
            # Try to query users table
            user_count = db.session.query(User).count()
            print(f"✅ Banco de dados OK. Encontrados {user_count} usuários.")
        except Exception as e:
            print(f"❌ Erro no banco de dados: {e}")
            print("💡 Execute 'python init_db.py' primeiro para inicializar o banco de dados.")
            return
        
        print("🔐 Gerando API keys para usuários existentes...")

        # Buscar usuários sem API key
        users_without_key = db.session.query(User).filter(
            (User.api_key.is_(None)) | (User.api_key == '')
        ).all()

        if not users_without_key:
            print("✅ Todos os usuários já têm API keys!")
            return

        print(f"📝 Encontrados {len(users_without_key)} usuários sem API key")

        encryption_service = EncryptionService()
        updated_count = 0
        for user in users_without_key:
            try:
                # Gerar nova API key
                api_key = encryption_service.generate_api_key()

                # Atualizar usuário
                user.api_key = api_key
                user.api_key_created_at = datetime.utcnow()

                print(f"🔑 Gerada API key para {user.username}: {api_key[:8]}...")
                updated_count += 1

            except Exception as e:
                print(f"❌ Erro ao gerar key para {user.username}: {e}")

        # Commit das mudanças
        try:
            db.session.commit()
            print(f"✅ {updated_count} API keys geradas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar mudanças: {e}")
            return

        # Mostrar resumo
        total_users = db.session.query(User).count()
        users_with_keys = db.session.query(User).filter(User.api_key.isnot(None)).count()

        print("\n📊 Resumo:")
        print(f"   Total de usuários: {total_users}")
        print(f"   Com API keys: {users_with_keys}")
        print(f"   Sem API keys: {total_users - users_with_keys}")

        if users_with_keys < total_users:
            print("\n⚠️  Ainda há usuários sem API keys. Execute novamente se necessário.")


if __name__ == "__main__":
    generate_api_keys_for_existing_users()