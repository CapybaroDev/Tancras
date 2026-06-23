from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_compress import Compress
import psycopg2
import psycopg2.extras
import bcrypt
import os
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
Compress(app)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

def conectar():
    url = os.getenv("URL_DB")
    if not url:
        raise Exception("URL_DB não definida")
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}sslmode={DB_SSLMODE}"
    return psycopg2.connect(url)

def gerar_hash(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def verificar_senha(senha, hash_senha):
    return bcrypt.checkpw(senha.encode(), hash_senha.encode())

def criar_tabelas():
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                usuario VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                bio TEXT,
                foto_perfil TEXT,
                banner TEXT,
                seguidores INTEGER DEFAULT 0,
                seguindo INTEGER DEFAULT 0,
                postagens INTEGER DEFAULT 0,
                verificado BOOLEAN DEFAULT FALSE,
                admin BOOLEAN DEFAULT FALSE,
                data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
                conteudo TEXT NOT NULL,
                imagem TEXT,
                curtidas INTEGER DEFAULT 0,
                comentarios INTEGER DEFAULT 0,
                reposts INTEGER DEFAULT 0,
                data_post TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS curtidas (
                usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                PRIMARY KEY (usuario_id, post_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                conteudo TEXT NOT NULL,
                data_comentario TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seguidores (
                seguidor_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
                seguindo_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
                PRIMARY KEY (seguidor_id, seguindo_id)
            );
        """)
        # Índices
        cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_usuario_id ON posts(usuario_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_data_post ON posts(data_post DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_post_id ON comentarios(post_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_curtidas_post_id ON curtidas(post_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_seguidores_seguindo_id ON seguidores(seguindo_id);")
        conn.commit()
        logger.info("Banco conectado e tabelas/índices criados.")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()

def erro_resposta(mensagem_publico, erro_interno=None, status=500):
    if DEBUG and erro_interno:
        logger.error(erro_interno)
        return jsonify({"erro": mensagem_publico, "detalhe": str(erro_interno)}), status
    else:
        if erro_interno: logger.error(erro_interno)
        return jsonify({"erro": mensagem_publico}), status

# ========== ROTAS ==========
@app.route("/auth/register", methods=["POST"])
def register():
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        nome = dados.get("nome")
        usuario = dados.get("usuario")
        email = dados.get("email")
        senha = dados.get("senha")
        if not nome or not usuario or not email or not senha:
            return jsonify({"erro": "todos os campos são obrigatórios"}), 400
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id FROM usuario WHERE email = %s OR usuario = %s", (email, usuario))
        if cur.fetchone():
            return jsonify({"erro": "email ou usuário já cadastrado"}), 400
        senha_hash = gerar_hash(senha)
        cur.execute("""
            INSERT INTO usuario (nome, usuario, email, senha)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (nome, usuario, email, senha_hash))
        novo_usuario = cur.fetchone()
        conn.commit()
        return jsonify({"mensagem": "usuário criado", "usuario_id": novo_usuario["id"]}), 201
    except Exception as e:
        return erro_resposta("Erro interno ao registrar", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/auth/login", methods=["POST"])
def login():
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        email = dados.get("email")
        senha = dados.get("senha")
        if not email or not senha:
            return jsonify({"erro": "email e senha obrigatórios"}), 400
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nome, usuario, senha, foto_perfil, admin, verificado FROM usuario WHERE email = %s", (email,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({"erro": "usuário não encontrado"}), 404
        if not verificar_senha(senha, usuario["senha"]):
            return jsonify({"erro": "senha incorreta"}), 401
        return jsonify({
            "mensagem": "login realizado",
            "usuario": {
                "id": usuario["id"],
                "nome": usuario["nome"],
                "usuario": usuario["usuario"],
                "foto_perfil": usuario["foto_perfil"],
                "admin": usuario["admin"],
                "verificado": usuario["verificado"]
            }
        })
    except Exception as e:
        return erro_resposta("Erro interno ao fazer login", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/posts", methods=["POST"])
def criar_post():
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        usuario_id = dados.get("usuario_id")
        conteudo = dados.get("conteudo", "").strip()
        imagem = dados.get("imagem", "").strip()

        if not usuario_id:
            return jsonify({"erro": "usuario_id obrigatório"}), 400
        if not conteudo and not imagem:
            return jsonify({"erro": "é necessário fornecer texto ou imagem"}), 400

        if imagem and len(imagem) > 5 * 1024 * 1024:
            return jsonify({"erro": "imagem muito grande (máx 5MB)"}), 400

        conn = conectar()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO posts (usuario_id, conteudo, imagem) VALUES (%s, %s, %s)",
            (usuario_id, conteudo, imagem if imagem else None)
        )
        cur.execute("UPDATE usuario SET postagens = postagens + 1 WHERE id = %s", (usuario_id,))
        conn.commit()
        return jsonify({"mensagem": "post criado"}), 201
    except Exception as e:
        return erro_resposta("Erro interno ao criar post", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/posts/<int:id>", methods=["DELETE"])
def deletar_post(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados or "usuario_id" not in dados:
            return jsonify({"erro": "usuario_id obrigatório"}), 400
        usuario_id = dados.get("usuario_id")
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT usuario_id FROM posts WHERE id = %s", (id,))
        post = cur.fetchone()
        if not post:
            return jsonify({"erro": "post não encontrado"}), 404

        # Verifica se o usuário atual é admin
        cur.execute("SELECT admin FROM usuario WHERE id = %s", (usuario_id,))
        user = cur.fetchone()
        is_admin = user and user["admin"]

        if post["usuario_id"] != usuario_id and not is_admin:
            return jsonify({"erro": "sem permissão"}), 403

        cur.execute("DELETE FROM posts WHERE id = %s", (id,))
        cur.execute("UPDATE usuario SET postagens = postagens - 1 WHERE id = %s AND postagens > 0", (post["usuario_id"],))
        conn.commit()
        return jsonify({"mensagem": "post deletado"})
    except Exception as e:
        return erro_resposta("Erro ao deletar post", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/posts/<int:id>/curtir", methods=["POST"])
def curtir_post(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        usuario_id = dados.get("usuario_id")
        if not usuario_id:
            return jsonify({"erro": "usuário inválido"}), 400
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM curtidas WHERE usuario_id = %s AND post_id = %s", (usuario_id, id))
        curtida = cur.fetchone()
        if curtida:
            cur.execute("DELETE FROM curtidas WHERE usuario_id = %s AND post_id = %s", (usuario_id, id))
            cur.execute("UPDATE posts SET curtidas = curtidas - 1 WHERE id = %s AND curtidas > 0", (id,))
            curtido = False
        else:
            cur.execute("INSERT INTO curtidas (usuario_id, post_id) VALUES (%s, %s)", (usuario_id, id))
            cur.execute("UPDATE posts SET curtidas = curtidas + 1 WHERE id = %s", (id,))
            curtido = True
        conn.commit()
        cur.execute("SELECT curtidas FROM posts WHERE id = %s", (id,))
        total = cur.fetchone()["curtidas"]
        return jsonify({"curtido": curtido, "curtidas": total})
    except Exception as e:
        return erro_resposta("Erro ao curtir", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/posts/<int:id>/comentarios", methods=["POST"])
def comentar(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        usuario_id = dados.get("usuario_id")
        conteudo = dados.get("conteudo")
        if not usuario_id or not conteudo:
            return jsonify({"erro": "dados inválidos"}), 400
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("INSERT INTO comentarios (usuario_id, post_id, conteudo) VALUES (%s, %s, %s)", (usuario_id, id, conteudo))
        cur.execute("UPDATE posts SET comentarios = comentarios + 1 WHERE id = %s", (id,))
        conn.commit()
        cur.execute("SELECT comentarios FROM posts WHERE id = %s", (id,))
        total = cur.fetchone()["comentarios"]
        return jsonify({"mensagem": "comentário criado", "comentarios": total})
    except Exception as e:
        return erro_resposta("Erro ao comentar", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/posts/<int:id>/comentarios", methods=["GET"])
def listar_comentarios(id):
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT c.id, c.conteudo, c.data_comentario, u.usuario
            FROM comentarios c
            JOIN usuario u ON c.usuario_id = u.id
            WHERE c.post_id = %s
            ORDER BY c.id DESC
        """, (id,))
        comentarios = cur.fetchall()
        return jsonify(comentarios)
    except Exception as e:
        return erro_resposta("Erro ao listar comentários", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/usuarios/<int:id>/seguir", methods=["POST"])
def seguir(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        seguidor_id = dados.get("seguidor_id")
        if not seguidor_id:
            return jsonify({"erro": "seguidor inválido"}), 400
        if seguidor_id == id:
            return jsonify({"erro": "não pode seguir a si mesmo"}), 400
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM seguidores WHERE seguidor_id = %s AND seguindo_id = %s", (seguidor_id, id))
        seguindo = cur.fetchone()
        if seguindo:
            cur.execute("DELETE FROM seguidores WHERE seguidor_id = %s AND seguindo_id = %s", (seguidor_id, id))
            cur.execute("UPDATE usuario SET seguidores = seguidores - 1 WHERE id = %s AND seguidores > 0", (id,))
            cur.execute("UPDATE usuario SET seguindo = seguindo - 1 WHERE id = %s AND seguindo > 0", (seguidor_id,))
            seguindo_status = False
        else:
            cur.execute("INSERT INTO seguidores (seguidor_id, seguindo_id) VALUES (%s, %s)", (seguidor_id, id))
            cur.execute("UPDATE usuario SET seguidores = seguidores + 1 WHERE id = %s", (id,))
            cur.execute("UPDATE usuario SET seguindo = seguindo + 1 WHERE id = %s", (seguidor_id,))
            seguindo_status = True
        conn.commit()
        return jsonify({"seguindo": seguindo_status})
    except Exception as e:
        return erro_resposta("Erro ao seguir", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/feed", methods=["GET"])
def feed():
    conn = None
    cur = None
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = (page - 1) * limit
        usuario_logado_id = request.args.get('usuario_id', type=int)

        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT COUNT(*) FROM posts")
        total_posts = cur.fetchone()["count"]

        cur.execute("""
            SELECT
                p.id,
                p.usuario_id,
                p.conteudo,
                p.imagem,
                p.curtidas,
                p.comentarios,
                p.reposts,
                p.data_post,
                u.nome,
                u.usuario,
                u.foto_perfil,
                u.verificado,
                CASE WHEN %s IS NOT NULL AND EXISTS (
                    SELECT 1 FROM seguidores 
                    WHERE seguidor_id = %s AND seguindo_id = p.usuario_id
                ) THEN true ELSE false END AS seguindo
            FROM posts p
            JOIN usuario u ON p.usuario_id = u.id
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """, (usuario_logado_id, usuario_logado_id, limit, offset))

        posts = cur.fetchall()
        has_more = offset + limit < total_posts

        return jsonify({
            "posts": posts,
            "total": total_posts,
            "page": page,
            "limit": limit,
            "has_more": has_more
        })
    except Exception as e:
        logger.error(f"Erro no feed: {e}")
        return jsonify({"erro": "Erro interno ao carregar feed", "detalhe": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/usuarios/search", methods=["GET"])
def buscar_usuarios():
    conn = None
    cur = None
    try:
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify([])
        
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, nome, usuario, foto_perfil
            FROM usuario
            WHERE usuario ILIKE %s OR nome ILIKE %s
            ORDER BY 
                CASE 
                    WHEN usuario ILIKE %s THEN 1
                    WHEN nome ILIKE %s THEN 2
                    ELSE 3
                END
            LIMIT 10
        """, (f"%{q}%", f"%{q}%", f"{q}%", f"{q}%"))
        usuarios = cur.fetchall()
        return jsonify(usuarios)
    except Exception as e:
        return erro_resposta("Erro na busca", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/usuarios/<int:id>", methods=["GET"])
def buscar_usuario(id):
    conn = None
    cur = None
    try:
        usuario_logado_id = request.args.get("usuario_id", type=int)
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verifica se o usuário logado é admin
        is_admin = False
        if usuario_logado_id:
            cur.execute("SELECT admin FROM usuario WHERE id = %s", (usuario_logado_id,))
            admin_row = cur.fetchone()
            if admin_row:
                is_admin = admin_row["admin"]
        
        if is_admin:
            cur.execute("""
                SELECT
                    id, nome, usuario, bio, foto_perfil, banner,
                    seguidores, seguindo, postagens, verificado, admin, data_criacao,
                    CASE WHEN %s IS NOT NULL AND EXISTS (
                        SELECT 1 FROM seguidores 
                        WHERE seguidor_id = %s AND seguindo_id = id
                    ) THEN true ELSE false END AS seguido_por_voce
                FROM usuario
                WHERE id = %s
            """, (usuario_logado_id, usuario_logado_id, id))
        else:
            cur.execute("""
                SELECT
                    id, nome, usuario, bio, foto_perfil, banner,
                    seguidores, seguindo, postagens, verificado, data_criacao,
                    CASE WHEN %s IS NOT NULL AND EXISTS (
                        SELECT 1 FROM seguidores 
                        WHERE seguidor_id = %s AND seguindo_id = id
                    ) THEN true ELSE false END AS seguido_por_voce
                FROM usuario
                WHERE id = %s
            """, (usuario_logado_id, usuario_logado_id, id))
        
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({"erro": "usuário não encontrado"}), 404
        return jsonify(usuario)
    except Exception as e:
        return erro_resposta("Erro ao buscar usuário", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/usuarios/<int:id>", methods=["PUT"])
def atualizar_usuario(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", 400)
        usuario_id = dados.get("usuario_id")
        if not usuario_id:
            return jsonify({"erro": "usuario_id obrigatório"}), 400

        # 1. Conectar ao banco
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 2. Verificar se o solicitante é admin
        cur.execute("SELECT admin FROM usuario WHERE id = %s", (usuario_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({"erro": "usuário não encontrado"}), 404
        is_admin = user["admin"]

        # 3. Verificar permissão: só o próprio usuário ou admin podem editar
        if usuario_id != id and not is_admin:
            return jsonify({"erro": "sem permissão"}), 403

        # 4. Buscar dados atuais do perfil a ser atualizado
        cur.execute("SELECT * FROM usuario WHERE id = %s", (id,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({"erro": "usuário não encontrado"}), 404

        # 5. Obter novos valores (ou manter os antigos)
        nome = dados.get("nome", usuario["nome"])
        bio = dados.get("bio", usuario.get("bio"))
        foto_perfil = dados.get("foto_perfil", usuario.get("foto_perfil"))

        if foto_perfil and len(foto_perfil) > 1000000:
            return jsonify({"erro": "imagem muito grande"}), 400

        # 6. Atualizar
        cur.execute(
            "UPDATE usuario SET nome=%s, bio=%s, foto_perfil=%s WHERE id=%s",
            (nome, bio, foto_perfil, id)
        )
        conn.commit()

        # 7. Retornar dados atualizados
        cur.execute("""
            SELECT id, nome, usuario, bio, foto_perfil, seguidores, seguindo, postagens, admin, verificado
            FROM usuario WHERE id=%s
        """, (id,))
        atualizado = cur.fetchone()
        return jsonify(atualizado)

    except Exception as e:
        return erro_resposta("Erro ao atualizar perfil", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/usuarios/<int:id>/posts", methods=["GET"])
def posts_usuario(id):
    conn = None
    cur = None
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = (page - 1) * limit
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT p.*, u.nome, u.usuario, u.verificado
            FROM posts p
            JOIN usuario u ON p.usuario_id = u.id
            WHERE u.id = %s
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """, (id, limit, offset))
        posts = cur.fetchall()
        return jsonify(posts)
    except Exception as e:
        return erro_resposta("Erro ao listar posts do usuário", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/usuarios/<int:id>", methods=["DELETE"])
def deletar_usuario(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados or "usuario_id" not in dados:
            return jsonify({"erro": "usuario_id obrigatório"}), 400

        admin_id = dados.get("usuario_id")
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Verifica se o solicitante é admin
        cur.execute("SELECT admin FROM usuario WHERE id = %s", (admin_id,))
        admin_check = cur.fetchone()
        if not admin_check or not admin_check["admin"]:
            return jsonify({"erro": "Apenas administradores podem deletar usuários"}), 403

        if id == admin_id:
            return jsonify({"erro": "Não é possível deletar o próprio administrador"}), 403

        cur.execute("SELECT id FROM usuario WHERE id = %s", (id,))
        if not cur.fetchone():
            return jsonify({"erro": "Usuário não encontrado"}), 404

        cur.execute("DELETE FROM usuario WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"mensagem": "Usuário deletado com sucesso"}), 200

    except Exception as e:
        return erro_resposta("Erro ao deletar usuário", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ========== ROTA ADMIN ==========
@app.route("/admin/usuarios/<int:id>", methods=["PUT"])
def admin_atualizar_usuario(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados or "admin_id" not in dados:
            return jsonify({"erro": "admin_id obrigatório"}), 400
        
        admin_id = dados.get("admin_id")
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se quem está fazendo a requisição é admin
        cur.execute("SELECT admin FROM usuario WHERE id = %s", (admin_id,))
        admin_check = cur.fetchone()
        if not admin_check or not admin_check["admin"]:
            return jsonify({"erro": "Apenas administradores podem executar esta ação"}), 403
        
        # Atualizar campos do usuário alvo
        set_clauses = []
        params = []
        if "admin" in dados:
            set_clauses.append("admin = %s")
            params.append(dados["admin"])
        if "verificado" in dados:
            set_clauses.append("verificado = %s")
            params.append(dados["verificado"])
        
        if not set_clauses:
            return jsonify({"erro": "Nenhum campo para atualizar"}), 400
        
        params.append(id)
        query = f"UPDATE usuario SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, nome, usuario, admin, verificado"
        cur.execute(query, params)
        updated = cur.fetchone()
        
        if not updated:
            return jsonify({"erro": "Usuário não encontrado"}), 404
        
        conn.commit()
        return jsonify(updated)
    
    except Exception as e:
        return erro_resposta("Erro ao atualizar usuário pelo admin", e, 500)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"mensagem": "API funcionando"})

if __name__ == "__main__":
    try:
        criar_tabelas()
    except Exception as e:
        logger.critical("Erro crítico ao criar tabelas")
        sys.exit(1)
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)