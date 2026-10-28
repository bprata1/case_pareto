import os
import io
import json
import pandas as pd
import streamlit as st
from datetime import datetime

import agents
import erp_integration
import database

st.set_page_config(
    page_title="Vitalis | Pareto AI Builder V2 - Condições Comerciais",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Garantir inicialização do banco SQLite
database.init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMAILS_DIR = os.path.join(BASE_DIR, "dataset", "emails")


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
    """Renderiza a barra lateral com informações da sessão e a Área do Avaliador discreta porém visível."""
    with st.sidebar:
        st.markdown("## 💊 Vitalis Comercial")
        st.caption("Sistema Corporativo de Gestão de Condições Comerciais e Compliance (V2)")
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
            st.markdown(f"**Perfil:** `{usuario['cargo_exibicao']}`")
            st.markdown(f"**Matrícula ERP:** `{usuario['matricula']}`")

            if st.button("🚪 Sair / Trocar Usuário", width="stretch"):
                st.session_state["usuario_logado"] = None
                st.rerun()
        else:
            st.info("🔒 Faça login na tela principal para acessar o sistema.")

        st.divider()
        st.caption("⚙️ *Governança, Credenciais de Teste e Reset do Banco:*")
        with st.expander("🛠️ Área do Avaliador", expanded=False):
            st.markdown("**Credenciais de Teste (Senha: `123`):**")
            st.markdown(
                "- `analista` — Nível 1 (Ingestão e Edição)\n"
                "- `coordenador` — Alçada até 10%\n"
                "- `gerente` — Alçada até 20% / Verba ≤ 5k\n"
                "- `diretor` — Alçada Total + Exceções Sazonais"
            )

            st.markdown("**Troca Rápida de Perfil (1-Click):**")
            c_a, c_b = st.columns(2)
            with c_a:
                if st.button("🧑‍💻 Analista", key="quick_ana", width="stretch"):
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("analista")
                    st.rerun()
                if st.button("🏅 Gerente", key="quick_ger", width="stretch"):
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("gerente")
                    st.rerun()
            with c_b:
                if st.button("👔 Coord.", key="quick_coord", width="stretch"):
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("coordenador")
                    st.rerun()
                if st.button("🏛️ Diretor", key="quick_dir", width="stretch"):
                    st.session_state["usuario_logado"] = database.obter_usuario_por_username("diretor")
                    st.rerun()

            st.divider()
            st.markdown("**Manutenção do Ambiente:**")
            if st.button(
                "🗑️ Resetar Sistema e Limpar Banco de Dados",
                type="secondary",
                width="stretch",
            ):
                ok = database.reset_db()
                for k in ["condicoes_extraidas", "nome_fornecedor_email", "processado", "alerta_injection", "message_id_email", "texto_bruto_atual"]:
                    st.session_state.pop(k, None)
                if ok:
                    st.success("Banco SQLite e sessão resetados com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao resetar o banco de dados.")


def renderizar_tela_login():
    """Renderiza a tela de autenticação corporativa."""
    st.title("🔐 Portal de Condições Comerciais — Vitalis V2")
    st.markdown(
        "Bem-vindo ao sistema de automação e governança de condições comerciais (Descontos e Verbas). "
        "Autentique-se com seu perfil para acessar sua área de trabalho."
    )

    col_login, col_info = st.columns([1, 1.2])
    with col_login:
        with st.container(border=True):
            st.subheader("Acesso ao Sistema")
            with st.form("form_login"):
                username = st.text_input("Usuário", placeholder="Ex: analista, coordenador, gerente, diretor")
                password = st.text_input("Senha", type="password", placeholder="Senha padrão de teste: 123")
                btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary", width="stretch")

                if btn_entrar:
                    user = database.autenticar_usuario(username, password)
                    if user:
                        st.session_state["usuario_logado"] = user
                        st.success(f"Bem-vindo(a), {user['nome']}!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos. (Dica: use senha '123' ou consulte a 🛠️ Área do Avaliador na barra lateral).")

    with col_info:
        with st.container(border=True):
            st.subheader("🧭 Hierarquia de Perfis e Alçadas (POL-COM-004)")
            st.markdown("""
| Perfil (`username`) | Senha | Função no Fluxo e Alçada Visível |
| :--- | :--- | :--- |
| **`analista`** | `123` | **Nível 1 (Ingestão):** Upload de e-mails/planilhas, extração via IA, revisão de alertas e envio para a fila. |
| **`coordenador`** | `123` | **Coordenação Comercial:** Visualiza e aprova descontos de **até 10%**. |
| **`gerente`** | `123` | **Gerência Comercial:** Visualiza e aprova **Coordenação + Gerência** (descontos até 20% e verbas até R$ 5.000). |
| **`diretor`** | `123` | **Diretoria Comercial:** Visualiza e aprova **todas as alçadas**, incluindo descontos até 25%, verbas > R$ 5.000 e **Exceções Sazonais (até 30%)**. |
            """)
            st.caption("💡 *Dica para a Banca Avaliadora: Você também pode alternar de perfil instantaneamente ou resetar o banco de dados no menu **🛠️ Área do Avaliador** na barra lateral esquerda.*")


def processar_ingestao_texto(texto_contexto_completo: str):
    """Executa o Agente 1 (Extrator) e prepara o estado da sessão com detecção de Edge Cases."""
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

        # Limpar widgets antigos de edição para carregar os novos valores extraídos
        chaves_antigas = [k for k in st.session_state.keys() if k.startswith(("forn_", "cat_", "tipo_", "val_", "loja_", "dt_ini_", "dt_fim_", "contra_", "saz_", "subst_"))]
        for k in chaves_antigas:
            st.session_state.pop(k, None)

        st.session_state["condicoes_extraidas"] = condicoes_lista
        st.session_state["nome_fornecedor_email"] = nome_forn
        st.session_state["message_id_email"] = msg_id
        st.session_state["alerta_injection"] = alerta_inj
        st.session_state["texto_bruto_atual"] = texto_contexto_completo
        st.session_state["processado"] = True


def renderizar_visao_analista(usuario: dict):
    """Renderiza a interface de Nível 1 (Analista): Ingestão, Auditoria dos 7 Edge Cases, Edição e Envio para Fila."""
    st.title("📥 Painel do Analista Comercial — Ingestão e Auditoria IA")
    st.markdown(
        "Insira o e-mail do fornecedor e eventuais planilhas anexas. A IA extrairá as condições comerciais, "
        "o motor determinístico validará os cadastros do ERP e você poderá revisar os dados antes de enviá-los para a Fila de Aprovação."
    )

    aba_ingestao, aba_historico = st.tabs([
        "1️⃣ Nova Ingestão e Revisão de Condições",
        "2️⃣ Acompanhamento da Fila de Aprovação"
    ])

    with aba_ingestao:
        with st.container(border=True):
            st.subheader("1. Inserir Dados da Negociação")
            col1, col2 = st.columns(2)

            with col1:
                arquivos = st.file_uploader(
                    "Upload de E-mails e Planilhas Anexas (.eml, .txt, .csv, .xlsx)",
                    type=["eml", "txt", "csv", "xlsx"],
                    accept_multiple_files=True,
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
                )

            with col2:
                texto_livre = st.text_area(
                    "Ou cole o texto do e-mail / negociação aqui:",
                    height=155,
                    placeholder="Cole aqui o corpo do e-mail caso não utilize upload de arquivo...",
                )

            if st.button("🚀 Extrair e Auditar Condições", type="primary"):
                texto_contexto = ""
                if arquivos:
                    texto_contexto += ler_arquivos_upload(arquivos)
                if caso_rapido and not caso_rapido.startswith("--"):
                    texto_contexto += carregar_caso_dataset(caso_rapido)
                if texto_livre.strip():
                    texto_contexto += f"\n--- Texto Colado Manualmente ---\n{texto_livre}\n"

                if not texto_contexto.strip():
                    st.warning("⚠️ Por favor, faça upload de um arquivo, selecione um caso de teste ou cole o texto do e-mail.")
                else:
                    processar_ingestao_texto(texto_contexto)

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
                st.warning("Nenhuma condição comercial pôde ser extraída do texto fornecido.")
                return

            # EDGE CASE 3: Alerta Visual de Condições Mistas (Desconto + Verba no mesmo e-mail)
            tipos_extraidos = {str(c.get("tipo_condicao", "")).upper() for c in condicoes}
            if len(condicoes) > 1 and ("DESCONTO_PERCENTUAL" in tipos_extraidos and "VERBA_EXPOSICAO" in tipos_extraidos):
                st.warning(
                    f"🔀 **CONDIÇÕES MISTAS DETECTADAS (Regra 5 / Edge Case 3):**\n\n"
                    f"Esta negociação contém simultaneamente **Desconto Percentual** e **Verba de Exposição**. "
                    f"Em conformidade com o Item 5 da Política Comercial, a IA desmembrou a proposta em **{len(condicoes)} objetos independentes**, "
                    f"que devem ser revisados e encaminhados individualmente para suas respectivas alçadas."
                )
            elif len(condicoes) > 1:
                st.info(f"ℹ️ Foram identificadas **{len(condicoes)} condições comerciais independentes** nesta negociação.")

            for i, cond in enumerate(condicoes):
                renderizar_card_condicao_analista(i, cond, usuario)

    with aba_historico:
        st.subheader("📋 Condições Enviadas para a Fila de Aprovação")
        itens_fila = database.listar_fila_por_perfil("analista")
        if not itens_fila:
            st.info("Nenhuma condição foi enviada para a fila ainda.")
        else:
            df_resumo = pd.DataFrame([
                {
                    "ID": f"#{it['id']}",
                    "Status": it["status_fila"],
                    "Fornecedor": f"{it['cod_fornecedor']} ({it['razao_social']})",
                    "Categoria": it["cod_categoria"],
                    "Tipo": it["tipo"],
                    "Valor": f"{it['valor']:.2f}%" if it["tipo"] == "DESCONTO_PERCENTUAL" else f"R$ {it['valor']:,.2f}",
                    "Alçada Exigida": it["alcada_exibicao"],
                    "Vigência": f"{it['data_inicio']} a {it['data_fim']}",
                    "Decidido Por": it["aprovado_por"] or "Aguardando Aprovador",
                }
                for it in itens_fila
            ])
            st.dataframe(df_resumo, width="stretch", hide_index=True)


def renderizar_card_condicao_analista(i: int, cond: dict, usuario: dict):
    """Renderiza o card de revisão, validação em tempo real, alertas de Edge Cases e preview JSON de uma condição."""
    tipo_inicial = str(cond.get("tipo_condicao", "DESCONTO_PERCENTUAL")).upper()
    if "VERBA" in tipo_inicial:
        tipo_inicial = "VERBA_EXPOSICAO"
    else:
        tipo_inicial = "DESCONTO_PERCENTUAL"

    titulo_card = f"Condição #{i+1} — {tipo_inicial} ({cond.get('categoria', 'CATEGORIA')})"

    with st.expander(titulo_card, expanded=True):
        # 1. Sugestão inicial de Fornecedor e Lojas a partir da extração
        forn_bruto = st.session_state.get("nome_fornecedor_email", "") or cond.get("fornecedor", cond.get("nome_fornecedor_email", ""))
        info_forn_ini = erp_integration.buscar_fornecedor_detalhado(forn_bruto)
        forn_default = info_forn_ini["cod_fornecedor"] if info_forn_ini["encontrado"] else forn_bruto

        lojas_brutas = cond.get("lojas_mencionadas", cond.get("lojas", ""))
        cods_lojas_ini, _, flag_indireta_ini = erp_integration.resolver_lista_lojas(lojas_brutas)
        if cods_lojas_ini:
            loja_default = ", ".join(cods_lojas_ini)
        elif isinstance(lojas_brutas, list):
            loja_default = ", ".join(str(x) for x in lojas_brutas)
        else:
            loja_default = str(lojas_brutas or "")

        cat_default = erp_integration.normalizar_categoria(cond.get("categoria", "GENERICOS"))
        if cat_default not in erp_integration.CATEGORIAS_VALIDAS:
            cat_default = "GENERICOS"

        val_raw = cond.get("valor_extraido", cond.get("percentual", cond.get("valor", 0.0)))
        try:
            val_default = float(val_raw)
        except Exception:
            val_default = 0.0

        dt_ini_default = str(cond.get("data_inicio") or "") if cond.get("data_inicio") else ""
        dt_fim_default = str(cond.get("data_fim") or "") if cond.get("data_fim") else ""
        contra_default = str(cond.get("contrapartida") or "") if cond.get("contrapartida") else ""
        sazonal_default = bool(cond.get("campanha_sazonal", False))

        # Divergência detectada entre e-mail e anexo CSV (ex: Gama 12% vs 12,5%)
        if cond.get("divergencia_detectada"):
            st.warning(f"📊 **Divergência E-mail vs. Planilha Anexa Detectada:** {cond.get('divergencia_detectada')}")

        st.markdown("#### ✏️ Formulário de Revisão e Ajuste (Sobrescreve Alucinações da IA)")
        c1, c2, c3 = st.columns(3)
        with c1:
            edit_forn = st.text_input(
                "Fornecedor (Código FORN-### ou Nome)",
                value=forn_default,
                key=f"forn_{i}",
                help="Aceita código (ex: FORN-001) ou nome parcial/aproximado (ex: Alfa Pharma, Distribuidora Beta).",
            )
            edit_cat = st.selectbox(
                "Categoria ERP",
                options=erp_integration.CATEGORIAS_VALIDAS,
                index=erp_integration.CATEGORIAS_VALIDAS.index(cat_default),
                key=f"cat_{i}",
            )
            edit_sazonal = st.checkbox(
                "🎄 Campanha Sazonal (Trade Marketing)",
                value=sazonal_default,
                key=f"saz_{i}",
                help="Permite teto de até 30% para GENERICOS e MIP conforme Nota (*) da Política Comercial.",
            )

        with c2:
            opcoes_tipo = ["DESCONTO_PERCENTUAL", "VERBA_EXPOSICAO"]
            edit_tipo = st.selectbox(
                "Tipo de Condição",
                options=opcoes_tipo,
                index=0 if tipo_inicial == "DESCONTO_PERCENTUAL" else 1,
                key=f"tipo_{i}",
            )
            label_val = "Percentual de Desconto (%)" if edit_tipo == "DESCONTO_PERCENTUAL" else "Valor da Verba (R$)"
            edit_valor = st.number_input(
                label_val,
                min_value=0.0,
                value=val_default,
                step=0.5 if edit_tipo == "DESCONTO_PERCENTUAL" else 100.0,
                format="%.2f",
                key=f"val_{i}",
            )
            edit_contra = st.text_input(
                "Contrapartida Acordada",
                value=contra_default,
                key=f"contra_{i}",
                placeholder="Ex: Ponta de gôndola / Ilha promocional...",
            )

        with c3:
            edit_loja = st.text_input(
                "Lojas (Códigos LOJA-###, Nomes ou REDE)",
                value=loja_default,
                key=f"loja_{i}",
                help="Aceita 'REDE', códigos separados por vírgula ('LOJA-101, LOJA-102') ou nomes das filiais ('Copacabana, Méier').",
            )
            edit_dt_ini = st.text_input(
                "Data de Início (YYYY-MM-DD)",
                value=dt_ini_default,
                key=f"dt_ini_{i}",
            )
            edit_dt_fim = st.text_input(
                "Data de Fim (YYYY-MM-DD)",
                value=dt_fim_default,
                key=f"dt_fim_{i}",
            )

        # --- MOTOR DE VALIDAÇÃO DETERMINÍSTICA EM TEMPO REAL (7 EDGE CASES) ---
        erros_bloqueantes = []
        alertas_negocio = []

        # Validação 1: Fornecedor (Edge Case 2 - Fornecedor Inativo & Bug de Nomes)
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
        else:
            st.caption(
                f"✅ **Fornecedor Validado no ERP:** `{info_forn['cod_fornecedor']}` — "
                f"**{info_forn['razao_social']}** (CNPJ: `{info_forn['cnpj']}` | Status: `ATIVO`)"
            )

        # Validação 2: Lojas e Busca Indireta em Anexo (Edge Case 5)
        lojas_resolvidas, erros_lojas, flag_busca_indireta = erp_integration.resolver_lista_lojas(edit_loja)
        if flag_busca_indireta or cond.get("busca_indireta_anexo") and not lojas_resolvidas:
            erros_bloqueantes.append(
                "📎 **BUSCA INDIRETA EM ANEXO SEM LOJAS DEFINIDAS (Edge Case 5):** O e-mail faz referência indireta "
                "a lojas em anexo (*'lojas listadas na planilha anexa'*), mas nenhuma loja válida foi carregada. "
                "Faça upload do arquivo `.csv`/`.xlsx` anexo junto com o e-mail ou digite os nomes/códigos das lojas acima."
            )
        elif erros_lojas:
            for el in erros_lojas:
                erros_bloqueantes.append(f"**Erro na Validação de Loja:** {el}")
        else:
            st.caption(f"✅ **Lojas Mapeadas no ERP ({len(lojas_resolvidas)}):** `{', '.join(lojas_resolvidas)}`")

        # Validação 3: Limites de Vigência (Regra 6 / Edge Case 7)
        val_vigencia = erp_integration.validar_vigencia(edit_dt_ini, edit_dt_fim)
        if not val_vigencia["valido"]:
            for ev in val_vigencia["erros"]:
                erros_bloqueantes.append(f"📅 **VIOLAÇÃO DE VIGÊNCIA (Regra 6 / Edge Case 7):** {ev}")

        # Validação 4: Sobreposição Contratual no Extrato ERP (Regra 9 / Edge Case 6)
        cod_forn_valido = info_forn["cod_fornecedor"] if info_forn["encontrado"] else edit_forn
        sobreposicao = erp_integration.verificar_sobreposicao_extrato(
            cod_fornecedor=cod_forn_valido,
            cod_categoria=edit_cat,
            lojas=lojas_resolvidas,
            data_inicio_str=edit_dt_ini,
            data_fim_str=edit_dt_fim,
        )
        if sobreposicao["tem_conflito"]:
            erros_bloqueantes.append(
                f"⚠️ **SOBREPOSIÇÃO CONTRATUAL DETECTADA (Regra 9 / Edge Case 6):** {sobreposicao['mensagem']}"
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

        # Exibir Banners de Status e Alertas
        st.markdown("#### 🔍 Diagnóstico de Auditoria e Alçada")
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            st.metric("Alçada Mínima Exigida", aval_pol["alcada_exibicao"])
        with col_st2:
            st.metric("Status na Política", aval_pol["status_politica"])
        with col_st3:
            dias_txt = f"{val_vigencia['dias_vigencia']} dias" if val_vigencia.get("dias_vigencia") else "Inválida"
            st.metric("Duração da Vigência", dias_txt)

        for alerta in alertas_negocio:
            st.warning(alerta)

        if erros_bloqueantes:
            for erro_msg in erros_bloqueantes:
                st.error(erro_msg)
        else:
            st.success(
                f"✅ **Condição 100% Validada!** Pronta para ser enviada à fila da **{aval_pol['alcada_exibicao']}**."
            )

        # Construir Payload JSON para Preview Técnico e Download (Requisito 4)
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
                key=f"dl_analista_{i}",
            )

        # Botão de Envio para a Fila de Aprovação (SQLite)
        btn_enviar = st.button(
            f"📤 Enviar Condição #{i+1} para Fila de Aprovação ({aval_pol['alcada_exibicao']})",
            key=f"btn_fila_{i}",
            type="primary",
            disabled=(len(erros_bloqueantes) > 0),
        )
        if btn_enviar:
            ok_schema, erros_schema = erp_integration.validar_schema_payload(payload_preview)
            if not ok_schema:
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
                    "criado_por": usuario.get("nome", "Analista"),
                })
                st.success(
                    f"🎉 Condição enviada com sucesso para a **Fila de Aprovação** sob o protocolo **#{novo_id}** "
                    f"(Alçada: **{aval_pol['alcada_exibicao']}**)! Acesse com perfil de `{aval_pol['alcada_minima']}` (ou superior) para aprovar."
                )


