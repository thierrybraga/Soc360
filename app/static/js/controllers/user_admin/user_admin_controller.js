/**
 * user_admin_controller.js - Controlador de Administração de Usuários
 * Versão: 1.0 - Criado em Janeiro 2025
 * Gerenciamento completo de usuários via API
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
                users: '/users',
                user: '/users/{id}',
                roles: '/users/roles',
                userRoles: '/users/{id}/roles'
            }
        },
        pagination: {
            defaultPageSize: 20,
            maxPageSize: 100
        },
        debounce: {
            search: 300,
            form: 500
        }
    };

    // ==========================================================================
    // Classe Principal - UserAdminController
    // ==========================================================================

    class UserAdminController {
        constructor() {
            this.currentPage = 1;
            this.pageSize = CONFIG.pagination.defaultPageSize;
            this.searchQuery = '';
            this.selectedUsers = new Set();
            this.isLoading = false;

            this.init();
        }

        // ======================================================================
        // Inicialização
        // ======================================================================

        init() {
            this.bindEvents();
            this.loadUsers();
            this.loadRoles();
        }

        bindEvents() {
            // Botões principais
            $('#btn-refresh-users').on('click', () => this.loadUsers());
            $('#btn-create-user').on('click', () => this.showCreateUserModal());
            $('#btn-bulk-delete').on('click', () => this.showBulkDeleteConfirm());

            // Busca
            $('#user-search').on('input', this.debounce(() => {
                this.searchQuery = $('#user-search').val().trim();
                this.currentPage = 1;
                this.loadUsers();
            }, CONFIG.debounce.search));

            // Filtros
            $('#user-role-filter').on('change', () => {
                this.currentPage = 1;
                this.loadUsers();
            });

            $('#user-status-filter').on('change', () => {
                this.currentPage = 1;
                this.loadUsers();
            });

            // Paginação
            $('#users-table').on('click', '.page-link', (e) => {
                e.preventDefault();
                const page = $(e.target).data('page');
                if (page) {
                    this.currentPage = page;
                    this.loadUsers();
                }
            });

            // Seleção de usuários
            $('#users-table').on('change', '.user-checkbox', (e) => {
                const userId = $(e.target).data('user-id');
                if (e.target.checked) {
                    this.selectedUsers.add(userId);
                } else {
                    this.selectedUsers.delete(userId);
                }
                this.updateBulkActions();
            });

            $('#select-all-users').on('change', (e) => {
                const isChecked = e.target.checked;
                $('.user-checkbox').prop('checked', isChecked);
                this.selectedUsers.clear();
                if (isChecked) {
                    $('.user-checkbox').each((i, checkbox) => {
                        this.selectedUsers.add($(checkbox).data('user-id'));
                    });
                }
                this.updateBulkActions();
            });

            // Ações individuais
            $('#users-table').on('click', '.btn-edit-user', (e) => {
                const userId = $(e.target).data('user-id');
                this.showEditUserModal(userId);
            });

            $('#users-table').on('click', '.btn-delete-user', (e) => {
                const userId = $(e.target).data('user-id');
                this.showDeleteUserConfirm(userId);
            });

            $('#users-table').on('click', '.btn-toggle-status', (e) => {
                const userId = $(e.target).data('user-id');
                this.toggleUserStatus(userId);
            });

            // Modais
            $('#userModal').on('hidden.bs.modal', () => {
                this.resetUserForm();
            });

            $('#userForm').on('submit', (e) => {
                e.preventDefault();
                this.saveUser();
            });
        }

        // ======================================================================
        // Carregamento de Dados
        // ======================================================================

        async loadUsers() {
            if (this.isLoading) return;

            this.isLoading = true;
            this.showLoading();

            try {
                const params = new URLSearchParams({
                    page: this.currentPage,
                    per_page: this.pageSize,
                    search: this.searchQuery,
                    role: $('#user-role-filter').val(),
                    status: $('#user-status-filter').val()
                });

                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.users}?${params}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                this.renderUsers(data.users || []);
                this.renderPagination(data.pagination || {});

            } catch (error) {
                console.error('Erro ao carregar usuários:', error);
                this.showError('Erro ao carregar usuários: ' + error.message);
            } finally {
                this.isLoading = false;
                this.hideLoading();
            }
        }

        async loadRoles() {
            try {
                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.roles}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (response.ok) {
                    const roles = await response.json();
                    this.renderRoleOptions(roles);
                }
            } catch (error) {
                console.error('Erro ao carregar roles:', error);
            }
        }

        // ======================================================================
        // Renderização
        // ======================================================================

        renderUsers(users) {
            const tbody = $('#users-table tbody');
            tbody.empty();

            if (users.length === 0) {
                tbody.append(`
                    <tr>
                        <td colspan="7" class="text-center text-muted py-4">
                            <i class="fas fa-users"></i> Nenhum usuário encontrado
                        </td>
                    </tr>
                `);
                return;
            }

            users.forEach(user => {
                const statusBadge = this.getStatusBadge(user.is_active);
                const roleBadges = this.getRoleBadges(user.roles || []);
                const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString() : 'Nunca';

                tbody.append(`
                    <tr>
                        <td>
                            <input type="checkbox" class="user-checkbox" data-user-id="${user.id}">
                        </td>
                        <td>
                            <div class="d-flex align-items-center">
                                <div class="avatar-circle me-2">
                                    ${user.username.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <div class="fw-bold">${user.username}</div>
                                    <small class="text-muted">${user.email}</small>
                                </div>
                            </div>
                        </td>
                        <td>${roleBadges}</td>
                        <td>${statusBadge}</td>
                        <td>${lastLogin}</td>
                        <td>${new Date(user.created_at).toLocaleDateString()}</td>
                        <td>
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-outline-primary btn-edit-user"
                                        data-user-id="${user.id}"
                                        title="Editar usuário">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-warning btn-toggle-status"
                                        data-user-id="${user.id}"
                                        title="${user.is_active ? 'Desativar' : 'Ativar'} usuário">
                                    <i class="fas fa-${user.is_active ? 'ban' : 'check'}"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger btn-delete-user"
                                        data-user-id="${user.id}"
                                        title="Excluir usuário">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `);
            });
        }

        renderPagination(pagination) {
            const nav = $('#users-pagination');
            nav.empty();

            if (!pagination || pagination.total_pages <= 1) return;

            const { current_page, total_pages, has_prev, has_next } = pagination;

            let html = '<nav><ul class="pagination justify-content-center">';

            // Anterior
            html += `<li class="page-item ${!has_prev ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${current_page - 1}">Anterior</a>
            </li>`;

            // Páginas
            const startPage = Math.max(1, current_page - 2);
            const endPage = Math.min(total_pages, current_page + 2);

            if (startPage > 1) {
                html += `<li class="page-item">
                    <a class="page-link" href="#" data-page="1">1</a>
                </li>`;
                if (startPage > 2) {
                    html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
                }
            }

            for (let i = startPage; i <= endPage; i++) {
                html += `<li class="page-item ${i === current_page ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>`;
            }

            if (endPage < total_pages) {
                if (endPage < total_pages - 1) {
                    html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
                }
                html += `<li class="page-item">
                    <a class="page-link" href="#" data-page="${total_pages}">${total_pages}</a>
                </li>`;
            }

            // Próximo
            html += `<li class="page-item ${!has_next ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${current_page + 1}">Próximo</a>
            </li>`;

            html += '</ul></nav>';
            nav.html(html);
        }

        renderRoleOptions(roles) {
            const select = $('#user-role-filter');
            select.empty();
            select.append('<option value="">Todos os roles</option>');

            roles.forEach(role => {
                select.append(`<option value="${role.name}">${role.name}</option>`);
            });
        }

        // ======================================================================
        // Ações do Usuário
        // ======================================================================

        showCreateUserModal() {
            $('#userModalLabel').text('Criar Novo Usuário');
            $('#user-id').val('');
            $('#userModal').modal('show');
        }

        async showEditUserModal(userId) {
            try {
                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.user.replace('{id}', userId)}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const user = await response.json();

                $('#userModalLabel').text('Editar Usuário');
                $('#user-id').val(user.id);
                $('#user-username').val(user.username);
                $('#user-email').val(user.email);
                $('#user-first-name').val(user.first_name || '');
                $('#user-last-name').val(user.last_name || '');
                $('#user-is-active').prop('checked', user.is_active);

                // Roles
                $('#user-roles').val(user.roles ? user.roles.map(r => r.name) : []);

                $('#userModal').modal('show');

            } catch (error) {
                console.error('Erro ao carregar usuário:', error);
                this.showError('Erro ao carregar dados do usuário: ' + error.message);
            }
        }

        async saveUser() {
            const userId = $('#user-id').val();
            const isEdit = !!userId;

            const userData = {
                username: $('#user-username').val().trim(),
                email: $('#user-email').val().trim(),
                first_name: $('#user-first-name').val().trim(),
                last_name: $('#user-last-name').val().trim(),
                is_active: $('#user-is-active').is(':checked'),
                roles: $('#user-roles').val() || []
            };

            if (isEdit) {
                userData.password = $('#user-password').val() || undefined; // Só atualiza se fornecido
            } else {
                userData.password = $('#user-password').val();
            }

            // Validações
            if (!userData.username || !userData.email) {
                this.showError('Nome de usuário e email são obrigatórios');
                return;
            }

            if (!isEdit && !userData.password) {
                this.showError('Senha é obrigatória para novos usuários');
                return;
            }

            try {
                const url = isEdit
                    ? `${CONFIG.api.baseUrl}${CONFIG.api.endpoints.user.replace('{id}', userId)}`
                    : `${CONFIG.api.baseUrl}${CONFIG.api.endpoints.users}`;

                const response = await fetch(url, {
                    method: isEdit ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    },
                    body: JSON.stringify(userData)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
                }

                $('#userModal').modal('hide');
                this.showSuccess(`Usuário ${isEdit ? 'atualizado' : 'criado'} com sucesso`);
                this.loadUsers();

            } catch (error) {
                console.error('Erro ao salvar usuário:', error);
                this.showError('Erro ao salvar usuário: ' + error.message);
            }
        }

        async toggleUserStatus(userId) {
            try {
                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.user.replace('{id}', userId)}/toggle-status`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.showSuccess('Status do usuário alterado com sucesso');
                this.loadUsers();

            } catch (error) {
                console.error('Erro ao alterar status do usuário:', error);
                this.showError('Erro ao alterar status: ' + error.message);
            }
        }

        showDeleteUserConfirm(userId) {
            if (confirm('Tem certeza que deseja excluir este usuário? Esta ação não pode ser desfeita.')) {
                this.deleteUser(userId);
            }
        }

        async deleteUser(userId) {
            try {
                const response = await fetch(`${CONFIG.api.baseUrl}${CONFIG.api.endpoints.user.replace('{id}', userId)}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.showSuccess('Usuário excluído com sucesso');
                this.loadUsers();

            } catch (error) {
                console.error('Erro ao excluir usuário:', error);
                this.showError('Erro ao excluir usuário: ' + error.message);
            }
        }

        showBulkDeleteConfirm() {
            if (this.selectedUsers.size === 0) {
                this.showWarning('Nenhum usuário selecionado');
                return;
            }

            const count = this.selectedUsers.size;
            if (confirm(`Tem certeza que deseja excluir ${count} usuário(s)? Esta ação não pode ser desfeita.`)) {
                this.bulkDeleteUsers();
            }
        }

        async bulkDeleteUsers() {
            try {
                const response = await fetch(`${CONFIG.api.baseUrl}/users/bulk-delete`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': this.getApiKey()
                    },
                    body: JSON.stringify({ user_ids: Array.from(this.selectedUsers) })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.showSuccess(`${this.selectedUsers.size} usuário(s) excluído(s) com sucesso`);
                this.selectedUsers.clear();
                this.updateBulkActions();
                this.loadUsers();

            } catch (error) {
                console.error('Erro ao excluir usuários em lote:', error);
                this.showError('Erro ao excluir usuários: ' + error.message);
            }
        }

        // ======================================================================
        // Utilitários
        // ======================================================================

        updateBulkActions() {
            const hasSelection = this.selectedUsers.size > 0;
            $('#btn-bulk-delete').prop('disabled', !hasSelection);

            if (hasSelection) {
                $('#bulk-actions').show();
                $('#selected-count').text(this.selectedUsers.size);
            } else {
                $('#bulk-actions').hide();
            }
        }

        resetUserForm() {
            $('#userForm')[0].reset();
            $('#user-id').val('');
        }

        getStatusBadge(isActive) {
            return isActive
                ? '<span class="badge bg-success">Ativo</span>'
                : '<span class="badge bg-danger">Inativo</span>';
        }

        getRoleBadges(roles) {
            if (!roles || roles.length === 0) return '<span class="text-muted">Nenhum</span>';

            return roles.map(role => {
                const color = this.getRoleColor(role.name);
                return `<span class="badge bg-${color} me-1">${role.name}</span>`;
            }).join('');
        }

        getRoleColor(roleName) {
            const colors = {
                'admin': 'danger',
                'manager': 'warning',
                'user': 'primary',
                'viewer': 'info'
            };
            return colors[roleName] || 'secondary';
        }

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
            $('#users-loading').show();
        }

        hideLoading() {
            $('#users-loading').hide();
        }

        showSuccess(message) {
            // Usar o sistema de notificações existente
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

        showWarning(message) {
            if (window.Notifications) {
                window.Notifications.show('warning', message);
            } else {
                alert('Aviso: ' + message);
            }
        }
    }

    // ==========================================================================
    // Inicialização Global
    // ==========================================================================

    $(document).ready(function() {
        // Inicializar apenas se estamos na página de administração de usuários
        if ($('#users-admin-page').length > 0) {
            window.UserAdminController = new UserAdminController();
        }
    });

})();