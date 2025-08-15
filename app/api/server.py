# server.py — API unificada
# - Preview guarda JSON por bloco em Backend/OutputBlocks/<slug>/
# - "Continuar" (frontend) chama /outputs/<slug>/finalize → consolida ficheiro a ficheiro (sem _index),
#   importa para BD e gera Excel (pipeline igual ao modo automático)
# - Mantém: upload, navegação, chatbot, LLM status/progress, download-excel

from __future__ import annotations

import os
import re
import sys
import json
import unicodedata
import subprocess
from datetime import timedelta

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests

# ---------------- Paths base ----------------
HERE        = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR    = os.path.abspath(os.path.join(HERE, ".."))         # raiz do projeto
BACKEND_DIR = os.path.join(ROOT_DIR, "Backend")
FRONTEND_DIR= os.path.join(ROOT_DIR, "Frontend")
OUTPUT_BLOCKS_ROOT = os.path.join(BACKEND_DIR, "OutputBlocks")

# Permitir "from Backend...." ao correr a partir de /app/api
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ---------------- Model / Env ----------------
CHAT_MODEL = os.getenv("CHAT_MODEL", "mistral")

# Onde o Preview guarda o mapeamento slug → caminho do PDF original
PREVIEW_INDEX = os.path.join("/app", "preview-index.json")

# Pasta onde o Excel final é gerado (mantém como no projeto)
UPLOAD_FOLDER = os.path.join("/app", "pdfs-excels")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- Blueprints / Chatbot ----------------
from user import user_bp  # type: ignore
from Backend.Chatbot.qdrant_query import answer_question  # type: ignore
from Backend.PdfViewMode.PreviewMode import finalizar_a_partir_dos_blocos  # type: ignore

# ---------------- App Flask ----------------
app = Flask(
    __name__,
    static_url_path="/static",
    static_folder=os.path.join(FRONTEND_DIR, "static"),
)
CORS(app)

# Sem cache para estáticos (dev)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(seconds=0)

@app.after_request
def _no_store(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp

# Regista outros blueprints
app.register_blueprint(user_bp)

# ---------------- Helpers ----------------
ID_RE = re.compile(r"^\s*([A-Za-z]+)\.(\d+)\s*$")

def _load_preview_index() -> dict:
    if os.path.exists(PREVIEW_INDEX):
        try:
            with open(PREVIEW_INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}
    return {}

def _save_preview_index(d: dict) -> None:
    with open(PREVIEW_INDEX, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def _natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.findall(r"\d+|\D+", s or "")]

def _slug(txt: str) -> str:
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9._-]+", "_", txt).strip("_")
    return txt[:120] or "x"

def _ident_from_filename(fname: str) -> str:
    base = os.path.splitext(fname)[0]
    if "__" in base:
        return base.split("__", 1)[1]
    return ""

def _ident_key(ident: str):
    if not ident:
        return ("", None)
    s = str(ident).strip()
    m = ID_RE.match(s)
    if m:
        return (m.group(1).upper(), int(m.group(2)))
    return (s.upper(), None)

def _listar_itens(questionario: str):
    """Lista blocos guardados em OutputBlocks/<questionario> em ordem natural.
       Retorna lista de tuplos: [(ident_display, ident_key, filename), ...]
    """
    pasta = os.path.join(OUTPUT_BLOCKS_ROOT, questionario)
    if not os.path.isdir(pasta):
        return []
    itens = []
    for fname in os.listdir(pasta):
        if not fname.endswith(".json"):
            continue
        if fname.startswith("_") or fname.endswith("__malformado.json"):
            continue
        fpath = os.path.join(pasta, fname)
        ident_disp = ""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            ident_disp = (data.get("Identificador") or "").strip()
        except Exception:  # noqa: BLE001
            pass
        if not ident_disp:
            ident_disp = _ident_from_filename(fname)
        if not ident_disp:
            continue
        itens.append((ident_disp, _ident_key(ident_disp), fname))
    itens.sort(key=lambda x: (x[1], x[2]))
    return itens

def _carregar_por_file(questionario: str, fname: str):
    fpath = os.path.join(OUTPUT_BLOCKS_ROOT, questionario, fname)
    if not (os.path.isfile(fpath) and fpath.endswith(".json")):
        return None
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- ENDPOINTS ----------------

