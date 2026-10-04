import streamlit as st
import pandas as pd
import json
import agents
import erp_integration
from datetime import datetime

st.set_page_config(page_title="Pareto AI Builder - Condições Comerciais", layout="wide")

def ler_arquivos_upload(uploaded_files):
    """Lê múltiplos arquivos e converte para texto."""
    texto = ""
    for file in uploaded_files:
        nome_arquivo = file.name.lower()
        try:
            if nome_arquivo.endswith('.csv'):
                df = pd.read_csv(file)
                texto += f"\n--- Arquivo: {file.name} ---\n{df.to_string()}\n"
            elif nome_arquivo.endswith('.xlsx'):
                df = pd.read_excel(file)
                texto += f"\n--- Arquivo: {file.name} ---\n{df.to_string()}\n"
            else:
                # Trata .eml e .txt como texto puro
                content = file.getvalue().decode("utf-8", errors="ignore")
                texto += f"\n--- Arquivo: {file.name} ---\n{content}\n"
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {file.name}: {e}")
    return texto

st.title("🤖 Pareto AI Builder - Extrator de Condições Comerciais")

st.markdown("""
Esta ferramenta utiliza IA para extrair automaticamente condições comerciais de e-mails, 
auditar de acordo com a política vigente e gerar o formato de integração para o ERP.
""")

# Área de Ingestão
st.subheader("1. Inserir Dados da Negociação")
col1, col2 = st.columns(2)

with col1:
    arquivos = st.file_uploader(
        "Upload de E-mails ou Planilhas (.eml, .txt, .csv, .xlsx)",
        type=["eml", "txt", "csv", "xlsx"],
        accept_multiple_files=True
    )

with col2:
    texto_livre = st.text_area("Ou cole o texto do e-mail aqui:", height=150)

if st.button("Extrair e Auditar Condições", type="primary"):
    texto_contexto_completo = ""
    if arquivos:
        texto_contexto_completo += ler_arquivos_upload(arquivos)
    if texto_livre:
        texto_contexto_completo += f"\n--- Texto Colado ---\n{texto_livre}\n"

    if not texto_contexto_completo.strip():
        st.warning("Por favor, insira arquivos ou cole o texto do e-mail.")
    else:
        with st.spinner("A IA está analisando a negociação..."):
            resultado = agents.extrair_condicoes(texto_contexto_completo)
            
            if "erro" in resultado:
                st.error(resultado["erro"])
            else:
                # Tentar inferir onde está a lista no JSON retornado
                condicoes_lista = []
                nome_forn = ""
                if isinstance(resultado, list):
                    condicoes_lista = resultado
                elif isinstance(resultado, dict):
                    nome_forn = resultado.get("nome_fornecedor_email", "")
                    for k, v in resultado.items():
                        if isinstance(v, list):
                            condicoes_lista = v
                            break
                    if not condicoes_lista:
                        condicoes_lista = [resultado] # Se for um único objeto
                
                st.session_state['condicoes_extraidas'] = condicoes_lista
                st.session_state['nome_fornecedor_email'] = nome_forn
                st.session_state['processado'] = True
                st.success(f"Extração concluída! {len(condicoes_lista)} condição(ões) encontrada(s).")

