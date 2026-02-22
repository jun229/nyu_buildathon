# FlipKit Design System

**Theme**: Brutalist Resale Market — Raw, energetic, trustworthy, with a hint of controlled chaos

The aesthetic combines brutalist design principles (heavy borders, stark contrasts, geometric shapes) with the energy of a garage sale (warm accents, playful rotations, handwritten elements). This creates a platform that feels both professional and human.

---

## Color Palette

### Primary Colors
```css
--primary: #FF6B35;        /* Sunset Orange - CTAs, active states, highlights */
--primary-dark: #E55A2B;   /* Darker orange for hover states */
--primary-light: #FF8C61;  /* Lighter orange for backgrounds */
```

### Secondary Colors
```css
--secondary: #004E89;      /* Deep Blue - Trust, information, marketplace */
--secondary-dark: #003D6B; /* Darker blue for depth */
--secondary-light: #1A6BA8; /* Lighter blue for accents */
```

### Accent Colors
```css
--accent-green: #06D6A0;   /* Success, sold, agent completion */
--accent-yellow: #FFD23F;  /* Warnings, pending, attention */
--accent-red: #EF476F;     /* Errors, urgent, declined offers */
--accent-purple: #9B5DE5;  /* Premium features, special offers */
```

### Neutral Colors
```css
--black: #1A1A1D;          /* Primary text, borders */
--gray-900: #2D2D30;       /* Secondary text */
--gray-700: #4A4A4F;       /* Muted text */
--gray-500: #7A7A82;       /* Disabled text */
--gray-300: #C4C4CC;       /* Borders, dividers */
--gray-100: #E8E8ED;       /* Subtle backgrounds */
--gray-50: #F5F5F7;        /* Page backgrounds */
--white: #FFFFFF;          /* Cards, primary backgrounds */
```

### Semantic Colors
```css
--success: var(--accent-green);
--warning: var(--accent-yellow);
--error: var(--accent-red);
--info: var(--secondary);
```

---

## Typography

### Font Families
```css
--font-display: 'Space Grotesk', system-ui, sans-serif;  /* Headings, bold statements */
--font-body: 'Inter', system-ui, sans-serif;             /* Body text, descriptions */
--font-mono: 'JetBrains Mono', 'Courier New', monospace; /* Prices, codes, status */
```

### Font Sizes (Mobile-first, then desktop)
```css
--text-xs: 0.75rem;      /* 12px - Labels, captions */
--text-sm: 0.875rem;     /* 14px - Small body text */
--text-base: 1rem;       /* 16px - Body text */
--text-lg: 1.125rem;     /* 18px - Large body */
--text-xl: 1.25rem;      /* 20px - Small headings */
--text-2xl: 1.5rem;      /* 24px - Headings */
--text-3xl: 1.875rem;    /* 30px - Large headings */
--text-4xl: 2.25rem;     /* 36px - Hero headings */
--text-5xl: 3rem;        /* 48px - Display */
--text-6xl: 3.75rem;     /* 60px - Large display */
```

### Font Weights
```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-extrabold: 800;
```

### Line Heights
```css
--leading-tight: 1.2;    /* Headings */
--leading-snug: 1.375;   /* Subheadings */
--leading-normal: 1.5;   /* Body text */
--leading-relaxed: 1.625; /* Comfortable reading */
```

### Letter Spacing
```css
--tracking-tight: -0.02em;   /* Large headings */
--tracking-normal: 0;        /* Body text */
--tracking-wide: 0.025em;    /* Small caps, labels */
--tracking-wider: 0.05em;    /* Spaced headings */
```

---

## Spacing Scale

Based on 4px grid system:

```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
--space-24: 6rem;     /* 96px */
```

**Usage:**
- Tight spacing (1-2): Related items, compact layouts
- Medium spacing (4-6): Standard component padding, gaps
- Loose spacing (8-12): Section spacing, visual breathing room
- Extra loose (16-24): Page-level spacing, hero sections

---

## Border & Shadows

### Border Widths
```css
--border-thin: 1px;
--border-default: 2px;   /* Most components */
--border-thick: 3px;     /* Emphasis, hover states */
--border-chunky: 4px;    /* CTAs, important elements */
```

### Border Radius
```css
--radius-sm: 4px;        /* Small elements, tags */
--radius-md: 8px;        /* Cards, buttons */
--radius-lg: 12px;       /* Large cards, modals */
--radius-xl: 16px;       /* Hero elements */
--radius-full: 9999px;   /* Pills, avatars */
```

