# previewMode.py
import sys
import json
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))

from Extração.ExtrairPDF import processar_pdf
from LLM.PromptLLM import enviar_pagina_para_llm, obter_pergunta
from DataBaseConnection import importar_json_para_bd  # (mantido para compat)
from PdfViewMode.utils_extracao import processar_bloco

SEPARADOR_BLOCOS = "\n" + "-" * 60 + "\n"
REG_ID_LINHA = re.compile(r"^\s*ID:\s*(?P<id>[^|]+)\|\s*Página:\s*(?P<pag>\d+)\s*$", re.IGNORECASE)
REG_SECAO = re.compile(r"^\s*Sec[çc][ãa]o\s*:\s*(?P<sec>.+?)\s*$", re.IGNORECASE)

def _normalizar_campos_llm(corpo_llm: dict) -> dict:
    """Aceita 'ID'/'id' e mapeia para 'Identificador' antes da validação."""
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

def _extrair_primeiro_bloco_txt(txt_path):
    """Lê o TXT do ExtrairPDF e devolve: bloco_str, identificador, pagina, secao (ou None)."""
    with open(txt_path, "r", encoding="utf-8") as f:
        conteudo = f.read()

    blocos = [b.strip() for b in conteudo.split(SEPARADOR_BLOCOS) if b.strip()]
    if not blocos:
        return None, None, None, None

    for b in blocos:
        linhas = [l.rstrip() for l in b.splitlines()]
        if not linhas:
            continue
        if any(l.strip().lower().startswith("pergunta:") for l in linhas) and \
           any(l.strip().lower().startswith("resposta:") for l in linhas):

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

            return b, ident, pag, secao

    return blocos[0], None, None, None

