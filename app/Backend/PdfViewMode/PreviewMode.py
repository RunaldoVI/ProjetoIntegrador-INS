# previewMode.py
import sys
import json
import os
import re
import unicodedata

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))

from Extração.ExtrairPDF import processar_pdf
from LLM.PromptLLM import enviar_pagina_para_llm, obter_pergunta
from DataBaseConnection import importar_json_para_bd  # (mantido para compat)
from PdfViewMode.utils_extracao import processar_bloco

SEPARADOR_BLOCOS = "\n" + "-" * 60 + "\n"
REG_ID_LINHA = re.compile(r"^\s*ID:\s*(?P<id>[^|]+)\|\s*Página:\s*(?P<pag>\d+)\s*$", re.IGNORECASE)
REG_SECAO = re.compile(r"^\s*Sec[çc][ãa]o\s*:\s*(?P<sec>.+?)\s*$", re.IGNORECASE)

OUTPUT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "OutputBlocks"))

def _normalizar_campos_llm(corpo_llm: dict) -> dict:
    if not isinstance(corpo_llm, dict):
        return corpo_llm
    if "Identificador" not in corpo_llm:
        if "ID" in corpo_llm:
            corpo_llm["Identificador"] = str(corpo_llm.pop("ID")).strip()
        elif "id" in corpo_llm:
            corpo_llm["Identificador"] = str(corpo_llm.pop("id")).strip()
    return corpo_llm

def respostas_validas(respostas):
    return [r for r in (respostas or []) if r.get("opção", "").strip() and r.get("valor", "").strip()]

def _slug(txt: str) -> str:
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9._-]+", "_", txt).strip("_")
    return txt[:120]  # evitar nomes gigantes

def _iterar_blocos_txt(txt_path):
    """Gera (bloco_str, identificador, pagina, secao) para TODOS os blocos Pergunta/Resposta."""
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

        ident = None
        pag = None
        secao = None

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

def validar_resposta_llm(resposta):
    erros = []
    if not isinstance(resposta, dict):
        erros.append("❌ A resposta não é um dicionário JSON.")
        return False, erros
    if "Identificador" not in resposta or not str(resposta["Identificador"]).strip():
        erros.append("❌ Campo 'Identificador' está ausente ou vazio.")
    if "Pergunta" not in resposta or not str(resposta["Pergunta"]).strip():
        erros.append("❌ Campo 'Pergunta' está ausente ou vazio.")
    if "Secção" not in resposta:
        erros.append("❌ Campo 'Secção' está ausente.")
    if "Respostas" not in resposta or not isinstance(resposta["Respostas"], list):
        erros.append("❌ Campo 'Respostas' está ausente ou não é uma lista.")
    else:
        rv = [r for r in resposta["Respostas"] if r.get("opção") and r.get("valor")]
        if not rv:
            erros.append("❌ Nenhuma resposta válida com opção + valor numérico.")
    return len(erros) == 0, erros

def _guardar_json(dest_dir, nome_base, data):
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"{nome_base}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

