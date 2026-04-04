#!/usr/bin/env python
"""
Examples of using the OmniPro 220 Expert system

These are realistic scenarios showing how the system handles different types of queries.
"""

# ============================================================================
# EXAMPLE 1: Technical Accuracy - Duty Cycle Query
# ============================================================================

EXAMPLE_1_QUERY = "What's the duty cycle for MIG welding at 200A on 240V?"

EXAMPLE_1_FLOW = """
1. User asks question
   ↓
2. Claude reads: "This is asking for specific technical data"
   ↓
3. Claude decidesFACT: "I should use lookup_duty_cycle tool"
   ↓
4. Tool executes:
   Process: MIG
   Voltage: 240V
   Amperage: 200A
   ↓
5. Tool looks up in store.structured_data:
   Returns: 30% duty cycle
   ↓
6. Claude receives data:
   "30% duty cycle means 3 minutes welding, 7 minutes cooling"
   ↓
7. Claude generates response:
   - Explains what 30% means
   - Creates HTML table showing full MIG duty cycle matrix
   - Highlights the 200A/240V cell
   - Explains implications
"""

EXAMPLE_1_RESPONSE = """
The Vulcan OmniPro 220 has a **30% duty cycle** for MIG welding at 200A on 240V.

What that means: You can weld continuously for 3 minutes, then you must let the machine cool for 7 minutes before welding again.

Here's the complete MIG duty cycle table:

┌─────────┬──────────┬──────────┬──────────┬──────────┐
│         │ 90A      │ 130A     │ 200A ← │ 220A     │
├─────────┼──────────┼──────────┼──────────┼──────────┤
│ 240V    │ 60%      │ 40%      │ 30%  ← │ 20%      │
│ 120V    │ 60%      │ 40%      │ 30%      │ N/A      │
└─────────┴──────────┴──────────┴──────────┴──────────┘

Why this matters:
• At higher amperages, duty cycle drops (generates more heat)
• Plan your work sessions around cooling periods
• If you exceed duty cycle, the machine will shut down to protect itself
"""

# ============================================================================
# EXAMPLE 2: Multimodal - Polarity Setup with Diagram
# ============================================================================

EXAMPLE_2_QUERY = "How do I set up TIG welding? Which cable goes where?"

EXAMPLE_2_RESPONSE = """
For TIG welding, you'll use **DCEN** (DC Electrode Negative) polarity.

**Socket Connections:**
• Torch connects to: **NEGATIVE (-)** socket
• Ground clamp connects to: **POSITIVE (+)** socket

[Visual Diagram - SVG]
┌─────────────────────────────────────────┐
│     Front of Vulcan OmniPro 220         │
├─────────────────────────────────────────┤
│                                         │
│  🔴 + POSITIVE (Red)                   │
│  ├─ Connected to: Ground clamp          │
│  │                                      │
│  🔵 - NEGATIVE (Blue)                  │
│  ├─ Connected to: TIG Torch             │
│                                         │
│  Current flow: + Ground → Arc → - Torch│
│                                         │
└─────────────────────────────────────────┘

**Step-by-step:**
1. Locate the two welding terminals on the front panel
2. Connect torch cable to NEGATIVE terminal (blue)
3. Connect ground clamp to POSITIVE terminal (red)
4. Select TIG on the control panel
5. Adjust amperageto match your material and thickness
6. Use AC current for aluminum, DC for steel

⚠️ Safety: Never hot-swap cables under arc!
"""

# ============================================================================
# EXAMPLE 3: Problem Solving - Troubleshooting with Flow
# ============================================================================

EXAMPLE_3_QUERY = "My flux-cored welds keep getting porosity. What's wrong?"

EXAMPLE_3_RESPONSE = """
Porosity (those small holes in your weld) is usually caused by shielding gas issues or surface contamination.

**Diagnostic Flowchart - Follow these steps:**

1. First, check your shielding gas:
   ├─ Is the gas cylinder valve open? (Turn counterclockwise)
   ├─ Is the regulator showing pressure? (Should be 15-25 CFM)
   ├─ Are all connections tight? (Use wrench, check for leaks)
   └─ Is the gas newer than 6 months? (Old gas can cause issues)

2. If gas is OK, check your wire:
   ├─ Is the wire feed smooth? (No grinding sounds)
   ├─ Is there dust in the feeder? (Clean with wire brush)
   └─ Is the liner not worn out? (Should be smooth inside)

3. If wire is OK, check your work area:
   ├─ Clean the base metal (brush off aluminum oxide, scale, etc.)
   ├─ Dry the material (wet metal = porosity)
   └─ Avoid drafts during welding (wind disrupts shielding gas)

4. Last resort: Check your settings
   ├─ Increase wire speed slightly
   ├─ Decrease amp slightly (cooler arc = better gas coverage)
   └─ Move torch slower over the weld

**Most Common Fix:** Check gas flow. 70% of porosity cases are gas-related.
"""

# ============================================================================
# EXAMPLE 4: Specifications Query
# ============================================================================

EXAMPLE_4_QUERY = "What are the machine specs? I want to know about amperage and wire sizes."

