# pip install opencv-python pdfplumber numpy pillow
import cv2, numpy as np, pdfplumber
from dataclasses import dataclass
from operator import itemgetter

# ==== Config que pertence à deteção ====
HSV_COLOR_RANGES = [((90, 10, 80), (170, 130, 255))]

# ==== Tipos ====
@dataclass
class TableDetection:
    roi_box: tuple            # (x, y, w, h) relativos à página
    borders: tuple            # (left, top, right, bottom) relativos à ROI
    filtered_h: list          # [(x1, y, x2, y), ...] relativos à ROI
    filtered_v: list          # [(x, y1, x, y2), ...] relativos à ROI

# ==== Utils ====
def dedup(items, key=lambda x: x, tolerance_px=3):
    items = sorted(items, key=key)
    out = []
    for item in items:
        if not out or abs(key(item) - key(out[-1])) > tolerance_px:
            out.append(item)
    return out

def cluster_mode(values, tolerance_px=6):
    if not values: return None
    values = sorted(int(v) for v in values)
    clusters = [[values[0]]]
    for v in values[1:]:
        if abs(v - clusters[-1][-1]) <= tolerance_px:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return int(np.median(max(clusters, key=len)))

def infer_borders_from_segments(h_segments, v_segments, roi_w, roi_h, tolerance_px=6):
    left  = cluster_mode([min(x1,x2) for x1,y1,x2,y2 in h_segments if abs(y2-y1)<=2], tolerance_px)
    right = cluster_mode([max(x1,x2) for x1,y1,x2,y2 in h_segments if abs(y2-y1)<=2], tolerance_px)
    top   = cluster_mode([min(y1,y2) for x1,y1,x2,y2 in v_segments if abs(x2-x1)<=2], tolerance_px)
    bottom= cluster_mode([max(y1,y2) for x1,y1,x2,y2 in v_segments if abs(x2-x1)<=2], tolerance_px)

    left   = 0 if left   is None else left
    right  = roi_w-1 if right  is None else right
    top    = 0 if top    is None else top
    bottom = roi_h-1 if bottom is None else bottom

    if right-left < max(20, int(.1*roi_w)): left, right = 0, roi_w-1
    if bottom-top < max(20, int(.1*roi_h)): top, bottom = 0, roi_h-1
    return left, top, right, bottom

def render_first_pdf_page(pdf_path, dpi=350):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        pil_img = page.to_image(resolution=dpi).original
        rotation = (page.rotation or 0) % 360
    image_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    if rotation == 0:   return image_bgr
    rot_map = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return cv2.rotate(image_bgr, rot_map[rotation])

def read_input(pdf_path=None, image_path=None, dpi=350):
    if image_path:
        image = cv2.imread(image_path)
        if image is None: raise RuntimeError(f"Não consegui ler a imagem: {image_path}")
        return image
    if not pdf_path:
        raise RuntimeError("Fornece pdf_path ou image_path.")
    return render_first_pdf_page(pdf_path, dpi)

