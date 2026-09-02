import sys
import re

input_file = sys.argv[1]
output_file = sys.argv[2]

with open(input_file, "r", encoding="utf-8") as f:
    svg = f.read()

# Function to create a tree SVG group
def create_tree(x, y, size, color):
    trunk_height = size * 0.4
    leaves_radius = size * 0.6

    return f'''
    <g transform="translate({x},{y})">
        <!-- trunk -->
        <rect x="-1" y="{trunk_height}" width="2" height="{trunk_height}" fill="#5D4037"/>
        
        <!-- leaves -->
        <circle cx="0" cy="{trunk_height}" r="{leaves_radius}" fill="{color}" />
    </g>
    '''

# Find rectangles (bars from original SVG)
rects = re.findall(
    r'<rect[^>]*x="([\d.]+)"[^>]*y="([\d.]+)"[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"[^>]*fill="([^"]+)"[^>]*/>',
    svg
)

trees_svg = ""

for rect in rects:
    x, y, w, h, color = rect
    x = float(x)
    y = float(y)
    h = float(h)

    if h < 2:
        continue  # skip empty cells

    size = max(4, h * 2)

    trees_svg += create_tree(x, y, size, color)

# Replace all rects with trees
svg = re.sub(r'<rect[^>]*/>', '', svg)

# Insert trees before closing SVG
svg = svg.replace('</svg>', trees_svg + '\n</svg>')

# Add background
svg = svg.replace(
    "<svg",
    '<svg style="background:#0d1117"',
    1
)

with open(output_file, "w", encoding="utf-8") as f:
    f.write(svg)

print("🌳 Trees generated successfully!")
