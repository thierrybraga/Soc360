-- ============================================================================
-- Open-Monitor: GIN Indexes for JSONB Vulnerability Data
-- Optimizes vendor/product matching queries for CVE scanning
-- ============================================================================

-- Index GIN para busca eficiente de vendors em JSONB
-- Usado por: match_assets.py, FortinetMatchingService
CREATE INDEX IF NOT EXISTS ix_vuln_vendors_gin
    ON vulnerabilities USING GIN (nvd_vendors_data);

-- Index GIN para busca eficiente de products em JSONB
-- Usado por: FortinetMatchingService.get_cves_by_product()
CREATE INDEX IF NOT EXISTS ix_vuln_products_gin
    ON vulnerabilities USING GIN (nvd_products_data);

-- Index GIN para busca em cpe_configurations
-- Usado por: version range matching
CREATE INDEX IF NOT EXISTS ix_vuln_cpe_config_gin
    ON vulnerabilities USING GIN (cpe_configurations);

-- Index composto para queries frequentes de severidade + vendor
CREATE INDEX IF NOT EXISTS ix_vuln_severity_score
    ON vulnerabilities (base_severity, cvss_score DESC NULLS LAST);

-- Index para CISA KEV filtering
CREATE INDEX IF NOT EXISTS ix_vuln_cisa_kev
    ON vulnerabilities (is_in_cisa_kev)
    WHERE is_in_cisa_kev = true;

-- Index para busca por data de publicacao
CREATE INDEX IF NOT EXISTS ix_vuln_published_date
    ON vulnerabilities (published_date DESC);
