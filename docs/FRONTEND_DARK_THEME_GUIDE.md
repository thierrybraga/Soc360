# Open-Monitor - Guia do Tema Escuro Aprimorado

## Visão Geral

Este guia documenta o novo tema escuro consistente e aprimorado do Open-Monitor, com melhorias significativas em UI/UX.

## Arquivos do Novo Tema

| Arquivo | Descrição |
|---------|-----------|
| `app/static/css/dark-theme-enhanced.css` | Tema escuro completo e otimizado |
| `app/static/css/variables.css` | Variáveis CSS existentes (mantido) |

## Principais Melhorias

### 1. Cores do Tema Escuro

#### Backgrounds (Mais Profundos)
```css
--bg-primary:   #0a0f1a;    /* Mais escuro para melhor contraste */
--bg-secondary: #111827;    /* Nível intermediário */
--bg-tertiary:  #1f2937;    /* Elementos elevados */
--bg-card:      rgba(17, 24, 39, 0.85);  /* Cards com transparência */
```

#### Texto (Melhor Legibilidade)
```css
--text-primary:   #f9fafb;    /* Quase branco */
--text-secondary: #e5e7eb;    /* Cinza claro */
--text-muted:     #9ca3af;    /* Cinza médio */
--text-subtle:    #6b7280;    /* Cinza escuro */
```

#### Cores de Severidade (Mais Vibrantes)
```css
--critical: #f87171;  /* Vermelho vibrante */
--high:     #fb923c;  /* Laranja vibrante */
--medium:   #facc15;  /* Amarelo vibrante */
--low:      #4ade80;  /* Verde vibrante */
```

### 2. Componentes UI Aprimorados