def renderizar_visao_aprovador(usuario: dict):
    """
    Renderiza a tela de Fila de Aprovação para Coordenador, Gerente e Diretor,
    respeitando rigorosamente a hierarquia cumulativa de alçadas.
    """
    role = usuario["role"].lower()
    desc_escopo = {
        "coordenador": "Você visualiza e aprova condições de **Coordenação Comercial** (Descontos até 10%).",
        "gerente": "Você visualiza e aprova condições de **Coordenação Comercial** e **Gerência Comercial** (Descontos até 20% e Verbas até R$ 5.000,00).",
        "diretor": "Você possui alçada máxima (**Diretoria Comercial**): visualiza e aprova **todas as condições** (Coordenação, Gerência, Diretoria e Exceções Sazonais até 30%).",
    }

    st.title(f"🏛️ Fila de Aprovação — {usuario['cargo_exibicao']}")
    st.info(f"🔐 **Escopo Hierárquico Ativo ({usuario['nome']}):** {desc_escopo.get(role, '')}")

    todos_visiveis = database.listar_fila_por_perfil(role)
    pendentes = [x for x in todos_visiveis if x["status_fila"] == "PENDENTE"]
    aprovados = [x for x in todos_visiveis if x["status_fila"] == "APROVADO"]
    rejeitados = [x for x in todos_visiveis if x["status_fila"] == "REJEITADO"]
    acima_alcada = database.contar_itens_acima_alcada(role)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏳ Pendentes no seu Escopo", len(pendentes))
    m2.metric("✅ Aprovadas", len(aprovados))
    m3.metric("❌ Reprovadas", len(rejeitados))
    m4.metric("🔒 Retidas em Alçada Superior", acima_alcada)

    if acima_alcada > 0:
        st.caption(
            f"ℹ️ *Existem **{acima_alcada}** condição(ões) pendente(s) que exigem alçada superior à sua "
            f"(`{'Gerente ou Diretor' if role == 'coordenador' else 'Diretor'}`) e por governança não são listadas para aprovação neste perfil.*"
        )

    st.divider()
    filtro = st.radio(
        "Filtrar por Status:",
        ["PENDENTE", "APROVADO", "REJEITADO", "TODOS"],
        horizontal=True,
    )

    lista_exibicao = (
        todos_visiveis if filtro == "TODOS"
        else [x for x in todos_visiveis if x["status_fila"] == filtro]
    )

    if not lista_exibicao:
        st.warning(f"Nenhuma condição encontrada com status **{filtro}** para a sua alçada ({usuario['cargo_exibicao']}).")
        return

    for item in lista_exibicao:
        renderizar_card_item_fila(item, usuario)


