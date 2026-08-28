Trigger: When the approved surface includes iOS, iPadOS, or macOS UI.
Purpose: Apply Apple-platform interaction, layout, accessibility, and platform convention guidance.
Preserved Contract: Keep registered design truth authoritative while adapting implementation details to the selected Apple platform.

# Apple platform guidance

Load this reference for iOS, iPadOS, or macOS. Preserve shared product intent
across Apple platforms, but branch the interaction and window model by device.

## iOS and iPadOS

- Design for touch, safe areas, Dynamic Type, VoiceOver, orientation/window
  changes, and interruption recovery.
- Prefer familiar system components and navigation patterns. Provide visible
  alternatives to custom gestures.
- Aim for 44 x 44 pt controls; treat 28 x 28 pt as a lower bound only when the
  surrounding spacing and task risk make it safe.
- Let iPad layouts reveal or reflow useful content instead of merely stretching
  an iPhone composition. Account for keyboard and pointer input when relevant.

## macOS

- Use large, resizable windows to expose hierarchy with fewer nested levels.
  Demonstrate compact and spacious window states rather than one fixed frame.
- Support keyboard shortcuts, menu-bar command discoverability, precise
  pointer input, focus order, multiple windows, active/inactive states, and
  full-screen behavior as applicable.
- Prefer native controls and platform density. Aim for 28 x 28 pt default
  controls; use 20 x 20 pt only where the context remains comfortably usable.
- Preserve user customization of windows and toolbars when the product's work
  style benefits from it.

Primary references:

- https://developer.apple.com/design/human-interface-guidelines/design-principles
- https://developer.apple.com/design/human-interface-guidelines/layout
- https://developer.apple.com/design/human-interface-guidelines/accessibility
- https://developer.apple.com/design/human-interface-guidelines/designing-for-macos/
