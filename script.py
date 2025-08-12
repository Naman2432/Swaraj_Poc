import os
import re
import json
import math
import argparse
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
pytesseract.pytesseract.tesseract_cmd = r'C:/py-ocr/tesseract.exe'

# If tesseract is not on PATH, uncomment and set your path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---------- Utilities ----------


def ensure_output_dir(p: str) -> Path:
    # Normalize once, return a Path
    p = (p or "").strip().strip('"\'')

    out = Path(os.path.expandvars(os.path.expanduser(p))).resolve()
    if out.exists() and not out.is_dir():
        raise RuntimeError(f"Output path points to a file, not a folder: {out}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_debug(path, img):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), img)
    if not ok:
        print(f"[WARN] cv2.imwrite failed for {p}")

def rotate_image(image, angle_deg, border=cv2.BORDER_REPLICATE):
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angle_deg, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=border)
    return rotated

def auto_contrast(img_gray):
    # CLAHE for line/text pop
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(img_gray)

def largest_rect_contour(bin_img):
    contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    return c

def four_point_warp(img, cnt):
    # approximate to polygon; try to get a 4-point border
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    rect = None

    if len(approx) == 4:
        rect = approx.reshape(4, 2)
    else:
        # fallback to minAreaRect box
        r = cv2.minAreaRect(cnt)
        rect = cv2.boxPoints(r)
        rect = np.array(rect, dtype=np.int32)

    # order points
    def order_pts(pts):
        pts = np.array(pts, dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        tl = pts[np.argmin(s)]
        br = pts[np.argmax(s)]
        tr = pts[np.argmin(diff)]
        bl = pts[np.argmax(diff)]
        return np.array([tl, tr, br, bl], dtype="float32")

    src = order_pts(rect)
    (tl, tr, br, bl) = src
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxW = int(max(widthA, widthB))
    maxH = int(max(heightA, heightB))
    dst = np.array([[0,0], [maxW-1,0], [maxW-1,maxH-1], [0,maxH-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (maxW, maxH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return warped

def estimate_skew_angle(bin_img):
    # Use Hough lines on edges to estimate the dominant angle (near 0 or 90)
    edges = cv2.Canny(bin_img, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180.0, threshold=200)
    if lines is None:
        return 0.0
    angles = []
    for rho, theta in lines[:,0,:]:
        angle = (theta * 180.0 / np.pi)
        # convert to [-90, 90)
        if angle > 90:
            angle -= 180
        angles.append(angle)
    if not angles:
        return 0.0
    # cluster around the two main axes; pick the one with smaller abs mean
    med = np.median(angles)
    # We want to rotate so that med ~ 0
    return med

def adaptive_binarize(img_gray):
    return cv2.adaptiveThreshold(
        img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11
    )

def morphological_textmap(bin_img):
    # Create a "text likelihood" map by connecting small components horizontally and vertically
    hkernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    vkernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    hclose = cv2.morphologyEx(255 - bin_img, cv2.MORPH_CLOSE, hkernel, iterations=1)
    vclose = cv2.morphologyEx(255 - bin_img, cv2.MORPH_CLOSE, vkernel, iterations=1)
    textmap = cv2.bitwise_or(hclose, vclose)
    return textmap

def crop_to_frame(image):
    # rough binarization for contour detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thr = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # Invert so border is white (easier to join)
    inv = 255 - thr
    # Close gaps on rectangle
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(inv, cv2.MORPH_CLOSE, kernel, iterations=1)
    cnt = largest_rect_contour(closed)
    if cnt is None:
        return image, False
    warped = four_point_warp(image, cnt)
    return warped, True

# ---------- OCR & Dimension parsing ----------

DIM_CHAR_WHITELIST = "0123456789.-+±°xX⌀ØøφΦ()[]/RrMmMINmaxMAXrefREF"

# Common replacements to normalize OCR quirks
CHAR_NORMALIZATION = {
    "Ø": "⌀",
    "ø": "⌀",
    "φ": "⌀",
    "Φ": "⌀",
    "O": "0",   # sometimes O instead of 0
    "—": "-",
    "–": "-",
    "° ": "°",  # remove trailing spaces before degree
}

# Regex patterns for dimension-like tokens
RE_DIAM = re.compile(r"^(?:⌀|DIA\.?\s*)\s*\d+(?:\.\d+)?(?:\s*±\s*\d+(?:\.\d+)?)?$", re.I)
RE_RADIUS = re.compile(r"^R\s*\d+(?:\.\d+)?(?:\s*±\s*\d+(?:\.\d+)?)?$", re.I)
RE_ANGLE = re.compile(r"^\d+(?:\.\d+)?\s*°(?:\s*±\s*\d+(?:\.\d+)?)?$")
RE_COUNT_X_ANGLE = re.compile(r"^\d+\s*[xX]\s*\d+(?:\.\d+)?\s*°")
RE_PLAIN_NUM = re.compile(r"^\d+(?:\.\d+)?(?:\s*±\s*\d+(?:\.\d+)?)?$")
RE_TOL_NOTE = re.compile(r"^(MIN\.?|MAX\.?|REF\.?)$", re.I)

@dataclass
class DimItem:
    text: str
    kind: str  # DIAMETER / RADIUS / ANGLE / COUNTxANGLE / NUMBER
    value: Optional[float]
    tolerance: Optional[float]
    qualifiers: List[str]
    bbox: Tuple[int, int, int, int]  # x,y,w,h
    rotation_applied: int  # degrees rotated during OCR (0/90/270)
    conf: float

def normalize_text(s: str) -> str:
    out = s
    for k, v in CHAR_NORMALIZATION.items():
        out = out.replace(k, v)
    # normalize spaces
    out = re.sub(r"\s+", " ", out).strip()
    return out

def parse_dim_text(s: str) -> Tuple[str, Optional[float], Optional[float], List[str]]:
    """
    Returns (kind, value, tolerance, qualifiers)
    """
    s0 = s
    s = s.upper()
    qualifiers = []
    # Pull out trailing qualifiers like MIN/MAX/REF
    parts = s.split()
    if parts and RE_TOL_NOTE.match(parts[-1]):
        qualifiers.append(parts[-1])
        s = " ".join(parts[:-1]).strip()

    # match specific kinds
    if RE_DIAM.match(s):
        # remove symbol
        core = re.sub(r"^(?:⌀|DIA\.?\s*)", "", s, flags=re.I).strip()
        val, tol = parse_value_tol(core)
        return "DIAMETER", val, tol, qualifiers
    if RE_RADIUS.match(s):
        core = re.sub(r"^R\s*", "", s).strip()
        val, tol = parse_value_tol(core)
        return "RADIUS", val, tol, qualifiers
    if RE_COUNT_X_ANGLE.match(s):
        return "COUNTxANGLE", None, None, qualifiers
    if RE_ANGLE.match(s):
        core = s.replace("°", "")
        val, tol = parse_value_tol(core)
        return "ANGLE", val, tol, qualifiers
    if RE_PLAIN_NUM.match(s):
        val, tol = parse_value_tol(s)
        return "NUMBER", val, tol, qualifiers
    # not a dimension-like string
    return "OTHER", None, None, qualifiers

def parse_value_tol(core: str) -> Tuple[Optional[float], Optional[float]]:
    # handles "54.0 ± 0.2" or "54.0+0.2/-0.1" (keep simple: detect ± first)
    core = core.replace(" ", "")
    if "±" in core:
        try:
            v, t = core.split("±")
            return float(v), float(t)
        except:
            return None, None
    # +/- stacked tolerances (rare in 1-line OCR) not handled fully here
    try:
        return float(core), None
    except:
        return None, None

def run_tesseract_on_crop(crop, psm=7, dpi=300, whitelist=DIM_CHAR_WHITELIST):
    # start minimal; add whitelist later if needed
    config = f'--psm {psm}'
    txt = pytesseract.image_to_string(crop, lang='eng', config=config)
    return normalize_text(txt)

    # config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist} -c user_defined_dpi={dpi}'
    # txt = pytesseract.image_to_string(crop, lang="eng", config=config)
    # return normalize_text(txt)

def ocr_box_with_orientation(img, box):
    x, y, w, h = box
    crop = img[y:y+h, x:x+w]
    # try three orientations: 0, 90, 270
    tries = [(0, crop)]
    if h > w * 1.3 or w > h * 1.3:
        tries.append((90, cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)))
        tries.append((270, cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)))
    best = ("", 0, 0.0)
    for rot, c in tries:
        txt = run_tesseract_on_crop(c)
        conf = 0.0
        # crude conf from length of numeric content
        conf = min(95.0, 40.0 + 5.0 * len(re.findall(r"[0-9]", txt)))
        if len(txt) > len(best[0]):
            best = (txt, rot, conf)
    return best  # (text, rotation, pseudo_conf)

def image_to_data_boxes(img_bin):
    # super-safe config on Windows (we can add flags later)
    config = '--psm 6'
    data = pytesseract.image_to_data(img_bin, lang='eng', config=config, output_type=Output.DICT)

    boxes = []
    n = len(data.get("level", []))
    for i in range(n):
        txt = (data.get("text", [""])[i] or "").strip()
        if not txt:
            continue

        # Coerce ints with safe defaults
        x = int(data.get("left",  [0])[i] or 0)
        y = int(data.get("top",   [0])[i] or 0)
        w = int(data.get("width", [0])[i] or 0)
        h = int(data.get("height",[0])[i] or 0)

        # conf may be missing or non-numeric in some builds
        conf_str = str(data.get("conf", ["-1"])[i])
        try:
            conf = float(conf_str)
        except:
            conf = 0.0

        boxes.append((x, y, w, h, txt, conf))
    return boxes
    
    
    # # Use pytesseract data API for initial coarse boxes
    # config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
    # data = pytesseract.image_to_data(img_bin, lang="eng", config=config, output_type=Output.DICT)

    # boxes = []
    # n = len(data["level"])
    # for i in range(n):
    #     txt = data["text"][i]
    #     if not txt or txt.strip() == "":
    #         continue
    #     conf = float(data["conf"][i]) if data["conf"][i] != "-1" else 0.0
    #     x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
    #     boxes.append((x, y, w, h, txt, conf))
    # return boxes

def merge_overlapping_boxes(boxes, iou_thresh=0.2):
    # Normalize: ensure (x, y, w, h, txt, conf)
    norm = []
    for b in boxes:
        if len(b) == 6:
            norm.append(b)
        elif len(b) == 5:
            x, y, w, h, txt = b
            norm.append((x, y, w, h, txt, 0.0))
        else:
            # unexpected shape; skip
            continue
    boxes = norm

    rects = [(x, y, x+w, y+h, txt, conf) for (x, y, w, h, txt, conf) in boxes]
    rects.sort(key=lambda r: (r[1], r[0]))
    merged = []
    for r in rects:
        x1, y1, x2, y2, txt, conf = r
        placed = False
        for j in range(len(merged)):
            a1, b1, a2, b2, ttxt, tconf = merged[j]
            ix1 = max(x1, a1); iy1 = max(y1, b1)
            ix2 = min(x2, a2); iy2 = min(y2, b2)
            iw = max(0, ix2 - ix1); ih = max(0, iy2 - iy1)
            inter = iw * ih
            ua = (x2 - x1) * (y2 - y1) + (a2 - a1) * (b2 - b1) - inter
            iou = inter / ua if ua > 0 else 0
            if iou > iou_thresh:
                nx1, ny1 = min(x1, a1), min(y1, b1)
                nx2, ny2 = max(x2, a2), max(y2, b2)
                merged[j] = (nx1, ny1, nx2, ny2, ttxt + " " + txt, max(conf, tconf))
                placed = True
                break
        if not placed:
            merged.append((x1, y1, x2, y2, txt, conf))
    out = []
    for x1, y1, x2, y2, txt, conf in merged:
        out.append((x1, y1, x2 - x1, y2 - y1, txt, conf))
    return out


# def merge_overlapping_boxes(boxes, iou_thresh=0.2):
#     # simple IOU-based merge pass
#     rects = [(x, y, x+w, y+h, txt, conf) for (x, y, w, h, txt, conf) in boxes]
#     rects.sort(key=lambda r: (r[1], r[0]))
#     merged = []
#     for r in rects:
#         x1, y1, x2, y2, txt, conf = r
#         placed = False
#         for j in range(len(merged)):
#             a1, b1, a2, b2, ttxt, tconf = merged[j]
#             ix1 = max(x1, a1); iy1 = max(y1, b1)
#             ix2 = min(x2, a2); iy2 = min(y2, b2)
#             iw = max(0, ix2 - ix1); ih = max(0, iy2 - iy1)
#             inter = iw * ih
#             ua = (x2 - x1) * (y2 - y1) + (a2 - a1) * (b2 - b1) - inter
#             iou = inter / ua if ua > 0 else 0
#             if iou > iou_thresh:
#                 # merge
#                 nx1, ny1 = min(x1, a1), min(y1, b1)
#                 nx2, ny2 = max(x2, a2), max(y2, b2)
#                 merged[j] = (nx1, ny1, nx2, ny2, ttxt + " " + txt, max(conf, tconf))
#                 placed = True
#                 break
#         if not placed:
#             merged.append((x1, y1, x2, y2, txt, conf))
#     out = []
#     for x1, y1, x2, y2, txt, conf in merged:
#         out.append((x1, y1, x2 - x1, y2 - y1, txt, conf))
#     return out

def filter_dimension_like(text: str) -> bool:
    s = normalize_text(text)
    if not s:
        return False
    # discard obvious long words or non-dim note lines
    if len(s) > 25:
        return False
    # must have digits or known dimension symbol
    if not re.search(r"[0-9⌀]", s):
        return False
    # try classify
    kind, *_ = parse_dim_text(s)
    return kind != "OTHER"

# ---------- Main pipeline ----------

def process_image(path: str, outdir: str) -> Dict:
    outdir_path = ensure_output_dir(outdir)
    steps_dir = outdir_path / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    save_debug(steps_dir / "00_original.png", img)

    # 2) Crop to frame (border)
    cropped, did_warp = crop_to_frame(img)
    save_debug(steps_dir / "01_cropped_to_frame.png", cropped.copy())

    # 3) Grayscale + denoise + contrast
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    den = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
    enh = auto_contrast(den)
    save_debug(steps_dir / "02_grayscale_enhanced.png", enh)

    # 4) Adaptive threshold (B/W blueprint)
    bin_img = adaptive_binarize(enh)
    save_debug(steps_dir / "03_adaptive_binary.png", bin_img)

    # 5) Deskew (estimate from lines)
    angle = estimate_skew_angle(bin_img)
    deskewed = rotate_image(cropped, angle * (-1.0))
    deskewed_gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
    deskewed_bin = adaptive_binarize(auto_contrast(deskewed_gray))
    save_debug(steps_dir / "04_deskewed_binary.png", deskewed_bin)

    # 6) Line detection (debug, optional)
    edges = cv2.Canny(deskewed_bin, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=150, minLineLength=80, maxLineGap=10)
    line_vis = deskewed.copy()
    if lines is not None:
        for l in lines[:,0,:]:
            x1,y1,x2,y2 = l
            cv2.line(line_vis, (x1,y1), (x2,y2), (0,0,255), 1)
    save_debug(steps_dir / "05_lines_debug.png", line_vis)

    # 7) Text candidate map (for better box proposals)
    textmap = morphological_textmap(deskewed_bin)
    save_debug(steps_dir / "06_textmap.png", textmap)

    # 8) OCR coarse boxes from Tesseract
    boxes = image_to_data_boxes(deskewed_bin)
    boxes = merge_overlapping_boxes(boxes)

    # 9) Per-box orientation-aware OCR + dimension filtering
    dim_items: List[DimItem] = []
    ocr_vis = deskewed.copy()

    for (x, y, w, h, coarse_txt, conf) in boxes:
        if w*h < 60 or w*h > (deskewed.shape[0]*deskewed.shape[1]*0.2):
            continue
        txt, rot, pseudo_conf = ocr_box_with_orientation(deskewed_gray, (x,y,w,h))
        txt = normalize_text(txt)
        if not txt or not filter_dimension_like(txt):
            continue
        kind, val, tol, quals = parse_dim_text(txt)
        dim_items.append(DimItem(
            text=txt, kind=kind, value=val, tolerance=tol,
            qualifiers=quals, bbox=(x,y,w,h), rotation_applied=rot, conf=max(conf, pseudo_conf)
        ))
        cv2.rectangle(ocr_vis, (x,y), (x+w, y+h), (0,255,0), 1)
        cv2.putText(ocr_vis, f"{kind}:{txt}", (x, max(0, y-4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,0,255), 1, cv2.LINE_AA)

    save_debug(steps_dir / "07_ocr_dim_overlays.png", ocr_vis)

    # 10) Consolidate
    deduped = dedupe_dimensions(dim_items)

    # 11) Final overlay
    final_vis = deskewed.copy()
    for it in deduped:
        x,y,w,h = it.bbox
        cv2.rectangle(final_vis, (x,y), (x+w, y+h), (255,0,0), 2)
        label = f"{it.kind}:{it.text}"
        cv2.putText(final_vis, label, (x, max(10, y-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 1, cv2.LINE_AA)
    save_debug(steps_dir / "08_final_dimensions.png", final_vis)

    # 12) JSON dump
    result = {
        "image_path": path,
        "deskew_angle_deg": float(angle),
        "dimensions": [asdict(d) for d in deduped]
    }

    json_path = outdir_path / "dimensions.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def dedupe_dimensions(items: List[DimItem]) -> List[DimItem]:
    # Merge items with nearly identical text & close boxes
    kept: List[DimItem] = []
    for it in sorted(items, key=lambda d: (-d.conf, d.kind)):
        keep = True
        for jt in kept:
            if jt.kind != it.kind:
                continue
            if normalize_text(jt.text) == normalize_text(it.text):
                # check distance
                d = box_distance(it.bbox, jt.bbox)
                if d < 40:  # pixels
                    keep = False
                    break
        if keep:
            kept.append(it)
    return kept

def box_center(b):
    x,y,w,h = b
    return (x + w/2.0, y + h/2.0)

def box_distance(b1, b2):
    c1 = box_center(b1); c2 = box_center(b2)
    return math.hypot(c1[0]-c2[0], c1[1]-c2[1])

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Dimensional OCR for mechanical drawings (offline).")
    ap.add_argument("--image", required=True, help="Path to PNG/JPG")
    ap.add_argument("--outdir", default="./out", help="Output directory")
    args = ap.parse_args()

    outdir_path = ensure_output_dir(args.outdir)
    print(f"[INFO] Writing outputs to: {outdir_path}")

    result = process_image(args.image, str(outdir_path))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


#  python script.py --image "D:\Invoice NTZ\InvoiceStructure\uploads\drawings\hq720.jpg" --outdir "D:\Invoice NTZ\InvoiceStructure\uploads"
