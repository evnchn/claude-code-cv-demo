"""
Net Occlusion Removal — L1 → L2 → L3 Pipeline

Removes safety netting from construction/scaffolding images to reveal
underlying structure. Implements a three-level progression:

  L1: Detect net presence (color-based + FFT frequency analysis)
  L2: Generate pixel-level net mask (HSV segmentation + morphology)
  L3: Reconstruct underlying structure via multiple techniques:
      - 3a: Colour correction (desaturate net tint to see through)
      - 3b: Fine strand detection + targeted inpainting
      - 3c: Coarse mask inpainting (baseline)

Output is organized into per-image subdirectories under:
  images/output/net_removal/{source_category}/{image_name}/
"""

from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).parent.parent
INPUT = ROOT / "images" / "input"
OUTPUT_BASE = ROOT / "images" / "output" / "net_removal"

# ---- Image catalogue: source → list of filenames ----
# Claude-sourced: downloaded from Wikimedia Commons
# User-sourced: provided by Evan
IMAGE_CATALOGUE = {
    "claude_sourced": [
        "scaffold_net_hk_construction.jpg",
        "scaffold_net_hk_highrise.jpg",
        "scaffold_net_hk_building.jpg",
        "scaffold_net_hk_gloucester.jpg",
        "scaffold_net_debris_philly.jpg",
    ],
    "user_sourced": [
        "construction-safety-net-mysample.jpg",
        "scaffold-net-fall-protection.jpg",
        "HX4004-1.jpg",
        "Construction-Safety-Net-for-Buliding-Construction-with-High-Quality.jpeg",
    ],
}

# ---------- colour ranges for common safety nets (HSV) ----------
NET_COLOUR_RANGES = {
    "green": {
        "lower": np.array([30, 40, 30]),
        "upper": np.array([85, 255, 220]),
    },
    "blue": {
        "lower": np.array([90, 40, 30]),
        "upper": np.array([130, 255, 220]),
    },
    "teal": {
        "lower": np.array([75, 40, 30]),
        "upper": np.array([95, 255, 220]),
    },
}


def detect_net_colour(hsv: np.ndarray) -> tuple[np.ndarray, str]:
    """L1 — Detect which colour net is dominant and return the initial mask."""
    best_name = "none"
    best_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    best_count = 0

    for name, rng in NET_COLOUR_RANGES.items():
        mask = cv2.inRange(hsv, rng["lower"], rng["upper"])
        count = int(np.count_nonzero(mask))
        if count > best_count:
            best_count = count
            best_mask = mask
            best_name = name

    return best_mask, best_name


def compute_fft_spectrum(gray: np.ndarray) -> np.ndarray:
    """Compute log-magnitude FFT spectrum (shifted so DC is at centre)."""
    f = np.fft.fft2(gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    magnitude = 20 * np.log(np.abs(fshift) + 1)
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-8) * 255
    return magnitude.astype(np.uint8)


def refine_mask(raw_mask: np.ndarray) -> np.ndarray:
    """L2 — Refine the colour mask into a clean region mask."""
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_med = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    cleaned = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel_small, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_med, iterations=3)
    return cleaned


def colour_correct(bgr: np.ndarray, region_mask: np.ndarray, net_colour: str) -> np.ndarray:
    """L3a — Remove the colour tint caused by the net in the masked region."""
    result = bgr.copy()
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)

    mask_bool = region_mask > 0

    hsv[mask_bool, 1] *= 0.15
    hsv[mask_bool, 2] = np.minimum(hsv[mask_bool, 2] * 1.3, 255)

    hsv = np.clip(hsv, 0, 255).astype(np.uint8)
    corrected = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    soft_mask = cv2.GaussianBlur(region_mask, (21, 21), 0)
    soft_mask_3ch = np.stack([soft_mask] * 3, axis=-1).astype(np.float32) / 255.0

    result = (corrected * soft_mask_3ch + bgr * (1 - soft_mask_3ch)).astype(np.uint8)
    return result


