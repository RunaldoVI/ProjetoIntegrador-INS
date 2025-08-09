# AutomaticPreviewMode.py
import sys, os, json, re

# paths base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))

from Extração.ExtrairPDF import processar_pdf
from LLM.PromptLLM import obter_pergunta
from ExcelWriter.ExcelWriter import executar
from DataBaseConnection import importar_json_para_bd
from PdfViewMode.utils_extracao import processar_bloco

# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

def _ordenar_campos(item: dict) -> dict:
    return {
        "Identificador": item.get("Identificador", ""),
        "Secção": item.get("Secção", "Nenhuma"),
        "Pergunta": item.get("Pergunta", ""),
        "Respostas": item.get("Respostas", []),
    }

def _out_dir_e_txt_do_pdf(caminho_pdf: str):
    base = os.path.splitext(os.path.basename(caminho_pdf))[0]
    out_dir = os.path.join(os.path.dirname(caminho_pdf), f"{base}_out")
    txt_path = os.path.join(out_dir, f"{base}_perguntas_e_respostas.txt")
    return out_dir, txt_path

def garantir_txt_extracao(caminho_pdf: str) -> str:
    out_dir, txt_path = _out_dir_e_txt_do_pdf(caminho_pdf)
    if os.path.exists(txt_path):
        return txt_path
    print("🧩 TXT não encontrado. A extrair do PDF…")
    _, gerado = processar_pdf(caminho_pdf)
    if not os.path.exists(gerado):
        raise FileNotFoundError(f"Falha a criar o TXT de extração: {gerado}")
    return gerado

BLOCO_RE = re.compile(
    r"^ID:\s*(?P<id>.+?)\s*\|\s*Página:\s*(?P<pag>\d+)\s*?\n"
    r"(?:Sec[çc][ãa]o\s*:\s*(?P<sec>.+?)\s*\n)?"
    r"Pergunta:\s*\n(?P<pergunta>.*?)\nResposta:\s*\n(?P<resposta>.*?)(?=\n-+\n|\Z)",
    re.DOTALL | re.MULTILINE
)

def _parse_respostas(texto: str):
    linhas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
    out = []
    for l in linhas:
        m = re.match(r"^\s*(?P<v>\d+)\s*[-:]\s*(?P<op>.+?)\s*$", l) \
            or re.match(r"^\s*(?P<op>.+?)\s*[\(\[]\s*(?P<v>\d+)\s*[\)\]]\s*$", l) \
            or re.match(r"^\s*(?P<v>\d+)[\)\.]\s*(?P<op>.+?)\s*$", l)
        if m:
            out.append({"opção": m.group("op").strip(), "valor": m.group("v").strip()})
    return out

def ler_blocos_do_txt(caminho_txt: str):
    with open(caminho_txt, "r", encoding="utf-8") as f:
        raw = f.read()

    blocos = []
    for m in BLOCO_RE.finditer(raw):
        ident = m.group("id").strip()
        pagina = int(m.group("pag"))
        secao = (m.group("sec") or "").strip()
        pergunta_txt = (m.group("pergunta") or "").strip()
        resposta_txt = (m.group("resposta") or "").strip()

        pergunta_linhas = [l for l in pergunta_txt.splitlines() if l.strip()]
        resposta_linhas = [l for l in resposta_txt.splitlines() if l.strip()]

        estrutura_original = {
            "Identificador": ident,
            "Secção": secao or "Nenhuma",
            "Pergunta": "\n".join(pergunta_linhas),
            "Respostas": _parse_respostas(resposta_txt)
        }

        blocos.append({
            "Identificador": ident,
            "Pagina": pagina,
            "Secao": secao or "Nenhuma",
            "PerguntaLinhas": pergunta_linhas,
            "RespostaLinhas": resposta_linhas,
            "EstruturaOriginal": estrutura_original
        })
    return blocos

def formatar_para_llm(bloco: dict) -> str:
    p = "\n".join(bloco["PerguntaLinhas"]) if bloco["PerguntaLinhas"] else ""
    r = "\n".join(bloco["RespostaLinhas"]) if bloco["RespostaLinhas"] else ""
    s = bloco.get("Secao", "Nenhuma")
    return (
        f"ID: {bloco['Identificador']}\n"
        f"Página: {bloco['Pagina']}\n"
        f"Secção: {s}\n"
        f"Pergunta:\n{p}\n"
        f"Resposta:\n{r}\n"
    )

