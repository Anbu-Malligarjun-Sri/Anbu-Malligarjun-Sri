import sys

input_file = sys.argv[1]
output_file = sys.argv[2]

with open(input_file, "r", encoding="utf-8") as f:
    svg = f.read()

# Replace cube colors with green shades (tree-like)
svg = svg.replace("#0f0", "#2e7d32")
svg = svg.replace("#00ff00", "#388e3c")

# Optional: add white background
if "<svg" in svg:
    svg = svg.replace(
        "<svg",
        '<svg style="background-color:white"',
        1
    )

with open(output_file, "w", encoding="utf-8") as f:
    f.write(svg)

print("Tree-style SVG generated!")