def renderizar_card_item_fila(item: dict, usuario: dict):
    """Renderiza cada card da fila de aprovação com detalhes, expander JSON técnico, download e botões de decisão."""
    item_id = item["id"]
    status = item["status_fila"]
    icone_st = {"PENDENTE": "⏳", "APROVADO": "✅", "REJEITADO": "❌"}.get(status, "📋")
    val_fmt = (
        f"{item['valor']:.2f}% de Desconto"
        if item["tipo"] == "DESCONTO_PERCENTUAL"
        else f"R$ {item['valor']:,.2f} (Verba de Exposição)"
    )

    try:
        lojas_lista = json.loads(item["lojas_json"])
    except Exception:
        lojas_lista = [item["lojas_json"]]

    try:
        payload_dict = json.loads(item["payload_json"])
    except Exception:
        payload_dict = {}

    # Se ainda estiver PENDENTE, mostrar no preview JSON como ficará com os dados do aprovador logado
    payload_exibicao = dict(payload_dict)
    if status == "PENDENTE":
        payload_exibicao["aprovador"] = {
            "matricula": usuario["matricula"],
            "nome": usuario["nome"],
        }

    with st.container(border=True):
        c_top1, c_top2 = st.columns([3, 1])
        with c_top1:
            st.subheader(f"{icone_st} Protocolo #{item_id} — {item['cod_fornecedor']} ({item['razao_social']})")
        with c_top2:
            st.markdown(f"**Status:** `{status}`  \n**Alçada Mínima:** `{item['alcada_exibicao']}`")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**Categoria ERP:**\n`{item['cod_categoria']}`")
        c2.markdown(f"**Condição Comercial:**\n`{val_fmt}`")
        c3.markdown(f"**Vigência:**\n`{item['data_inicio']}` até `{item['data_fim']}`")
        c4.markdown(f"**Lojas ({len(lojas_lista)}):**\n`{', '.join(lojas_lista)}`")

        if item.get("contrapartida"):
            st.markdown(f"**Contrapartida Acordada:** {item['contrapartida']}")

        if item["status_politica"] == "EXCECAO_SAZONAL":
            st.warning(f"🎄 **Exceção Sazonal (Nota * da Política):** {item.get('parecer_ia', '')}")
        else:
            st.caption(f"📋 **Parecer de Compliance:** {item.get('parecer_ia', '')} | Enviado por: {item.get('criado_por')} em {item.get('criado_em')}")

        if status != "PENDENTE":
            st.info(
                f"**Decisão Registrada:** `{status}` por **{item.get('aprovado_por')}** "
                f"(Matrícula `{item.get('aprovador_matricula')}`) em `{item.get('aprovado_em')}`"
                + (f" — Obs: *{item.get('observacao_decisao')}*" if item.get("observacao_decisao") else "")
            )

        # Requisito 4: Visibilidade Técnica do JSON + Download
        json_formatado = json.dumps(payload_exibicao, indent=2, ensure_ascii=False)
        envelope_http = erp_integration.envelopar_requisicao_post(payload_exibicao)

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
                key=f"dl_fila_{item_id}",
            )

        if status == "PENDENTE":
            obs = st.text_input(
                "Observação da Aprovação / Justificativa (Opcional):",
                key=f"obs_dec_{item_id}",
                placeholder="Ex: De acordo com campanha comercial Q4...",
            )
            b_col1, b_col2, _ = st.columns([1.2, 1.2, 2])
            with b_col1:
                if st.button("✅ Aprovar e Integrar ao ERP", key=f"aprov_{item_id}", type="primary", width="stretch"):
                    database.decidir_condicao_fila(item_id, "APROVADO", usuario, obs)
                    st.success(f"Condição #{item_id} APROVADA com sucesso! Payload JSON integrado ao ERP.")
                    st.rerun()
            with b_col2:
                if st.button("❌ Reprovar Condição", key=f"rejeit_{item_id}", width="stretch"):
                    database.decidir_condicao_fila(item_id, "REJEITADO", usuario, obs)
                    st.warning(f"Condição #{item_id} REPROVADA.")
                    st.rerun()


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
