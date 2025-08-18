# api_utils.py
import time

def now():
    # relógio de alta resolução para medir duração
    return time.perf_counter()

def fmt_duration(seconds: float) -> str:
    ms = int(seconds * 1000)
    if ms < 1000:
        return f"{ms} ms"
    m, s = divmod(seconds, 60)
    if m < 1:
        return f"{s:.1f} s"
    h, m = divmod(m, 60)
    if h < 1:
        return f"{int(m)} min {int(s)} s"
    return f"{int(h)} h {int(m)} min"