def respostas_validas(respostas):
    return [r for r in (respostas or []) if r.get("opção", "").strip() and r.get("valor", "").strip()]

def _expandir_multi_id(resposta_llm):
    out = []
    if isinstance(resposta_llm, dict) and resposta_llm and all(isinstance(v, dict) for v in resposta_llm.values()):
        for ident, corpo in resposta_llm.items():
            c = dict(corpo)
            if "Identificador" not in c:
                c["Identificador"] = ident
            if "ID" in c and "Identificador" not in c:
                c["Identificador"] = str(c.pop("ID")).strip()
            out.append(c)
    elif isinstance(resposta_llm, dict):
        c = dict(resposta_llm)
        if "Identificador" not in c and "ID" in c:
            c["Identificador"] = str(c.pop("ID")).strip()
        out.append(c)
    return out

# -----------------------------------------------------------
# Main
# -----------------------------------------------------------

if len(sys.argv) < 2:
    print("❌ Uso: python AutomaticPreviewMode.py caminho_para_pdf [--reuse-preview]")
    sys.exit(1)

caminho_pdf = sys.argv[1]
reuse_preview = any(arg.strip().lower() == "--reuse-preview" for arg in sys.argv[2:])

try:
    caminho_txt = garantir_txt_extracao(caminho_pdf)
except Exception as e:
    print("❌", e)
    sys.exit(1)

prompt_llm = obter_pergunta()

preview_path = "preview_output.json"
identificadores_vistos = set()
blocos_finais = []

if reuse_preview and os.path.exists(preview_path):
    try:
        with open(preview_path, "r", encoding="utf-8") as f:
            bloco_preview = json.load(f)
        if isinstance(bloco_preview, dict) and bloco_preview.get("Identificador"):
            blocos_finais.append(_ordenar_campos(bloco_preview))  # <--
            identificadores_vistos.add(bloco_preview["Identificador"])
            print(f"✅ Reutilizado preview: {bloco_preview['Identificador']}")
    except Exception as e:
        print("⚠️ Não foi possível ler preview_output.json:", e)

blocos_txt = ler_blocos_do_txt(caminho_txt)
print(f"🔎 {len(blocos_txt)} blocos encontrados no TXT.")

for idx, bloco in enumerate(blocos_txt, start=1):
    ident = bloco["Identificador"]
    if ident in identificadores_vistos:
        continue

    texto_para_llm = formatar_para_llm(bloco)

    estrutura_original, resposta_llm = processar_bloco(
        texto_para_llm,
        prompt_llm,
        bloco.get("Secao", "Nenhuma"),
        preview_identificador=None
    )

    expandidas = _expandir_multi_id(resposta_llm) if resposta_llm else []

    if expandidas:
        for item in expandidas:
            ident_item = item.get("Identificador")
            if not ident_item:
                continue

            rv_llm  = respostas_validas(item.get("Respostas"))
            rv_orig = respostas_validas(bloco["EstruturaOriginal"].get("Respostas"))
            if len(rv_llm) < len(rv_orig):
                faltantes = [r for r in rv_orig if not any(r.get('valor') == x.get('valor') for x in rv_llm)]
                rv_llm.extend(faltantes)
            item["Respostas"] = rv_llm or rv_orig

            if ident_item not in identificadores_vistos:
                blocos_finais.append(_ordenar_campos(item))
                identificadores_vistos.add(ident_item)
    else:
        if ident not in identificadores_vistos:
            blocos_finais.append(_ordenar_campos(bloco["EstruturaOriginal"]))  # <--
            identificadores_vistos.add(ident)

output_path = os.path.join(os.getcwd(), "output_blocos_conciliados.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(blocos_finais, f, indent=2, ensure_ascii=False)

print(f"\n✅ Guardado: {output_path} (total {len(blocos_finais)} blocos)")

try:
    importar_json_para_bd("output_blocos_conciliados.json")
except Exception as e:
    print("⚠️ importar_json_para_bd falhou:", e)

try:
    executar()
except Exception as e:
    print("⚠️ ExcelWriter.executar falhou:", e)
