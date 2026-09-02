#!/usr/bin/env python3
"""
svg_to_trees.py

Usage:
  python3 svg_to_trees.py input.svg output.svg

What it does (best-effort):
 - Backs up input.svg -> input.svg.bak
 - Replaces very wide low-height rects (identified as 'stripe') with a white rectangle
 - Converts other rect "bars" into tree groups (trunk + canopy) preserving bar height -> tree height
 - Recolors other fills to neutral/white to reduce colorful noise
 - Leaves everything else untouched (safe fallback)
"""

import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
import math
import os

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ns = {"svg": SVG_NS}

def float_or(v, default=0.0):
    try:
        return float(v)
    except:
        return default

def create_tree_group(x, y, w, h, trunk_color="#6b3b17", canopy_color="#2e7d32"):
    """
    Create an Element <g> like:
      <g>
        <rect ... trunk .../>
        <polygon points="..." ... canopy .../>
      </g>
    Coordinates: x,y is rect.x, rect.y ; w,h are rect.width,height
    We'll place trunk at bottom, canopy above trunk. Return Element
    """
    g = ET.Element(f"{{{SVG_NS}}}g")
    # trunk dimensions (small fraction of original width/height)
    trunk_h = max(4, h * 0.18)
    trunk_w = max( max(2, w * 0.35), 3 )
    trunk_x = x + (w - trunk_w) / 2.0
    trunk_y = y + (h - trunk_h)  # trunk sits at bottom of original rect

    trunk = ET.Element(f"{{{SVG_NS}}}rect", {
        "x": str(round(trunk_x,2)),
        "y": str(round(trunk_y,2)),
        "width": str(round(trunk_w,2)),
        "height": str(round(trunk_h,2)),
        "fill": trunk_color,
        "stroke": "none"
    })
    g.append(trunk)

    # canopy: an isosceles triangle centered above trunk
    canopy_h = max(8, h * 0.5)
    cx = x + w/2.0
    top_y = trunk_y - canopy_h  # apex y
    left_x = x
    right_x = x + w

    points = f"{round(cx,2)},{round(top_y,2)} {round(left_x,2)},{round(trunk_y-1,2)} {round(right_x,2)},{round(trunk_y-1,2)}"
    canopy = ET.Element(f"{{{SVG_NS}}}polygon", {
        "points": points,
        "fill": canopy_color,
        "stroke": "none",
        "opacity": "1"
    })
    g.append(canopy)

    return g

def main(inp_path, out_path):
    if not os.path.exists(inp_path):
        print("Input file not found:", inp_path)
        sys.exit(1)

    # backup
    bak = inp_path + ".bak"
    if not os.path.exists(bak):
        print("Creating backup:", bak)
        import shutil
        shutil.copy2(inp_path, bak)

    tree = ET.parse(inp_path)
    root = tree.getroot()

    # 1) Replace linear/radial gradients stops to white (reduces stripe color)
    for gradient_tag in ["{http://www.w3.org/2000/svg}linearGradient", "{http://www.w3.org/2000/svg}radialGradient"]:
        for g in root.findall(".//" + gradient_tag):
            for stop in list(g):
                if stop.tag.endswith("stop"):
                    stop.set("stop-color", "#ffffff")
                    stop.set("stop-opacity", "1")

    # 2) Find very wide, low rects (the stripe) and paint them white
    # thresholds (tweak if needed)
    STRIPE_MIN_WIDTH = 600.0   # width considered as the long stripe (tweak)
    STRIPE_MAX_HEIGHT = 120.0  # must be relatively low (tweak)

    rects = list(root.findall(".//{http://www.w3.org/2000/svg}rect"))
    replaced = 0
    tree_count = 0

    for r in rects:
        # read commonly used attributes
        x = float_or(r.get("x", "0"))
        y = float_or(r.get("y", "0"))
        w = float_or(r.get("width") or r.get("w") or r.get("data-width") or "0")
        h = float_or(r.get("height") or r.get("h") or r.get("data-height") or "0")

        # fallback: sometimes width/height are inside transform or style; try style attr parse
        style = r.get("style", "")
        if (w == 0 or h == 0) and style:
            # parse style like "fill:#...;width:10;height:20" (not always present)
            for token in style.split(";"):
                if ":" in token:
                    k,v = token.split(":",1)
                    if k.strip() in ("width","height"):
                        try:
                            if k.strip()=="width":
                                w = float(v)
                            else:
                                h = float(v)
                        except:
                            pass

        # If this looks like the long color stripe, set it white and remove stroke
        if w >= STRIPE_MIN_WIDTH and h <= STRIPE_MAX_HEIGHT:
            r.set("fill", "#ffffff")
            r.set("stroke", "none")
            replaced += 1
            continue

    # 3) Convert remaining rects (small bars) into tree groups (best effort)
    # We'll only convert rects that look like bars (small width, varying heights)
    SMALL_BAR_MAX_WIDTH = 80.0
    SMALL_BAR_MIN_HEIGHT = 6.0

    # Need to iterate again because we will replace nodes: collect candidates first
    rects = list(root.findall(".//{http://www.w3.org/2000/svg}rect"))
    for r in rects:
        parent = r.getparent() if hasattr(r, "getparent") else None  # ElementTree may not support getparent
        # Because xml.etree.ElementTree doesn't have getparent, we search parent manually
        # find parent by iterating tree
        p = None
        for cand in root.iter():
            for child in list(cand):
                if child is r:
                    p = cand
                    break
            if p is not None:
                break
        if p is None:
            p = root

        x = float_or(r.get("x", "0"))
        y = float_or(r.get("y", "0"))
        w = float_or(r.get("width") or "0")
        h = float_or(r.get("height") or "0")

        # qualify candidate: small width and reasonable height
        if 0 < w <= SMALL_BAR_MAX_WIDTH and h >= SMALL_BAR_MIN_HEIGHT:
            # Make tree group and replace the rect element with the tree group
            tree_g = create_tree_group(x, y, w, h,
                                      trunk_color="#6b3b17",
                                      canopy_color="#2e7d32")
            # preserve position in parent: find index
            idx = None
            children = list(p)
            for i,ch in enumerate(children):
                if ch is r:
                    idx = i
                    break
            if idx is not None:
                # remove old rect and insert tree group
                p.remove(r)
                p.insert(idx, tree_g)
                tree_count += 1
            else:
                # fallback: append
                p.append(tree_g)
                try:
                    p.remove(r)
                except:
                    pass

    # 4) Desaturate other colored fills: set non-white fills to light gray / white
    for elem in root.iter():
        # skip defs, gradients, etc
        if elem.tag.endswith("stop"): 
            continue
        fill = elem.get("fill")
        if fill and fill.strip() != "" and fill.strip().lower() not in ("none", "#ffffff", "white", "rgb(255,255,255)"):
            # set to white or faint gray so images are monochrome
            elem.set("fill", "#ffffff")

        # remove heavy strokes/colors (optional)
        stroke = elem.get("stroke")
        if stroke and stroke.strip().lower() not in ("none", "#ffffff", "white"):
            elem.set("stroke", "none")

    print(f"Stripe rects replaced: {replaced}; Trees created from rects: {tree_count}")

    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    print("Saved:", out_path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: svg_to_trees.py in.svg out.svg")
    else:
        main(sys.argv[1], sys.argv[2])
