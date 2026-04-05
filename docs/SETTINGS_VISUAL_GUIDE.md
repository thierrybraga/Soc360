# 🎨 Guia Visual de Componentes - Settings Page

## Estrutura de Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ⚙️ Configurações                              (Gradiente)│
│  │ Gerencie informações de perfil, credenciais e API...    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SECURITY ALERT (se needed)                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ⚠️ AVISO: Credenciais padrão detectadas!                ││
│  │    Altere sua senha imediatamente em "Segurança".       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  MAIN CONTENT AREA                                           │
│                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ PROFILE CARD         │  │ SECURITY CARD        │        │
│  ├──────────────────────┤  ├──────────────────────┤        │
│  │ 👤 Informações       │  │ 🔒 Segurança         │        │
│  │                      │  │                      │        │
│  │ Label: Username      │  │ Label: Senha Atual   │        │
│  │ [Input Field]        │  │ [Input Field] [👁️]   │        │
│  │ Hint: Seu username   │  │                      │        │
│  │                      │  │ Label: Nova Senha    │        │
│  │ Label: Email         │  │ [Input Field] [👁️]   │        │
│  │ [Input Field]        │  │ Hint: Mín 12 chars   │        │
│  │ Hint: Para notif...  │  │                      │        │
│  │                      │  │ Label: Confirmar     │        │
│  │ [💾 Salvar Mudanças]│  │ [Input Field] [👁️]   │        │
│  └──────────────────────┘  │                      │        │
│                             │ [🔑 Atualizar Senha]│        │
│                             └──────────────────────┘        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ API ACCESS CARD                                      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ 💻 Acesso à API                                      │  │
│  │                                                      │  │
│  │ ℹ️ Use sua chave de API para autenticar requisições │  │
│  │                                                      │  │
│  │ [Show API Key Section - if exists]                 │  │
│  │ Label: Sua Chave de API                            │  │
│  │ [Cha ve: sk_... readonly] [📋 Copy]                │  │
│  │ Criada em: 04/04/2026 às 10:00                     │  │
│  │                                                      │  │
│  │ ℹ️ Like usar:                                       │  │
│  │ curl -H "Auth: Bearer YOUR_KEY" https://api...    │  │
│  │                                                      │  │
│  │ [🔄 Regenerar Chave] [🗑️ Revogar Chave]           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SECURITY TIPS CARD                                   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ 💡 Dicas de Segurança                               │  │
│  │                                                      │  │
│  │ ┌──────────────┐  ┌──────────────┐                 │  │
│  │ │ ✅ Senha     │  │ ✅ API Key   │                 │  │
│  │ │ Combine: MAI │  │ Nunca         │                 │  │
│  │ │ UP/low/num/  │  │ compartilhe   │                 │  │
│  │ │ símbos       │  │               │                 │  │
│  │ └──────────────┘  └──────────────┘                 │  │
│  │ ┌──────────────┐  ┌──────────────┐                 │  │
│  │ │ 📊 Monitor   │  │ 🔄 Atualiz.  │                 │  │
│  │ │ Verifique    │  │ Regenere     │                 │  │
│  │ │ atividades   │  │ comreg.      │                 │  │
│  │ │ suspeitas    │  │               │                 │  │
│  │ └──────────────┘  └──────────────┘                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Detalhados

### 📝 Form Group (Padrão para todos os campos)

```
┌─ form-group ──────────────────────┐
│                                   │
│  Label *                   (required indicator)
│  ┌────────────────────────────┐   │
│  │ Placeholder text...        │   │ ← form-input
│  └────────────────────────────┘   │
│  💡 Hint text or helper text      │ ← form-text
│                                   │
└───────────────────────────────────┘

Estados:
  • Normal:    border: 2px solid #94a3b8
  • Focus:     border: 2px solid #3b82f6, box-shadow: glow
  • Error:     border: 2px solid #ef4444, feedback: red text
  • Disabled:  opacity: 0.6, cursor: not-allowed
```

### 🔐 Password Input Group

