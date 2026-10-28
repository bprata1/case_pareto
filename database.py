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
                observacao_decisao TEXT
            )
        """)

        # Garantir coluna justificativa_analista caso a tabela já existisse de versão anterior
        cursor.execute("PRAGMA table_info(fila_aprovacao)")
        colunas_existentes = [col["name"] for col in cursor.fetchall()]
        if "justificativa_analista" not in colunas_existentes:
            cursor.execute("ALTER TABLE fila_aprovacao ADD COLUMN justificativa_analista TEXT DEFAULT ''")

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


def listar_condicoes_ativas_sqlite() -> list:
    """
    Retorna todas as condições no SQLite com status 'PENDENTE' ou 'APROVADO'
    para verificação contra duplicidade e sobreposição no momento da ingestão.
    """
    try:
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM fila_aprovacao WHERE status_fila IN ('PENDENTE', 'APROVADO') ORDER BY id DESC"
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Erro ao consultar condições ativas no SQLite: {e}")
        return []


def listar_fila_por_perfil(role: str, status_filtro: str = None, incluir_todas_alcadas: bool = False) -> list:
    """
    Retorna os itens da fila para o perfil informado:
    - Se `role == 'analista'` ou `incluir_todas_alcadas == True`: retorna todas as demandas da fila para visualização.
    - Caso contrário (visão estrita de alçada do gestor):
      * coordenador (nível 2): vê itens com nivel_hierarquia <= 2
      * gerente (nível 3): vê itens com nivel_hierarquia <= 3
      * diretor (nível 4): vê todos os itens (nivel_hierarquia <= 4)
    """
    init_db()
    r = role.strip().lower() if role else "analista"
    if r == "analista" or incluir_todas_alcadas:
        return listar_todas_condicoes_fila(status_filtro)

    nivel_usuario = HIERARQUIA_CARGOS.get(r, 1)
    conn = get_connection()
    cursor = conn.cursor()

    if status_filtro and status_filtro != "TODOS":
        cursor.execute(
            "SELECT * FROM fila_aprovacao WHERE nivel_hierarquia <= ? AND status_fila = ? ORDER BY id DESC",
            (nivel_usuario, status_filtro),
        )
    else:
        cursor.execute(
            "SELECT * FROM fila_aprovacao WHERE nivel_hierarquia <= ? ORDER BY id DESC",
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


def decidir_condicao_fila(item_id: int, novo_status: str, usuario: dict, observacao: str = "") -> bool:
    """
    Registra a aprovação ou reprovação de um item na fila.
    Atualiza também o bloco `aprovador` dentro do `payload_json` com o nome e matrícula reais do aprovador.
    """
    try:
        init_db()
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

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE fila_aprovacao
            SET status_fila = ?,
                aprovado_por = ?,
                aprovador_matricula = ?,
                aprovado_em = ?,
                observacao_decisao = ?,
                payload_json = ?
            WHERE id = ?
        """, (
            novo_status.upper(),
            f"{nome_aprov} ({usuario.get('cargo_exibicao', usuario.get('role', ''))})",
            mat_aprov,
            agora,
            observacao.strip() if observacao else "",
            json.dumps(payload, ensure_ascii=False),
            item_id,
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar decisão na fila: {e}")
        return False
