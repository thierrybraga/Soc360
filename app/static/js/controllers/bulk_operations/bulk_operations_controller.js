/**
 * bulk_operations_controller.js - Controlador de Operações em Lote
 * Versão: 1.0 - Criado em Janeiro 2025
 * Gerenciamento de exportações e importações em lote via API
 */

(function() {
    'use strict';

    // ==========================================================================
    // Configurações e Constantes
    // ==========================================================================

    const CONFIG = {
        api: {
            baseUrl: '/api/v1',
            endpoints: {
                exportAssets: '/bulk/export/assets',
                importAssets: '/bulk/import/assets',
                exportVulnerabilities: '/bulk/export/vulnerabilities',
                backup: '/bulk/backup'
            }
        },
        maxFileSize: 10 * 1024 * 1024, // 10MB
        supportedFormats: {
            export: ['csv', 'json'],
            import: ['csv', 'json']
        }
    };

    // ==========================================================================
    // Classe Principal - BulkOperationsController
    // ==========================================================================

    class BulkOperationsController {
        constructor() {
            this.currentOperation = null;
            this.isProcessing = false;

            this.init();
        }

        // ======================================================================
        // Inicialização
        // ======================================================================

        init() {
            this.bindEvents();
        }

        bindEvents() {
            // Exportações
            $('#btn-export-assets').on('click', () => this.showExportModal('assets'));
            $('#btn-export-vulnerabilities').on('click', () => this.showExportModal('vulnerabilities'));
            $('#btn-create-backup').on('click', () => this.createBackup());

            // Importações
            $('#btn-import-assets').on('click', () => this.showImportModal('assets'));

            // Formulários
            $('#exportForm').on('submit', (e) => {
                e.preventDefault();
                this.performExport();
            });

            $('#importForm').on('submit', (e) => {
                e.preventDefault();
                this.performImport();
            });

            // Validação de arquivo
            $('#import-file').on('change', (e) => this.validateImportFile(e.target));

            // Modais
            $('#exportModal').on('hidden.bs.modal', () => this.resetExportForm());
            $('#importModal').on('hidden.bs.modal', () => this.resetImportForm());

            // Download automático de resultados
            $(document).on('click', '.download-result', (e) => {
                e.preventDefault();
                const url = $(e.target).data('url');
                if (url) {
                    window.open(url, '_blank');
                }
            });
        }

        // ======================================================================
        // Exportações
        // ======================================================================

        showExportModal(type) {
            this.currentOperation = { type: 'export', resource: type };
            $('#export-resource-type').val(type);
            $('#exportModalLabel').text(`Exportar ${this.getResourceName(type)}`);

            // Configurar opções específicas
            this.configureExportOptions(type);

            $('#exportModal').modal('show');
        }

        configureExportOptions(type) {
            const optionsContainer = $('#export-options');
            optionsContainer.empty();

            if (type === 'assets') {
                optionsContainer.append(`
                    <div class="mb-3">
                        <label class="form-label">Incluir dados adicionais:</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="export-include-vulnerabilities" checked>
                            <label class="form-check-label" for="export-include-vulnerabilities">
                                Incluir contagem de vulnerabilidades
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="export-include-monitoring" checked>
                            <label class="form-check-label" for="export-include-monitoring">
                                Incluir status de monitoramento
                            </label>
                        </div>
                    </div>
                `);
            }
        }

        async performExport() {
            const format = $('#export-format').val();
            const resource = this.currentOperation.resource;

            if (!format || !CONFIG.supportedFormats.export.includes(format)) {
                this.showError('Formato de exportação inválido');
                return;
            }

            try {
                $('#btn-perform-export').prop('disabled', true)
                    .html('<i class="fas fa-spinner fa-spin"></i> Exportando...');

                let url = `${CONFIG.api.baseUrl}${CONFIG.api.endpoints.exportAssets}`;
                if (resource === 'vulnerabilities') {
                    url = `${CONFIG.api.baseUrl}${CONFIG.api.endpoints.exportVulnerabilities}`;
                }

                const params = new URLSearchParams({ format });

                // Opções específicas
                if (resource === 'assets') {
                    if ($('#export-include-vulnerabilities').is(':checked')) {
                        params.append('include_vulnerabilities', 'true');
                    }
                    if ($('#export-include-monitoring').is(':checked')) {
                        params.append('include_monitoring', 'true');
                    }
                }

                const response = await fetch(`${url}?${params}`, {
                    method: 'GET',
                    headers: {
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                // Para downloads diretos, o navegador deve lidar automaticamente
                // Para outros casos, podemos mostrar uma mensagem de sucesso
                if (response.headers.get('content-disposition')) {
                    // Download automático
                    const blob = await response.blob();
                    this.downloadBlob(blob, response.headers.get('content-disposition'));
                } else {
                    const result = await response.json();
                    this.showExportResult(result);
                }

                $('#exportModal').modal('hide');
                this.showSuccess(`${this.getResourceName(resource)} exportado(s) com sucesso`);

            } catch (error) {
                console.error('Erro na exportação:', error);
                this.showError('Erro na exportação: ' + error.message);
            } finally {
                $('#btn-perform-export').prop('disabled', false)
                    .html('<i class="fas fa-download"></i> Exportar');
            }
        }

        showExportResult(result) {
            // Mostrar resultado em um modal ou toast
            console.log('Resultado da exportação:', result);
        }

        downloadBlob(blob, contentDisposition) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;

            // Extrair nome do arquivo do header
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            const filename = filenameMatch ? filenameMatch[1].replace(/['"]/g, '') : 'export.csv';

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }

        // ======================================================================
        // Importações
        // ======================================================================

        showImportModal(type) {
            this.currentOperation = { type: 'import', resource: type };
            $('#import-resource-type').val(type);
            $('#importModalLabel').text(`Importar ${this.getResourceName(type)}`);

            // Configurar opções específicas
            this.configureImportOptions(type);

            $('#importModal').modal('show');
        }

        configureImportOptions(type) {
            const optionsContainer = $('#import-options');
            optionsContainer.empty();

            if (type === 'assets') {
                optionsContainer.append(`
                    <div class="mb-3">
                        <label class="form-label">Opções de importação:</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="import-update-existing" checked>
                            <label class="form-check-label" for="import-update-existing">
                                Atualizar ativos existentes
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="import-skip-errors">
                            <label class="form-check-label" for="import-skip-errors">
                                Pular erros e continuar
                            </label>
                        </div>
                    </div>
                `);
            }
        }

        validateImportFile(input) {
            const file = input.files[0];
            if (!file) return;

            // Verificar tamanho
            if (file.size > CONFIG.maxFileSize) {
                this.showError(`Arquivo muito grande. Tamanho máximo: ${CONFIG.maxFileSize / (1024 * 1024)}MB`);
                input.value = '';
                return;
            }

            // Verificar extensão
            const extension = file.name.split('.').pop().toLowerCase();
            if (!CONFIG.supportedFormats.import.includes(extension)) {
                this.showError(`Formato não suportado. Use: ${CONFIG.supportedFormats.import.join(', ')}`);
                input.value = '';
                return;
            }

            // Mostrar informações do arquivo
            $('#file-info').html(`
                <small class="text-muted">
                    <i class="fas fa-file"></i> ${file.name} (${this.formatFileSize(file.size)})
                </small>
            `);
        }

        async performImport() {
            const fileInput = $('#import-file')[0];
            const file = fileInput.files[0];

            if (!file) {
                this.showError('Selecione um arquivo para importar');
                return;
            }

            try {
                $('#btn-perform-import').prop('disabled', true)
                    .html('<i class="fas fa-spinner fa-spin"></i> Importando...');

                const formData = new FormData();
                formData.append('file', file);

                // Opções específicas
                if (this.currentOperation.resource === 'assets') {
                    formData.append('update_existing', $('#import-update-existing').is(':checked'));
                    formData.append('skip_errors', $('#import-skip-errors').is(':checked'));
                }

                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.importAssets}`, {
                    method: 'POST',
                    headers: {
                        'X-API-Key': this.getApiKey()
                    },
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                $('#importModal').modal('hide');

                this.showImportResult(result);

            } catch (error) {
                console.error('Erro na importação:', error);
                this.showError('Erro na importação: ' + error.message);
            } finally {
                $('#btn-perform-import').prop('disabled', false)
                    .html('<i class="fas fa-upload"></i> Importar');
            }
        }

        showImportResult(result) {
            const { imported, errors, message } = result;

            let content = `<div class="alert alert-success">${message}</div>`;

            if (errors && errors.length > 0) {
                content += `
                    <div class="alert alert-warning">
                        <h6>Erros encontrados (${errors.length}):</h6>
                        <ul class="mb-0">
                            ${errors.slice(0, 10).map(error => `<li>${error}</li>`).join('')}
                            ${errors.length > 10 ? `<li>... e mais ${errors.length - 10} erros</li>` : ''}
                        </ul>
                    </div>
                `;
            }

            // Mostrar em um modal de resultado
            $('#import-result-content').html(content);
            $('#importResultModal').modal('show');
        }

        // ======================================================================
        // Backup
        // ======================================================================

        async createBackup() {
            try {
                $('#btn-create-backup').prop('disabled', true)
                    .html('<i class="fas fa-spinner fa-spin"></i> Criando backup...');

                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.backup}`, {
                    method: 'GET',
                    headers: {
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                // Download automático do backup
                const blob = await response.blob();
                this.downloadBlob(blob, response.headers.get('content-disposition') || 'attachment; filename=backup.json');

                this.showSuccess('Backup criado com sucesso');

            } catch (error) {
                console.error('Erro ao criar backup:', error);
                this.showError('Erro ao criar backup: ' + error.message);
            } finally {
                $('#btn-create-backup').prop('disabled', false)
                    .html('<i class="fas fa-download"></i> Criar Backup');
            }
        }

        // ======================================================================
        // Utilitários
        // ======================================================================

        resetExportForm() {
            $('#exportForm')[0].reset();
            $('#export-options').empty();
        }

        resetImportForm() {
            $('#importForm')[0].reset();
            $('#import-options').empty();
            $('#file-info').empty();
        }

        getResourceName(type) {
            const names = {
                assets: 'Ativos',
                vulnerabilities: 'Vulnerabilidades'
            };
            return names[type] || type;
        }

        formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        getApiKey() {
            return $('meta[name="api-key"]').attr('content') || '';
        }

        showSuccess(message) {
            if (window.Notifications) {
                window.Notifications.show('success', message);
            } else {
                alert(message);
            }
        }

        showError(message) {
            if (window.Notifications) {
                window.Notifications.show('error', message);
            } else {
                alert('Erro: ' + message);
            }
        }
    }

    // ==========================================================================
    // Inicialização Global
    // ==========================================================================

    $(document).ready(function() {
        // Inicializar apenas se estamos na página de operações em lote
        if ($('#bulk-operations-page').length > 0) {
            window.BulkOperationsController = new BulkOperationsController();
        }
    });

})();