import os
import re
import sqlite3
import openai
from typing import Optional, List, Dict, Tuple

class LLMConnector:
    """
    Uma classe para conectar a um banco de dados SQLite, recuperar informações de CVE,
    e gerar relatórios de análise de risco cibernético usando a API da OpenAI.
    """

    def __init__(self, db_path: str = 'vulnerabilities.db'):
        """
        Inicializa o LLMConnector com o caminho do banco de dados e configura a chave da API OpenAI.
        """
        self.db_path = db_path
        self._set_openai_api_key()
        self._initialize_database()

    def _set_openai_api_key(self):
        """
        Define a chave da API OpenAI a partir das variáveis de ambiente.
        Levanta um EnvironmentError se a chave não for encontrada.
        """
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise EnvironmentError("A chave OPENAI_API_KEY não foi definida no ambiente!")

    def _initialize_database(self):
        """
        Garante que a tabela 'vulnerabilities' e a coluna 'risks' existam.
        Também cria uma tabela 'versions' se ela não existir para demonstração.
        Em uma aplicação real, o esquema do banco de dados seria gerenciado por migrações.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Cria a tabela vulnerabilities se não existir
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    cve_id TEXT PRIMARY KEY,
                    vendor TEXT,
                    description TEXT,
                    baseSeverity TEXT,
                    cvssScore REAL,
                    risks TEXT
                )
            """)
            # Adiciona a coluna risks se não existir
            cursor.execute("PRAGMA table_info(vulnerabilities)")
            column_names = [col[1] for col in cursor.fetchall()]
            if 'risks' not in column_names:
                cursor.execute("ALTER TABLE vulnerabilities ADD COLUMN risks TEXT")

            # Cria a tabela versions se não existir
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cve_id TEXT,
                    feature_version TEXT,
                    affected_version TEXT,
                    fixed_version TEXT,
                    FOREIGN KEY (cve_id) REFERENCES vulnerabilities(cve_id)
                )
            """)
            conn.commit()

    def _get_cve_data(self, cve_id: str) -> Optional[Tuple[str, str, str, float, List[Dict]]]:
        """
        Recupera os detalhes básicos da CVE e as versões afetadas do banco de dados.
        Retorna uma tupla (vendor, description, baseSeverity, cvssScore, affected_versions)
        ou None se a CVE não for encontrada.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Obter detalhes da CVE
            cursor.execute("""
                SELECT vendor, description, baseSeverity, cvssScore, risks
                FROM vulnerabilities
                WHERE cve_id = ?
            """, (cve_id,))
            cve_details = cursor.fetchone()

            if not cve_details:
                return None

            vendor, description, base_severity, cvss_score, risks_content = cve_details

            # Obter versões afetadas
            cursor.execute("""
                SELECT feature_version, affected_version, fixed_version
                FROM versions
                WHERE cve_id = ?
            """, (cve_id,))
            version_rows = cursor.fetchall()
            affected_versions = [{
                'feature_version': v[0],
                'affected_version': v[1],
                'fixed_version': v[2]
            } for v in version_rows]

            return vendor, description, base_severity, cvss_score, affected_versions, risks_content

    def _update_cve_risks(self, cve_id: str, risks_content: str):
        """
        Atualiza a coluna 'risks' para um dado ID de CVE no banco de dados.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE vulnerabilities SET risks = ? WHERE cve_id = ?", (risks_content, cve_id))
            conn.commit()

    def _sanitize_markdown_output(self, text: str) -> str:
        """
        Remove blocos de código Markdown (```markdown ... ```) do texto, para evitar exibição literal.
        """
        return re.sub(r"```(?:markdown)?\s*([\s\S]*?)\s*```", r"\1", text)

    def _build_markdown_prompt(self, cve_data: Dict) -> str:
        """
        Constrói um prompt Markdown detalhado para o LLM gerar um relatório de risco cibernético.
        Inclui detalhes da CVE, fornecedor, severidade, pontuação CVSS e versões afetadas em uma tabela.
        O relatório é estruturado para um público executivo com storytelling claro.
        """
        description = cve_data.get('description', 'Nenhuma informação conhecida.')
        vendor = cve_data.get('vendor', 'Produto/Serviço')
        base_severity = cve_data.get('base_severity', 'Nenhuma informação conhecida.')
        cvss_score = cve_data.get('cvss_score', 'Nenhuma informação conhecida.')
        affected_versions = cve_data.get('affected_versions', [])

        versions_table = ""
        if affected_versions:
            versions_table = "\n### 4. Versões Afetadas Conhecidas\n\n"
            versions_table += "| Recurso/Produto | Versões Afetadas | Versões Corrigidas |\n"
            versions_table += "|-----------------|------------------|--------------------|\n"
            for ver in affected_versions:
                feature = ver.get('feature_version', 'N/A')
                affected = ver.get('affected_version', 'N/A')
                fixed = ver.get('fixed_version', 'N/A')
                versions_table += f"| {feature} | {affected} | {fixed} |\n"
        else:
            versions_table = "\n### 4. Versões Afetadas Conhecidas\n\nNenhuma informação conhecida sobre versões específicas."

        return f"""Você é um analista de risco cibernético sênior e um especialista em segurança da informação, com foco em comunicação executiva.