def detect_net_strands(bgr: np.ndarray, region_mask: np.ndarray) -> np.ndarray:
    """L3b (mask) — Detect thin net strand lines within the net region."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    high_pass = cv2.subtract(blurred, gray)

    _, strand_mask = cv2.threshold(high_pass, 8, 255, cv2.THRESH_BINARY)
    strand_mask = cv2.bitwise_and(strand_mask, region_mask)

    kernel_thin = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    strand_mask = cv2.morphologyEx(strand_mask, cv2.MORPH_OPEN, kernel_thin)
    strand_mask = cv2.dilate(strand_mask, kernel_thin, iterations=1)

    return strand_mask


def inpaint_strands(bgr: np.ndarray, strand_mask: np.ndarray) -> np.ndarray:
    """L3b — Inpaint only the thin net strands."""
    return cv2.inpaint(bgr, strand_mask, 3, cv2.INPAINT_TELEA)


def inpaint_coarse(bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """L3c — Inpaint the full colour-masked region (baseline)."""
    return cv2.inpaint(bgr, mask, 5, cv2.INPAINT_TELEA)


def add_label(panel: np.ndarray, text: str) -> np.ndarray:
    """Add a black label bar at the top of a panel."""
    p = panel.copy()
    h, w = p.shape[:2]
    cv2.rectangle(p, (0, 0), (w, 36), (0, 0, 0), -1)
    cv2.putText(p, text, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return p


def build_comparison_grid(panels: list[np.ndarray], labels: list[str], cols: int = 3) -> np.ndarray:
    """Build an N-panel comparison grid with labels."""
    labeled = [add_label(p, t) for p, t in zip(panels, labels)]

    while len(labeled) % cols != 0:
        blank = np.zeros_like(labeled[0])
        labeled.append(blank)

    rows = []
    for i in range(0, len(labeled), cols):
        rows.append(np.hstack(labeled[i:i + cols]))
    return np.vstack(rows)


def process_image(image_path: Path, out_dir: Path) -> None:
    """Run the full L1→L2→L3 pipeline on a single image."""
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Processing: {image_path.name}")
    print(f"  Output → {out_dir.relative_to(ROOT)}/")
    print(f"{'='*60}")

    bgr = cv2.imread(str(image_path))
    if bgr is None:
        print(f"  ERROR: Could not read {image_path}")
        return

    # Resize large images (max 1200px on longest side)
    h, w = bgr.shape[:2]
    max_dim = 1200
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        h, w = bgr.shape[:2]
        print(f"  Resized to {w}x{h}")

    # --- L1: Net Detection ---
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    raw_mask, net_colour = detect_net_colour(hsv)
    total_pixels = h * w
    net_pixels = int(np.count_nonzero(raw_mask))
    net_pct = 100.0 * net_pixels / total_pixels

    print(f"  L1 — Net detected: {net_colour}")
    print(f"       Coverage: {net_pixels:,} / {total_pixels:,} px ({net_pct:.1f}%)")

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    fft_spectrum = compute_fft_spectrum(gray)
    cv2.imwrite(str(out_dir / "fft.png"), fft_spectrum)

    if net_pct < 2.0:
        print(f"  SKIP: Net coverage too low ({net_pct:.1f}%)")
        return

    # --- L2: Region Mask ---
    region_mask = refine_mask(raw_mask)
    mask_pct = 100.0 * np.count_nonzero(region_mask) / total_pixels
    print(f"  L2 — Region mask: {mask_pct:.1f}% of image")
    cv2.imwrite(str(out_dir / "mask.png"), region_mask)

    # --- L3a: Colour Correction ---
    corrected = colour_correct(bgr, region_mask, net_colour)
    cv2.imwrite(str(out_dir / "colour_corrected.jpg"), corrected, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  L3a — Colour-corrected image saved")

    # --- L3b: Fine Strand Detection + Inpainting ---
    strand_mask = detect_net_strands(bgr, region_mask)
    strand_pct = 100.0 * np.count_nonzero(strand_mask) / total_pixels
    print(f"  L3b — Strand mask: {strand_pct:.1f}% of image")
    cv2.imwrite(str(out_dir / "strand_mask.png"), strand_mask)

    strand_inpainted = inpaint_strands(bgr, strand_mask)
    cv2.imwrite(str(out_dir / "strand_inpainted.jpg"), strand_inpainted, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  L3b — Strand-inpainted image saved")

    # --- L3b+a: Strand inpainting THEN colour correction (best combo) ---
    combo = colour_correct(strand_inpainted, region_mask, net_colour)
    cv2.imwrite(str(out_dir / "combo.jpg"), combo, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  L3b+a — Combined (strand inpaint + colour correct) saved")

    # --- L3c: Coarse inpainting (baseline) ---
    coarse = inpaint_coarse(bgr, region_mask)
    cv2.imwrite(str(out_dir / "coarse.jpg"), coarse, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  L3c — Coarse inpainted (baseline) saved")

    # --- 6-panel comparison grid ---
    mask_vis = cv2.cvtColor(region_mask, cv2.COLOR_GRAY2BGR)
    strand_vis = cv2.cvtColor(strand_mask, cv2.COLOR_GRAY2BGR)

    grid = build_comparison_grid(
        panels=[bgr, mask_vis, strand_vis, corrected, strand_inpainted, combo],
        labels=[
            f"Original ({net_colour} net, {net_pct:.1f}%)",
            "L2: Region Mask",
            "L3b: Strand Mask",
            "L3a: Colour Corrected",
            "L3b: Strand Inpainted",
            "L3b+a: Combined (best)",
        ],
        cols=3,
    )
    cv2.imwrite(str(out_dir / "comparison.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  Comparison grid saved")


def main():
    total = 0

    for category, filenames in IMAGE_CATALOGUE.items():
        print(f"\n{'#'*60}")
        print(f"# Category: {category} ({len(filenames)} images)")
        print(f"{'#'*60}")

        for fname in filenames:
            image_path = INPUT / fname
            if not image_path.exists():
                print(f"\n  WARNING: {fname} not found in {INPUT}, skipping")
                continue

            stem = image_path.stem
            out_dir = OUTPUT_BASE / category / stem
            process_image(image_path, out_dir)
            total += 1

    print(f"\n{'='*60}")
    print(f"Done — processed {total} images")
    print(f"Output tree: {OUTPUT_BASE.relative_to(ROOT)}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
