import sys
import json
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))

from Extração.TextExtractorPDF import extrair_texto_para_txt
from LLM.PromptLLM import enviar_pagina_para_llm, obter_pergunta
from Extração.VisualExtractorPDF import extrair_blocos_visuais
from Limpeza.PreProcessamento import (
    identificar_secao_mais_comum,
    extrair_blocos_limpos,
)
from DataBaseConnection import importar_json_para_bd
from PdfViewMode.utils_extracao import processar_bloco

# 🧹 Filtra apenas respostas com texto e valor
def respostas_validas(respostas):
    return [r for r in respostas if r.get("opção", "").strip() and r.get("valor", "").strip()]

def executar_preview(caminho_pdf, instrucoes=""):
    caminho_txt = extrair_texto_para_txt(caminho_pdf)
    extrair_blocos_visuais(caminho_pdf) 

    with open(caminho_txt, "r", encoding="utf-8") as f:
        conteudo = f.read()

    paginas = [p.strip() for p in conteudo.split("===== Página") if p.strip()]
    secao_geral = identificar_secao_mais_comum(paginas)

    if not paginas:
        print("❌ Nenhuma página encontrada no PDF.")
        return

    texto_pagina = paginas[0]
    blocos = extrair_blocos_limpos(texto_pagina)

    if not blocos:
        print("❌ Primeira página não tem blocos válidos.")
        return

    # 🔁 REANÁLISE: Se houver instruções e ficheiro anterior
    if instrucoes.strip() and os.path.exists("preview_output.json"):
        with open("preview_output.json", "r", encoding="utf-8") as f:
            estrutura_antiga = json.load(f)

        bloco_original = f"{estrutura_antiga['Identificador']} {estrutura_antiga['Pergunta']}"
        prompt = obter_pergunta(instrucoes)

        print("\n🔁 Reanalisando com novas instruções...\n")
        resposta_raw = enviar_pagina_para_llm(bloco_original, prompt)

        try:
            resposta_json = json.loads(resposta_raw if isinstance(resposta_raw, str) else json.dumps(resposta_raw))
            if isinstance(resposta_json, dict) and len(resposta_json) == 1:
                identificador = next(iter(resposta_json))
                corpo_llm = resposta_json[identificador]
                corpo_llm["Identificador"] = identificador
            else:
                corpo_llm = resposta_json

            pergunta_llm = corpo_llm.get("Pergunta", "").strip()
            secao_llm = corpo_llm.get("Secção", "").strip()
            respostas_llm = corpo_llm.get("Respostas", [])

            respostas_llm_validas = respostas_validas(respostas_llm)
            respostas_originais_validas = respostas_validas(estrutura_antiga.get("Respostas", []))

            estrutura_final = {
                "Identificador": estrutura_antiga["Identificador"],
                "Pergunta": pergunta_llm if pergunta_llm and len(pergunta_llm.split()) >= len(estrutura_antiga.get("Pergunta", "").split()) else estrutura_antiga.get("Pergunta"),
                "Secção": secao_llm if secao_llm and secao_llm.lower() != "nenhuma" else estrutura_antiga.get("Secção"),
                "Respostas": respostas_llm_validas if len(respostas_llm_validas) >= len(respostas_originais_validas) else respostas_originais_validas
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

    for j, bloco in enumerate(blocos, start=1):
        if bloco["tipo"] != "Pergunta":
            continue
        if len(bloco["texto"].strip()) < 20:
            continue

        print("\n📨 Prompt enviado para o LLM:\n", pergunta)
        estrutura_original, resposta_raw_llm = processar_bloco(bloco["texto"], pergunta, secao_geral)

        if not estrutura_original or not resposta_raw_llm:
            print("❌ Bloco inválido ou LLM sem resposta. A terminar o preview aqui.")
            break  # força saída após o primeiro bloco

        try:
            resposta_json = json.loads(resposta_raw_llm if isinstance(resposta_raw_llm, str) else json.dumps(resposta_raw_llm))

            if isinstance(resposta_json, dict) and all(isinstance(v, dict) for v in resposta_json.values()):
                identificador = next(iter(resposta_json))
                corpo_llm = resposta_json[identificador]
                corpo_llm["Identificador"] = identificador
            else:
                corpo_llm = resposta_json

            # ✅ Validação estruturada
            valido, erros = validar_resposta_llm(corpo_llm)

            if not valido:
                print("⚠️ LLM respondeu com estrutura inválida:")
                for e in erros:
                    print("   ", e)

                with open("preview_output_malformado.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "Erro": erros,
                        "RespostaOriginal": corpo_llm
                    }, f, indent=2, ensure_ascii=False)

                print("💾 Estrutura malformada guardada em 'preview_output_malformado.json'")
                break  # termina o preview após erro
            else:
                pergunta_llm = corpo_llm.get("Pergunta", "").strip()
                secao_llm = corpo_llm.get("Secção", "").strip()
                respostas_llm = corpo_llm.get("Respostas", [])

                respostas_llm_validas = respostas_validas(respostas_llm)
                respostas_originais_validas = respostas_validas(estrutura_original.get("Respostas", []))

                resposta_final = {
                    "Identificador": estrutura_original.get("Identificador"),
                    "Pergunta": pergunta_llm if pergunta_llm and len(pergunta_llm.split()) >= len(estrutura_original.get("Pergunta", "").split()) else estrutura_original.get("Pergunta"),
                    "Secção": secao_llm if secao_llm and secao_llm.lower() != "nenhuma" else estrutura_original.get("Secção"),
                    "Respostas": respostas_llm_validas if len(respostas_llm_validas) >= len(respostas_originais_validas) else respostas_originais_validas
                }


        except Exception as e:
            print(f"❌ Erro ao interpretar ou combinar a resposta do LLM: {e}")
            break

        print(f"\n🧠 Pré-visualização - Bloco {j}:")
        print(json.dumps(resposta_final, indent=2, ensure_ascii=False))

        print(f"\n🧠 Resposta do LLM (completa + merge se necessário):")
        print(json.dumps(resposta_final, indent=2, ensure_ascii=False))

        with open("preview_output.json", "w", encoding="utf-8") as f:
            json.dump(resposta_final, f, indent=2, ensure_ascii=False)

        print(json.dumps({"status": "preview", "mensagem": "Pré-visualização concluída."}))
        break

def validar_resposta_llm(resposta):
    erros = []

    if not isinstance(resposta, dict):
        erros.append("❌ A resposta não é um dicionário JSON.")
        return False, erros

    if "Identificador" not in resposta or not resposta["Identificador"].strip():
        erros.append("❌ Campo 'Identificador' está ausente ou vazio.")

    if "Pergunta" not in resposta or not resposta["Pergunta"].strip():
        erros.append("❌ Campo 'Pergunta' está ausente ou vazio.")

    if "Secção" not in resposta:
        erros.append("❌ Campo 'Secção' está ausente.")

    if "Respostas" not in resposta or not isinstance(resposta["Respostas"], list):
        erros.append("❌ Campo 'Respostas' está ausente ou não é uma lista.")
    else:
        respostas_validas = [r for r in resposta["Respostas"] if r.get("opção") and r.get("valor")]
        if not respostas_validas:
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