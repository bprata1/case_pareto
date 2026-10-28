import os
import io
import json
import pandas as pd
import streamlit as st

import agents
import erp_integration
import database

st.set_page_config(
    page_title="Vitalis | Pareto AI Builder V3 - Condições Comerciais",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Garantir inicialização do banco SQLite com usuários nominais da V3
database.init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMAILS_DIR = os.path.join(BASE_DIR, "dataset", "emails")

LABELS_AMIGAVEIS = {
    "DESCONTO_PERCENTUAL": "Desconto Percentual",
    "VERBA_EXPOSICAO": "Verba de Exposição",
    "GENERICOS": "Genéricos",
    "MEDICAMENTOS_REFERENCIA": "Medicamentos de Referência",
    "MIP": "MIP (Isentos de Prescrição)",
    "HIGIENE_BELEZA": "Higiene e Beleza",
    "DERMOCOSMETICOS": "Dermocosméticos",
    "SUPLEMENTOS": "Suplementos",
    "DENTRO_DA_POLITICA": "Dentro da Política",
    "EXCECAO_SAZONAL": "Exceção Sazonal (Campanha Trade)",
    "FORA_DA_POLITICA": "Fora da Política (Violação)",
    "PENDENTE": "Pendente de Aprovação",
    "APROVADO": "Aprovado e Integrado ao ERP",
    "REJEITADO": "Reprovado",
}


def formatar_termo_humano(valor: str) -> str:
    """
    Épico 2.1: Converte variáveis técnicas (ex: DESCONTO_PERCENTUAL) em textos limpos
    para o usuário de negócio (ex: 'Desconto Percentual'), mantendo o código técnico apenas no JSON.
    """
    if not valor:
        return ""
    chave = str(valor).strip().upper()
    if chave in LABELS_AMIGAVEIS:
        return LABELS_AMIGAVEIS[chave]
    return str(valor).replace("_", " ").title()


def clear_form_state():
    """
    Limpa completamente o estado visual do formulário de ingestão, arquivos carregados e extração da UI,
    destruindo qualquer cache anterior no `st.session_state` e forçando novas chaves de widgets,
    preservando intacto o banco SQLite e o usuário logado.
    """
    chaves_fixas_ui = [
        "condicoes_extraidas",
        "nome_fornecedor_email",
        "message_id_email",
        "alerta_injection",
        "texto_bruto_atual",
        "processado",
        "uploaded_file",
        "arquivos_carregados",
        "json_extraido",
    ]
    for k in chaves_fixas_ui:
        st.session_state.pop(k, None)

    prefixos_dinamicos = (
        "forn_", "cat_", "tipo_", "val_", "loja_",
        "dt_ini_", "dt_fim_", "contra_", "saz_", "subst_",
        "dl_analista_", "btn_fila_",
        "uploader_", "caso_rapido_", "texto_livre_",
    )
    chaves_dinamicas = [k for k in list(st.session_state.keys()) if k.startswith(prefixos_dinamicos)]
    for k in chaves_dinamicas:
        st.session_state.pop(k, None)

    # Incrementar contadores de geração para destruir qualquer cache de widget no frontend do Streamlit
    st.session_state["form_reset_counter"] = st.session_state.get("form_reset_counter", 0) + 1
    st.session_state["extraction_gen"] = st.session_state.get("extraction_gen", 0) + 1


def ler_arquivos_upload(uploaded_files) -> str:
    """Lê múltiplos arquivos (.eml, .txt, .csv, .xlsx) de forma resiliente e converte para texto."""
    texto = ""
    for file in uploaded_files:
        nome_arquivo = file.name.lower()
        try:
            if nome_arquivo.endswith(".csv"):
                raw_bytes = file.getvalue()
                raw_text = raw_bytes.decode("utf-8", errors="ignore")
                sep = ";" if ";" in raw_text.splitlines()[0] else ","
                df = pd.read_csv(io.StringIO(raw_text), sep=sep)
                texto += f"\n--- Anexo Planilha CSV: {file.name} ---\n{raw_text}\nResumo Tabela:\n{df.to_string(index=False)}\n"
            elif nome_arquivo.endswith(".xlsx"):
                df = pd.read_excel(file)
                texto += f"\n--- Anexo Planilha Excel: {file.name} ---\n{df.to_string(index=False)}\n"
            else:
                content = file.getvalue().decode("utf-8", errors="ignore")
                texto += f"\n--- E-mail / Texto: {file.name} ---\n{content}\n"
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {file.name}: {e}")
    return texto


def carregar_caso_dataset(opcao: str) -> str:
    """Carrega arquivos reais da pasta `dataset/emails/` para facilitar testes rápidos da banca."""
    texto = ""
    try:
        if "Alfa" in opcao:
            p = os.path.join(EMAILS_DIR, "2026-09-28_0912_alfa.eml")
            with open(p, "r", encoding="utf-8") as f:
                texto += f"--- E-mail: 2026-09-28_0912_alfa.eml ---\n{f.read()}\n"
        elif "Caso 2A" in opcao or "Apenas E-mail" in opcao:
            p = os.path.join(EMAILS_DIR, "2026-09-28_1640_gama.eml")
            with open(p, "r", encoding="utf-8") as f:
                texto += f"--- E-mail: 2026-09-28_1640_gama.eml ---\n{f.read()}\n"
        elif "Caso 2B" in opcao or "Anexo CSV" in opcao:
            p_eml = os.path.join(EMAILS_DIR, "2026-09-28_1640_gama.eml")
            p_csv = os.path.join(EMAILS_DIR, "anexos", "proposta_gama_q4.csv")
            with open(p_eml, "r", encoding="utf-8") as f:
                texto += f"--- E-mail: 2026-09-28_1640_gama.eml ---\n{f.read()}\n"
            with open(p_csv, "r", encoding="utf-8") as f:
                csv_txt = f.read()
                texto += f"\n--- Anexo Planilha CSV: proposta_gama_q4.csv ---\n{csv_txt}\n"
        elif "Beta" in opcao:
            p = os.path.join(EMAILS_DIR, "2026-09-29_1005_beta.eml")
            with open(p, "r", encoding="utf-8") as f:
                texto += f"--- E-mail: 2026-09-29_1005_beta.eml ---\n{f.read()}\n"
        elif "Nutrivida" in opcao:
            p = os.path.join(EMAILS_DIR, "2026-09-29_1830_nutrivida.eml")
            with open(p, "r", encoding="utf-8") as f:
                texto += f"--- E-mail: 2026-09-29_1830_nutrivida.eml ---\n{f.read()}\n"
    except Exception as e:
        st.error(f"Erro ao carregar arquivo de teste: {e}")
    return texto


def renderizar_sidebar():
    """
    Renderiza a barra lateral com sessão do usuário e as duas abas laterais recolhíveis:
    1) Guia de Perfis e Alçadas (POL-COM-004)
    2) Área do Avaliador (Credenciais Nominais, Troca Rápida e Reset do Banco)
    """
    with st.sidebar:
        st.markdown("## 💊 Vitalis Comercial")
        st.caption("Sistema Corporativo de Gestão de Condições Comerciais e Compliance (V3)")
        st.divider()

        usuario = st.session_state.get("usuario_logado")
        if usuario:
            icones_cargo = {
                "analista": "🧑‍💻",
                "coordenador": "👔",
                "gerente": "🏅",
                "diretor": "🏛️",
            }
            ic = icones_cargo.get(usuario["role"], "👤")
            st.markdown(f"### {ic} {usuario['nome']}")
            st.markdown(f"**Login:** `{usuario['username']}`")
            st.markdown(f"**Cargo:** `{usuario['cargo_exibicao']}`")
            st.markdown(f"**Matrícula ERP:** `{usuario['matricula']}`")

            if st.button("🚪 Sair / Trocar Usuário", width="stretch"):
                clear_form_state()
                st.session_state.pop("flash_sucesso_fila", None)
                st.session_state["usuario_logado"] = None
                st.rerun()
        else:
            st.info("🔒 Autentique-se na tela principal ou utilize os recursos da barra lateral abaixo.")

        st.divider()
        st.caption("📚 *Documentação de Alçadas e Governança de Testes:*")

        with st.expander("🧭 Guia de Perfis e Alçadas (POL-COM-004)", expanded=False):
            st.markdown("""
**Regras de Visibilidade e Aprovação:**
- **Analista (`renata.alves`):** Realiza a ingestão de e-mails/planilhas, audita alertas e envia para a fila. Também acompanha a Fila de Aprovação em modo leitura.
- **Coordenador (`carlos.eduardo`):** Aprova descontos de **até 10%**.
- **Gerente (`fernanda.lima`):** Aprova **Coordenação + Gerência** (descontos até 20% e verbas até R$ 5.000).
- **Diretor (`roberto.almeida`):** Aprova **todas as alçadas**, incluindo descontos até 25%, verbas > R$ 5.000 e **Exceções Sazonais (até 30%)**.
            """)

        with st.expander("🛠️ Área do Avaliador", expanded=False):
            st.info("🔑 **SENHA PADRÃO PARA TODOS OS USUÁRIOS: 123**")
            st.markdown("**Logins Corporativos de Teste:**")
            st.markdown(
                "- `renata.alves` — **Analista** Comercial\n"
                "- `carlos.eduardo` — **Coordenador** Comercial\n"
                "- `fernanda.lima` — **Gerente** Comercial\n"
                "- `roberto.almeida` — **Diretor** Comercial"
            )

            st.markdown("**Troca Rápida por Cargo/Alçada (1-Click):**")
            c_a, c_b = st.columns(2)
            with c_a:
                if st.button("🧑‍💻 Analista", key="quick_ana", width="stretch"):
                    clear_form_state()
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("renata.alves")
                    st.rerun()
                if st.button("🏅 Gerente", key="quick_ger", width="stretch"):
                    clear_form_state()
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("fernanda.lima")
                    st.rerun()
            with c_b:
                if st.button("👔 Coordenador", key="quick_coord", width="stretch"):
                    clear_form_state()
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("carlos.eduardo")
                    st.rerun()
                if st.button("🏛️ Diretor", key="quick_dir", width="stretch"):
                    clear_form_state()
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("roberto.almeida")
                    st.rerun()

            st.divider()
            st.markdown("**Manutenção do Ambiente:**")
            if st.button(
                "🗑️ Resetar Sistema e Limpar Banco de Dados",
                type="secondary",
                width="stretch",
            ):
                ok = database.reset_db()
                clear_form_state()
                st.session_state.pop("flash_sucesso_fila", None)
                if ok:
                    st.success("Banco SQLite e estado da sessão resetados com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao resetar o banco de dados.")


def renderizar_tela_login():
    """
    Épico 1.2: Tela inicial corporativa limpa (sem tabela aberta de senhas e alçadas),
    mas sinalizando claramente na tela principal a existência das duas abas na barra lateral esquerda.
    """
    st.title("🔐 Portal Corporativo de Condições Comerciais — Vitalis")
    st.markdown(
        "Bem-vindo à plataforma de automação, auditoria de compliance e integração ERP para condições comerciais."
    )

    col_esq, col_centro, col_dir = st.columns([0.6, 1.8, 0.6])
    with col_centro:
        with st.container(border=True):
            st.subheader("Identificação Corporativa")
            with st.form("form_login"):
                username = st.text_input("Usuário Corporativo", placeholder="Ex: nome.sobrenome")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha de acesso")
                btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary", width="stretch")

                if btn_entrar:
                    user = database.autenticar_usuario(username, password)
                    if user:
                        clear_form_state()
                        st.session_state["usuario_logado"] = user
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Verifique seu login na aba '🛠️ Área do Avaliador' na barra lateral.")

        st.info(
            "👈 **Aviso para a Banca Avaliadora (Recursos na Barra Lateral Esquerda):**\n\n"
            "Para manter esta tela inicial limpa conforme padrões corporativos de segurança, as informações de apoio encontram-se nas **duas abas recolhíveis na barra lateral esquerda**:\n"
            "1. **🧭 Guia de Perfis e Alçadas (POL-COM-004):** Consulta às regras de visibilidade e limites de aprovação de cada cargo.\n"
            "2. **🛠️ Área do Avaliador:** Consulta aos logins nominais de teste (`renata.alves`, `carlos.eduardo`, `fernanda.lima`, `roberto.almeida`), **acesso rápido em 1 clique** e botão de **Reset do Banco de Dados**."
        )


def processar_ingestao_texto(texto_contexto_completo: str):
    """Executa o Agente 1 (Extrator) e prepara o estado da sessão limpa com detecção de Edge Cases."""
    with st.spinner("🤖 Agente Extrator e Motor Determinístico analisando negociação..."):
        inj_check = erp_integration.detectar_prompt_injection(texto_contexto_completo)
        resultado = agents.extrair_condicoes(texto_contexto_completo)

        if "erro" in resultado:
            st.error(resultado["erro"])
            return

        condicoes_lista = []
        nome_forn = ""
        msg_id = "EMAIL_MANUAL"
        alerta_inj = inj_check["mensagem"] if inj_check["detectado"] else None

        if isinstance(resultado, list):
            condicoes_lista = resultado
        elif isinstance(resultado, dict):
            nome_forn = resultado.get("nome_fornecedor_email", "")
            msg_id = resultado.get("message_id", "EMAIL_MANUAL")
            if resultado.get("tentativa_prompt_injection") or inj_check["detectado"]:
                alerta_inj = resultado.get("alerta_seguranca") or inj_check["mensagem"] or "Tentativa de Prompt Injection neutralizada."
            condicoes_lista = resultado.get("condicoes_extraidas", [])
            if not condicoes_lista:
                for k, v in resultado.items():
                    if isinstance(v, list):
                        condicoes_lista = v
                        break
            if not condicoes_lista and "tipo_condicao" in resultado:
                condicoes_lista = [resultado]

        # Destruir qualquer cache de extração/widgets anterior antes de gravar os novos dados
        clear_form_state()

        st.session_state["condicoes_extraidas"] = condicoes_lista
        st.session_state["nome_fornecedor_email"] = nome_forn
        st.session_state["message_id_email"] = msg_id
        st.session_state["alerta_injection"] = alerta_inj
        st.session_state["texto_bruto_atual"] = texto_contexto_completo
        st.session_state["processado"] = True


def renderizar_visao_analista(usuario: dict):
    """
    Renderiza a interface do Analista:
    - Aba 1: Ingestão, Auditoria dos 7 Edge Cases, Edição e Envio para Fila (com limpeza automática de estado).
    - Aba 2: Fila de Aprovação completa em modo visualização (Épico 3.1).
    """
    st.title("📥 Painel do Analista Comercial — Ingestão e Governança")
    st.markdown(
        f"Olá, **{usuario['nome']}**! Insira o e-mail do fornecedor e eventuais planilhas anexas para extração via IA, "
        "ou acompanhe em tempo real o andamento das condições na aba **Fila de Aprovação**."
    )

    # Exibir mensagem flash caso um item tenha acabado de ser enviado e o formulário tenha sido limpo (Épico 4)
    msg_flash = st.session_state.pop("flash_sucesso_fila", None)
    if msg_flash:
        st.success(msg_flash)

    aba_ingestao, aba_fila = st.tabs([
        "1️⃣ Ingestão e Auditoria de Condições",
        "🏛️ Fila de Aprovação (Acompanhamento em Tempo Real)",
    ])

    reset_cnt = st.session_state.get("form_reset_counter", 0)

    with aba_ingestao:
        with st.container(border=True):
            st.subheader("1. Inserir Dados da Negociação")
            col1, col2 = st.columns(2)

            with col1:
                arquivos = st.file_uploader(
                    "Upload de E-mails e Planilhas Anexas (.eml, .txt, .csv, .xlsx)",
                    type=["eml", "txt", "csv", "xlsx"],
                    accept_multiple_files=True,
                    key=f"uploader_{reset_cnt}",
                )
                caso_rapido = st.selectbox(
                    "⚡ Ou carregue um caso oficial do Dataset para teste rápido:",
                    [
                        "-- Selecionar arquivo manualmente acima --",
                        "Caso 1: Alfa Pharma (2026-09-28_0912_alfa.eml) — Exceção Sazonal 28%",
                        "Caso 2A: Gama Dermo (Apenas E-mail sem anexo) — Busca Indireta + Condições Mistas",
                        "Caso 2B: Gama Dermo (E-mail + Anexo CSV proposta_gama_q4.csv) — Condições Mistas Completas",
                        "Caso 3: Distribuidora Beta (2026-09-29_1005_beta.eml) — Sobreposição Contratual ERP",
                        "Caso 4: Nutrivida (2026-09-29_1830_nutrivida.eml) — Prompt Injection + Fornecedor Inativo",
                    ],
                    key=f"caso_rapido_{reset_cnt}",
                )

            with col2:
                texto_livre = st.text_area(
                    "Ou cole o texto do e-mail / negociação aqui:",
                    height=155,
                    placeholder="Cole aqui o corpo do e-mail caso não utilize upload de arquivo...",
                    key=f"texto_livre_{reset_cnt}",
                )

            c_btn1, c_btn2 = st.columns([3, 1])
            with c_btn1:
                if st.button("🚀 Extrair e Auditar Condições", type="primary", width="stretch"):
                    texto_contexto = ""
                    if arquivos:
                        texto_contexto += ler_arquivos_upload(arquivos)
                    elif caso_rapido and not caso_rapido.startswith("--"):
                        texto_contexto += carregar_caso_dataset(caso_rapido)
                    if texto_livre and texto_livre.strip():
                        texto_contexto += f"\n--- Texto Colado Manualmente ---\n{texto_livre}\n"

                    if not texto_contexto.strip():
                        st.warning("⚠️ Por favor, faça upload de um arquivo, selecione um caso de teste ou cole o texto do e-mail.")
                    else:
                        processar_ingestao_texto(texto_contexto)
                        st.rerun()
            with c_btn2:
                if st.button("🧹 Limpar Formulário", width="stretch"):
                    clear_form_state()
                    st.rerun()

        if st.session_state.get("processado", False):
            st.divider()
            st.subheader("2. Auditoria de Compliance, Validação ERP e Revisão Humana")

            # EDGE CASE 1: Alerta Visual de Prompt Injection
            alerta_inj = st.session_state.get("alerta_injection")
            if alerta_inj:
                st.error(
                    f"🛡️ **ALERTA DE SEGURANÇA — TENTATIVA DE PROMPT INJECTION DETECTADA (Edge Case 1):**\n\n"
                    f"{alerta_inj}\n\n"
                    f"*A arquitetura Multi-Agent isolou o comando malicioso: o Agente Extrator ignorou a instrução de aprovação automática e submeteu os dados brutos às travas do ERP e da Política Comercial.*"
                )

            condicoes = st.session_state.get("condicoes_extraidas", [])
            if not condicoes:
                st.warning("Nenhuma condição comercial pendente de envio nesta extração.")
            else:
                # EDGE CASE 3: Alerta Visual de Condições Mistas
                tipos_extraidos = {str(c.get("tipo_condicao", "")).upper() for c in condicoes}
                if len(condicoes) > 1 and ("DESCONTO_PERCENTUAL" in tipos_extraidos and "VERBA_EXPOSICAO" in tipos_extraidos):
                    st.warning(
                        f"🔀 **CONDIÇÕES MISTAS DETECTADAS (Regra 5 / Edge Case 3):**\n\n"
                        f"Esta negociação contém simultaneamente **Desconto Percentual** e **Verba de Exposição**. "
                        f"Em conformidade com o Item 5 da Política Comercial, a IA desmembrou a proposta em **{len(condicoes)} objetos independentes**, "
                        f"que devem ser revisados e encaminhados para suas respectivas alçadas."
                    )
                elif len(condicoes) > 1:
                    st.info(f"ℹ️ Foram identificadas **{len(condicoes)} condições comerciais independentes** nesta negociação.")

                for i, cond in enumerate(condicoes):
                    renderizar_card_condicao_analista(i, cond, usuario, len(condicoes))

    with aba_fila:
        renderizar_conteudo_fila_aprovacao(usuario, modo_analista=True)


def renderizar_card_condicao_analista(i: int, cond: dict, usuario: dict, total_condicoes: int):
    """Renderiza o card de revisão, validação em tempo real, alertas de Edge Cases e preview JSON de uma condição."""
    tipo_inicial = str(cond.get("tipo_condicao", "DESCONTO_PERCENTUAL")).upper()
    if "VERBA" in tipo_inicial:
        tipo_inicial = "VERBA_EXPOSICAO"
    else:
        tipo_inicial = "DESCONTO_PERCENTUAL"

    cat_inicial_norm = erp_integration.normalizar_categoria(cond.get("categoria", "GENERICOS"))
    if cat_inicial_norm not in erp_integration.CATEGORIAS_VALIDAS:
        cat_inicial_norm = "GENERICOS"

    # Épico 2.1: Título sem underline
    titulo_card = f"Condição #{i+1} — {formatar_termo_humano(tipo_inicial)} ({formatar_termo_humano(cat_inicial_norm)})"

    with st.expander(titulo_card, expanded=True):
        forn_bruto = st.session_state.get("nome_fornecedor_email", "") or cond.get("fornecedor", cond.get("nome_fornecedor_email", ""))
        info_forn_ini = erp_integration.buscar_fornecedor_detalhado(forn_bruto)
        forn_default = info_forn_ini["cod_fornecedor"] if info_forn_ini["encontrado"] else forn_bruto

        lojas_brutas = cond.get("lojas_mencionadas", cond.get("lojas", ""))
        cods_lojas_ini, _, _ = erp_integration.resolver_lista_lojas(lojas_brutas)
        if cods_lojas_ini:
            loja_default = ", ".join(cods_lojas_ini)
        elif isinstance(lojas_brutas, list):
            loja_default = ", ".join(str(x) for x in lojas_brutas)
        else:
            loja_default = str(lojas_brutas or "")

        val_raw = cond.get("valor_extraido", cond.get("percentual", cond.get("valor", 0.0)))
        try:
            val_default = float(val_raw)
        except Exception:
            val_default = 0.0

        dt_ini_default = str(cond.get("data_inicio") or "") if cond.get("data_inicio") else ""
        dt_fim_default = str(cond.get("data_fim") or "") if cond.get("data_fim") else ""
        contra_default = str(cond.get("contrapartida") or "") if cond.get("contrapartida") else ""
        sazonal_default = bool(cond.get("campanha_sazonal", False))

        if cond.get("divergencia_detectada"):
            st.warning(f"📊 **Divergência E-mail vs. Planilha Anexa Detectada:** {cond.get('divergencia_detectada')}")

        gen = st.session_state.get("extraction_gen", 0)

        st.markdown("#### ✏️ Formulário de Revisão e Ajuste (Sobrescreve Alucinações da IA)")
        c1, c2, c3 = st.columns(3)
        with c1:
            edit_forn = st.text_input(
                "Fornecedor (Código FORN-### ou Nome)",
                value=forn_default,
                key=f"forn_{gen}_{i}",
                help="Aceita código (ex: FORN-001) ou nome parcial/aproximado (ex: Alfa Pharma, Distribuidora Beta).",
            )
            edit_cat = st.selectbox(
                "Categoria de Produto",
                options=erp_integration.CATEGORIAS_VALIDAS,
                index=erp_integration.CATEGORIAS_VALIDAS.index(cat_inicial_norm),
                format_func=formatar_termo_humano,
                key=f"cat_{gen}_{i}",
            )
            edit_sazonal = st.checkbox(
                "🎄 Campanha Sazonal (Trade Marketing)",
                value=sazonal_default,
                key=f"saz_{gen}_{i}",
                help="Permite teto de até 30% para Genéricos e MIP conforme Nota (*) da Política Comercial.",
            )

        with c2:
            opcoes_tipo = ["DESCONTO_PERCENTUAL", "VERBA_EXPOSICAO"]
            edit_tipo = st.selectbox(
                "Modalidade da Condição",
                options=opcoes_tipo,
                index=0 if tipo_inicial == "DESCONTO_PERCENTUAL" else 1,
                format_func=formatar_termo_humano,
                key=f"tipo_{gen}_{i}",
            )
            label_val = "Percentual de Desconto (%)" if edit_tipo == "DESCONTO_PERCENTUAL" else "Valor da Verba (R$)"
            edit_valor = st.number_input(
                label_val,
                min_value=0.0,
                value=val_default,
                step=0.5 if edit_tipo == "DESCONTO_PERCENTUAL" else 100.0,
                format="%.2f",
                key=f"val_{gen}_{i}",
            )
            edit_contra = st.text_input(
                "Contrapartida Acordada",
                value=contra_default,
                key=f"contra_{gen}_{i}",
                placeholder="Ex: Ponta de gôndola / Ilha promocional...",
            )

        with c3:
            edit_loja = st.text_input(
                "Lojas (Códigos LOJA-###, Nomes ou REDE)",
                value=loja_default,
                key=f"loja_{gen}_{i}",
                help="Aceita 'REDE', códigos separados por vírgula ('LOJA-101, LOJA-102') ou nomes das filiais ('Copacabana, Méier').",
            )
            edit_dt_ini = st.text_input(
                "Data de Início (YYYY-MM-DD)",
                value=dt_ini_default,
                key=f"dt_ini_{gen}_{i}",
            )
            edit_dt_fim = st.text_input(
                "Data de Fim (YYYY-MM-DD)",
                value=dt_fim_default,
                key=f"dt_fim_{gen}_{i}",
            )

        # --- MOTOR DE VALIDAÇÃO DETERMINÍSTICA EM TEMPO REAL (7 EDGE CASES + DUPLICIDADE SQLITE) ---
        erros_bloqueantes = []
        alertas_negocio = []

        # Validação 1: Fornecedor (Edge Case 2 & Épico 2.3 Checkmarks Visíveis)
        info_forn = erp_integration.buscar_fornecedor_detalhado(edit_forn)
        if not info_forn["encontrado"]:
            erros_bloqueantes.append(f"**Fornecedor Não Encontrado:** {info_forn['erro']}")
        elif not info_forn["ativo"]:
            erros_bloqueantes.append(
                f"🚫 **FORNECEDOR INATIVO NO ERP (Regra 8 / Edge Case 2):** O fornecedor **{info_forn['razao_social']}** "
                f"(`{info_forn['cod_fornecedor']}`, CNPJ `{info_forn['cnpj']}`) encontra-se com status **INATIVO** "
                f"desde `{info_forn['data_inativacao']}` (Motivo: *{info_forn['motivo_inativacao']}*). "
                "O cadastro de novas condições está bloqueado até a regularização."
            )

        # Validação 2: Lojas e Busca Indireta em Anexo (Edge Case 5 & Épico 2.3 Checkmarks Visíveis)
        lojas_resolvidas, erros_lojas, flag_busca_indireta = erp_integration.resolver_lista_lojas(edit_loja)
        if flag_busca_indireta or (cond.get("busca_indireta_anexo") and not lojas_resolvidas):
            erros_bloqueantes.append(
                "📎 **BUSCA INDIRETA EM ANEXO SEM LOJAS DEFINIDAS (Edge Case 5):** O e-mail faz referência indireta "
                "a lojas em anexo (*'lojas listadas na planilha anexa'*), mas nenhuma loja válida foi carregada. "
                "Faça upload do arquivo `.csv`/`.xlsx` anexo junto com o e-mail ou digite os nomes/códigos das lojas acima."
            )
        elif erros_lojas:
            for el in erros_lojas:
                erros_bloqueantes.append(f"**Erro na Validação de Loja:** {el}")

        # Épico 2.3: Exibir Checkmarks com alto contraste (componentes sólidos em vez de st.caption translúcido)
        col_chk1, col_chk2 = st.columns(2)
        with col_chk1:
            if info_forn["encontrado"] and info_forn["ativo"]:
                st.success(
                    f"✅ **Fornecedor Validado no ERP:** `{info_forn['cod_fornecedor']}` — "
                    f"**{info_forn['razao_social']}** (CNPJ: `{info_forn['cnpj']}` | Status: **Ativo**)"
                )
        with col_chk2:
            if lojas_resolvidas and not flag_busca_indireta and not erros_lojas:
                st.success(
                    f"✅ **Lojas Mapeadas no ERP ({len(lojas_resolvidas)}):** `{', '.join(lojas_resolvidas)}`"
                )

        # Validação 3: Limites de Vigência (Regra 6 / Edge Case 7)
        val_vigencia = erp_integration.validar_vigencia(edit_dt_ini, edit_dt_fim)
        if not val_vigencia["valido"]:
            for ev in val_vigencia["erros"]:
                erros_bloqueantes.append(f"📅 **VIOLAÇÃO DE VIGÊNCIA (Regra 6 / Edge Case 7):** {ev}")

        # Validação 4: Sobreposição Contratual no Extrato ERP + Duplicidade no SQLite (Edge Case 6 & Épico 3.2)
        cod_forn_valido = info_forn["cod_fornecedor"] if info_forn["encontrado"] else edit_forn
        sobreposicao = erp_integration.verificar_sobreposicao_extrato(
            cod_fornecedor=cod_forn_valido,
            cod_categoria=edit_cat,
            lojas=lojas_resolvidas,
            data_inicio_str=edit_dt_ini,
            data_fim_str=edit_dt_fim,
            tipo_condicao=edit_tipo,
            valor_proposto=edit_valor,
        )
        if sobreposicao["tem_conflito"]:
            erros_bloqueantes.append(
                f"🚫 **SOBREPOSIÇÃO CONTRATUAL / DUPLICIDADE NO ERP (Regra 9):** {sobreposicao['mensagem']}"
            )

        # Validação 5: Política Comercial, Tetos e Exceção Sazonal (Regra 4, Regra 5, Nota * / Edge Case 4)
        aval_pol = erp_integration.avaliar_politica_deterministica(
            cod_categoria=edit_cat,
            tipo_condicao=edit_tipo,
            valor=edit_valor,
            campanha_sazonal=edit_sazonal,
            contrapartida=edit_contra,
        )
        for ep in aval_pol["erros"]:
            erros_bloqueantes.append(f"📜 **VIOLAÇÃO DA POLÍTICA COMERCIAL:** {ep}")
        for ap in aval_pol["alertas"]:
            alertas_negocio.append(f"🎄 **EXCEÇÃO SAZONAL RECONHECIDA (Edge Case 4):** {ap}")

        # Épico 2.2: Painel "Diagnóstico de Auditoria e Alçada" com quebra de linha (sem truncamento de texto)
        st.markdown("#### 🔍 Diagnóstico de Auditoria e Alçada")
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            st.info(f"**🏛️ Alçada Mínima Exigida:**\n\n{aval_pol['alcada_exibicao']}")
        with col_st2:
            status_pol_limpo = formatar_termo_humano(aval_pol["status_politica"])
            if aval_pol["aprovado_politica"]:
                st.success(f"**📜 Status na Política:**\n\n{status_pol_limpo}")
            else:
                st.error(f"**📜 Status na Política:**\n\n{status_pol_limpo}")
        with col_st3:
            dias_txt = f"{val_vigencia['dias_vigencia']} dias corridos (Dentro do limite de 12 meses)" if val_vigencia.get("dias_vigencia") and val_vigencia["valido"] else "Período Inválido / Fora da Regra 6"
            st.info(f"**📅 Duração da Vigência:**\n\n{dias_txt}")

        for alerta in alertas_negocio:
            st.warning(alerta)

        if erros_bloqueantes:
            for erro_msg in erros_bloqueantes:
                st.error(erro_msg)
        else:
            st.success(
                f"✅ **Condição 100% Validada!** Pronta para ser enviada à fila da **{aval_pol['alcada_exibicao']}**."
            )

        # Construir Payload JSON para Preview Técnico e Download
        origem_ref = st.session_state.get("message_id_email", "Processamento AI Builder")
        payload_preview = erp_integration.construir_payload_erp(
            cod_fornecedor=cod_forn_valido,
            cod_categoria=edit_cat,
            tipo=edit_tipo,
            valor=edit_valor,
            lojas=lojas_resolvidas if lojas_resolvidas else [edit_loja],
            data_inicio=edit_dt_ini,
            data_fim=edit_dt_fim,
            aprovador_nome=f"Aguardando ({aval_pol['alcada_exibicao']})",
            aprovador_matricula="PENDENTE",
            contrapartida=edit_contra,
            origem_referencia=origem_ref,
        )
        envelope_post = erp_integration.envelopar_requisicao_post(payload_preview)
        json_str_download = json.dumps(payload_preview, indent=2, ensure_ascii=False)

        with st.expander("Visualizar Payload JSON (Técnico)", expanded=False):
            st.caption("Formato estritamente aderente ao contrato `dataset/mock_erp/schema/condicao_post.schema.json`:")
            tab_body, tab_req = st.tabs(["Body do POST (`/condicoes`)", "Requisição HTTP Completa (com Headers)"])
            with tab_body:
                st.json(payload_preview)
                st.code(json_str_download, language="json")
            with tab_req:
                st.json(envelope_post)

            st.download_button(
                label="📥 Baixar Payload JSON (.json)",
                data=json_str_download.encode("utf-8"),
                file_name=f"payload_{cod_forn_valido}_{edit_cat}_{i+1}.json",
                mime="application/json",
                key=f"dl_analista_{gen}_{i}",
            )

        # Botão de Envio para a Fila de Aprovação (SQLite)
        btn_enviar = st.button(
            f"📤 Enviar Condição #{i+1} para Fila de Aprovação ({aval_pol['alcada_exibicao']})",
            key=f"btn_fila_{i}",
            type="primary",
            disabled=(len(erros_bloqueantes) > 0),
        )
        if btn_enviar:
            # Dupla checagem contra duplicidade no momento exato do clique
            recheck_sob = erp_integration.verificar_sobreposicao_extrato(
                cod_fornecedor=cod_forn_valido,
                cod_categoria=edit_cat,
                lojas=lojas_resolvidas,
                data_inicio_str=edit_dt_ini,
                data_fim_str=edit_dt_fim,
                tipo_condicao=edit_tipo,
                valor_proposto=edit_valor,
            )
            ok_schema, erros_schema = erp_integration.validar_schema_payload(payload_preview)
            if recheck_sob["tem_conflito"]:
                st.error(f"🚫 {recheck_sob['mensagem']}")
            elif not ok_schema:
                for es in erros_schema:
                    st.error(f"Erro de Schema ERP: {es}")
            else:
                novo_id = database.inserir_condicao_fila({
                    "cod_fornecedor": cod_forn_valido,
                    "razao_social": info_forn.get("razao_social", ""),
                    "cod_categoria": edit_cat,
                    "tipo": edit_tipo,
                    "valor": edit_valor,
                    "lojas": lojas_resolvidas,
                    "data_inicio": edit_dt_ini.strip()[:10],
                    "data_fim": edit_dt_fim.strip()[:10],
                    "contrapartida": edit_contra,
                    "cod_condicao_substituida": None,
                    "alcada_minima": aval_pol["alcada_minima"],
                    "alcada_exibicao": aval_pol["alcada_exibicao"],
                    "status_politica": aval_pol["status_politica"],
                    "parecer_ia": "; ".join(alertas_negocio) if alertas_negocio else "Dentro dos limites da Política Comercial.",
                    "alertas": alertas_negocio,
                    "payload": payload_preview,
                    "origem_referencia": origem_ref,
                    "criado_por": usuario.get("nome", "Renata Alves"),
                })

                msg_sucesso = (
                    f"🎉 Condição enviada com sucesso para a **Fila de Aprovação** sob o protocolo **#{novo_id}** "
                    f"(Alçada: **{aval_pol['alcada_exibicao']}**)! O cache e o formulário foram limpos."
                )

                # Verificar se há condição irmã restante (caso de condições mistas no mesmo e-mail)
                restantes = [c for idx, c in enumerate(st.session_state.get("condicoes_extraidas", [])) if idx != i]
                forn_salvo = st.session_state.get("nome_fornecedor_email", "")
                msg_id_salvo = st.session_state.get("message_id_email", "EMAIL_MANUAL")

                # Chamar obrigatoriamente a limpeza total do estado do formulário antes do rerun
                clear_form_state()

                if total_condicoes > 1 and restantes:
                    st.session_state["condicoes_extraidas"] = restantes
                    st.session_state["nome_fornecedor_email"] = forn_salvo
                    st.session_state["message_id_email"] = msg_id_salvo
                    st.session_state["processado"] = True

                st.session_state["flash_sucesso_fila"] = msg_sucesso
                st.rerun()


def renderizar_visao_aprovador(usuario: dict):
    """Renderiza a tela principal para Coordenador, Gerente e Diretor."""
    st.title(f"🏛️ Fila de Aprovação — {usuario['cargo_exibicao']}")
    renderizar_conteudo_fila_aprovacao(usuario, modo_analista=False)


def renderizar_conteudo_fila_aprovacao(usuario: dict, modo_analista: bool = False):
    """
    Épico 3.1: Componente unificado da Fila de Aprovação.
    - Analista (`renata.alves`): visualiza todas as demandas da fila para acompanhamento, sem botões de decisão.
    - Gestores (`carlos.eduardo`, `fernanda.lima`, `roberto.almeida`): visualizam as demandas e possuem botões de
      Aprovar/Reprovar habilitados estritamente dentro de suas respectivas alçadas.
    """
    role = usuario["role"].lower()
    desc_escopo = {
        "analista": "Modo de **Acompanhamento (Somente Leitura)**: Você visualiza o status de todas as condições enviadas para aprovação.",
        "coordenador": "Você aprova condições de **Coordenação Comercial** (Descontos até 10%).",
        "gerente": "Você aprova condições de **Coordenação Comercial** e **Gerência Comercial** (Descontos até 20% e Verbas até R$ 5.000,00).",
        "diretor": "Você possui alçada máxima (**Diretoria Comercial**): aprova **todas as condições** (Coordenação, Gerência, Diretoria e Exceções Sazonais até 30%).",
    }

    st.info(f"🔐 **Perfil Ativo ({usuario['nome']} — `{usuario['username']}`):** {desc_escopo.get(role, '')}")

    if modo_analista:
        incluir_todas = True
    else:
        col_f1, col_f2 = st.columns([2, 2])
        with col_f1:
            escopo_visao = st.radio(
                "Escopo de Visualização:",
                ["Apenas Minha Alçada de Aprovação", "Todas as Demandas da Fila"],
                horizontal=True,
                key=f"escopo_fila_{role}",
            )
            incluir_todas = (escopo_visao == "Todas as Demandas da Fila")

    todos_visiveis = database.listar_fila_por_perfil(role, incluir_todas_alcadas=incluir_todas)
    pendentes = [x for x in todos_visiveis if x["status_fila"] == "PENDENTE"]
    aprovados = [x for x in todos_visiveis if x["status_fila"] == "APROVADO"]
    rejeitados = [x for x in todos_visiveis if x["status_fila"] == "REJEITADO"]
    acima_alcada = database.contar_itens_acima_alcada(role) if not modo_analista else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏳ Pendentes Listadas", len(pendentes))
    m2.metric("✅ Aprovadas", len(aprovados))
    m3.metric("❌ Reprovadas", len(rejeitados))
    m4.metric("🔒 Pendentes em Alçada Superior", acima_alcada)

    if acima_alcada > 0 and not incluir_todas:
        st.caption(
            f"ℹ️ *Existem **{acima_alcada}** condição(ões) pendente(s) em alçada superior à sua. "
            "Você pode alternar o filtro acima para 'Todas as Demandas da Fila' caso deseje consultá-las em modo leitura.*"
        )

    st.divider()
    filtro = st.radio(
        "Filtrar por Status:",
        ["PENDENTE", "APROVADO", "REJEITADO", "TODOS"],
        format_func=lambda x: "Todos os Status" if x == "TODOS" else formatar_termo_humano(x),
        horizontal=True,
        key=f"filtro_status_{role}_{'ana' if modo_analista else 'ges'}",
    )

    lista_exibicao = (
        todos_visiveis if filtro == "TODOS"
        else [x for x in todos_visiveis if x["status_fila"] == filtro]
    )

    if not lista_exibicao:
        st.warning(f"Nenhuma condição encontrada para o filtro selecionado (**{formatar_termo_humano(filtro)}**).")
        return

    for item in lista_exibicao:
        renderizar_card_item_fila(item, usuario, modo_analista=modo_analista)


def renderizar_card_item_fila(item: dict, usuario: dict, modo_analista: bool = False):
    """Renderiza cada card da fila de aprovação com textos limpos (Épico 2.1) e controle de alçada (Épico 3.1)."""
    item_id = item["id"]
    status = item["status_fila"]
    icone_st = {"PENDENTE": "⏳", "APROVADO": "✅", "REJEITADO": "❌"}.get(status, "📋")
    tipo_limpo = formatar_termo_humano(item["tipo"])
    cat_limpa = formatar_termo_humano(item["cod_categoria"])
    status_limpo = formatar_termo_humano(status)

    val_fmt = (
        f"{item['valor']:.2f}% ({tipo_limpo})"
        if item["tipo"] == "DESCONTO_PERCENTUAL"
        else f"R$ {item['valor']:,.2f} ({tipo_limpo})"
    )

    try:
        lojas_lista = json.loads(item["lojas_json"])
    except Exception:
        lojas_lista = [item["lojas_json"]]

    try:
        payload_dict = json.loads(item["payload_json"])
    except Exception:
        payload_dict = {}

    pode_aprovar = (not modo_analista) and database.usuario_pode_aprovar(usuario["role"], item["nivel_hierarquia"])

    payload_exibicao = dict(payload_dict)
    if status == "PENDENTE" and pode_aprovar:
        payload_exibicao["aprovador"] = {
            "matricula": usuario["matricula"],
            "nome": usuario["nome"],
        }

    with st.container(border=True):
        c_top1, c_top2 = st.columns([2.6, 1.4])
        with c_top1:
            st.subheader(f"{icone_st} Protocolo #{item_id} — {item['cod_fornecedor']} ({item['razao_social']})")
        with c_top2:
            st.markdown(f"**Status:** {status_limpo}  \n**Alçada Exigida:** {item['alcada_exibicao']}")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**Categoria de Produto:**\n{cat_limpa}")
        c2.markdown(f"**Condição Comercial:**\n{val_fmt}")
        c3.markdown(f"**Período de Vigência:**\n`{item['data_inicio']}` até `{item['data_fim']}`")
        c4.markdown(f"**Lojas Contempladas ({len(lojas_lista)}):**\n`{', '.join(lojas_lista)}`")

        if item.get("contrapartida"):
            st.markdown(f"**Contrapartida Acordada:** {item['contrapartida']}")

        if item["status_politica"] == "EXCECAO_SAZONAL":
            st.warning(f"🎄 **{formatar_termo_humano('EXCECAO_SAZONAL')}:** {item.get('parecer_ia', '')}")
        else:
            st.markdown(
                f"📋 **Status na Política:** {formatar_termo_humano(item['status_politica'])} — *{item.get('parecer_ia', '')}*  \n"
                f"👤 **Enviado por:** {item.get('criado_por')} em `{item.get('criado_em')}`"
            )

        if status != "PENDENTE":
            st.info(
                f"**Decisão Registrada:** {status_limpo} por **{item.get('aprovado_por')}** "
                f"(Matrícula `{item.get('aprovador_matricula')}`) em `{item.get('aprovado_em')}`"
                + (f" — Observação: *{item.get('observacao_decisao')}*" if item.get("observacao_decisao") else "")
            )

        # Visibilidade Técnica do JSON + Download
        json_formatado = json.dumps(payload_exibicao, indent=2, ensure_ascii=False)
        envelope_http = erp_integration.envelopar_requisicao_post(payload_exibicao)
        sufixo_key = "ana" if modo_analista else "ges"

        with st.expander("Visualizar Payload JSON (Técnico)", expanded=False):
            st.caption("Payload final formatado para `POST /api/v1/condicoes` (`condicao_post.schema.json`):")
            t_body, t_env = st.tabs(["Body JSON (Schema ERP)", "Envelope HTTP POST Completo"])
            with t_body:
                st.json(payload_exibicao)
                st.code(json_formatado, language="json")
            with t_env:
                st.json(envelope_http)

            st.download_button(
                label="📥 Baixar Payload JSON (.json)",
                data=json_formatado.encode("utf-8"),
                file_name=f"erp_condicao_{item_id}_{item['cod_fornecedor']}.json",
                mime="application/json",
                key=f"dl_fila_{sufixo_key}_{item_id}",
            )

        if status == "PENDENTE":
            if pode_aprovar:
                obs = st.text_input(
                    "Observação da Aprovação / Justificativa (Opcional):",
                    key=f"obs_dec_{sufixo_key}_{item_id}",
                    placeholder="Ex: De acordo com campanha comercial Q4...",
                )
                b_col1, b_col2, _ = st.columns([1.2, 1.2, 2])
                with b_col1:
                    if st.button("✅ Aprovar e Integrar ao ERP", key=f"aprov_{sufixo_key}_{item_id}", type="primary", width="stretch"):
                        database.decidir_condicao_fila(item_id, "APROVADO", usuario, obs)
                        st.success(f"Condição #{item_id} APROVADA com sucesso! Payload JSON integrado ao ERP.")
                        st.rerun()
                with b_col2:
                    if st.button("❌ Reprovar Condição", key=f"rejeit_{sufixo_key}_{item_id}", width="stretch"):
                        database.decidir_condicao_fila(item_id, "REJEITADO", usuario, obs)
                        st.warning(f"Condição #{item_id} REPROVADA.")
                        st.rerun()
            else:
                if modo_analista:
                    st.caption(f"👁️ *Modo Acompanhamento: Aguardando decisão da alçada **{item['alcada_exibicao']}**.*")
                else:
                    st.warning(
                        f"🔒 **Alçada Insuficiente para Decisão:** Este item exige alçada de **{item['alcada_exibicao']}** "
                        f"(seu perfil atual é **{usuario['cargo_exibicao']}**)."
                    )


# --- FLUXO PRINCIPAL DA APLICAÇÃO ---
renderizar_sidebar()

usuario_atual = st.session_state.get("usuario_logado")
if not usuario_atual:
    renderizar_tela_login()
else:
    perfil = usuario_atual.get("role", "").lower()
    if perfil == "analista":
        renderizar_visao_analista(usuario_atual)
    else:
        renderizar_visao_aprovador(usuario_atual)
