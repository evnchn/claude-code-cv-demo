from PIL import Image
import numpy as np
from scipy.ndimage import label

img = Image.open("mysterious.png").convert("RGBA")
data = np.array(img)

# Sample background color from top-left corner
bg_color = data[0, 0, :3]

# Create a mask of pixels close to the background color
threshold = 40
diff = np.sqrt(np.sum((data[:, :, :3].astype(float) - bg_color.astype(float)) ** 2, axis=2))
bg_mask = diff < threshold

# Flood-fill from edges to remove connected background
h, w = bg_mask.shape
filled = np.zeros_like(bg_mask)
stack = []

for x in range(w):
    if bg_mask[0, x]:
        stack.append((0, x))
    if bg_mask[h - 1, x]:
        stack.append((h - 1, x))
for y in range(h):
    if bg_mask[y, 0]:
        stack.append((y, 0))
    if bg_mask[y, w - 1]:
        stack.append((y, w - 1))

while stack:
    py, px = stack.pop()
    if py < 0 or py >= h or px < 0 or px >= w:
        continue
    if filled[py, px]:
        continue
    if not bg_mask[py, px]:
        continue
    filled[py, px] = True
    stack.append((py - 1, px))
    stack.append((py + 1, px))
    stack.append((py, px - 1))
    stack.append((py, px + 1))

# Remove the flood-filled background first
data[filled, 3] = 0

# Now use connected component analysis on remaining visible pixels
# to remove small isolated clusters (stars)
visible = data[:, :, 3] > 0
labeled, num_features = label(visible)

# Find the largest connected component (the Nyan Cat)
component_sizes = np.bincount(labeled.ravel())
# Index 0 is the background (transparent), skip it
component_sizes[0] = 0
largest_component = np.argmax(component_sizes)

print(f"Found {num_features} connected components")
print(f"Largest component (Nyan Cat): label={largest_component}, size={component_sizes[largest_component]} pixels")
print(f"Other components (stars/artifacts):")
for i in range(1, num_features + 1):
    if i != largest_component:
        print(f"  Component {i}: {component_sizes[i]} pixels")

# Remove all components except the largest one
star_mask = (labeled != largest_component) & (labeled != 0)
data[star_mask, 3] = 0

result = Image.fromarray(data)
result.save("mysterious_no_bg.png")
print("\nSaved to mysterious_no_bg.png")