# 1) Finalizar a partir dos blocos do preview (sem LLM e sem reconstruir PDF)
@app.post("/outputs/<questionario>/finalize")
def finalize(questionario):
    try:
        res = finalizar_a_partir_dos_blocos(questionario, gerar_excel=True, importar_bd=True)

        # Confirmar no disco (caso a função não tenha conseguido detetar)
        excel_path = os.path.join(UPLOAD_FOLDER, "INS-NHANES-DPQ_J.xlsx")
        excel_exists = os.path.exists(excel_path) or bool(res.get("excel"))

        payload = {
            "ok": True,
            "mensagem": f"Consolidação feita a partir de {res.get('total', 0)} ficheiros JSON.",
            "json_path": res.get("json_path"),
            "excel": excel_exists,
            "bd_import": res.get("bd_import"),
            "erros": res.get("erros", []),
        }
        if excel_exists:
            payload["download_excel"] = "http://localhost:5000/download-excel"

        return jsonify(payload)
    except Exception as e:
        app.logger.exception("Erro no finalize")
        return jsonify({"ok": False, "mensagem": f"{type(e).__name__}: {e}"}), 500

# 2) Chatbot RAG
@app.post('/chat-rag')
def chat_rag():
    try:
        data = request.get_json(silent=True) or {}
        q = (data.get('question') or request.form.get('question') or request.values.get('question') or '').strip()
        if not q:
            return jsonify({'error': 'Pergunta vazia'}), 400
        topk = int(os.getenv("TOPK", "5"))
        resp = answer_question(q, k=topk)
        return jsonify(resp), 200
    except Exception as e:  # noqa: BLE001
        app.logger.exception("Erro em /chat-rag")
        return jsonify({'error': str(e)}), 500

# 3) Upload de PDF (preview ou automático)
@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_pdf():
    if request.method == 'OPTIONS':
        return '', 200

    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de ficheiro inválido'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    questionario_slug = _slug(os.path.splitext(os.path.basename(filepath))[0])
    idx = _load_preview_index()
    idx[questionario_slug] = filepath
    _save_preview_index(idx)

    try:
        modo_bruto = request.form.get("modo", "automatico")
        modo = modo_bruto.replace("--modo", "").strip().lower()
        instrucoes_extra = request.form.get("instrucoes", "").strip()
        reuse_preview = request.form.get("reuse_preview", "").strip().lower() in ("1", "true", "yes")

        args = ["python", "/app/Backend/ProjetoFinal.py", filepath, modo]
        if modo == "preview":
            args.append(instrucoes_extra or "")
        elif modo == "automatico" and reuse_preview:
            args.append("--reuse-preview")

        subprocess.run(args, check=True)

        if modo == "preview":
            # Devolve o primeiro bloco e apontadores de navegação
            itens = _listar_itens(questionario_slug)
            if not itens:
                preview_path = "preview_output.json"
                if os.path.exists(preview_path):
                    with open(preview_path, "r", encoding="utf-8") as f:
                        preview_data = json.load(f)
                    return jsonify(preview_data), 200
                return jsonify({'error': 'Nenhum bloco encontrado para este questionário.'}), 500

            ident0, _key0, fname0 = itens[0]
            data0 = _carregar_por_file(questionario_slug, fname0)

            prev_ident = None
            next_ident = itens[1][0] if len(itens) > 1 else None
            prev_file  = None
            next_file  = itens[1][2] if len(itens) > 1 else None

            return jsonify({
                "questionario": questionario_slug,
                "ident": ident0,
                "file": fname0,
                "prev_ident": prev_ident,
                "next_ident": next_ident,
                "prev_file": prev_file,
                "next_file": next_file,
                "item": data0,
            }), 200

        return jsonify({'status': 'Processamento concluído com sucesso'}), 200

    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Erro ao processar PDF: {str(e)}'}), 500

# 4) Listar itens (para navegação)
@app.get("/outputs/<questionario>/items")
def listar_items(questionario):
    itens = _listar_itens(questionario)
    return jsonify([{"ident": ident, "file": fname} for ident, _key, fname in itens]), 200

# 5) Obter bloco específico (por file ou ident) + prev/next
@app.get("/outputs/<questionario>/item")
def obter_item(questionario):
    file = (request.args.get("file") or "").strip()
    ident = (request.args.get("ident") or "").strip()

    itens = _listar_itens(questionario)
    if not itens:
        return jsonify({"error": f"Sem itens para '{questionario}'."}), 404

    idx_sel = None

    # prioridade ao file
    if file:
        for i, (_disp, _key, fname) in enumerate(itens):
            if fname == file:
                idx_sel = i
                break
        if idx_sel is None:
            return jsonify({"error": f"Ficheiro '{file}' não encontrado em {questionario}."}), 404
    else:
        # senão, tenta pelo ident
        req_key = _ident_key(ident) if ident else itens[0][1]
        for i, (_disp, key, _fname) in enumerate(itens):
            if key == req_key:
                idx_sel = i
                break
        if idx_sel is None:
            idx_sel = 0

    ident_disp, _key, fname = itens[idx_sel]
    data = _carregar_por_file(questionario, fname)
    if data is None:
        return jsonify({"error": f"Erro a ler '{fname}'"}), 500

    prev_ident = itens[idx_sel-1][0] if idx_sel > 0 else None
    next_ident = itens[idx_sel+1][0] if idx_sel < len(itens)-1 else None
    prev_file  = itens[idx_sel-1][2] if idx_sel > 0 else None
    next_file  = itens[idx_sel+1][2] if idx_sel < len(itens)-1 else None

    return jsonify({
        "questionario": questionario,
        "ident": ident_disp,
        "file": fname,
        "prev_ident": prev_ident,
        "next_ident": next_ident,
        "prev_file": prev_file,
        "next_file": next_file,
        "item": data,
    }), 200