#### Cards
- Efeito glassmorphism melhorado
- Hover com elevação e glow
- Borda sutil com gradiente no topo
- Sombras mais profundas para dark mode

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), 0 0 30px rgba(59, 130, 246, 0.1);
}
```

#### Botões
- Gradientes suaves
- Efeito de brilho no hover
- Estados visuais claros
- Tamanhos consistentes

```css
.btn-primary {
  background: linear-gradient(135deg, var(--primary-600), var(--primary-500));
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
}
```

#### Formulários
- Inputs com fundo escuro
- Foco com anel de cor azul
- Placeholders visíveis mas sutis
- Estados de erro/sucesso claros

```css
.form-control {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.form-control:focus {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}
```

#### Tabelas
- Header com fundo distinto
- Hover suave nas linhas
- Bordas sutis
- Texto bem contrastado

```css
.table thead th {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}
```

### 3. Efeitos Visuais

#### Glassmorphism
```css
--glass-bg: rgba(17, 24, 39, 0.75);
--glass-border: rgba(75, 85, 99, 0.2);
--glass-blur: blur(16px) saturate(180%);
```

#### Sombras (Otimizadas para Dark Mode)
```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow:    0 4px 6px -1px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
--shadow-glow: 0 0 20px rgba(59, 130, 246, 0.3);
```

#### Scrollbar Personalizada
```css
::-webkit-scrollbar {
  width: 10px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
}
```

### 4. Animações Suaves

#### Transições
```css
--transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
```

#### Animações de Entrada
- Cards: Fade + slide up
- Modais: Scale + fade
- Toasts: Slide from right
- Skeleton: Shimmer effect

## Como Usar

### 1. Incluir o CSS no Template

```html
<!-- No arquivo base.html ou template principal -->
<head>
  <!-- CSS existente -->
  <link rel="stylesheet" href="{{ url_for('static', filename='css/variables.css') }}">
  
  <!-- Novo tema escuro aprimorado -->
  <link rel="stylesheet" href="{{ url_for('static', filename='css/dark-theme-enhanced.css') }}">
  
  <!-- Outros CSS específicos -->
  <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
</head>
```

### 2. Estrutura HTML Recomendada

#### Card Básico
```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Título do Card</h3>
    <span class="badge badge-high">High</span>
  </div>
  <div class="card-body">
    <p>Conteúdo do card...</p>
  </div>
</div>
```

#### Formulário
```html
<div class="form-group">
  <label class="form-label">Email</label>
  <div class="input-group">
    <i class="input-icon fas fa-envelope"></i>
    <input type="email" class="form-control" placeholder="seu@email.com">
  </div>
</div>
```

#### Tabela
```html
<div class="table-container">
  <table class="table">
    <thead>
      <tr>
        <th>ID</th>
        <th>Nome</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>Item 1</td>
        <td><span class="badge badge-success">Ativo</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

#### Botões
```html
<button class="btn btn-primary">
  <i class="fas fa-save"></i>
  Salvar
</button>

<button class="btn btn-secondary">Cancelar</button>
<button class="btn btn-danger">Excluir</button>
<button class="btn btn-ghost">Voltar</button>
```

### 3. Classes Utilitárias

```html
<!-- Texto gradiente -->
<h1 class="text-gradient">Título Destacado</h1>

<!-- Efeito glass -->
<div class="glass">Conteúdo com blur</div>

<!-- Divisor -->
<hr class="divider">

<!-- Cores de texto -->
<p class="text-success">Sucesso!</p>
<p class="text-warning">Atenção!</p>
<p class="text-danger">Erro!</p>
```

## Integração com CSS Existente

### Ordem de Carregamento Recomendada

1. `reset.css` - Reset de estilos
2. `variables.css` - Variáveis base
3. **`dark-theme-enhanced.css`** - Tema escuro aprimorado
4. `base.css` - Estilos base
5. Componentes específicos

### Compatibilidade

O novo tema é **compatível** com os arquivos CSS existentes:
- Mantém as mesmas variáveis CSS
- Sobrescreve apenas quando necessário
- Classes existentes continuam funcionando
- Novas classes adicionam funcionalidades

## Melhorias de Acessibilidade

### 1. Contraste
- Todos os textos possuem contraste WCAG AA ou superior
- Cores de severidade distintas para daltônicos
- Foco visível em todos os elementos interativos

### 2. Navegação por Teclado
```css
:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: 2px;
}
```

### 3. Redução de Movimento
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 4. Alto Contraste
```css
@media (prefers-contrast: high) {
  :root {
    --border-color: rgba(255, 255, 255, 0.5);
    --text-primary: #ffffff;
  }
}
```

## Páginas para Atualizar

### Prioridade Alta
1. [ ] Dashboard principal (`templates/dashboard.html`)
2. [ ] Lista de vulnerabilidades (`templates/vulnerabilities/`)
3. [ ] Página de assets (`templates/assets/`)
4. [ ] Relatórios (`templates/reports/`)

### Prioridade Média
5. [ ] Configurações (`templates/settings/`)
6. [ ] Perfil do usuário (`templates/account/`)
7. [ ] Admin (`templates/admin/`)

### Prioridade Baixa
8. [ ] Páginas de erro (`templates/errors/`)
9. [ ] Autenticação (`templates/auth/`)

## Checklist de Implementação

### Por Página
- [ ] Incluir `dark-theme-enhanced.css`
- [ ] Atualizar estrutura de cards
- [ ] Verificar contraste de textos
- [ ] Testar botões e formulários
- [ ] Validar tabelas
- [ ] Verificar modais (se houver)
- [ ] Testar responsividade
- [ ] Validar acessibilidade (teclado)

### Testes Recomendados
- [ ] Navegação por teclado completa
- [ ] Teste com leitor de tela
- [ ] Verificação de contraste (WCAG)
- [ ] Teste em diferentes tamanhos de tela
- [ ] Teste de performance ( Lighthouse )

## Exemplos de Antes/Depois

### Antes (Tema Escuro Antigo)
```css
.card {
  background: #1e293b;
  border: 1px solid #334155;
}
```

### Depois (Tema Escuro Aprimorado)
```css
.card {
  background: rgba(17, 24, 39, 0.85);
  border: 1px solid rgba(75, 85, 99, 0.4);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  transition: all 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 
              0 0 30px rgba(59, 130, 246, 0.1);
}
```

## Suporte e Debugging

### Ferramentas Recomendadas
- **Chrome DevTools**: Inspeção de cores e contraste
- **WAVE**: Avaliação de acessibilidade
- **Lighthouse**: Performance e acessibilidade
- ** axe DevTools**: Testes de acessibilidade automatizados

### Problemas Comuns

#### 1. Cores não aplicadas
**Solução**: Verificar ordem de carregamento do CSS

#### 2. Contraste insuficiente
**Solução**: Usar ferramenta de contraste do DevTools

#### 3. Animações lentas
**Solução**: Reduzir duração ou usar `prefers-reduced-motion`

## Referências

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Material Design Dark Theme](https://material.io/design/color/dark-theme.html)
- [Apple Human Interface Guidelines - Dark Mode](https://developer.apple.com/design/human-interface-guidelines/macos/overview/themes/)

---

*Última atualização: $(date)*
*Versão: 1.0*
*Autor: Frontend Team*