EXAMPLE_4_RESPONSE = """
**Vulcan OmniPro 220 Specifications:**

┌─────────────────────────────────────────────────┐
│ POWER INPUT                                     │
├─────────────────────────────────────────────────┤
│ Voltage:        120V / 240V (auto-switching)   │
│ Frequency:      50/60 Hz                        │
│ Max Input:      30A @ 240V                      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ WELDING OUTPUT                                  │
├─────────────────────────────────────────────────┤
│ MIG:            30-220A @ 240V                  │
│ Flux-Cored:     30-175A @ 240V                  │
│ TIG (DC):       10-80A @ 240V                   │
│ Stick:          30-120A @ 240V                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ WIRE COMPATIBILITY                              │
├─────────────────────────────────────────────────┤
│ MIG Wire:       .024", .030", .035" diameter   │
│ Flux-Cored:     .035", .045" diameter          │
│ Spool Size:     2 lb, 10 lb compatible         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ PHYSICAL                                        │
├─────────────────────────────────────────────────┤
│ Dimensions:     30" wide × 36" tall × 16" deep │
│ Weight:         170 lbs                         │
│ Cooling:        Fan cooled (runs auto)          │
└─────────────────────────────────────────────────┘
"""

# ============================================================================
# EXAMPLE 5: Visual Explanation
# ============================================================================

EXAMPLE_5_QUERY = "How does the wire feed mechanism work?"

EXAMPLE_5_RESPONSE = """
The wire feed mechanism drives the wire from the spool through the nozzle into your weld pool.

**How it works (step by step):**

[SVG Diagram showing:]
        Spool
         ↓ (wire)
        Feeder Wheel (motor-driven)
         ↓ (feeds wire)
        Liner (guides wire cleanly)
         ↓
        Contact Tip (maintains electrical connection)
         ↓
        Nozzle (directs shielding gas)
         ↓
        Arc & Weld Pool

**Tension Calibration:**

The feeder wheel has a tensioner dial. When you hear a steady "ch-ch-ch-ch" sound, it's perfect.

If too loose:      "ch...ch...ch" (slow or slipping)
If too tight:      "CRUNCH" (wheel slipping, skipping)
Just right:        "ch-ch-ch-ch" (regular, smooth sound)

**Maintenance:**
1. Clean the liner every 20 hours of welding
2. Replace if kinked or damaged
3. Adjust tensioner for each wire size
4. Keep drive wheels clean and dry

**Common Problems:**
• Bird nesting (wire balled up inside):
  ├─ Loose tensioner, or
  ├─ Dirty feeder wheel, or
  └─ Kinked liner
  ✓ Fix: Clean everything, check tensioner

• Wire burns back:
  ├─ Usually just normal operation
  ├─ Happens when shielding gas expires
  └─ Stop welding, let tip cool slightly
"""

# ============================================================================
# EXAMPLE 6: Image-Based Diagnosis
# ============================================================================

EXAMPLE_6_QUERY = "[User uploads photo of weld]"

EXAMPLE_6_RESPONSE = """
I can see you've got a weld with some issues. Let me compare it to the diagnosis photos from the manual:

[Manual diagnosis photo displayed]

**What I see in your photo:**
√ The overall weld bead shape looks good
√ Good color (indicates proper shielding)
✗ Small holes/pits visible on the surface (porosity)
✗ Some spatter around the weld

**Diagnosis:**

This is **porosity** with minor spatter.

Likely causes (in order of probability):
1. Shielding gas flow too weak or not flowing at all
2. Arc length too long (gas can't reach weld pool)
3. Travel speed too fast (not enough gas coverage)

**What to do next:**
1. Check gas flow rate (should be 15-25 CFM for flux-cored)
2. Retest with shorter arc length
3. Move slower over the weld
4. Clean the material surface first

[Shows manual comparison diagram]

Notice the difference between your weld and the "Good" vs "Bad" reference samples on page 34 of the manual. Yours is closer to the "porosity" category.

Try the fixes above and send another photo. We can dial it in!
"""

# ============================================================================
# Running These Examples
# ============================================================================

if __name__ == "__main__":
    examples = [
        ("Duty Cycle", EXAMPLE_1_QUERY, EXAMPLE_1_RESPONSE),
        ("Polarity Setup", EXAMPLE_2_QUERY, EXAMPLE_2_RESPONSE),
        ("Troubleshooting", EXAMPLE_3_QUERY, EXAMPLE_3_RESPONSE),
        ("Specifications", EXAMPLE_4_QUERY, EXAMPLE_4_RESPONSE),
        ("Visual Explanation", EXAMPLE_5_QUERY, EXAMPLE_5_RESPONSE),
        ("Image Diagnosis", EXAMPLE_6_QUERY, EXAMPLE_6_RESPONSE),
    ]

    for title, query, response in examples:
        print("\n" + "="*70)
        print(f"  EXAMPLE: {title}")
        print("="*70)
        print(f"\n📝 Query:\n{query}\n")
        print(f"📋 Response:\n{response}\n")

    print("\n" + "="*70)
    print("  These are representative examples.")
    print("  Actual responses will vary based on current knowledge base.")
    print("="*70 + "\n")
