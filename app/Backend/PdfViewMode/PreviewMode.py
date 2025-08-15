from __future__ import annotations

import os
import re
import sys
import json
import unicodedata
import argparse
from typing import Generator, Iterable, List, Tuple, Dict, Any

# -------------------------------
# Caminhos base e sys.path
# -------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))             # /app/Backend
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))                                 # /app
DB_DIR   = os.path.abspath(os.path.join(BASE_DIR, "..", "Database"))                 # /app/Database
sys.path.append(BASE_DIR)
sys.path.append(DB_DIR)

# -------------------------------
# Imports do projeto (topo! sem imports locais em funções)
# -------------------------------
from Extração.ExtrairPDF import processar_pdf                 # type: ignore
from LLM.PromptLLM import obter_pergunta                      # type: ignore
from PdfViewMode.utils_extracao import processar_bloco        # type: ignore
from DataBaseConnection import importar_json_para_bd          # type: ignore
from ExcelWriter.ExcelWriter import executar                  # type: ignore

# Onde os JSONs por bloco são guardados
OUTPUT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "OutputBlocks"))

# Delimitadores/regex para iterar blocos no TXT consolidado
SEPARADOR_BLOCOS = "\n" + "-" * 60 + "\n"
REG_ID_LINHA = re.compile(r"^\s*ID:\s*(?P<id>[^|]+)\|\s*Página:\s*(?P<pag>\d+)\s*$", re.IGNORECASE)
REG_SECAO    = re.compile(r"^\s*Sec[çc][ãa]o\s*:\s*(?P<sec>.+?)\s*$", re.IGNORECASE)

# -------------------------------
# Utils
# -------------------------------
def _slug(txt: str) -> str:
    if not txt:
        return "x"
    s = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    return s[:120] or "x"

def _natural_key(s: str) -> List[Any]:
    return [int(t) if t.isdigit() else t.lower() for t in re.findall(r"\d+|\D+", s or "")]

def _ident_from_filename(filename: str) -> str | None:
    base = os.path.splitext(os.path.basename(filename))[0]
    if "__" in base:
        return base.split("__", 1)[1]
    return None

def _guardar_json(dest_dir: str, nome_base: str, data: Dict[str, Any]) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"{nome_base}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

def respostas_validas(respostas: Iterable[Dict[str, Any]] | None) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in (respostas or []):
        if isinstance(r, dict):
            opt = str(r.get("opção", "")).strip()
            val = str(r.get("valor", "")).strip()
            if opt and val:
                out.append({"opção": opt, "valor": val})
    return out