### Shadows (Brutalist-inspired)
```css
--shadow-brutal-sm: 3px 3px 0px var(--black);
--shadow-brutal: 5px 5px 0px var(--black);
--shadow-brutal-lg: 8px 8px 0px var(--black);
--shadow-brutal-color: 5px 5px 0px var(--primary);

--shadow-soft: 0 2px 8px rgba(0, 0, 0, 0.08);
--shadow-medium: 0 4px 16px rgba(0, 0, 0, 0.12);
--shadow-large: 0 8px 32px rgba(0, 0, 0, 0.16);
```

---

## Animation & Transitions

### Timing Functions
```css
--ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
--ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);
--ease-accelerate: cubic-bezier(0.4, 0.0, 1, 1);
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### Durations
```css
--duration-instant: 100ms;   /* Immediate feedback */
--duration-quick: 150ms;     /* Hovers, simple transitions */
--duration-normal: 250ms;    /* Standard transitions */
--duration-slow: 400ms;      /* Complex transitions */
--duration-slower: 600ms;    /* Page transitions, modals */
```

### Standard Transitions
```css
--transition-all: all var(--duration-quick) var(--ease-standard);
--transition-colors: color, background-color, border-color var(--duration-quick) var(--ease-standard);
--transition-transform: transform var(--duration-normal) var(--ease-standard);
--transition-shadow: box-shadow var(--duration-quick) var(--ease-standard);
```

---

## Component Patterns

### Buttons

**Primary Button (CTA)**
```css
- Background: var(--primary)
- Text: var(--white)
- Border: 2px solid var(--black)
- Shadow: var(--shadow-brutal)
- Padding: var(--space-3) var(--space-6)
- Font: var(--font-display), var(--font-semibold)
- Border radius: var(--radius-md)
- Hover: Translate up 2px, shadow increases
- Active: Translate down 1px, shadow decreases
```

**Secondary Button**
```css
- Background: var(--white)
- Text: var(--black)
- Border: 2px solid var(--black)
- Shadow: var(--shadow-brutal)
- Hover: Background to var(--gray-50)
```

**Ghost Button**
```css
- Background: transparent
- Text: var(--gray-900)
- Border: none
- Hover: Background to var(--gray-100)
```

### Cards

**Standard Card**
```css
- Background: var(--white)
- Border: 2px solid var(--black)
- Border radius: var(--radius-lg)
- Shadow: var(--shadow-brutal)
- Padding: var(--space-6)
- Slight rotation: rotate(-0.5deg) for variety
- Hover: Translate -2px -2px, shadow increases
```

**Agent Activity Card**
```css
- Background: var(--gray-50)
- Border: 2px solid var(--gray-300)
- Border-left: 4px solid var(--primary) (activity indicator)
- Icon with pulsing animation for active states
```

**Price Comparison Card**
```css
- Background: var(--white)
- Border: 2px solid var(--secondary)
- Price in var(--font-mono), var(--text-2xl)
- Green highlight for best offer
- Subtle yellow tag for "recommended"
```

### Forms

**Input Fields**
```css
- Background: var(--white)
- Border: 2px solid var(--gray-300)
- Border radius: var(--radius-md)
- Padding: var(--space-3) var(--space-4)
- Focus: Border color to var(--primary), shadow-brutal-sm
- Error: Border color to var(--error)
```

**File Upload (Image Upload)**
```css
- Dashed border: 2px dashed var(--gray-300)
- Border radius: var(--radius-lg)
- Background: var(--gray-50) with subtle pattern
- Drag-over state: Background var(--primary-light), border solid
- Icon size: 48px
```

### Status Indicators

**Badge/Tag**
```css
- Small: 20px height
- Border radius: var(--radius-sm)
- Font: var(--text-xs), var(--font-medium)
- Border: 1px solid
- Slight rotation for visual interest