Gere um **relatório técnico-executivo profissional em formato Markdown**, com linguagem clara, concisa e com um storytelling direto para a tomada de decisão. O relatório deve ser completo, autônomo e direcionado a gerentes e diretores.

**Estrutura do Relatório:**
- Comece com um **Resumo Executivo** que capture a essência do problema, impacto e a urgência.
- Use títulos e subtítulos numerados para clareza e navegação.
- Use tabelas para apresentar dados estruturados, como as versões afetadas.
- Sempre que uma informação não estiver disponível ou aplicável, indique explicitamente com: **Não aplicável** ou **Nenhuma informação conhecida**.
- Mantenha a formatação Markdown estrita.

---

## Relatório de Análise de Risco Cibernético: {vendor} - Vulnerabilidade Crítica (CVE)

### 1. Resumo Executivo

<Escreva um parágrafo conciso aqui que descreva a vulnerabilidade em termos de negócio, seu impacto potencial imediato e o nível de risco geral para a organização. O objetivo é fornecer uma visão de alto nível que justifique a atenção imediata.>

### 2. Visão Geral da Vulnerabilidade

**2.1. Descrição Técnica Detalhada:**
{description}

**2.2. Detalhes Cruciais:**
- **Fornecedor Impactado:** {vendor}
- **Severidade Base (NVD):** {base_severity}
- **Pontuação CVSS:** {cvss_score}
- **Vetor de Ataque Mais Provável:** <Descreva o método mais provável de exploração e os pré-requisitos para um ataque bem-sucedido em termos de como isso pode ser explorado na organização.>

### 3. Impacto e Cenários de Risco

**3.1. Impacto Técnico Direto:**
* <Explique as consequências técnicas diretas (ex: comprometimento de servidores, roubo de dados sensíveis, interrupção de serviços críticos). Relacione isso com ativos tecnológicos da organização.>

**3.2. Impacto de Negócio e Organizacional:**
* <Analise o impacto potencial no negócio: perdas financeiras (diretas e indiretas), danos à reputação, multas regulatórias, interrupção de operações e impacto na conformidade. Use uma abordagem de storytelling: "Imagine que...", "Se não endereçado, isso poderia levar a...".>

**3.3. Status de Exploits Conhecidos:**
* **Disponibilidade Pública:** <Indique se exploits públicos (ex: Metasploit, PoC no GitHub) estão disponíveis. Se sim, mencione o nível de sofisticação e acessibilidade. Isso eleva a urgência.>
* **Casos de Ataque Registrados:** <Há registros de ataques em larga escala ou campanhas ativas explorando esta vulnerabilidade globalmente? Se sim, forneça exemplos relevantes ou o tipo de ataque. Isso contextualiza o risco real.>

{versions_table}

### 5. Tecnologias da Organização Afetadas

* **Sistemas/Serviços Vulneráveis Internos:** <Liste e descreva as tecnologias específicas da organização que são diretamente afetadas. Seja específico: "Nossos servidores web rodando Apache X.Y.Z", "Nossa aplicação de CRM usando biblioteca A.B.C".>
* **Criticidade para o Negócio:** <Avalie a criticidade dos sistemas afetados para as operações de negócio da organização.>