def deskew_image(image_bgr, max_correction_deg=7):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    binary_inv = cv2.bitwise_not(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
    coords = np.column_stack(np.where(binary_inv > 0))
    if coords.size == 0: return image_bgr
    raw_angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + raw_angle) if raw_angle < -45 else -raw_angle
    if abs(angle) > max_correction_deg: return image_bgr
    h, w = image_bgr.shape[:2]
    rot_mx = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    return cv2.warpAffine(image_bgr, rot_mx, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def merge_colinear_segments(segments, axis="h", tolerance_px=3):
    if not segments: return []
    key = (lambda s:(round(s[1]/tolerance_px), s[0])) if axis=="h" else (lambda s:(round(s[0]/tolerance_px), s[1]))
    segments = sorted(segments, key=key); merged=[]
    for x1,y1,x2,y2 in segments:
        if not merged: merged.append([x1,y1,x2,y2]); continue
        X1,Y1,X2,Y2 = merged[-1]
        can_merge = (abs(y1-Y1)<=tolerance_px and x1<=X2+tolerance_px) if axis=="h" \
                    else (abs(x1-X1)<=tolerance_px and y1<=Y2+tolerance_px)
        if can_merge:
            if axis=="h": merged[-1][2] = max(X2, x2)
            else:         merged[-1][3] = max(Y2, y2)
        else:
            merged.append([x1,y1,x2,y2])
    return [tuple(s) for s in merged]

def detect_lines_in_roi(image_bgr, roi_box):
    x, y, roi_w, roi_h = roi_box
    roi_img = image_bgr[y:y+roi_h, x:x+roi_w]

    hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
    color_mask = np.zeros(hsv.shape[:2], np.uint8)
    for low, high in HSV_COLOR_RANGES:
        color_mask |= cv2.inRange(hsv, np.array(low, np.uint8), np.array(high, np.uint8))

    if cv2.countNonZero(color_mask) < 0.002 * roi_w * roi_h:
        gray = cv2.normalize(cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY), None, 0, 255, cv2.NORM_MINMAX)
        bin_img = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, -10)
    else:
        bin_img = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8), 1)

    def build_hv_masks(src, h_len, v_len):
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len,1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,v_len))
        h_mask = cv2.dilate(cv2.erode(src, h_kernel, 1), h_kernel, 1)
        v_mask = cv2.dilate(cv2.erode(src, v_kernel, 1), v_kernel, 1)
        return h_mask, v_mask

    def hough_segments(mask, expected="h", min_frac=.75, gap=6, angle_tol=3, threshold=100):
        edges = cv2.Canny(mask, 50, 150, apertureSize=3)
        ref_len = roi_w if expected=="h" else roi_h
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=threshold,
                                minLineLength=int(min_frac*ref_len), maxLineGap=gap)
        segs=[]
        if lines is not None:
            for X1,Y1,X2,Y2 in lines[:,0,:]:
                dx, dy = X2-X1, Y2-Y1
                if (expected=="h" and abs(dy)<=angle_tol) or (expected=="v" and abs(dx)<=angle_tol):
                    segs.append((int(X1),int(Y1),int(X2),int(Y2)))
        return segs

    horiz_mask_long, vert_mask_long = build_hv_masks(bin_img, max(25, roi_w//35), max(25, roi_h//35))
    horiz_long = hough_segments(horiz_mask_long, "h", .70, 6, 3, 100)
    vert_long  = hough_segments(vert_mask_long,   "v", .70, 6, 3, 100)

    horiz_mask_short, vert_mask_short = build_hv_masks(bin_img, max(10, roi_w//90), max(10, roi_h//90))
    horiz_short = hough_segments(horiz_mask_short, "h", .15, 12, 3, 80)
    vert_short  = hough_segments(vert_mask_short,  "v", .15, 12, 3, 80)

    horiz_segments = merge_colinear_segments(horiz_long + horiz_short, "h", 3)
    vert_segments  = merge_colinear_segments(vert_long  + vert_short,  "v", 3)
    return horiz_mask_long, vert_mask_long, horiz_segments, vert_segments

def validate_by_crossings(h_segments, v_segments, roi_w, roi_h,
                          tolerance_px=6, min_h_frac=.35, min_v_frac=.35, margin_px=6):
    if len(h_segments) < 2 or len(v_segments) < 2:
        return (False, (0,0,roi_w-1,roi_h-1), [], [])

    left, top, right, bottom = infer_borders_from_segments(h_segments, v_segments, roi_w, roi_h, tolerance_px)
    inner_w, inner_h = max(1, right-left), max(1, bottom-top)
    min_h_len = max(20, int(min_h_frac * inner_w))
    min_v_len = max(20, int(min_v_frac * inner_h))

    filtered_h, filtered_v = [], []
    for x1,y1,x2,y2 in h_segments:
        x1,x2 = sorted((x1,x2)); y = int(round((y1+y2)/2))
        if (x2-x1)>=min_h_len and (top+margin_px)<y<(bottom-margin_px) and x2>left+margin_px and x1<right-margin_px:
            filtered_h.append((x1,y,x2,y))
    for x1,y1,x2,y2 in v_segments:
        y1,y2 = sorted((y1,y2)); x = int(round((x1+x2)/2))
        if (y2-y1)>=min_v_len and (left+margin_px)<x<(right-margin_px) and y2>top+margin_px and y1<bottom-margin_px:
            filtered_v.append((x,y1,x,y2))

    filtered_h = dedup(filtered_h, key=itemgetter(1), tolerance_px=3)
    filtered_v = dedup(filtered_v, key=itemgetter(0), tolerance_px=3)
    if len(filtered_h) < 2 or len(filtered_v) < 2:
        return (False, (left, top, right, bottom), filtered_h, filtered_v)

    crossings = set()
    for hx1,hy,hx2,_ in filtered_h:
        for vx,vy1,_,vy2 in filtered_v:
            if hx1-tolerance_px <= vx <= hx2+tolerance_px and \
               vy1-tolerance_px <= hy <= vy2+tolerance_px and \
               left+margin_px < vx < right-margin_px and \
               top+margin_px  < hy < bottom-margin_px:
                crossings.add((vx,hy))
    is_valid = len(crossings) >= 4
    return (is_valid, (left, top, right, bottom), filtered_h, filtered_v)

def find_rois(image_bgr, min_area_ratio=.02, min_vert_cov=.001, min_intersections=4):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    bin_img = cv2.adaptiveThreshold(~cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX),
                                    255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, -10)
    img_h, img_w = bin_img.shape[:2]
    hk, vk = max(15, img_w//25), max(15, img_h//25)

    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (hk,1))
    vert_kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (1,vk))
    horiz_mask = cv2.dilate(cv2.erode(bin_img, horiz_kernel, 1), horiz_kernel, 1)
    vert_mask  = cv2.dilate(cv2.erode(bin_img, vert_kernel, 1),  vert_kernel, 1)

    grid_mask   = cv2.morphologyEx(cv2.bitwise_or(horiz_mask, vert_mask), cv2.MORPH_CLOSE, np.ones((5,5),np.uint8), 2)
    cross_mask  = cv2.bitwise_and(horiz_mask, vert_mask)

    contours,_ = cv2.findContours(grid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = img_h * img_w; rois=[]
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        if w*h < min_area_ratio * page_area: continue
        vert_roi = vert_mask[y:y+h, x:x+w]
        vert_ratio = cv2.countNonZero(vert_roi) / float(w*h)
        if vert_ratio < min_vert_cov:
            edges = cv2.Canny(vert_roi,50,150,apertureSize=3)
            lines = cv2.HoughLinesP(edges,1,np.pi/180,threshold=30,minLineLength=int(0.5*h),maxLineGap=6)
            if not any(abs(x2-x1)<=2 for x1,y1,x2,y2 in (lines[:,0,:] if lines is not None else [])):
                continue
        if cv2.countNonZero(cross_mask[y:y+h, x:x+w]) < min_intersections: continue
        rois.append((x,y,w,h))

    rois.sort(key=lambda r: r[1])
    return rois

# ==== Validação (sem desenho) ====
def validate_table_in_roi(image_bgr, roi_box, tolerance_px=6):
    _, _, horiz_segments, vert_segments = detect_lines_in_roi(image_bgr, roi_box)
    _, _, roi_w, roi_h = roi_box
    is_valid, borders, filtered_h, filtered_v = validate_by_crossings(
        horiz_segments, vert_segments, roi_w, roi_h, tolerance_px
    )
    return is_valid, borders, filtered_h, filtered_v

# ==== Função de alto nível para o “main” ====
def analyze_pdf_all_pages(pdf_path, dpi=350, min_area_ratio=.02, tolerance_px=6):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            pil_img = page.to_image(resolution=dpi).original
            rotation = (page.rotation or 0) % 360
            image_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            if rotation != 0:
                rot_map = {90: cv2.ROTATE_90_CLOCKWISE,
                           180: cv2.ROTATE_180,
                           270: cv2.ROTATE_90_COUNTERCLOCKWISE}
                image_bgr = cv2.rotate(image_bgr, rot_map[rotation])

            page_image = deskew_image(image_bgr)
            rois = find_rois(page_image, min_area_ratio)

            detections = []
            for roi in rois:
                is_valid, borders, fh, fv = validate_table_in_roi(page_image, roi, tolerance_px)
                if is_valid:
                    detections.append(TableDetection(roi_box=roi, borders=borders,
                                                     filtered_h=fh, filtered_v=fv))

            results.append((page_num, page_image, detections))
    return results