def _normalizar_campos_llm(corpo_llm: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(corpo_llm, dict):
        return corpo_llm  # type: ignore
    if "Identificador" not in corpo_llm:
        if "ID" in corpo_llm:
            corpo_llm["Identificador"] = str(corpo_llm.pop("ID")).strip()
        elif "id" in corpo_llm:
            corpo_llm["Identificador"] = str(corpo_llm.pop("id")).strip()
    return corpo_llm

def validar_resposta_llm(resposta: Dict[str, Any]) -> Tuple[bool, List[str]]:
    erros: List[str] = []
    if not isinstance(resposta, dict):
        return False, ["❌ A resposta não é um dicionário JSON."]
    if not str(resposta.get("Identificador", "")).strip():
        erros.append("❌ Campo 'Identificador' está ausente ou vazio.")
    if not str(resposta.get("Pergunta", "")).strip():
        erros.append("❌ Campo 'Pergunta' está ausente ou vazio.")
    if "Secção" not in resposta:
        erros.append("❌ Campo 'Secção' está ausente.")
    if not isinstance(resposta.get("Respostas"), list):
        erros.append("❌ Campo 'Respostas' está ausente ou não é uma lista.")
    else:
        if not respostas_validas(resposta.get("Respostas")):
            erros.append("❌ Nenhuma resposta válida com opção + valor numérico.")
    return len(erros) == 0, erros

# -------------------------------
# Iterar blocos a partir do TXT
# -------------------------------
def _iterar_blocos_txt(txt_path: str) -> Generator[Tuple[str, str | None, int | None, str], None, None]:
    with open(txt_path, "r", encoding="utf-8") as f:
        conteudo = f.read()

    blocos = [b.strip() for b in conteudo.split(SEPARADOR_BLOCOS) if b.strip()]
    for b in blocos:
        linhas = [l.rstrip() for l in b.splitlines()]
        if not linhas:
            continue

        tem_pergunta = any(l.strip().lower().startswith("pergunta:") for l in linhas)
        tem_resposta = any(l.strip().lower().startswith("resposta:") for l in linhas)
        if not (tem_pergunta and tem_resposta):
            continue

        ident: str | None = None
        pag: int | None = None
        secao: str | None = None

        m = REG_ID_LINHA.match(linhas[0]) if linhas else None
        if m:
            ident = m.group("id").strip()
            try:
                pag = int(m.group("pag"))
            except Exception:
                pag = None

        for l in linhas[:5]:
            ms = REG_SECAO.match(l)
            if ms:
                secao = ms.group("sec").strip()
                break

        yield b, ident, pag, (secao or "Nenhuma")

# -------------------------------
# Modo PREVIEW — gerar JSON por bloco
# -------------------------------
def executar_preview_todos(
    caminho_pdf: str,
    instrucoes: str = "",
    only_ident: str | None = None,
    only_file: str | None = None,
    reuse_preview: bool = False,  # (mantido para compat)
) -> Dict[str, Any]:

    # 1) Extrair → TXT consolidado
    out_dir, txt_path = processar_pdf(caminho_pdf)
    if not os.path.exists(txt_path):
        raise FileNotFoundError("TXT consolidado não encontrado após ExtrairPDF.")

    # 2) Pasta do questionário
    nome_questionario  = os.path.splitext(os.path.basename(caminho_pdf))[0]
    slug_questionario  = _slug(nome_questionario) or "Questionario"
    pasta_questionario = os.path.join(OUTPUT_ROOT, slug_questionario)
    os.makedirs(pasta_questionario, exist_ok=True)

    # 3) only_file → deduzir ident
    effective_only_ident = (only_ident or "").strip()
    if (not effective_only_ident) and only_file:
        cand = _ident_from_filename(only_file)
        if cand:
            effective_only_ident = cand.strip()

    # 4) Prompt LLM
    prompt_base = obter_pergunta()
    if instrucoes:
        prompt_base += f"\n\n📌 Instruções extra do utilizador:\n{instrucoes}"

    index: List[Dict[str, Any]] = []
    total = 0
    gerados = 0

    # 5) Percorrer blocos do TXT e gerar JSON por bloco
    for i, (bloco_txt, ident_do_txt, pag, secao_do_txt) in enumerate(_iterar_blocos_txt(txt_path), start=1):
        total += 1

        if effective_only_ident:
            if not ident_do_txt or ident_do_txt.strip() != effective_only_ident:
                continue

        secao_geral = secao_do_txt or "Nenhuma"

        estrutura_original, resposta_raw_llm = processar_bloco(
            bloco_txt, prompt_base, secao_geral, preview_identificador=None
        )
        if not estrutura_original or not resposta_raw_llm:
            base_mal = _slug(f"{slug_questionario}__{ident_do_txt or f'semID_{i}'}") or f"{slug_questionario}__semID_{i}"
            _guardar_json(pasta_questionario, base_mal + "__malformado", {
                "Erros": ["LLM sem resposta ou estrutura_original vazia"],
                "BlocoTXT": bloco_txt[:6000]
            })
            continue

        # Interpretar resposta do LLM
        try:
            if isinstance(resposta_raw_llm, str):
                resposta_json = json.loads(resposta_raw_llm)
            else:
                resposta_json = resposta_raw_llm  # type: ignore

            if isinstance(resposta_json, dict) and resposta_json and all(isinstance(v, dict) for v in resposta_json.values()):
                ident_map = next(iter(resposta_json))
                corpo_llm = resposta_json[ident_map]
                corpo_llm["Identificador"] = ident_map
            else:
                corpo_llm = resposta_json
        except Exception:
            corpo_llm = {}

        corpo_llm = _normalizar_campos_llm(corpo_llm if isinstance(corpo_llm, dict) else {})

        # Validação
        valido, erros = validar_resposta_llm(corpo_llm)
        if not valido:
            base = _slug(f"{slug_questionario}__{ident_do_txt or f'semID_{i}'}") or f"{slug_questionario}__semID_{i}"
            _guardar_json(pasta_questionario, base + "__malformado", {
                "Erros": erros,
                "RespostaOriginal": corpo_llm,
            })
            continue

        # Fusão (LLM + original)
        pergunta_llm  = str(corpo_llm.get("Pergunta", "")).strip()
        pergunta_orig = str(estrutura_original.get("Pergunta", "")).strip()
        secao_llm     = str(corpo_llm.get("Secção", "")).strip()
        secao_final   = (secao_llm or estrutura_original.get("Secção") or secao_geral).strip() or "Nenhuma"

        resp_llm          = respostas_validas(corpo_llm.get("Respostas"))
        resp_orig_validas = respostas_validas(estrutura_original.get("Respostas"))
        if len(resp_llm) < len(resp_orig_validas):
            faltantes = [r for r in resp_orig_validas if not any(r.get('valor') == x.get('valor') for x in resp_llm)]
            resp_llm.extend(faltantes)

        resposta_final = {
            "Identificador": (estrutura_original.get("Identificador") or ident_do_txt or "").strip(),
            "Pergunta": (pergunta_llm if pergunta_llm and len(pergunta_llm.split()) >= len(pergunta_orig.split())
                         else pergunta_orig),
            "Secção": secao_final,
            "Respostas": resp_llm or resp_orig_validas,
        }

        ident_final = resposta_final.get("Identificador") or ident_do_txt or f"semID_{i}"
        base_name   = _slug(f"{slug_questionario}__{ident_final}") or f"{slug_questionario}__semID_{i}"

        if only_file:
            alvo = os.path.splitext(os.path.basename(only_file))[0]
            if base_name != alvo:
                continue

        path_json = _guardar_json(pasta_questionario, base_name, resposta_final)
        index.append({
            "ficheiro": os.path.basename(path_json),
            "identificador": ident_final,
            "pagina": pag,
            "secao": resposta_final.get("Secção", ""),
        })
        gerados += 1

    # _index.json (só para navegação; finalize não depende disto)
    _guardar_json(pasta_questionario, "_index", {
        "questionario": nome_questionario,
        "total_blocos_detectados": total,
        "total_json_gerados": gerados,
        "itens": index,
    })

    return {
        "status": "preview",
        "mensagem": "Pré-visualização concluída.",
        "questionario": nome_questionario,
        "pasta_saida": pasta_questionario,
        "total_blocos": total,
        "gerados": gerados,
    }

# -------------------------------
# FINALIZE — consolidar e gerar Excel/BD
# -------------------------------
def finalizar_a_partir_dos_blocos(
    questionario: str,
    gerar_excel: bool = True,
    importar_bd: bool = True,
) -> Dict[str, Any]:
    
    print("[DEBUG] PreviewMode:", __file__)
    print("[DEBUG] BASE_DIR   :", BASE_DIR)
    print("[DEBUG] PROJECT_ROOT:", PROJECT_ROOT)
    print("[DEBUG] CWD antes  :", os.getcwd())
    """
    Consolida TODOS os JSONs de OutputBlocks/<slug>/ → Backend/output_blocos_conciliados.json
    e corre o MESMO pipeline do modo automático:
      importar_json_para_bd("output_blocos_conciliados.json") → ExcelWriter.executar()
    Sem reler PDF e sem chamar LLM.
    """
    slug  = _slug(questionario)
    pasta = os.path.join(OUTPUT_ROOT, slug)
    if not os.path.isdir(pasta):
        raise FileNotFoundError(f"Pasta do questionário não encontrada: {pasta}")

    blocos: List[Dict[str, Any]] = []
    erros:  List[str] = []

    # --- ler ficheiro a ficheiro (ignora auxiliares) ---
    for nome in sorted(os.listdir(pasta)):
        if not nome.lower().endswith(".json"):
            continue
        if nome.startswith("_") or nome.lower() in {"_index.json", "preview_output.json"} or nome.endswith("__malformado.json"):
            continue

        try:
            with open(os.path.join(pasta, nome), "r", encoding="utf-8") as jf:
                raw = json.load(jf)

            respostas_norm: List[Dict[str, str]] = []
            for r in (raw.get("Respostas") or []):
                if isinstance(r, dict):
                    opt = r.get("opção") or r.get("option") or r.get("label") or r.get("texto") or ""
                    val = r.get("valor") or r.get("value")  or r.get("numero") or r.get("code")  or ""
                    respostas_norm.append({"opção": str(opt), "valor": str(val)})
                else:
                    respostas_norm.append({"opção": str(r), "valor": ""})

            blocos.append({
                "Identificador": (raw.get("Identificador") or "").strip(),
                "Secção":        (raw.get("Secção") or "Nenhuma").strip() or "Nenhuma",
                "Pergunta":      (raw.get("Pergunta") or "").strip(),
                "Respostas":     respostas_norm,
            })
        except Exception as e:
            erros.append(f"{nome}: {e}")

    # ordenação natural por Identificador
    blocos.sort(key=lambda b: _natural_key(b.get("Identificador", "")))

    # --- escrever o JSON consolidado EXACTAMENTE onde o automático espera ---
    out_path = os.path.join(PROJECT_ROOT, "output_blocos_conciliados.json")  # BASE_DIR = /app/Backend
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(blocos, f, indent=2, ensure_ascii=False)

    # --- pipeline do AUTOMÁTICO: importar_json_para_bd → ExcelWriter.executar ---
    bd_ok      = False
    excel_ok   = False
    excel_path = None
    excel_dir  = os.path.join(PROJECT_ROOT, "pdfs-excels")

    # dica: alguns writers escolhem template pela "context var"
    os.environ["CURRENT_QUESTIONNAIRE_SLUG"] = slug
    os.environ["RUN_CONTEXT"] = "preview_finalize"

    # captura estado dos .xlsx antes, para detetar mudanças
    def _xlsx_snapshot():
        if not os.path.isdir(excel_dir):
            return {}
        return {fn: os.path.getmtime(os.path.join(excel_dir, fn))
                for fn in os.listdir(excel_dir) if fn.lower().endswith(".xlsx")}

    snap_before = _xlsx_snapshot()

    orig_cwd = os.getcwd()
    try:
        # MUITO IMPORTANTE: replicar o CWD do automático
        os.chdir(PROJECT_ROOT)  # /app (raiz), para ExcelWriter ver 'pdfs-excels'

        if importar_bd:
            try:
                # passar CAMINHO RELATIVO como no automático
                from DataBaseConnection import importar_json_para_bd  # type: ignore
                importar_json_para_bd("output_blocos_conciliados.json")
                bd_ok = True
            except Exception as e:
                print("⚠️ importar_json_para_bd falhou:", e)

        if gerar_excel:
            try:
                from ExcelWriter.ExcelWriter import executar  # type: ignore
                executar()  # exatamente como no automático
            except Exception as e:
                print("⚠️ ExcelWriter.executar falhou:", e)
            else:
                # escolher o .xlsx mais recente pós-execução
                snap_after = _xlsx_snapshot()
                changed = []
                for fn, mt in snap_after.items():
                    if fn not in snap_before or mt > snap_before.get(fn, 0):
                        changed.append((mt, fn))
                if changed:
                    changed.sort()
                    newest = changed[-1][1]
                    excel_path = os.path.join(excel_dir, newest)
                    excel_ok = True
    finally:
        os.chdir(orig_cwd)

    return {
        "ok": True,
        "slug": slug,
        "json_path": out_path,
        "total": len(blocos),
        "bd_import": bd_ok,
        "excel": excel_ok,
        "excel_path": excel_path,
        "erros": erros,
    }

# -------------------------------
# CLI — apenas para gerar preview
# -------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview de questionário: gerar JSON por bloco.")
    parser.add_argument("caminho_pdf", help="Caminho para o PDF do questionário")
    parser.add_argument("instrucoes", nargs="?", default="", help="Instruções extra para o LLM")
    parser.add_argument("--only-ident", dest="only_ident", type=str, default=None)
    parser.add_argument("--only-file",  dest="only_file",  type=str, default=None)
    parser.add_argument("--reuse-preview", dest="reuse_preview", action="store_true")
    args = parser.parse_args()

    res = executar_preview_todos(
        args.caminho_pdf,
        args.instrucoes,
        only_ident=args.only_ident,
        only_file=args.only_file,
        reuse_preview=args.reuse_preview,
    )
    print(json.dumps(res, ensure_ascii=False))