```
┌─ input-group ─────────────────────────────┐
│                                           │
│  ┌─────────────────────────┐ ┌─────────┐ │
│  │ • • • • • • • •          │ │ 👁️     │ │ ← Toggle Button
│  │ (password input)         │ │ (show)  │ │
│  └─────────────────────────┘ └─────────┘ │
│                                           │
└───────────────────────────────────────────┘

Interação:
  1. Click 👁️ → type="password" → type="text"
  2. Icon changes: fa-eye → fa-eye-slash
  3. ARIA label updates
```

### 📋 API Key Group

```
┌─ input-group ─────────────────────────────────────┐
│                                                   │
│  ┌──────────────────────────────────────┐ ┌────┐ │
│  │ sk_live_4eC39HqLyjWDarhtT657... (ro) │ │📋 │ │
│  │ (font-monospace, readonly)            │ │(C) │ │
│  └──────────────────────────────────────┘ └────┘ │
│                                                   │
│  Criada em: 04/04/2026 às 20:10                 │
│                                                   │
└───────────────────────────────────────────────────┘

On Copy Click:
  ✨ Button feedback: .copied class added
  📋 Content copied to clipboard
  ✓ Checkmark animation
  📱 Toast notification
  Reset after 1.5s
```

### 🎯 Button Styles

```
PRIMARY BUTTON
┌─────────────────────────────┐
│ 💾 Salvar Alterações        │
│                             │
│ bg: linear-gradient(135deg, #3b82f6, #1e40af)
│ color: white                │
│ shadow: 0 4px 12px rgba    │
│ hover: elevated + glow      │
│ active: pressed down + fade │
└─────────────────────────────┘

WARNING BUTTON
┌─────────────────────────────┐
│ 🔑 Atualizar Senha          │
│                             │
│ bg: linear-gradient(135deg, #f59e0b, #b45309)
│ color: white                │
│ shadow: orange glow         │
└─────────────────────────────┘

DANGER BUTTON
┌─────────────────────────────┐
│ 🗑️ Revogar Chave            │
│                             │
│ bg: linear-gradient(135deg, #ef4444, #b91c1c)
│ color: white                │
│ shadow: red glow            │
│ hover: confirmation needed  │
└─────────────────────────────┘

OUTLINE BUTTON
┌─────────────────────────────┐
│ 🔄 Regenerar                │
│                             │
│ bg: transparent             │
│ border: 2px solid #3b82f6   │
│ color: #60a5fa              │
│ hover: bg fill with hover   │
└─────────────────────────────┘
```

### ⚠️ Alert Styles

```
INFO ALERT
┌─ alert alert-info ────────────────────────┐
│ ℹ️  Você não possui uma chave de API ativa│
│    Clique para gerar uma nova chave.      │
│                                           │
│ bg: rgba(59, 130, 246, 0.1)               │
│ border-left: 4px solid #3b82f6            │
│ color: #3b82f6                            │
└───────────────────────────────────────────┘

WARNING ALERT
┌─ alert alert-warning ─────────────────────┐
│ ⚠️  AVISO: Credenciais padrão!            │
│    Conte a senha imediatamente.           │
│                                           │
│ bg: rgba(245, 158, 11, 0.1)               │
│ border-left: 4px solid #f59e0b            │
│ color: #f59e0b                            │
└───────────────────────────────────────────┘
```

---

## Responsividade

### 🖥️ Desktop (>992px)
```
┌────────────────────────────────────┐
│ Header                              │
├────────────────────────────────────┤
│                                    │
│ ┌──────────────┐ ┌──────────────┐ │
│ │  Profile 50% │ │ Security 50% │ │
│ └──────────────┘ └──────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ API Access 100%                │ │
│ └────────────────────────────────┘ │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ Tips 100%                      │ │
│ └────────────────────────────────┘ │
└────────────────────────────────────┘
```