def executar_preview_todos(caminho_pdf, instrucoes="", only_ident=None, only_file=None, reuse_preview=False):
    """
    Processa todos os blocos em modo preview, ou apenas um bloco específico
    se 'only_ident' ou 'only_file' for fornecido. Mantém os outros JSONs intocados.
    """
    # 1) Extrair (gera TXT consolidado com blocos)
    try:
        # Se o teu processar_pdf suportar reaproveitamento, passa o sinal aqui (TODO).
        out_dir, txt_path = processar_pdf(caminho_pdf)
    except Exception as e:
        print(f"❌ Erro ao processar o PDF com ExtrairPDF: {e}")
        return

    if not os.path.exists(txt_path):
        print("❌ Não encontrei o TXT gerado pelo ExtrairPDF.")
        return

    # Pasta do questionário dentro do OutputBlocks
    nome_questionario = os.path.splitext(os.path.basename(caminho_pdf))[0]
    slug_questionario = _slug(nome_questionario) or "Questionario"
    pasta_questionario = os.path.join(OUTPUT_ROOT, slug_questionario)
    os.makedirs(pasta_questionario, exist_ok=True)

    # Se vier only_file, deduzir o ident alvo para filtrar cedo
    effective_only_ident = (only_ident or "").strip()
    if (not effective_only_ident) and only_file:
        cand = _ident_from_filename(only_file)
        if cand:
            effective_only_ident = cand.strip()

    # Prompt base
    prompt_base = obter_pergunta()
    if instrucoes:
        prompt_base += f"\n\n📌 Instruções extra do utilizador:\n{instrucoes}"

    index = []
    total = 0
    gerados = 0

    for i, (bloco_txt, ident_do_txt, pag, secao_do_txt) in enumerate(_iterar_blocos_txt(txt_path), start=1):
        total += 1
        secao_geral = secao_do_txt or "Nenhuma"

        # --- FILTRO de bloco (evita gastar LLM nos outros) ---
        if effective_only_ident:
            if not ident_do_txt or ident_do_txt.strip() != effective_only_ident:
                continue

        # Processa bloco com LLM + heurísticas existentes
        estrutura_original, resposta_raw_llm = processar_bloco(bloco_txt, prompt_base, secao_geral)
        if not estrutura_original or not resposta_raw_llm:
            print(f"⚠️ Bloco {i}: inválido ou LLM sem resposta. Saltar.")
            continue

        try:
            resposta_json = json.loads(resposta_raw_llm if isinstance(resposta_raw_llm, str) else json.dumps(resposta_raw_llm))
            if isinstance(resposta_json, dict) and all(isinstance(v, dict) for v in resposta_json.values()):
                identificador = next(iter(resposta_json))
                corpo_llm = resposta_json[identificador]
                corpo_llm["Identificador"] = identificador
            else:
                corpo_llm = resposta_json

            corpo_llm = _normalizar_campos_llm(corpo_llm)

            # valida
            valido, erros = validar_resposta_llm(corpo_llm)
            if not valido:
                print(f"⚠️ Bloco {i}: estrutura inválida do LLM ({'; '.join(erros)}). Vai gravar versão 'malformado'.")
                base = _slug(f"{slug_questionario}__{ident_do_txt or f'semID_{i}'}") or f"semID_{i}"
                _guardar_json(pasta_questionario, base + "__malformado", {"Erros": erros, "RespostaOriginal": corpo_llm})
                continue

            # merge final (mesma lógica que já tinhas)
            pergunta_llm = corpo_llm.get("Pergunta", "").strip()
            secao_llm = corpo_llm.get("Secção", "").strip()
            if secao_llm != "":
                secao_final = secao_llm.strip()
            else:
                secao_final = (estrutura_original.get("Secção") or secao_geral).strip()
            respostas_llm = respostas_validas(corpo_llm.get("Respostas", []))
            respostas_originais_validas = respostas_validas(estrutura_original.get("Respostas", []))
            if len(respostas_llm) < len(respostas_originais_validas):
                faltantes = [r for r in respostas_originais_validas
                             if not any(r.get('valor') == x.get('valor') for x in respostas_llm)]
                respostas_llm.extend(faltantes)

            resposta_final = {
                "Identificador": (estrutura_original.get("Identificador") or ident_do_txt or "").strip(),
                "Pergunta": (pergunta_llm if pergunta_llm and len(pergunta_llm.split()) >= len(estrutura_original.get("Pergunta", "").split())
                             else estrutura_original.get("Pergunta", "")).strip(),
                "Secção": secao_final,
                "Respostas": respostas_llm or respostas_originais_validas
            }

            # nome do ficheiro: <questionario>__<Identificador>.json (slug)
            ident_final = resposta_final.get("Identificador") or ident_do_txt or f"semID_{i}"
            base_name = _slug(f"{slug_questionario}__{ident_final}") or f"{slug_questionario}__semID_{i}"

            # Se veio only_file e não bate no base_name, não gravar
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

        except Exception as e:
            print(f"❌ Bloco {i}: erro ao interpretar/combinar resposta do LLM: {e}")

    # Atualiza/gera um index.json com o sumário (não mexe nos outros JSONs)
    _guardar_json(pasta_questionario, "_index", {
        "questionario": nome_questionario,
        "total_blocos_detectados": total,
        "total_json_gerados": gerados,
        "itens": index
    })

    print(json.dumps({
        "status": "preview",
        "mensagem": "Pré-visualização concluída.",
        "questionario": nome_questionario,
        "pasta_saida": pasta_questionario,
        "total_blocos": total,
        "gerados": gerados
    }, ensure_ascii=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("caminho_pdf")
    parser.add_argument("instrucoes", nargs="?", default="")
    parser.add_argument("--only-ident", type=str, default=None)
    parser.add_argument("--only-file", type=str, default=None)
    parser.add_argument("--reuse-preview", action="store_true")
    args = parser.parse_args()

    print("🧪 Instruções recebidas via argumento:", args.instrucoes)
    if args.only_ident:
        print(f"🧪 Só processar Identificador: {args.only_ident}")
    if args.only_file:
        print(f"🧪 Só processar Ficheiro: {args.only_file}")
    if args.reuse_preview:
        print("🧪 reuse_preview=ON")

    executar_preview_todos(
        args.caminho_pdf,
        args.instrucoes,
        only_ident=args.only_ident,
        only_file=args.only_file,
        reuse_preview=args.reuse_preview
    )
