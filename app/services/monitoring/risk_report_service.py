# app/services/monitoring/risk_report_service.py

import os
import re
import sqlite3
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from flask import current_app

logger = logging.getLogger(__name__)

class RiskReportService:
    """
    Servico para geracao de relatorios de risco de vulnerabilidades usando OpenAI.

    Baseado no codigo de exemplo fornecido, este servico gera analises
    detalhadas de risco em formato Markdown para vulnerabilidades CVE.
    """

    def __init__(self):
        """
        Inicializa o servico de relatorios de risco.
        """
        self.client = None
        self._initialized = False

    def _initialize_client(self):
        """
        Inicializa o cliente OpenAI dentro do contexto da aplicacao.
        """
        if self._initialized:
            return

        self.api_key = current_app.config.get('OPENAI_API_KEY')
        self.model = current_app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.max_tokens = current_app.config.get('OPENAI_MAX_TOKENS', 800)
        self.temperature = current_app.config.get('OPENAI_TEMPERATURE', 0.5)

        if not self.api_key:
            logger.warning("OPENAI_API_KEY nao configurada - modo demo ativo")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("Cliente OpenAI inicializado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente OpenAI: {e}")
                self.client = None

        self._initialized = True

    def build_markdown_prompt(self, description: str) -> str:
        """
        Constroi o prompt em Markdown para analise de risco.
        """
        return f"""Voce e um analista de risco cibernetico especializado em seguranca da informacao.
Gere um **relatorio tecnico profissional em formato Markdown**, com linguagem clara, objetiva e com foco em acoes praticas para mitigacao da vulnerabilidade descrita a seguir.

Sempre que uma informacao nao estiver disponivel ou aplicavel, indique explicitamente com: **Nao aplicavel** ou **Nenhuma informacao conhecida**.

---

## Descricao Tecnica
{description}

## Impacto Potencial
**Impacto Tecnico Direto**
<Descreva aqui o impacto tecnico direto.>

**Impacto Organizacional e de Negocio**
<Descreva aqui o impacto organizacional e comercial.>

## Vetor de Ataque
<Descreva o metodo mais provavel de exploracao.>

## Tecnologias Afetadas
- Sistemas, servicos ou softwares vulneraveis.
- Versoes afetadas, se aplicavel.

## Exploits Conhecidos
- Exploits publicos disponiveis?
- Ha registros de ataques em larga escala?

## Mitigacoes e Correcoes
- Patches oficiais ou hotfixes disponiveis?
- Medidas temporarias recomendadas.

## Recomendacao de Acao
- Acoes imediatas e procedimentos internos recomendados.

## Avaliacao de Risco Interno
Classifique o risco considerando que a organizacao **utiliza a tecnologia afetada**:
- Exposicao tecnica
- Risco: **Baixo**, **Medio** ou **Alto** (com justificativa)

---

**Importante:** Mantenha o conteudo em formato Markdown, com tom tecnico, objetivo e direto ao ponto.
"""

    def sanitize_markdown_output(self, text: str) -> str:
        """
        Remove blocos de codigo Markdown do texto, para evitar exibicao literal.
        """
        return re.sub(r"```(?:markdown)?\s*([\s\S]*?)\s*```", r"\1", text)

    def get_risk_analysis(self, cve_id: str) -> str:
        """
        Retorna a analise de risco para a CVE fornecida.
        """
        self._initialize_client()

        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', 'vulnerabilities.db')

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("PRAGMA table_info(vulnerabilities)")
                colunas_nomes = [col[1] for col in cursor.fetchall()]
                if 'risks' not in colunas_nomes:
                    cursor.execute("ALTER TABLE vulnerabilities ADD COLUMN risks TEXT")
                    conn.commit()
                    logger.info("Coluna 'risks' adicionada a tabela vulnerabilities")

                cursor.execute("""
                    SELECT vendor, description, baseSeverity, cvssScore, risks
                    FROM vulnerabilities
                    WHERE cve_id = ?
                """, (cve_id,))
                row = cursor.fetchone()

                if not row:
                    logger.warning(f"CVE {cve_id} nao encontrada no banco de dados")
                    return "CVE id nao encontrada."

                vendor, description, base_severity, cvss_score, risks = row

                if not risks or not risks.strip():
                    logger.info(f"Gerando nova analise de risco para CVE {cve_id}")

                    if not self.client:
                        risks = self._generate_demo_risk_analysis(cve_id, description, base_severity, cvss_score)
                    else:
                        try:
                            prompt = self.build_markdown_prompt(description)

                            response = self.client.chat.completions.create(
                                model=self.model,
                                messages=[
                                    {"role": "system", "content": "Voce e um analista de risco especializado em vulnerabilidades."},
                                    {"role": "user", "content": prompt}
                                ],
                                max_tokens=self.max_tokens,
                                temperature=self.temperature
                            )

                            risks = response.choices[0].message.content.strip()
                            risks = self.sanitize_markdown_output(risks)

                        except Exception as e:
                            logger.error(f"Erro ao consultar OpenAI: {e}")
                            risks = self._generate_demo_risk_analysis(cve_id, description, base_severity, cvss_score)

                    cursor.execute("UPDATE vulnerabilities SET risks = ? WHERE cve_id = ?", (risks, cve_id))
                    conn.commit()
                    logger.info(f"Analise de risco salva para CVE {cve_id}")

                return risks

        except sqlite3.Error as e:
            logger.error(f"Erro no banco de dados: {e}")
            return f"Erro ao acessar banco de dados: {e}"
        except Exception as e:
            logger.error(f"Erro desconhecido: {e}")
            return f"Erro desconhecido: {e}"

    def _generate_demo_risk_analysis(self, cve_id: str, description: str, base_severity: str, cvss_score: float) -> str:
        """
        Gera uma analise de risco de demonstracao quando a API da OpenAI nao esta disponivel.
        """
        severity_map = {
            'LOW': 'Baixo',
            'MEDIUM': 'Medio',
            'HIGH': 'Alto',
            'CRITICAL': 'Critico'
        }

        severity_pt = severity_map.get(base_severity, 'Nao definido')

        return f"""# Relatorio de Analise de Risco - {cve_id}

## Descricao Tecnica
{description}

## Impacto Potencial
**Impacto Tecnico Direto**
Baseado na severidade {severity_pt} (CVSS: {cvss_score}), esta vulnerabilidade pode comprometer a seguranca do sistema afetado.

**Impacto Organizacional e de Negocio**
Potencial interrupcao de servicos e exposicao de dados sensiveis, dependendo do contexto de implementacao.

## Vetor de Ataque
**Nenhuma informacao conhecida** - Analise detalhada requer acesso a API da OpenAI.

## Tecnologias Afetadas
- Sistemas e softwares relacionados a vulnerabilidade {cve_id}
- **Nenhuma informacao conhecida** sobre versoes especificas

## Exploits Conhecidos
- **Nenhuma informacao conhecida** - Verificacao em bases de dados de exploits recomendada

## Mitigacoes e Correcoes
- Verificar disponibilidade de patches oficiais
- Implementar medidas de seguranca compensatorias
- Monitorar sistemas afetados

## Recomendacao de Acao
- Avaliar exposicao dos sistemas organizacionais
- Priorizar correcao baseada na severidade {severity_pt}
- Implementar monitoramento adicional

## Avaliacao de Risco Interno
**Exposicao tecnica:** Dependente da implementacao organizacional
**Risco:** {severity_pt} - Baseado na classificacao CVSS {cvss_score}

---

*Nota: Esta e uma analise de demonstracao. Para analise completa e detalhada, configure a chave da API OpenAI.*
"""

    def generate_risk_report_html(self, cve_id: str) -> str:
        """
        Gera um relatorio de risco em formato HTML para exibicao na web.
        """
        try:
            self._initialize_client()

            import markdown

            markdown_content = self.get_risk_analysis(cve_id)
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])

            return html_content

        except ImportError:
            logger.warning("Biblioteca markdown nao encontrada, retornando conteudo em texto")
            return f"<pre>{self.get_risk_analysis(cve_id)}</pre>"
        except Exception as e:
            logger.error(f"Erro ao gerar HTML: {e}")
            return f"<p>Erro ao gerar relatorio: {e}</p>"
