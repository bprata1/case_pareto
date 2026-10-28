import os
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pareto_v2.db")

HIERARQUIA_CARGOS = {
    "analista": 1,
    "coordenador": 2,
    "gerente": 3,
    "diretor": 4,
}

USUARIOS_PADRAO = [
    ("renata.alves", "123", "analista", "Renata Alves", "001120", "Analista Comercial"),
    ("carlos.eduardo", "123", "coordenador", "Carlos Eduardo", "002310", "Coordenação Comercial"),
    ("fernanda.lima", "123", "gerente", "Fernanda Lima", "003450", "Gerência Comercial"),
    ("roberto.almeida", "123", "diretor", "Roberto Almeida", "004512", "Diretoria Comercial"),
]

MAPA_ALIASES_LOGIN = {
    "analista": "renata.alves",
    "coordenador": "carlos.eduardo",
    "gerente": "fernanda.lima",
    "diretor": "roberto.almeida",
}


def get_connection():
    """Retorna conexão SQLite com row_factory configurado para dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Inicializa o banco SQLite local criando as tabelas `usuarios` e `fila_aprovacao`
    e populando os usuários nominais ('renata.alves', 'carlos.eduardo', 'fernanda.lima', 'roberto.almeida').
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                nome TEXT NOT NULL,
                matricula TEXT NOT NULL,
                cargo_exibicao TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fila_aprovacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_fornecedor TEXT NOT NULL,
                razao_social TEXT,
                cod_categoria TEXT NOT NULL,
                tipo TEXT NOT NULL,
                valor REAL NOT NULL,
                lojas_json TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                data_fim TEXT NOT NULL,
                contrapartida TEXT,
                cod_condicao_substituida TEXT,
                justificativa_analista TEXT DEFAULT '',
                alcada_minima TEXT NOT NULL,
                alcada_exibicao TEXT NOT NULL,
                nivel_hierarquia INTEGER NOT NULL,
                status_politica TEXT NOT NULL,
                parecer_ia TEXT,
                alertas_json TEXT,
                payload_json TEXT NOT NULL,
                origem_referencia TEXT,
                status_fila TEXT NOT NULL DEFAULT 'PENDENTE',
                criado_por TEXT,
                criado_em TEXT,
                aprovado_por TEXT,
                aprovador_matricula TEXT,
                aprovado_em TEXT,
                observacao_decisao TEXT,
                motivo_rejeicao TEXT DEFAULT ''
            )
        """)

        # Garantir colunas justificativa_analista e motivo_rejeicao caso a tabela já existisse de versão anterior
        cursor.execute("PRAGMA table_info(fila_aprovacao)")
        colunas_existentes = [col["name"] for col in cursor.fetchall()]
        if "justificativa_analista" not in colunas_existentes:
            cursor.execute("ALTER TABLE fila_aprovacao ADD COLUMN justificativa_analista TEXT DEFAULT ''")
        if "motivo_rejeicao" not in colunas_existentes:
            cursor.execute("ALTER TABLE fila_aprovacao ADD COLUMN motivo_rejeicao TEXT DEFAULT ''")

        # Remover logins genéricos legados da V2 caso existam, mantendo apenas os logins nominais da V3
        cursor.execute("DELETE FROM usuarios WHERE username IN ('analista', 'coordenador', 'gerente', 'diretor')")

        for u in USUARIOS_PADRAO:
            cursor.execute("""
                INSERT OR REPLACE INTO usuarios (username, password, role, nome, matricula, cargo_exibicao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, u)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar banco SQLite: {e}")


def reset_db():
    """
    Limpa completamente a fila de aprovação e restaura os usuários padrão.
    Usado pelo botão 'Resetar Sistema e Limpar Banco de Dados' na Área do Avaliador.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS fila_aprovacao")
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        conn.commit()
        conn.close()
        init_db()
        return True
    except Exception as e:
        print(f"Erro ao resetar banco SQLite: {e}")
        return False


def _normalizar_username(username: str) -> str:
    if not username:
        return ""
    u = username.strip().lower()
    return MAPA_ALIASES_LOGIN.get(u, u)


def autenticar_usuario(username: str, password: str) -> dict:
    """Valida credenciais na tabela `usuarios` e retorna dicionário do usuário ou None."""
    if not username or not password:
        return None
    try:
        init_db()
        u_norm = _normalizar_username(username)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM usuarios WHERE LOWER(username) = LOWER(?) AND password = ?",
            (u_norm, password.strip()),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return None


def obter_usuario_por_username(username: str) -> dict:
    try:
        init_db()
        u_norm = _normalizar_username(username)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(username) = LOWER(?)", (u_norm,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def usuario_pode_aprovar(role: str, nivel_hierarquia_item: int) -> bool:
    """
    Verifica se o perfil logado possui alçada para aprovar/rejeitar o item:
    - analista (nível 1): nunca aprova (apenas visualiza a fila)
    - coordenador (nível 2): aprova itens de nível <= 2
    - gerente (nível 3): aprova itens de nível <= 3
    - diretor (nível 4): aprova itens de nível <= 4 (todos)
    """
    if not role:
        return False
    r = role.strip().lower()
    if r == "analista":
        return False
    nivel_user = HIERARQUIA_CARGOS.get(r, 1)
    return nivel_user >= int(nivel_hierarquia_item)


def inserir_condicao_fila(dados: dict) -> int:
    """
    Insere uma nova condição comercial validada pelo Analista na `fila_aprovacao`.
    Retorna o ID inserido.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alcada_min = dados.get("alcada_minima", "coordenador")
    nivel = HIERARQUIA_CARGOS.get(alcada_min, 4)

    cursor.execute("""
        INSERT INTO fila_aprovacao (
            cod_fornecedor, razao_social, cod_categoria, tipo, valor,
            lojas_json, data_inicio, data_fim, contrapartida, cod_condicao_substituida,
            justificativa_analista, alcada_minima, alcada_exibicao, nivel_hierarquia,
            status_politica, parecer_ia, alertas_json, payload_json, origem_referencia,
            status_fila, criado_por, criado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', ?, ?)
    """, (
        dados.get("cod_fornecedor", ""),
        dados.get("razao_social", ""),
        dados.get("cod_categoria", ""),
        dados.get("tipo", ""),
        float(dados.get("valor", 0.0)),
        json.dumps(dados.get("lojas", []), ensure_ascii=False),
        dados.get("data_inicio", ""),
        dados.get("data_fim", ""),
        dados.get("contrapartida"),
        dados.get("cod_condicao_substituida"),
        dados.get("justificativa_analista", ""),
        alcada_min,
        dados.get("alcada_exibicao", ""),
        nivel,
        dados.get("status_politica", "DENTRO_DA_POLITICA"),
        dados.get("parecer_ia", ""),
        json.dumps(dados.get("alertas", []), ensure_ascii=False),
        json.dumps(dados.get("payload", {}), ensure_ascii=False),
        dados.get("origem_referencia", "EMAIL"),
        dados.get("criado_por", "Renata Alves"),
        agora,
    ))
    novo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return novo_id


def atualizar_condicao_rejeitada_fila(item_id: int, dados: dict) -> int:
    """
    Épico 3 (Ciclo de Vida da Rejeição e Correção):
    Atualiza uma condição anteriormente REJEITADA com os novos dados corrigidos pelo Analista,
    retornando seu status para 'PENDENTE' e limpando os metadados da reprovação anterior.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alcada_min = dados.get("alcada_minima", "coordenador")
    nivel = HIERARQUIA_CARGOS.get(alcada_min, 4)

    cursor.execute("""
        UPDATE fila_aprovacao
        SET cod_fornecedor = ?,
            razao_social = ?,
            cod_categoria = ?,
            tipo = ?,
            valor = ?,
            lojas_json = ?,
            data_inicio = ?,
            data_fim = ?,
            contrapartida = ?,
            cod_condicao_substituida = ?,
            justificativa_analista = ?,
            alcada_minima = ?,
            alcada_exibicao = ?,
            nivel_hierarquia = ?,
            status_politica = ?,
            parecer_ia = ?,
            alertas_json = ?,
            payload_json = ?,
            origem_referencia = ?,
            status_fila = 'PENDENTE',
            criado_por = ?,
            criado_em = ?,
            aprovado_por = NULL,
            aprovador_matricula = NULL,
            aprovado_em = NULL,
            observacao_decisao = NULL,
            motivo_rejeicao = ''
        WHERE id = ?
    """, (
        dados.get("cod_fornecedor", ""),
        dados.get("razao_social", ""),
        dados.get("cod_categoria", ""),
        dados.get("tipo", ""),
        float(dados.get("valor", 0.0)),
        json.dumps(dados.get("lojas", []), ensure_ascii=False),
        dados.get("data_inicio", ""),
        dados.get("data_fim", ""),
        dados.get("contrapartida"),
        dados.get("cod_condicao_substituida"),
        dados.get("justificativa_analista", ""),
        alcada_min,
        dados.get("alcada_exibicao", ""),
        nivel,
        dados.get("status_politica", "DENTRO_DA_POLITICA"),
        dados.get("parecer_ia", ""),
        json.dumps(dados.get("alertas", []), ensure_ascii=False),
        json.dumps(dados.get("payload", {}), ensure_ascii=False),
        dados.get("origem_referencia", "EMAIL"),
        dados.get("criado_por", "Renata Alves"),
        agora,
        int(item_id),
    ))
    conn.commit()
    conn.close()
    return int(item_id)


def listar_todas_condicoes_fila(status_filtro: str = None) -> list:
    """
    Retorna todos os itens da fila de aprovação (para acompanhamento geral).
    """
    try:
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        if status_filtro and status_filtro != "TODOS":
            cursor.execute(
                "SELECT * FROM fila_aprovacao WHERE status_fila = ? ORDER BY id DESC",
                (status_filtro,),
            )
        else:
            cursor.execute("SELECT * FROM fila_aprovacao ORDER BY id DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Erro ao listar fila completa: {e}")
        return []


def listar_condicoes_ativas_sqlite(ignorar_id: int = None) -> list:
    """
    Retorna todas as condições no SQLite com status 'PENDENTE' ou 'APROVADO'
    para verificação contra duplicidade e sobreposição no momento da ingestão.
    """
    try:
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        if ignorar_id is not None:
            cursor.execute(
                "SELECT * FROM fila_aprovacao WHERE status_fila IN ('PENDENTE', 'APROVADO') AND id != ? ORDER BY id DESC",
                (int(ignorar_id),),
            )
        else:
            cursor.execute(
                "SELECT * FROM fila_aprovacao WHERE status_fila IN ('PENDENTE', 'APROVADO') ORDER BY id DESC"
            )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Erro ao consultar condições ativas no SQLite: {e}")
        return []


def listar_fila_por_perfil(
    role: str,
    status_filtro: str = None,
    incluir_todas_alcadas: bool = False,
    modo_escopo: str = None,
) -> list:
    """
    Épico 1 (Missão V6) — Retorna os itens da fila para o perfil informado:
    - modo_escopo == 'TODOS' (ou Analista / incluir_todas_alcadas=True): retorna todas as demandas da fila.
    - modo_escopo == 'HIERARQUIA': retorna demandas da hierarquia acumulada do gestor (nivel_hierarquia <= nivel_usuario).
    - modo_escopo == 'ESTRITO' (padrão para 'Apenas minha alçada de aprovação'):
      retorna ESTRITAMENTE os itens cujo nível de alçada exigida seja EXATAMENTE IGUAL ao nível do cargo logado
      (ex: Diretor vê apenas itens de 'Diretoria Comercial' / nivel_hierarquia == 4).
    """
    init_db()
    r = role.strip().lower() if role else "analista"
    if r == "analista" or incluir_todas_alcadas or modo_escopo == "TODOS":
        return listar_todas_condicoes_fila(status_filtro)

    escopo = (modo_escopo or "ESTRITO").upper()
    nivel_usuario = HIERARQUIA_CARGOS.get(r, 1)
    conn = get_connection()
    cursor = conn.cursor()

    operador_sql = "<=" if escopo == "HIERARQUIA" else "="

    if status_filtro and status_filtro != "TODOS":
        cursor.execute(
            f"SELECT * FROM fila_aprovacao WHERE nivel_hierarquia {operador_sql} ? AND status_fila = ? ORDER BY id DESC",
            (nivel_usuario, status_filtro),
        )
    else:
        cursor.execute(
            f"SELECT * FROM fila_aprovacao WHERE nivel_hierarquia {operador_sql} ? ORDER BY id DESC",
            (nivel_usuario,),
        )

    rows = [dict(r_row) for r_row in cursor.fetchall()]
    conn.close()
    return rows


def contar_itens_acima_alcada(role: str) -> int:
    """Retorna quantos itens PENDENTES existem em alçadas superiores à do usuário logado."""
    init_db()
    nivel_usuario = HIERARQUIA_CARGOS.get(role.lower(), 1)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as total FROM fila_aprovacao WHERE nivel_hierarquia > ? AND status_fila = 'PENDENTE'",
        (nivel_usuario,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["total"] if row else 0


def decidir_condicao_fila(
    item_id: int,
    novo_status: str,
    usuario: dict,
    observacao: str = "",
    motivo_rejeicao: str = "",
) -> bool:
    """
    Registra a aprovação ou reprovação de um item na fila.
    - Para 'REJEITADO', exige motivo de rejeição preenchido e grava em `motivo_rejeicao`.
    - Atualiza também o bloco `aprovador` dentro do `payload_json` com o nome e matrícula reais do aprovador.
    """
    try:
        init_db()
        status_fim = novo_status.strip().upper()
        motivo_rej_limpo = (motivo_rejeicao or observacao or "").strip() if status_fim == "REJEITADO" else ""
        if status_fim == "REJEITADO" and not motivo_rej_limpo:
            return False

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT payload_json, nivel_hierarquia FROM fila_aprovacao WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        # Garantir trava de segurança de alçada no backend
        if not usuario_pode_aprovar(usuario.get("role", ""), row["nivel_hierarquia"]):
            conn.close()
            return False

        payload = json.loads(row["payload_json"])
        nome_aprov = usuario.get("nome", usuario.get("username", "Aprovador"))
        mat_aprov = usuario.get("matricula", "000000")
        payload["aprovador"] = {
            "matricula": mat_aprov,
            "nome": nome_aprov,
        }

        obs_final = observacao.strip() if observacao and observacao.strip() else motivo_rej_limpo

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE fila_aprovacao
            SET status_fila = ?,
                aprovado_por = ?,
                aprovador_matricula = ?,
                aprovado_em = ?,
                observacao_decisao = ?,
                motivo_rejeicao = ?,
                payload_json = ?
            WHERE id = ?
        """, (
            status_fim,
            f"{nome_aprov} ({usuario.get('cargo_exibicao', usuario.get('role', ''))})",
            mat_aprov,
            agora,
            obs_final,
            motivo_rej_limpo,
            json.dumps(payload, ensure_ascii=False),
            item_id,
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar decisão na fila: {e}")
        return False


def obter_notificacoes_recentes(usuario: dict, limite: int = 5) -> dict:
    """
    Épico 4 (Central de Notificações):
    Retorna as últimas interações relevantes do banco de dados de acordo com o perfil logado:
    - Para o Analista: condições que foram APROVADAS ou REJEITADAS (com snippet do motivo),
      além das últimas enviadas caso ainda estejam pendentes.
    - Para os Gestores: resumo de quantas condições aguardam aprovação na sua alçada estrita e na sua hierarquia,
      mais a lista das últimas demandas pendentes/movimentadas.
    """
    if not usuario:
        return {"resumo": "", "itens": [], "pendentes_estrito": 0, "pendentes_hierarquia": 0}

    try:
        init_db()
        role = str(usuario.get("role", "analista")).strip().lower()
        nivel_user = HIERARQUIA_CARGOS.get(role, 1)
        conn = get_connection()
        cursor = conn.cursor()

        if role == "analista":
            cursor.execute("""
                SELECT * FROM fila_aprovacao
                WHERE status_fila IN ('APROVADO', 'REJEITADO')
                ORDER BY COALESCE(aprovado_em, criado_em) DESC, id DESC
                LIMIT ?
            """, (limite,))
            decididas = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) as total FROM fila_aprovacao WHERE status_fila = 'REJEITADO'")
            tot_rej = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) as total FROM fila_aprovacao WHERE status_fila = 'APROVADO'")
            tot_aprov = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) as total FROM fila_aprovacao WHERE status_fila = 'PENDENTE'")
            tot_pend = cursor.fetchone()["total"]

            conn.close()
            if tot_rej > 0:
                resumo = f"⚠️ Você tem {tot_rej} condição(ões) REJEITADA(S) aguardando correção ({tot_aprov} aprovada(s), {tot_pend} pendente(s))."
            elif tot_aprov > 0:
                resumo = f"✅ {tot_aprov} condição(ões) APROVADA(S) recentemente ({tot_pend} aguardando aprovação)."
            elif tot_pend > 0:
                resumo = f"⏳ {tot_pend} condição(ões) enviada(s) aguardando avaliação dos gestores."
            else:
                resumo = "Nenhuma condição movimentada na fila até o momento."

            return {
                "resumo": resumo,
                "itens": decididas,
                "tot_rejeitadas": tot_rej,
                "tot_aprovadas": tot_aprov,
                "tot_pendentes": tot_pend,
            }
        else:
            cursor.execute(
                "SELECT COUNT(*) as total FROM fila_aprovacao WHERE status_fila = 'PENDENTE' AND nivel_hierarquia = ?",
                (nivel_user,),
            )
            pend_estrito = cursor.fetchone()["total"]

            cursor.execute(
                "SELECT COUNT(*) as total FROM fila_aprovacao WHERE status_fila = 'PENDENTE' AND nivel_hierarquia <= ?",
                (nivel_user,),
            )
            pend_hierarquia = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT * FROM fila_aprovacao
                WHERE nivel_hierarquia <= ?
                ORDER BY CASE WHEN status_fila = 'PENDENTE' THEN 0 ELSE 1 END,
                         CASE WHEN nivel_hierarquia = ? THEN 0 ELSE 1 END,
                         id DESC
                LIMIT ?
            """, (nivel_user, nivel_user, limite))
            itens_gestor = [dict(r) for r in cursor.fetchall()]
            conn.close()

            if pend_estrito > 0:
                resumo = f"Você tem {pend_estrito} nova(s) condição(ões) aguardando aprovação na sua alçada direta."
            elif pend_hierarquia > 0:
                resumo = f"Você tem {pend_hierarquia} condição(ões) aguardando aprovação na sua hierarquia."
            else:
                resumo = "Você não possui condições pendentes aguardando aprovação no momento."

            return {
                "resumo": resumo,
                "itens": itens_gestor,
                "pendentes_estrito": pend_estrito,
                "pendentes_hierarquia": pend_hierarquia,
            }
    except Exception as e:
        print(f"Erro ao obter notificações: {e}")
        return {"resumo": "", "itens": [], "pendentes_estrito": 0, "pendentes_hierarquia": 0}