Colors by status:
- Success: Green background, dark green border
- Warning: Yellow background, dark yellow border
- Error: Red background, dark red border
- Info: Blue background, dark blue border
```

**Progress Bar**
```css
- Height: 8px
- Background: var(--gray-200)
- Border: 2px solid var(--black)
- Fill: var(--primary) with animated gradient
- Border radius: var(--radius-full)
```

### Navigation

**Top Navigation**
```css
- Background: var(--white)
- Border-bottom: 3px solid var(--black)
- Height: 64px
- Sticky position
- Shadow on scroll: var(--shadow-medium)
```

**Tab Navigation**
```css
- Border-bottom: 2px solid var(--gray-300)
- Active tab: Border-bottom 3px solid var(--primary)
- Font: var(--font-display), var(--font-semibold)
- Hover: Background var(--gray-100)
```

---

## Iconography

**Icon Style**: Use Lucide React for consistency
**Icon Sizes**: 16px, 20px, 24px, 32px, 48px
**Icon Weight**: 2px stroke width (medium weight)

**Common Icons:**
- Camera: Image upload
- TrendingUp: Price increase
- Phone: Calling stores
- Calendar: Appointments
- Check: Success/completion
- AlertCircle: Warnings
- Zap: Active agents
- Package: Listings

---

## Layout Grid

**Container Max Widths:**
```css
--container-sm: 640px;
--container-md: 768px;
--container-lg: 1024px;
--container-xl: 1280px;
--container-2xl: 1536px;
```

**Grid Columns:**
- Mobile: 4 columns
- Tablet: 8 columns
- Desktop: 12 columns

**Gutters:**
- Mobile: 16px
- Tablet: 24px
- Desktop: 32px

---

## Responsive Breakpoints

```css
--screen-sm: 640px;
--screen-md: 768px;
--screen-lg: 1024px;
--screen-xl: 1280px;
--screen-2xl: 1536px;
```

---

## Animation Patterns

### Loading States
- **Skeleton**: Animated gradient from gray-100 to gray-200
- **Spinner**: Rotating circle with primary color
- **Pulse**: Subtle scale animation (0.95 → 1.0)

### Success States
- **Checkmark**: Draw animation with bounce
- **Confetti**: Brief particle animation for major milestones
- **Scale Pop**: Quick scale 1.0 → 1.05 → 1.0

### Agent Activity
- **Pulsing Dot**: For active/calling states
- **Typing Indicator**: Three dots bouncing
- **Progress Wave**: Animated gradient moving across bar

---

## Copy Voice & Tone

**Personality**: Helpful friend who knows the hustle. Knowledgeable but not preachy. Celebrates wins.

**Examples:**

❌ "Processing your request"
✅ "Finding you the best deals..."

❌ "Item uploaded successfully"
✅ "Got it! Let's find buyers 🎯"

❌ "Error: Unable to contact store"
✅ "Hmm, couldn't reach that shop - they might be closed"

❌ "3 offers available"
✅ "You've got 3 offers! Here's the best one ⭐"

**Agent Activity Feed Examples:**
- "Calling Joe's Pawn Shop..." ☎️
- "Listed on eBay - 47 people watching" 👀
- "Found a buyer willing to pay $240!" 💰
- "Scheduled appointment for tomorrow at 2pm" 📅

---

## Accessibility

**Color Contrast:**
- Text on white: Minimum 4.5:1 ratio
- Large text (18px+): Minimum 3:1 ratio
- Interactive elements: 3:1 ratio against adjacent colors

**Focus States:**
- 2px solid outline in var(--primary)
- 2px offset
- Never remove focus indicators

**Motion:**
- Respect `prefers-reduced-motion`
- Provide alternative static states
- Keep animations under 600ms

**Touch Targets:**
- Minimum 44x44px for interactive elements
- Adequate spacing (8px minimum) between targets

---

## Implementation Notes

### Tailwind Config

Map these tokens to Tailwind:
```javascript
colors: {
  primary: { DEFAULT: '#FF6B35', dark: '#E55A2B', light: '#FF8C61' },
  secondary: { DEFAULT: '#004E89', dark: '#003D6B', light: '#1A6BA8' },
  accent: {
    green: '#06D6A0',
    yellow: '#FFD23F',
    red: '#EF476F',
    purple: '#9B5DE5'
  }
}
```

### Custom Classes

Create utility classes for common patterns:
```css
.shadow-brutal { box-shadow: 5px 5px 0px theme('colors.black'); }
.rotate-slight { transform: rotate(-0.5deg); }
.border-chunky { border-width: 3px; }
```

### Component Library Priority

Build in this order:
1. Button (3 variants)
2. Card (2 variants)
3. Input + FileUpload
4. Badge/Tag
5. Progress Bar
6. Agent Activity Feed
7. Price Comparison Card
8. Appointment Scheduler

---

## Examples to Avoid

**Generic SaaS Aesthetics:**
- ❌ Soft gradients everywhere
- ❌ Rounded corners on everything (16px+)
- ❌ Pastel color schemes
- ❌ Minimal contrast
- ❌ Tons of whitespace with no energy
- ❌ Generic icon libraries without personality

**What Makes This Different:**
- ✅ Hard borders and shadows (brutalist)
- ✅ Bold, contrasting colors
- ✅ Slight rotations and asymmetry (controlled chaos)
- ✅ Personality in copy and micro-interactions
- ✅ Energy without sacrificing clarity

---

**Usage:** Reference this document when building any new component. Claude Code should use these exact values for colors, spacing, typography, and patterns to maintain consistency across the entire platform.