# ------------ prompts para reanálise (sem re-extrair PDF) ------------
def _montar_contexto_reanalise(estrutura_antiga: dict) -> str:
    """
    Contexto compacto para o LLM: usamos exatamente o que já temos no preview_output.json.
    """
    payload = {
        "Identificador": estrutura_antiga.get("Identificador", ""),
        "Secção": estrutura_antiga.get("Secção", "Nenhuma"),
        "Pergunta": estrutura_antiga.get("Pergunta", ""),
        "Respostas": estrutura_antiga.get("Respostas", []),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def _prompt_reanalise(instrucoes: str) -> str:
    """
    Pede para REFINAR a estrutura recebida (JSON) aplicando as instruções do utilizador.
    Não reanalisa PDF; não inventa opções/valores; manter tudo se não for pedido para remover.
    """
    return (
        "Refina a estrutura JSON fornecida (sem reanalisar o PDF). "
        "Mantém 'Identificador' igual. Podes reescrever 'Secção' e 'Pergunta' e ajustar 'Respostas' "
        "apenas conforme as instruções do utilizador. "
        "Não inventes novas opções/valores; preserva todas as opções originais, a menos que o utilizador peça para remover. "
        "Devolve JSON válido com os campos: 'Identificador', 'Secção', 'Pergunta', 'Respostas' (lista de objetos com 'opção' e 'valor').\n\n"
        f"Instruções do utilizador:\n{instrucoes}"
    )

def executar_preview(caminho_pdf, instrucoes=""):
    # 1) Extrair (gera previews + TXT por página)
    try:
        out_dir, txt_path = processar_pdf(caminho_pdf)
    except Exception as e:
        print(f"❌ Erro ao processar o PDF com ExtrairPDF: {e}")
        return

    if not os.path.exists(txt_path):
        print("❌ Não encontrei o TXT gerado pelo ExtrairPDF.")
        return

    # 2) Ler o primeiro bloco para o preview
    bloco_txt, ident_do_txt, pag, secao_do_txt = _extrair_primeiro_bloco_txt(txt_path)
    if not bloco_txt:
        print("❌ Não foi possível encontrar um bloco 'Pergunta/Resposta' no TXT.")
        return

    secao_geral = secao_do_txt or "Nenhuma"

    # 🔁 REANÁLISE (fluxo 'não gosto'): usa estrutura existente + instruções
    if instrucoes.strip() and os.path.exists("preview_output.json"):
        with open("preview_output.json", "r", encoding="utf-8") as f:
            estrutura_antiga = json.load(f)

        contexto = _montar_contexto_reanalise(estrutura_antiga)
        prompt = _prompt_reanalise(instrucoes)

        print("\n🔁 Reanalisando com novas instruções (sem re-extrair PDF)...\n")
        resposta_raw = enviar_pagina_para_llm(contexto, prompt)

        try:
            resposta_json = json.loads(resposta_raw if isinstance(resposta_raw, str) else json.dumps(resposta_raw))

            # aceitar formato { "DPQ.010": { ... } } ou direto
            if isinstance(resposta_json, dict) and len(resposta_json) == 1 and all(isinstance(v, dict) for v in resposta_json.values()):
                identificador = next(iter(resposta_json))
                corpo_llm = resposta_json[identificador]
                corpo_llm["Identificador"] = identificador
            else:
                corpo_llm = resposta_json

            corpo_llm = _normalizar_campos_llm(corpo_llm)

            # merge defensivo das respostas (se LLM cortou, repomos as originais)
            respostas_llm_validas = respostas_validas(corpo_llm.get("Respostas", []))
            respostas_originais_validas = respostas_validas(estrutura_antiga.get("Respostas", []))
            if len(respostas_llm_validas) < len(respostas_originais_validas):
                faltantes = [r for r in respostas_originais_validas
                             if not any(r.get('valor') == x.get('valor') for x in respostas_llm_validas)]
                respostas_llm_validas.extend(faltantes)

            estrutura_final = {
                "Identificador": estrutura_antiga.get("Identificador") or ident_do_txt or "",
                "Pergunta": (corpo_llm.get("Pergunta") or estrutura_antiga.get("Pergunta") or "").strip(),
                "Secção": (corpo_llm.get("Secção") or estrutura_antiga.get("Secção") or secao_geral or "Nenhuma").strip(),
                "Respostas": respostas_llm_validas or respostas_originais_validas
            }

            with open("preview_output.json", "w", encoding="utf-8") as f:
                json.dump(estrutura_final, f, indent=2, ensure_ascii=False)

            print(json.dumps({"status": "preview", "mensagem": "Reanálise com sucesso."}))
            return

        except Exception as e:
            print(f"❌ Erro ao interpretar nova resposta: {e}")
            return

    # ▶️ 1ª Execução normal
    pergunta = obter_pergunta()
    if instrucoes:
        pergunta += f"\n\n📌 Instruções extra do utilizador:\n{instrucoes}"

    print("\n📨 Prompt enviado para o LLM:\n", pergunta)
    estrutura_original, resposta_raw_llm = processar_bloco(bloco_txt, pergunta, secao_geral)

    if not estrutura_original or not resposta_raw_llm:
        print("❌ Bloco inválido ou LLM sem resposta. A terminar o preview aqui.")
        return

    try:
        resposta_json = json.loads(resposta_raw_llm if isinstance(resposta_raw_llm, str) else json.dumps(resposta_raw_llm))

        if isinstance(resposta_json, dict) and all(isinstance(v, dict) for v in resposta_json.values()):
            identificador = next(iter(resposta_json))
            corpo_llm = resposta_json[identificador]
            corpo_llm["Identificador"] = identificador
        else:
            corpo_llm = resposta_json

        corpo_llm = _normalizar_campos_llm(corpo_llm)

        # Validação
        valido, erros = validar_resposta_llm(corpo_llm)
        if not valido:
            print("⚠️ LLM respondeu com estrutura inválida:")
            for e in erros:
                print("   ", e)
            with open("preview_output_malformado.json", "w", encoding="utf-8") as f:
                json.dump({"Erro": erros, "RespostaOriginal": corpo_llm}, f, indent=2, ensure_ascii=False)
            print("💾 Estrutura malformada guardada em 'preview_output_malformado.json'")
            return

        # Merge final (preferimos campos do LLM; completamos com original quando necessário)
        pergunta_llm = corpo_llm.get("Pergunta", "").strip()
        secao_llm = corpo_llm.get("Secção", "").strip()
        respostas_llm = respostas_validas(corpo_llm.get("Respostas", []))
        respostas_originais_validas = respostas_validas(estrutura_original.get("Respostas", []))
        if len(respostas_llm) < len(respostas_originais_validas):
            faltantes = [r for r in respostas_originais_validas
                         if not any(r.get('valor') == x.get('valor') for x in respostas_llm)]
            respostas_llm.extend(faltantes)

        resposta_final = {
            "Identificador": estrutura_original.get("Identificador") or ident_do_txt or "",
            "Pergunta": pergunta_llm if pergunta_llm and len(pergunta_llm.split()) >= len(estrutura_original.get("Pergunta", "").split()) else estrutura_original.get("Pergunta"),
            "Secção": secao_llm if secao_llm and secao_llm.lower() != "nenhuma" else (estrutura_original.get("Secção") or secao_geral),
            "Respostas": respostas_llm or respostas_originais_validas
        }

    except Exception as e:
        print(f"❌ Erro ao interpretar ou combinar a resposta do LLM: {e}")
        return

    print(f"\n🧠 Pré-visualização - Primeiro bloco:")
    print(json.dumps(resposta_final, indent=2, ensure_ascii=False))

    print(f"\n🧠 Resposta do LLM (completa + merge se necessário):")
    print(json.dumps(resposta_final, indent=2, ensure_ascii=False))

    with open("preview_output.json", "w", encoding="utf-8") as f:
        json.dump(resposta_final, f, indent=2, ensure_ascii=False)

    print(json.dumps({"status": "preview", "mensagem": "Pré-visualização concluída."}))

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso: python PreviewMode.py caminho_para_pdf [instrucoes]")
        sys.exit(1)

    caminho_pdf = sys.argv[1]
    instrucoes = sys.argv[2] if len(sys.argv) > 2 else ""
    print("🧪 Instruções recebidas via argumento:", instrucoes)
    executar_preview(caminho_pdf, instrucoes)
