import os
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

cert_dir = os.path.join('docker', 'nginx', 'ssl')
if not os.path.exists(cert_dir):
    os.makedirs(cert_dir)

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
])
cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.utcnow()).not_valid_after(datetime.utcnow() + timedelta(days=3650)).add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False).sign(key, hashes.SHA256())

with open(os.path.join(cert_dir, "privkey.pem"), "wb") as f:
    f.write(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()))

with open(os.path.join(cert_dir, "fullchain.pem"), "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print('Certificados SSL gerados em docker/nginx/ssl')