### 6. Estratégias de Mitigação e Ações Recomendadas

**6.1. Ações Imediatas (Curto Prazo):**
* **Prioridade Máxima:** <Liste as ações mais críticas a serem tomadas *imediatamente*, com foco na contenção e remediação inicial (ex: aplicação de patch emergencial, isolamento de sistemas vulneráveis, desabilitação temporária de funcionalidades). Forneça passos claros.>
* **Medidas Temporárias/Workarounds:** <Recomende medidas temporárias (workarounds) que possam ser implementadas rapidamente se a correção permanente não for imediata (ex: configurações de firewall, regras de IPS/IDS, restrições de acesso).>

**6.2. Estratégias de Longo Prazo:**
* **Patches Oficiais/Hotfixes:** <Descreva a disponibilidade de patches oficiais ou hotfixes do fornecedor, incluindo números de versão e links, se possível. Oriente sobre o processo de aplicação.>
* **Fortalecimento da Postura de Segurança:** <Sugira configurações de segurança adicionais, atualização de políticas, treinamento de equipe ou revisão de arquiteturas para fortalecer a postura geral e prevenir futuras ocorrências.>

### 7. Avaliação de Risco e Próximos Passos

**7.1. Avaliação de Risco Interno:**
- **Exposição Técnica da Organização:** <Analise a exposição técnica específica da organização à vulnerabilidade (ex: sistemas expostos à internet, volume de ativos vulneráveis, presença em DMZ, criticidade do dado envolvido).>
- **Classificação de Risco para a Organização:** **Baixo**, **Médio** ou **Alto**
    - **Justificativa:** <Forneça uma justificativa clara e concisa para a classificação do risco, baseada na combinação da severidade da CVE, impacto potencial *para a organização*, vetor de ataque, disponibilidade de exploits e a exposição interna. Explique por que este risco é *real e relevante* para o negócio.>

**7.2. Recomendações Finais e Próximos Passos:**
* <Sumarize as principais recomendações e os próximos passos claros para as equipes de TI/Segurança e a liderança. Incentive a formação de um plano de ação detalhado com prazos e responsáveis.>
* <Sugira a importância do monitoramento contínuo e da comunicação de status.>

---

