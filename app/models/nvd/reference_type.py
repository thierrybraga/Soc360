"""
SOC360 Reference Type Model
Model de banco de dados para tipos de referencia.

Nota: Este e um modelo de banco de dados, distinto do Enum ReferenceType
em app.models.system.enums que e usado para categorizar tipos.
"""
from sqlalchemy import Column, Integer, String
from app.extensions.db import db
from app.models.system.base_model import CoreModel


class ReferenceTypeModel(CoreModel):
    """
    Modelo de banco de dados para tipos de referencia.

    Armazena tipos de referencia como NVD, ExploitDB, etc.
    Renomeado para ReferenceTypeModel para evitar conflito com o Enum ReferenceType.
    """
    __tablename__ = 'reference_type'

    # Name of the reference type (e.g., 'NVD', 'ExploitDB')
    name = Column(String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<ReferenceTypeModel id={self.id} name={self.name}>"