if st.session_state.get('processado', False):
    st.subheader("2. Revisão e Auditoria das Condições")
    
    condicoes = st.session_state.get('condicoes_extraidas', [])
    
    if not condicoes:
        st.warning("Nenhuma condição extraída.")
    
    for i, cond in enumerate(condicoes):
        with st.expander(f"Condição #{i+1}", expanded=True):
            
            # --- Validação Inicial e Auditoria ---
            # Aqui chamamos o motor determinístico apenas para sugerir ou alertar
            fornecedor_extraido = st.session_state.get("nome_fornecedor_email", "") or cond.get("fornecedor", cond.get("nome_fornecedor_email", ""))
            loja_extraida = cond.get("lojas_mencionadas", cond.get("lojas", ""))
            if isinstance(loja_extraida, list):
                loja_extraida_str = ", ".join(str(x) for x in loja_extraida)
            else:
                loja_extraida_str = str(loja_extraida)
                
            cod_forn_sugerido = ""
            loja_sugerida = ""
            
            # Validação Fornecedor
            err_forn_ph = st.empty()
            try:
                cod_forn, cnpj_forn = erp_integration.validar_fornecedor(fornecedor_extraido)
                cod_forn_sugerido = cod_forn
            except Exception as e:
                cod_forn_sugerido = fornecedor_extraido
                err_forn_ph.error(f"Erro ao validar Fornecedor: {e}. Edite manualmente abaixo.")
            
            # Validação Loja (tratando lista ou string)
            # A politica aceita ["REDE"] ou ["LOJA-###"]. O extrator pode trazer "todas as lojas"
            err_loja_ph = st.empty()
            try:
                if isinstance(loja_extraida, list) and loja_extraida:
                    lojas_validadas = []
                    for lj in loja_extraida:
                        if lj.upper() == "REDE" or lj.upper() == "TODAS":
                            lojas_validadas.append("REDE")
                        else:
                            lojas_validadas.append(erp_integration.validar_loja(lj))
                    loja_sugerida = ", ".join(lojas_validadas)
                elif "rede" in loja_extraida_str.lower() or "todas" in loja_extraida_str.lower():
                    loja_sugerida = "REDE"
                else:
                    loja_sugerida = erp_integration.validar_loja(loja_extraida_str)
            except Exception as e:
                loja_sugerida = loja_extraida_str
                err_loja_ph.error(f"Erro ao validar Loja: {e}. Edite manualmente abaixo.")
            
            # Auditoria inicial pela IA (apenas visualização)
            cond_json_str = json.dumps(cond, ensure_ascii=False)
            auditoria = agents.auditar_condicoes(cond_json_str)
            
            pareceres = auditoria.get("parecer_auditoria", [{}])
            p_dados = pareceres[0] if pareceres else {}
            
            parecer = p_dados.get("raciocinio_passo_a_passo", "")
            status_pol = p_dados.get("status_politica", "")
            aprovado = status_pol in ["DENTRO_DA_POLITICA", "EXCECAO_SAZONAL"]
            alcada = p_dados.get("alcada_necessaria", "N/A")
            
            if aprovado:
                st.success(f"**Parecer da IA:** {parecer} | **Alçada Necessária:** {alcada}")
            else:
                st.warning(f"**Parecer da IA:** {parecer} | **Alçada Necessária:** {alcada}")

            # Formulário de edição
            with st.form(key=f"form_{i}"):
                st.write("**Revise os dados abaixo (Edite caso a IA tenha errado):**")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_forn = st.text_input("Código do Fornecedor (ex: FORN-123)", value=cod_forn_sugerido, key=f"forn_{i}")
                    edit_cat = st.text_input("Categoria", value=cond.get("categoria", ""), key=f"cat_{i}")
                with c2:
                    edit_tipo = st.selectbox(
                        "Tipo", 
                        ["DESCONTO_PERCENTUAL", "VERBA_EXPOSICAO"], 
                        index=0 if "DESCONTO" in str(cond.get("tipo_condicao", "")).upper() else 1,
                        key=f"tipo_{i}"
                    )
                    # Convertendo valor ou percentual para float
                    val_perc = cond.get("valor_extraido", cond.get("percentual", cond.get("valor", 0.0)))
                    try:
                        val_perc = float(val_perc)
                    except:
                        val_perc = 0.0
                    
                    edit_valor = st.number_input("Valor/Percentual", value=val_perc, format="%.2f", key=f"val_{i}")
                with c3:
                    edit_loja = st.text_input("Lojas (ex: LOJA-001 ou REDE)", value=loja_sugerida, key=f"loja_{i}")
                    edit_dt_ini = st.text_input("Data Início (YYYY-MM-DD)", value=cond.get("data_inicio", ""), key=f"dt_ini_{i}")
                    edit_dt_fim = st.text_input("Data Fim (YYYY-MM-DD)", value=cond.get("data_fim", ""), key=f"dt_fim_{i}")

                edit_aprovador = st.text_input("Nome do Aprovador (Alçada)", value=auditoria.get("aprovador", cond.get("aprovador", "")), key=f"aprov_{i}")

                submit_btn = st.form_submit_button("Confirmar e Gerar Integração")
                
                if submit_btn:
                    # Limpa as mensagens de erro iniciais já que o usuário está submetendo
                    err_forn_ph.empty()
                    err_loja_ph.empty()
                    
                    # Montar JSON com as edições do usuário
                    dados_editados = {
                        "categoria": edit_cat,
                        "tipo_condicao": edit_tipo,
                        "valor_extraido": edit_valor,
                        "data_inicio": edit_dt_ini,
                        "data_fim": edit_dt_fim,
                        "lojas_mencionadas": edit_loja.split(",") if "," in edit_loja else [edit_loja],
                        "fornecedor": edit_forn
                    }
                    
                    # Reavaliar silenciosamente a regra
                    re_auditoria = agents.auditar_condicoes(json.dumps(dados_editados, ensure_ascii=False))
                    re_pareceres = re_auditoria.get("parecer_auditoria", [{}])
                    re_p_dados = re_pareceres[0] if re_pareceres else {}
                    
                    re_status_pol = re_p_dados.get("status_politica", "")
                    re_aprovado = re_status_pol in ["DENTRO_DA_POLITICA", "EXCECAO_SAZONAL"]
                    re_parecer_texto = re_p_dados.get("raciocinio_passo_a_passo", "Política infringida (sem detalhes).")
                    
                    if not re_aprovado:
                        st.error(f"Erro na validação pós-edição: {re_parecer_texto}")
                    else:
                        st.success("Dados aprovados! Gerando Payload...")
                        
                        # Payload JSON final
                        payload = {
                            "cod_fornecedor": edit_forn.strip(),
                            "cod_categoria": edit_cat.strip().upper(),
                            "tipo": edit_tipo,
                            "lojas": [l.strip().upper() for l in edit_loja.split(",")] if "," in edit_loja else [edit_loja.strip().upper()],
                            "data_inicio": edit_dt_ini.strip(),
                            "data_fim": edit_dt_fim.strip(),
                            "aprovador": {
                                "matricula": "12345", # mockado 
                                "nome": edit_aprovador.strip()
                            },
                            "origem": {
                                "tipo": "EMAIL",
                                "referencia": "Processamento AI Builder"
                            }
                        }
                        
                        if edit_tipo == "DESCONTO_PERCENTUAL":
                            payload["percentual"] = edit_valor
                        else:
                            payload["valor"] = edit_valor
                            
                        st.code(json.dumps(payload, indent=2, ensure_ascii=False), language="json")