**Importante:** Este relatório fornece uma análise de risco baseada nas informações disponíveis e deve ser complementado por uma análise interna aprofundada, considerando o contexto operacional e a infraestrutura específica da organização.
"""

    def generate_risk_analysis_report(self, cve_id: str, force_regeneration: bool = False) -> str:
        """
        Gera e retorna o relatório de análise de risco para a CVE fornecida.
        Se o relatório já existir no banco de dados e 'force_regeneration' for False, ele será retornado.
        Caso contrário, um novo relatório será gerado usando o modelo OpenAI e salvo no banco de dados.
        """
        cve_data_tuple = self._get_cve_data(cve_id)

        if not cve_data_tuple:
            return f"Erro: CVE ID '{cve_id}' não encontrada no banco de dados."

        vendor, description, base_severity, cvss_score, affected_versions, existing_risks = cve_data_tuple

        # Verifica se o relatório já existe e se não é para forçar a regeneração
        if existing_risks and existing_risks.strip() and not force_regeneration:
            print(f"Relatório de risco para {cve_id} encontrado no banco de dados. Retornando conteúdo existente.")
            return existing_risks

        # Prepara os dados para o prompt
        cve_data_for_prompt = {
            'cve_id': cve_id,
            'vendor': vendor,
            'description': description,
            'base_severity': base_severity,
            'cvss_score': cvss_score,
            'affected_versions': affected_versions
        }

        try:
            prompt = self._build_markdown_prompt(cve_data_for_prompt)
            print(f"Gerando novo relatório de risco para {cve_id} usando a API OpenAI...")
            response = openai.ChatCompletion.create(
                model="o4-mini", # Ou outro modelo mais recente se disponível
                messages=[
                    {"role": "system", "content": "Você é um analista de risco cibernético sênior e especializado em segurança da informação, com foco em relatórios técnicos detalhados e práticos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096, # Aumentado para relatórios mais completos
                temperature=0.5
            )
            generated_risks = response['choices'][0]['message']['content'].strip()
            sanitized_risks = self._sanitize_markdown_output(generated_risks)

            self._update_cve_risks(cve_id, sanitized_risks)
            print(f"Relatório de risco para {cve_id} gerado e salvo no banco de dados.")
            return sanitized_risks

        except openai.error.OpenAIError as e:
            return f"Erro ao consultar a API da OpenAI: {e}"
        except Exception as e:
            return f"Erro desconhecido durante a geração do relatório: {e}"


if __name__ == '__main__':
    current_dir = os.path.abspath(os.path.dirname(__file__))
    db_file_path = os.path.join(current_dir, 'vulnerabilities.db')

    try:
        connector = LLMConnector(db_path=db_file_path)
    except EnvironmentError as e:
        print(f"Erro de configuração: {e}")
        print("Por favor, defina a variável de ambiente OPENAI_API_KEY. Ex: export OPENAI_API_KEY='sua_chave_aqui'")
        exit(1)

    # Exemplo de adição de dados dummy para fins de teste
    # Certifique-se de que o campo 'risks' está vazio ou nulo para forçar a geração inicial
    with sqlite3.connect(db_file_path) as conn:
        cursor = conn.cursor()
        # Inserir um CVE dummy se não existir (com risks como NULL)
        cursor.execute("INSERT OR IGNORE INTO vulnerabilities (cve_id, vendor, description, baseSeverity, cvssScore, risks) VALUES (?, ?, ?, ?, ?, NULL)",
                       ('CVE-2023-1234', 'Microsoft', 'Uma vulnerabilidade de execução remota de código existe no serviço de impressão do Windows, que permite a um atacante executar código arbitrário com privilégios de SISTEMA. O atacante deve enviar uma solicitação especialmente criada para um servidor de impressão vulnerável.', 'CRITICAL', 9.8))
        # Inserir dados de versão dummy para o CVE
        cursor.execute("INSERT OR IGNORE INTO versions (cve_id, feature_version, affected_version, fixed_version) VALUES (?, ?, ?, ?)",
                       ('CVE-2023-1234', 'Windows Server 2019', 'Todas as versões anteriores ao patch de Março de 2023', 'Patch de Março de 2023 (KB1234567)'))
        cursor.execute("INSERT OR IGNORE INTO versions (cve_id, feature_version, affected_version, fixed_version) VALUES (?, ?, ?, ?)",
                       ('CVE-2023-1234', 'Windows 10', 'Builds 1809, 1903, 1909 antes do patch de Março de 2023', 'Patch de Março de 2023 (KB7654321)'))

        # Exemplo de outro CVE sem dados de versão inicialmente para testar 'Nenhuma informação conhecida'
        cursor.execute("INSERT OR IGNORE INTO vulnerabilities (cve_id, vendor, description, baseSeverity, cvssScore, risks) VALUES (?, ?, ?, ?, ?, NULL)",
                       ('CVE-2024-5678', 'Apache', 'Vulnerabilidade de injeção SQL no módulo mod_auth_mysql, permitindo autenticação bypass.', 'HIGH', 7.5))
        conn.commit()


    print("\n--- Testando CVE-2023-1234 (com dados de versão) ---")
    cve_id_input_1 = 'CVE-2023-1234'
    report_1 = connector.generate_risk_analysis_report(cve_id_input_1)
    print(f"\nRelatório para {cve_id_input_1}:\n{report_1}")

    # Testando a regeneração forçada
    print("\n--- Forçando a regeneração para CVE-2023-1234 ---")
    report_1_forced = connector.generate_risk_analysis_report(cve_id_input_1, force_regeneration=True)
    print(f"\nRelatório (forçadamente regenerado) para {cve_id_input_1}:\n{report_1_forced}")


    print("\n--- Testando CVE-2024-5678 (sem dados de versão inicial) ---")
    cve_id_input_2 = 'CVE-2024-5678'
    report_2 = connector.generate_risk_analysis_report(cve_id_input_2)
    print(f"\nRelatório para {cve_id_input_2}:\n{report_2}")

    print("\n--- Testando CVE inexistente ---")
    cve_id_input_invalid = 'CVE-9999-9999'
    report_invalid = connector.generate_risk_analysis_report(cve_id_input_invalid)
    print(f"\nRelatório para {cve_id_input_invalid}:\n{report_invalid}")