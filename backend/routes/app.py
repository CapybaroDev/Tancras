from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import bcrypt
import os
import logging
import sys

print(os.getenv("URL_DB"))

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# =========================
# CONFIGURAÇÕES
# =========================

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

# =========================
# CONEXÃO COM POSTGRESQL
# =========================

def conectar():
    url = os.getenv("URL_DB")
    if not url:
        raise Exception("URL_DB não definida")

    # Adiciona sslmode se não estiver na URL
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}sslmode={DB_SSLMODE}"

    return psycopg2.connect(url)


# =========================
# HASH
# =========================

def gerar_hash(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def verificar_senha(senha, hash_senha):
    return bcrypt.checkpw(senha.encode(), hash_senha.encode())


# =========================
# CRIAR TABELAS
# =========================

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

        conn.commit()
        logger.info("Banco conectado e tabelas criadas/verificadas.")

    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        raise  # Reproga a exceção para que o programa seja interrompido
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# AUXILIAR DE RESPOSTA DE ERRO
# =========================

def erro_resposta(mensagem_publico, erro_interno=None, status=500):
    if DEBUG and erro_interno:
        logger.error(erro_interno)
        return jsonify({"erro": mensagem_publico, "detalhe": str(erro_interno)}), status
    else:
        if erro_interno:
            logger.error(erro_interno)
        return jsonify({"erro": mensagem_publico}), status


# =========================
# REGISTER
# =========================

@app.route("/auth/register", methods=["POST"])
def register():
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", status=400)

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
        return erro_resposta("Erro interno ao registrar usuário", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# LOGIN
# =========================

@app.route("/auth/login", methods=["POST"])
def login():
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", status=400)

        email = dados.get("email")
        senha = dados.get("senha")

        if not email or not senha:
            return jsonify({"erro": "email e senha obrigatórios"}), 400

        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nome, usuario, senha FROM usuario WHERE email = %s", (email,))
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
                "usuario": usuario["usuario"]
            }
        })

    except Exception as e:
        return erro_resposta("Erro interno ao fazer login", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# CRIAR POST
# =========================

@app.route("/posts", methods=["POST"])
def criar_post():
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", status=400)

        usuario_id = dados.get("usuario_id")
        conteudo = dados.get("conteudo")

        if not usuario_id or not conteudo:
            return jsonify({"erro": "dados inválidos"}), 400

        if not isinstance(conteudo, str) or not conteudo.strip():
            return jsonify({"erro": "conteúdo inválido ou vazio"}), 400

        conn = conectar()
        cur = conn.cursor()
        cur.execute("INSERT INTO posts (usuario_id, conteudo) VALUES (%s, %s)", (usuario_id, conteudo))
        cur.execute("UPDATE usuario SET postagens = postagens + 1 WHERE id = %s", (usuario_id,))
        conn.commit()

        return jsonify({"mensagem": "post criado"}), 201

    except Exception as e:
        return erro_resposta("Erro interno ao criar post", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# LISTAR POSTS
# =========================

@app.route("/posts", methods=["GET"])
def listar_posts():
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                posts.*,
                usuario.nome,
                usuario.usuario,
                usuario.foto_perfil
            FROM posts
            JOIN usuario ON posts.usuario_id = usuario.id
            ORDER BY posts.id DESC
        """)
        posts = cur.fetchall()
        return jsonify(posts)

    except Exception as e:
        return erro_resposta("Erro interno ao listar posts", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# DELETAR POST
# =========================

@app.route("/posts/<int:id>", methods=["DELETE"])
def deletar_post(id):
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT usuario_id FROM posts WHERE id = %s", (id,))
        post = cur.fetchone()

        if not post:
            return jsonify({"erro": "post não encontrado"}), 404

        usuario_id = post["usuario_id"]
        cur.execute("DELETE FROM posts WHERE id = %s", (id,))
        cur.execute("UPDATE usuario SET postagens = postagens - 1 WHERE id = %s AND postagens > 0", (usuario_id,))
        conn.commit()

        return jsonify({"mensagem": "post deletado"})

    except Exception as e:
        return erro_resposta("Erro interno ao deletar post", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# CURTIR / DESCURTIR
# =========================

@app.route("/posts/<int:id>/curtir", methods=["POST"])
def curtir_post(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", status=400)

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
        return erro_resposta("Erro interno ao curtir/descurtir", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# COMENTAR
# =========================

@app.route("/posts/<int:id>/comentarios", methods=["POST"])
def comentar(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", status=400)

        usuario_id = dados.get("usuario_id")
        conteudo = dados.get("conteudo")

        if not usuario_id or not conteudo:
            return jsonify({"erro": "dados inválidos"}), 400

        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("INSERT INTO comentarios (usuario_id, post_id, conteudo) VALUES (%s, %s, %s)",
                    (usuario_id, id, conteudo))
        cur.execute("UPDATE posts SET comentarios = comentarios + 1 WHERE id = %s", (id,))
        conn.commit()
        cur.execute("SELECT comentarios FROM posts WHERE id = %s", (id,))
        total = cur.fetchone()["comentarios"]

        return jsonify({"mensagem": "comentário criado", "comentarios": total})

    except Exception as e:
        return erro_resposta("Erro interno ao comentar", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# LISTAR COMENTÁRIOS
# =========================

@app.route("/posts/<int:id>/comentarios", methods=["GET"])
def listar_comentarios(id):
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                comentarios.id,
                comentarios.conteudo,
                comentarios.data_comentario,
                usuario.usuario
            FROM comentarios
            JOIN usuario ON comentarios.usuario_id = usuario.id
            WHERE comentarios.post_id = %s
            ORDER BY comentarios.id DESC
        """, (id,))
        comentarios = cur.fetchall()
        return jsonify(comentarios)

    except Exception as e:
        return erro_resposta("Erro interno ao listar comentários", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# SEGUIR / DESSEGUIR
# =========================

@app.route("/usuarios/<int:id>/seguir", methods=["POST"])
def seguir(id):
    conn = None
    cur = None
    try:
        dados = request.get_json()
        if not dados:
            return erro_resposta("Dados JSON inválidos", status=400)

        seguidor_id = dados.get("seguidor_id")
        if not seguidor_id:
            return jsonify({"erro": "seguidor inválido"}), 400

        if seguidor_id == id:
            return jsonify({"erro": "você não pode seguir a si mesmo"}), 400

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
        return erro_resposta("Erro interno ao seguir/desseguir", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# FEED
# =========================

@app.route("/feed", methods=["GET"])
def feed():
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                posts.id,
                posts.usuario_id,
                posts.conteudo,
                posts.imagem,
                posts.curtidas,
                posts.comentarios,
                posts.reposts,
                posts.data_post,
                usuario.nome,
                usuario.usuario,
                usuario.foto_perfil
            FROM posts
            JOIN usuario ON posts.usuario_id = usuario.id
            ORDER BY posts.id DESC
        """)
        posts = cur.fetchall()
        return jsonify(posts)

    except Exception as e:
        return erro_resposta("Erro interno ao carregar feed", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# PERFIL
# =========================

@app.route("/usuarios/<int:id>", methods=["GET"])
def buscar_usuario(id):
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                id, nome, usuario, bio, foto_perfil, banner,
                seguidores, seguindo, postagens, verificado, data_criacao
            FROM usuario
            WHERE id = %s
        """, (id,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({"erro": "usuário não encontrado"}), 404

        return jsonify(usuario)

    except Exception as e:
        return erro_resposta("Erro interno ao buscar usuário", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# POSTS DO PERFIL
# =========================

@app.route("/usuarios/<int:id>/posts", methods=["GET"])
def posts_usuario(id):
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                posts.*,
                usuario.nome,
                usuario.usuario
            FROM posts
            JOIN usuario ON posts.usuario_id = usuario.id
            WHERE usuario.id = %s
            ORDER BY posts.id DESC
        """, (id,))
        posts = cur.fetchall()
        return jsonify(posts)

    except Exception as e:
        return erro_resposta("Erro interno ao listar posts do usuário", e, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# HOME
# =========================

@app.route("/", methods=["GET"])
def home():
    return jsonify({"mensagem": "API funcionando"})


# =========================
# START
# =========================

if __name__ == "__main__":
    try:
        criar_tabelas()
    except Exception as e:
        logger.critical("Não foi possível criar as tabelas. Abortando inicialização.")
        sys.exit(1)

    app.run(host="0.0.0.0", port=5000, debug=DEBUG)