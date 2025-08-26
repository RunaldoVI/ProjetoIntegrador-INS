# DesenharTabela.py
# pip install opencv-python
import cv2
from pathlib import Path
from typing import List, Optional

try:
    # se estiveres a usar tipagem do teu módulo
    from .ValidateTable import TableDetection  # type: ignore
except Exception:
    # fallback genérico p/ tipagem opcional
    from typing import NamedTuple
    class TableDetection(NamedTuple):  # minimal para hints
        roi_box: tuple
        borders: tuple
        filtered_h: list
        filtered_v: list


def render_table_overlay(base_image_bgr,
                         roi_box,
                         borders,
                         filtered_h,
                         filtered_v,
                         tolerance_px: int = 6,
                         thickness_px: int = 3):
    """
    Desenha as linhas da tabela sobre uma CÓPIA da imagem da página.
    - base_image_bgr: ndarray BGR da página inteira
    - roi_box: (x, y, w, h) relativo à página
    - borders: (left, top, right, bottom) relativo à ROI
    - filtered_h: [(x1, y, x2, y), ...] relativo à ROI
    - filtered_v: [(x, y1, x, y2), ...] relativo à ROI
    """
    x, y, w, h = roi_box
    left, top, right, bottom = borders
    output = base_image_bgr.copy()

    # Linhas horizontais (verde)
    for x1, hy, x2, _ in filtered_h:
        cv2.line(output, (x + max(left, x1), y + hy),
                 (x + min(right, x2), y + hy),
                 (0, 255, 0), thickness_px)

    # Linhas verticais (amarelo)
    for vx, y1, _, y2 in filtered_v:
        cv2.line(output, (x + vx, y + max(top, y1)),
                 (x + vx, y + min(bottom, y2)),
                 (0, 255, 255), thickness_px)

    # Borda (azul)
    cv2.rectangle(output, (x + left, y + top), (x + right, y + bottom),
                  (255, 0, 0), thickness_px)
    return output


def _ensure_dir(p: Path):
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


def save_page_overlays(page_num: int,
                       page_image_bgr,
                       detections: List[TableDetection],
                       outdir_base: Path,
                       base_name: Optional[str] = None,
                       tolerance_px: int = 6,
                       thickness_px: int = 3) -> Optional[Path]:
    """
    Guarda PNGs de uma PÁGINA com tabelas:
      - 1 PNG por tabela: <base|page>_pageNN_tableK.png
      - 1 PNG combinado:  <base|page>_pageNN_tables_all.png
    Se não houver tabelas, não grava nada e retorna None.

    Args:
        page_num: número da página (1-based)
        page_image_bgr: imagem BGR da página
        detections: lista de TableDetection (já filtradas)
        outdir_base: pasta base das saídas (ex.: .../<pdf>_out)
        base_name: prefixo opcional nos ficheiros (default: 'page')
    """
    if not detections:
        return None

    tag = (base_name or "page") + f"{page_num:02d}"
    outdir_page = outdir_base  # tudo na mesma pasta, como pediste
    _ensure_dir(outdir_page)

    combined = page_image_bgr.copy()
    for k, det in enumerate(detections, 1):
        single = render_table_overlay(page_image_bgr, det.roi_box, det.borders,
                                      det.filtered_h, det.filtered_v,
                                      tolerance_px=tolerance_px,
                                      thickness_px=thickness_px)
        cv2.imwrite(str(outdir_page / f"{tag}_table{k}.png"), single)
        combined = render_table_overlay(combined, det.roi_box, det.borders,
                                        det.filtered_h, det.filtered_v,
                                        tolerance_px=tolerance_px,
                                        thickness_px=thickness_px)

    cv2.imwrite(str(outdir_page / f"{tag}_tables_all.png"), combined)
    return outdir_page