### 📱 Mobile (<576px)
```
┌────────────────────┐
│ Header             │
├────────────────────┤
│ Alert (full width) │
├────────────────────┤
│ Profile 100%       │
├────────────────────┤
│ Security 100%      │
├────────────────────┤
│ API 100%           │
├────────────────────┤
│ Tips 100%          │
└────────────────────┘

Font size: 16px (iOS)
Buttons: Stacked vertically
Inputs: Full width
Gap: 1rem
```

---

## Estados de Validação

### ✅ Válido
```
┌─────────────────────────────────┐
│ Label: Username                 │
│ ┌─────────────────────────────┐ │
│ │ john_doe                    │ │
│ └─────────────────────────────┘ │  ← border: green
│ ✓ Seu nome de usuário público  │
└─────────────────────────────────┘
```

### ❌ Erro
```
┌─────────────────────────────────┐
│ Label: Email *                  │
│ ┌─────────────────────────────┐ │
│ │ invalid-email               │ │
│ └─────────────────────────────┘ │  ← border: red
│ ✗ Formato de email inválido     │
└─────────────────────────────────┘
```

### ⏳ Loading
```
┌─────────────────────────────────┐
│ [💾 Salvando...]                │
│                                 │
│ opacity: 0.6                    │
│ pointer-events: none            │
│ cursor: wait                    │
└─────────────────────────────────┘
```

---

## Paleta de Cores Completa

```
PRIMARY
  50: #eff6ff (muito claro)
  500: #3b82f6 (cores principal)
  900: #1e3a8a (muito escuro)

STATUS COLORS
  Success: #10b981 💚
  Warning: #f59e0b 🟨
  Danger: #ef4444 ❤️
  Info: #3b82f6 💙

BACKGROUNDS
  Primary: #0f172a (page bg)
  Secondary: #1e293b (cards)
  Card Hover: rgba(30, 41, 59, 0.9)
  Input: rgba(15, 23, 42, 0.5)

TEXT
  Primary: #f8fafc (títulos, labels)
  Secondary: #cbd5e1 (subtítulos)
  Muted: #64748b (hints, ajuda)
  Inverse: #ffffff (sobre cor)

BORDERS
  Default: rgba(148, 163, 184, 0.1)
  Hover: rgba(148, 163, 184, 0.2)
  Focus: #3b82f6
  Error: #ef4444
```

---

## Animações

### Entrance
```css
// Page Load
@keyframes slideInDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
Duration: 0.3s
Delay: 0.1s * card-index
```

### Hover
```css
// Card Hover
box-shadow: increased
border-color: lighter blue
transform: translateY(-2px)
Duration: 0.3s
Easing: cubic-bezier(0.4, 0, 0.2, 1)
```

### Click Feedback
```css
// Button Click
transform: scale(0.95) → 1.0
opacity fade
shine animation (left to right)
```

### Copy Feedback
```css
// Copy Success
@keyframes popIn {
  0%: scale(0.5), opacity: 1
  100%: scale(1.2), opacity: 0
}
Duration: 0.3s
```

---

## Breakpoints

```
Mobile:     < 576px   (xs)
Tablet:     576-768px (sm)
Tablet+:    768-992px (md)
Desktop:    992-1200px (lg)
Desktop+:   1200-1400px (xl)
Desktop++:  > 1400px  (xxl)
```

---

## Tipografia

```
Title (h1):        2.5rem, 700 weight, gradient
Subtitle:          1rem, 400 weight, secondary color
Card Title (h2):   1.25rem, 600 weight, primary color
Label:             0.95rem, 500 weight, uppercase
Input/Text:        0.95rem, 400 weight
Hint Text:         0.85rem, 400 weight, italic
Error Message:     0.85rem, 500 weight, error color

Font Family: Inter, -apple-system...
Line-height: 1.5 para body, 1.4 para labels
Letter-spacing: -0.5px para h1, 0.5px para labels
```

---

Este guia visual serve como referência para:
- ✅ Desenvolvimento futuro
- ✅ Manutenção do design
- ✅ Onboarding de novos devs
- ✅ Documentação visual do projeto