# 6) LLM status
@app.get('/llm-status')
def llm_status():
    try:
        response = requests.post("http://ollama:11434/api/show", json={"model": CHAT_MODEL}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pronto = "modelfile" in data
            return jsonify({"ready": pronto})
        else:
            return jsonify({"ready": False, "error": "Erro na resposta do Ollama"})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ready": False, "error": str(e)})

# 7) LLM progress
@app.get('/llm-progress')
def llm_progress():
    try:
        with open("/app/ollama-progress.log", "r") as f:
            lines = f.readlines()
        completed = total = 0
        for line in reversed(lines):
            if '"completed":' in line and '"total":' in line:
                data = json.loads(line.strip())
                completed = int(data.get("completed", 0))
                total = int(data.get("total", 0))
                break
        if total == 0:
            return jsonify({"progress": 0})
        percent = round(100 * completed / total, 2)
        return jsonify({"progress": percent})
    except Exception as e:  # noqa: BLE001
        return jsonify({"progress": 0, "error": str(e)})

# 8) Download do Excel final
@app.get('/download-excel')
def download_excel():
    excel_path = os.path.join(UPLOAD_FOLDER, "INS-NHANES-DPQ_J.xlsx")
    if os.path.exists(excel_path):
        return send_file(
            excel_path,
            as_attachment=True,
            download_name="INS-NHANES-DPQ_J.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        return jsonify({'error': 'Ficheiro Excel não encontrado'}), 404

# 9) Reprocessar apenas um bloco (aplica instruções extra)
@app.post("/outputs/<questionario>/item/reprocess")
def reprocess_item(questionario):
    try:
        data = request.get_json(force=True) or {}
        ident = (data.get("ident") or "").strip()
        fname = (data.get("file") or "").strip()
        instrucoes = (data.get("instructions") or "").strip()

        if not (ident or fname):
            return jsonify({"error": "É necessário 'ident' ou 'file'."}), 400

        # descobre o PDF original deste questionário
        idx = _load_preview_index()
        pdf_path = idx.get(questionario)
        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({"error": f"PDF para '{questionario}' não encontrado."}), 404

        # Montar argumentos para reprocesso focado
        args = ["python", "/app/Backend/ProjetoFinal.py", pdf_path, "preview"]
        if instrucoes:
            args.append(instrucoes)
        args.append("--reuse-preview")
        if ident:
            args += ["--only-ident", ident]
        if fname:
            args += ["--only-file", fname]

        subprocess.run(args, check=True)

        # Recarregar lista e devolver o bloco atualizado
        itens = _listar_itens(questionario)
        if not itens:
            return jsonify({"error": "Sem itens após reprocesso."}), 500

        idx_sel = 0
        if fname:
            for i, (_disp, _key, nm) in enumerate(itens):
                if nm == fname:
                    idx_sel = i
                    break
        elif ident:
            req_key = _ident_key(ident)
            for i, (_disp, key, _nm) in enumerate(itens):
                if key == req_key:
                    idx_sel = i
                    break

        ident_disp, _key, real_fname = itens[idx_sel]
        data_item = _carregar_por_file(questionario, real_fname)

        prev_ident = itens[idx_sel-1][0] if idx_sel > 0 else None
        next_ident = itens[idx_sel+1][0] if idx_sel < len(itens)-1 else None
        prev_file  = itens[idx_sel-1][2] if idx_sel > 0 else None
        next_file  = itens[idx_sel+1][2] if idx_sel < len(itens)-1 else None

        return jsonify({
            "questionario": questionario,
            "ident": ident_disp,
            "file": real_fname,
            "prev_ident": prev_ident,
            "next_ident": next_ident,
            "prev_file": prev_file,
            "next_file": next_file,
            "item": data_item,
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Falha ao reprocessar bloco: {str(e)}"}), 500
    except Exception as e:  # noqa: BLE001
        app.logger.exception("Erro em /item/reprocess")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
