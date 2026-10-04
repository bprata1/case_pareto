import os
import json
import agents
import erp_integration

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMAILS_DIR = os.path.join(BASE_DIR, 'dataset', 'emails')

def testar_bateria():
    print("=== INICIANDO BATERIA DE TESTES EM LOTE ===")
    
    arquivos = [f for f in os.listdir(EMAILS_DIR) if f.endswith('.eml') or f.endswith('.txt')]
    if not arquivos:
        print("Nenhum arquivo .eml ou .txt encontrado.")
        return

    for nome_arquivo in arquivos:
        print(f"\n>> Processando arquivo: {nome_arquivo}")
        caminho_arquivo = os.path.join(EMAILS_DIR, nome_arquivo)
        
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                texto_email = f.read()
                
            # Extração pela IA
            resultado_extraido = agents.extrair_condicoes(texto_email)
            if "erro" in resultado_extraido:
                print(f"  [ERRO NA API DA IA] {resultado_extraido['erro']}")
                continue
                
            # Normalizar a extração espelhando o que fizemos no app.py
            condicoes_lista = []
            nome_fornecedor_raiz = ""
            if isinstance(resultado_extraido, list):
                condicoes_lista = resultado_extraido
            elif isinstance(resultado_extraido, dict):
                nome_fornecedor_raiz = resultado_extraido.get("nome_fornecedor_email", "")
                for k, v in resultado_extraido.items():
                    if isinstance(v, list):
                        condicoes_lista = v
                        break
                if not condicoes_lista:
                    condicoes_lista = [resultado_extraido]
                    
            print(f"  Condições encontradas: {len(condicoes_lista)}")
            
            # Validação no Motor Determinístico e Auditoria IA
            for i, cond in enumerate(condicoes_lista):
                print(f"  --- Condição #{i+1} ---")
                
                # Validação de Fornecedor
                forn_extraido = nome_fornecedor_raiz or cond.get("fornecedor", cond.get("nome_fornecedor_email", ""))
                try:
                    cod_forn, cnpj = erp_integration.validar_fornecedor(forn_extraido)
                    print(f"    [OK] Fornecedor: {cod_forn} ({cnpj})")
                except ValueError as ve:
                    print(f"    [Aviso: Revisão Humana Necessária] {ve}")
                
                # Validação de Loja
                loja_extraida = cond.get("lojas_mencionadas", cond.get("lojas", ""))
                lojas_a_validar = loja_extraida if isinstance(loja_extraida, list) else [loja_extraida]
                for lj in lojas_a_validar:
                    lj_str = str(lj).strip().lower()
                    if "rede" in lj_str or "todas" in lj_str:
                        print("    [OK] Loja: REDE")
                    else:
                        try:
                            cod_loja = erp_integration.validar_loja(str(lj))
                            print(f"    [OK] Loja: {cod_loja}")
                        except ValueError as ve:
                            print(f"    [Aviso: Revisão Humana Necessária] {ve}")

                # Auditoria IA (Limitador da Política)
                try:
                    resultado_auditoria = agents.auditar_condicoes(json.dumps(cond, ensure_ascii=False))
                    aprovado = resultado_auditoria.get("aprovado", False)
                    alcada = resultado_auditoria.get("alcada_necessaria", "N/A")
                    print(f"    [AUDITORIA IA] Aprovado: {aprovado} | Alçada: {alcada}")
                except Exception as e:
                    print(f"    [ERRO CRÍTICO] Falha na auditoria: {type(e).__name__} - {e}")
                    
        except Exception as e:
            print(f"  [ERRO CRÍTICO] Falha inesperada ao processar {nome_arquivo}: {type(e).__name__} - {e}")

if __name__ == "__main__":
    testar_bateria()
