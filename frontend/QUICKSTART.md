# FlipKit Design System - Quick Start Guide

This guide helps you quickly implement the FlipKit design system when building new features.

## Installation

```bash
# Install dependencies
npm install class-variance-authority clsx tailwind-merge lucide-react framer-motion

# Or with yarn
yarn add class-variance-authority clsx tailwind-merge lucide-react framer-motion
```

## File Structure

```
/src
  /components
    /ui                  # Base components (Button, Card, Badge, etc.)
    /features            # Feature-specific components
  /lib
    utils.ts             # Utility functions
  /styles
    globals.css          # Global styles and CSS variables
  tailwind.config.ts     # Tailwind configuration
```

## Using the Design System

### 1. Colors

```tsx
// Primary Actions
<Button variant="primary">Sell Item</Button>

// Secondary Actions  
<Button variant="secondary">Learn More</Button>

// Success States
<Badge variant="success">Listed!</Badge>

// Custom colors via Tailwind
<div className="bg-primary text-white">
<div className="bg-accent-green border-accent-green">
```

### 2. Typography

```tsx
// Headings - use font-display
<h1 className="font-display font-bold text-4xl">FlipKit</h1>

// Body text - uses font-body by default
<p className="text-base text-neutral-700">Description here</p>

// Prices and codes - use font-mono
<span className="font-mono text-2xl text-accent-green">$240</span>
```

### 3. Spacing

```tsx
// Use Tailwind's spacing scale (based on 4px)
<div className="p-6">         {/* 24px padding */}
<div className="gap-4">       {/* 16px gap */}
<div className="mt-8 mb-12">  {/* 32px top, 48px bottom */}
```

### 4. Shadows (Brutalist)

```tsx
// Cards and elevated elements
<div className="shadow-brutal">         {/* Standard 5px shadow */}
<div className="shadow-brutal-lg">      {/* Larger 8px shadow */}
<div className="shadow-brutal-color">   {/* Colored shadow with primary */}

// On hover
<div className="shadow-brutal hover:shadow-brutal-hover">
```

### 5. Borders

```tsx
// Standard border
<div className="border-2 border-neutral-black">

// Thicker borders for emphasis
<div className="border-chunky border-primary">  {/* 3px */}
```

### 6. Rotations (Controlled Chaos)

```tsx
// Add subtle rotation to cards for visual interest
<Card rotation="slight">
<Badge rotation="slight">

// Or manually
<div className="rotate-slight">  {/* -0.5deg */}
```

## Common Patterns

### Creating a Card

```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

<Card hover="lift" rotation="slight">
  <CardHeader>
    <CardTitle>Price Comparison</CardTitle>
  </CardHeader>
  <CardContent>
    {/* Your content */}
  </CardContent>
</Card>
```

### Status Badges

```tsx
import { Badge } from '@/components/ui/Badge';
import { Zap } from 'lucide-react';

<Badge variant="success" pulse>
  Active
</Badge>

<Badge variant="warning" icon={<Zap className="w-3 h-3" />}>
  Processing
</Badge>
```

### Buttons with Icons

```tsx
import { Button } from '@/components/ui/Button';
import { Camera, Send } from 'lucide-react';

<Button 
  variant="primary" 
  leftIcon={<Camera className="w-4 h-4" />}
>
  Upload Photo
</Button>

<Button 
  variant="secondary"
  rightIcon={<Send className="w-4 h-4" />}
  isLoading={loading}
>
  Submit
</Button>
```

### Loading States

```tsx
// Skeleton loading
<div className="skeleton h-24 w-full rounded-lg" />

// Spinner
<Button isLoading>Processing</Button>

// Custom loading with animation
<div className="flex gap-1">
  <div className="typing-dot" />
  <div className="typing-dot" />
  <div className="typing-dot" />
</div>
```

### Empty States

```tsx
<div className="p-8 text-center pattern-dots rounded-lg">
  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-neutral-100 flex items-center justify-center">
    <Icon className="w-8 h-8 text-neutral-300" />
  </div>
  <p className="text-neutral-500 font-medium">No items yet</p>
  <p className="text-sm text-neutral-400 mt-1">Upload something to get started</p>
</div>
```

## Animations

### Hover Effects

```tsx
// Lift on hover
<Card hover="lift">

// Custom hover
<div className="transition-all hover:-translate-y-1 hover:shadow-brutal-hover">
```

### Success Animations

```tsx
// Scale pop effect
<div className="animate-scale-pop">
  ✓ Done!
</div>

// Pulsing indicator
<div className="animate-pulse-dot">●</div>
```

## Copy Voice

Follow these examples for consistent tone:

### Agent Activity Messages
✅ "Calling Joe's Pawn Shop..." ☎️
✅ "Found a buyer willing to pay $240!" 💰
✅ "Listed on eBay - 47 people watching" 👀

❌ "Processing request..."
❌ "Action completed successfully"
❌ "Marketplace listing created"

### Button Labels
✅ "Find Buyers"
✅ "Let's Go!"
✅ "Show Me Offers"

❌ "Submit"
❌ "Proceed"
❌ "Continue"

### Error Messages
✅ "Hmm, couldn't reach that shop - they might be closed"
✅ "Oops! That image is too large. Try one under 10MB?"

❌ "Error: Connection failed"
❌ "Invalid file size"

## Tips for Claude Code

When asking Claude Code to build components:

1. **Always reference the design system**: "Build this using our design system from DESIGN_SYSTEM.md"

2. **Point to examples**: "Make it similar to our AgentActivityFeed component"

3. **Be specific about styling**: "Use shadow-brutal, border-2, and the primary color"

4. **Request proper animations**: "Add hover states with the lift effect"

5. **Include copy examples**: "Use our conversational tone like in the design system"

## Color Reference (Quick Copy)

```tsx
// Primary
bg-primary text-primary border-primary

// Secondary  
bg-secondary text-secondary border-secondary

// Accents
bg-accent-green    // Success
bg-accent-yellow   // Warning
bg-accent-red      // Error
bg-accent-purple   // Premium

// Neutrals
bg-neutral-black bg-neutral-900 bg-neutral-700
bg-neutral-500 bg-neutral-300 bg-neutral-100 bg-neutral-50
```

## Spacing Reference (Quick Copy)

```tsx
p-2   // 8px
p-4   // 16px
p-6   // 24px - Most common for cards
p-8   // 32px

gap-2 gap-4 gap-6 gap-8  // Same scale
```

## Font Reference (Quick Copy)

```tsx
font-display  // Headings, buttons
font-body     // Body text (default)
font-mono     // Prices, codes

font-semibold font-bold  // Weights
text-sm text-base text-lg text-2xl  // Sizes
```

## Next Steps

1. Review `/components/ui/Button.tsx` for button patterns
2. Review `/components/ui/Card.tsx` for card patterns  
3. Review `/components/features/AgentActivityFeed.tsx` for a complete feature example
4. Review `/components/features/ImageUpload.tsx` for form patterns

When building new components, follow these examples and maintain consistency with the brutalist-garage-sale aesthetic!