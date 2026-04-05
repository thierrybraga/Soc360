/**
 * notification_settings_controller.js - Controlador de Configurações de Notificação
 * Versão: 1.0 - Criado em Janeiro 2025
 * Gerenciamento de preferências de notificação via API
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
                settings: '/notifications/settings',
                test: '/notifications/test'
            }
        },
        channels: {
            email: 'Email',
            sms: 'SMS',
            webhook: 'Webhook',
            slack: 'Slack',
            teams: 'Microsoft Teams'
        },
        eventTypes: {
            vulnerability_new: 'Nova Vulnerabilidade',
            vulnerability_update: 'Atualização de Vulnerabilidade',
            asset_offline: 'Ativo Offline',
            monitoring_alert: 'Alerta de Monitoramento',
            report_generated: 'Relatório Gerado',
            system_maintenance: 'Manutenção do Sistema'
        }
    };

    // ==========================================================================
    // Classe Principal - NotificationSettingsController
    // ==========================================================================

    class NotificationSettingsController {
        constructor() {
            this.settings = {};
            this.isLoading = false;

            this.init();
        }

        // ======================================================================
        // Inicialização
        // ======================================================================

        init() {
            this.bindEvents();
            this.loadSettings();
        }

        bindEvents() {
            // Botão salvar
            $('#btn-save-settings').on('click', () => this.saveSettings());

            // Botão testar
            $('#btn-test-notification').on('click', () => this.showTestModal());

            // Canais globais
            $('.channel-toggle').on('change', (e) => {
                const channel = $(e.target).data('channel');
                const enabled = e.target.checked;
                this.updateChannelSettings(channel, enabled);
            });

            // Configurações específicas de eventos
            $(document).on('change', '.event-channel-toggle', (e) => {
                const eventType = $(e.target).data('event');
                const channel = $(e.target).data('channel');
                this.updateEventChannelSetting(eventType, channel, e.target.checked);
            });

            // Configurações de webhook
            $('#webhook-url').on('input', this.debounce(() => {
                this.updateWebhookUrl();
            }, 500));

            $('#webhook-secret').on('input', this.debounce(() => {
                this.updateWebhookSecret();
            }, 500));

            // Configurações de Slack
            $('#slack-webhook-url').on('input', this.debounce(() => {
                this.updateSlackWebhookUrl();
            }, 500));

            // Configurações de Teams
            $('#teams-webhook-url').on('input', this.debounce(() => {
                this.updateTeamsWebhookUrl();
            }, 500));

            // Modal de teste
            $('#testNotificationForm').on('submit', (e) => {
                e.preventDefault();
                this.sendTestNotification();
            });

            $('#testNotificationModal').on('hidden.bs.modal', () => {
                this.resetTestForm();
            });
        }

        // ======================================================================
        // Carregamento de Dados
        // ======================================================================

        async loadSettings() {
            if (this.isLoading) return;

            this.isLoading = true;
            this.showLoading();

            try {
                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.settings}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.settings = await response.json();
                this.renderSettings();

            } catch (error) {
                console.error('Erro ao carregar configurações:', error);
                this.showError('Erro ao carregar configurações: ' + error.message);
            } finally {
                this.isLoading = false;
                this.hideLoading();
            }
        }

        // ======================================================================
        // Renderização
        // ======================================================================

        renderSettings() {
            // Canais globais
            Object.keys(CONFIG.channels).forEach(channel => {
                const enabled = this.settings.channels?.[channel]?.enabled || false;
                $(`.channel-toggle[data-channel="${channel}"]`).prop('checked', enabled);

                // Mostrar/ocultar configurações específicas do canal
                this.toggleChannelConfig(channel, enabled);
            });

            // Preencher configurações específicas
            this.renderChannelConfigs();

            // Configurações por evento
            this.renderEventSettings();
        }

        renderChannelConfigs() {
            // Webhook
            $('#webhook-url').val(this.settings.channels?.webhook?.url || '');
            $('#webhook-secret').val(this.settings.channels?.webhook?.secret || '');

            // Slack
            $('#slack-webhook-url').val(this.settings.channels?.slack?.webhook_url || '');

            // Teams
            $('#teams-webhook-url').val(this.settings.channels?.teams?.webhook_url || '');

            // Email (se houver configurações adicionais)
            $('#email-from').val(this.settings.channels?.email?.from_address || '');
        }

        renderEventSettings() {
            const container = $('#event-settings-container');
            container.empty();

            Object.entries(CONFIG.eventTypes).forEach(([eventType, eventName]) => {
                const eventSettings = this.settings.events?.[eventType] || {};
                const html = this.createEventSettingHtml(eventType, eventName, eventSettings);
                container.append(html);
            });
        }

        createEventSettingHtml(eventType, eventName, eventSettings) {
            let html = `
                <div class="event-setting-card mb-3">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="fas fa-bell me-2"></i>${eventName}
                                <small class="text-muted">(${eventType})</small>
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="row">
            `;

            Object.entries(CONFIG.channels).forEach(([channel, channelName]) => {
                const enabled = eventSettings.channels?.[channel] || false;
                html += `
                    <div class="col-md-4 mb-2">
                        <div class="form-check">
                            <input class="form-check-input event-channel-toggle"
                                   type="checkbox"
                                   data-event="${eventType}"
                                   data-channel="${channel}"
                                   id="event-${eventType}-${channel}"
                                   ${enabled ? 'checked' : ''}>
                            <label class="form-check-label" for="event-${eventType}-${channel}">
                                ${channelName}
                            </label>
                        </div>
                    </div>
                `;
            });

            html += `
                            </div>
                        </div>
                    </div>
                </div>
            `;

            return html;
        }

        // ======================================================================
        // Ações do Usuário
        // ======================================================================

        updateChannelSettings(channel, enabled) {
            if (!this.settings.channels) this.settings.channels = {};
            if (!this.settings.channels[channel]) this.settings.channels[channel] = {};

            this.settings.channels[channel].enabled = enabled;
            this.toggleChannelConfig(channel, enabled);
        }

        toggleChannelConfig(channel, enabled) {
            const configSection = $(`#${channel}-config`);
            if (enabled) {
                configSection.show();
            } else {
                configSection.hide();
            }
        }

        updateEventChannelSetting(eventType, channel, enabled) {
            if (!this.settings.events) this.settings.events = {};
            if (!this.settings.events[eventType]) this.settings.events[eventType] = { channels: {} };

            this.settings.events[eventType].channels[channel] = enabled;
        }

        updateWebhookUrl() {
            if (!this.settings.channels?.webhook) this.settings.channels.webhook = {};
            this.settings.channels.webhook.url = $('#webhook-url').val().trim();
        }

        updateWebhookSecret() {
            if (!this.settings.channels?.webhook) this.settings.channels.webhook = {};
            this.settings.channels.webhook.secret = $('#webhook-secret').val().trim();
        }

        updateSlackWebhookUrl() {
            if (!this.settings.channels?.slack) this.settings.channels.slack = {};
            this.settings.channels.slack.webhook_url = $('#slack-webhook-url').val().trim();
        }

        updateTeamsWebhookUrl() {
            if (!this.settings.channels?.teams) this.settings.channels.teams = {};
            this.settings.channels.teams.webhook_url = $('#teams-webhook-url').val().trim();
        }

        async saveSettings() {
            try {
                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.settings}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    },
                    body: JSON.stringify(this.settings)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                this.showSuccess('Configurações salvas com sucesso');

            } catch (error) {
                console.error('Erro ao salvar configurações:', error);
                this.showError('Erro ao salvar configurações: ' + error.message);
            }
        }

        showTestModal() {
            $('#testNotificationModal').modal('show');
        }

        async sendTestNotification() {
            const testData = {
                channel: $('#test-channel').val(),
                message: $('#test-message').val().trim()
            };

            if (!testData.channel || !testData.message) {
                this.showError('Selecione um canal e digite uma mensagem de teste');
                return;
            }

            try {
                $('#btn-send-test').prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Enviando...');

                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.test}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    },
                    body: JSON.stringify(testData)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                $('#testNotificationModal').modal('hide');
                this.showSuccess('Notificação de teste enviada com sucesso');

            } catch (error) {
                console.error('Erro ao enviar notificação de teste:', error);
                this.showError('Erro ao enviar teste: ' + error.message);
            } finally {
                $('#btn-send-test').prop('disabled', false).html('Enviar Teste');
            }
        }

        resetTestForm() {
            $('#testNotificationForm')[0].reset();
        }

        // ======================================================================
        // Utilitários
        // ======================================================================

        getApiKey() {
            return $('meta[name="api-key"]').attr('content') || '';
        }

        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }

        showLoading() {
            $('#settings-loading').show();
        }

        hideLoading() {
            $('#settings-loading').hide();
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
        // Inicializar apenas se estamos na página de configurações de notificação
        if ($('#notification-settings-page').length > 0) {
            window.NotificationSettingsController = new NotificationSettingsController();
        }
    });

})();