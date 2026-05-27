from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import bcrypt

app = Flask(__name__)

CORS(app)

# =========================
# CONEXÃO
# =========================

def conectar():

    conn = sqlite3.connect("backend/banco/banco.db")
    conn.row_factory = sqlite3.Row

    return conn


# =========================
# HASH
# =========================

def gerar_hash(senha):

    return bcrypt.hashpw(
        senha.encode(),
        bcrypt.gensalt()
    ).decode()


def verificar_senha(senha, hash):

    return bcrypt.checkpw(
        senha.encode(),
        hash.encode()
    )


# =========================
# AUTH REGISTER
# =========================

@app.route("/auth/register", methods=["POST"])
def register():

    dados = request.json

    nome = dados["nome"]
    usuario = dados["usuario"]
    email = dados["email"]
    senha = dados["senha"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM usuario WHERE email = ?",
        (email,)
    )

    usuario_existente = cursor.fetchone()

    if usuario_existente:

        conn.close()

        return jsonify({
            "erro": "email já cadastrado"
        }), 400

    senha_hash = gerar_hash(senha)

    cursor.execute("""
        INSERT INTO usuario (
            nome,
            usuario,
            email,
            senha
        )
        VALUES (?, ?, ?, ?)
    """, (
        nome,
        usuario,
        email,
        senha_hash
    ))

    conn.commit()

    conn.close()

    return jsonify({
        "mensagem": "usuário criado"
    }), 201


# =========================
# AUTH LOGIN
# =========================

@app.route("/auth/login", methods=["POST"])
def login():

    dados = request.json

    email = dados["email"]
    senha = dados["senha"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM usuario WHERE email = ?",
        (email,)
    )

    usuario = cursor.fetchone()

    conn.close()

    if not usuario:

        return jsonify({
            "erro": "usuário não encontrado"
        }), 404

    senha_correta = verificar_senha(
        senha,
        usuario["senha"]
    )

    if not senha_correta:

        return jsonify({
            "erro": "senha incorreta"
        }), 401

    return jsonify({
        "mensagem": "login realizado",
        "usuario": {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "usuario": usuario["usuario"]
        }
    })


# =========================
# CRIAR POST
# =========================

@app.route("/posts", methods=["POST"])
def criar_post():

    dados = request.json

    usuario_id = dados["usuario_id"]
    conteudo = dados["conteudo"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO posts (
            usuario_id,
            conteudo
        )
        VALUES (?, ?)
    """, (
        usuario_id,
        conteudo
    ))

    cursor.execute("""
        UPDATE usuario
        SET postagens = postagens + 1
        WHERE id = ?
    """, (usuario_id,))

    conn.commit()

    conn.close()

    return jsonify({
        "mensagem": "post criado"
    }), 201


# =========================
# LISTAR POSTS
# =========================

@app.route("/posts", methods=["GET"])
def listar_posts():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            posts.*,
            usuario.nome,
            usuario.usuario
        FROM posts

        JOIN usuario
        ON posts.usuario_id = usuario.id

        ORDER BY posts.id DESC
    """)

    posts = [
        dict(post)
        for post in cursor.fetchall()
    ]

    conn.close()

    return jsonify(posts)


# =========================
# DELETAR POST
# =========================

@app.route("/posts/<int:id>", methods=["DELETE"])
def deletar_post(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id
        FROM posts
        WHERE id = ?
    """, (id,))

    post = cursor.fetchone()

    if not post:

        conn.close()

        return jsonify({
            "erro": "post não encontrado"
        }), 404

    usuario_id = post["usuario_id"]

    cursor.execute("""
        DELETE FROM posts
        WHERE id = ?
    """, (id,))

    cursor.execute("""
        UPDATE usuario
        SET postagens = postagens - 1
        WHERE id = ?
        AND postagens > 0
    """, (usuario_id,))

    conn.commit()

    conn.close()

    return jsonify({
        "mensagem": "post deletado"
    })


# =========================
# CURTIR / DESCURTIR
# =========================

@app.route("/posts/<int:id>/curtir", methods=["POST"])
def curtir_post(id):

    dados = request.json

    usuario_id = dados["usuario_id"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM curtidas
        WHERE usuario_id = ?
        AND post_id = ?
    """, (
        usuario_id,
        id
    ))

    curtida_existente = cursor.fetchone()

    # DESCURTIR

    if curtida_existente:

        cursor.execute("""
            DELETE FROM curtidas
            WHERE usuario_id = ?
            AND post_id = ?
        """, (
            usuario_id,
            id
        ))

        cursor.execute("""
            UPDATE posts
            SET curtidas = curtidas - 1
            WHERE id = ?
            AND curtidas > 0
        """, (id,))

        conn.commit()

        cursor.execute("""
            SELECT curtidas
            FROM posts
            WHERE id = ?
        """, (id,))

        total = cursor.fetchone()["curtidas"]

        conn.close()

        return jsonify({
            "mensagem": "curtida removida",
            "curtido": False,
            "curtidas": total
        })

    # CURTIR

    cursor.execute("""
        INSERT INTO curtidas (
            usuario_id,
            post_id
        )
        VALUES (?, ?)
    """, (
        usuario_id,
        id
    ))

    cursor.execute("""
        UPDATE posts
        SET curtidas = curtidas + 1
        WHERE id = ?
    """, (id,))

    conn.commit()

    cursor.execute("""
        SELECT curtidas
        FROM posts
        WHERE id = ?
    """, (id,))

    total = cursor.fetchone()["curtidas"]

    conn.close()

    return jsonify({
        "mensagem": "post curtido",
        "curtido": True,
        "curtidas": total
    })


# =========================
# COMENTAR
# =========================

@app.route("/posts/<int:id>/comentarios", methods=["POST"])
def comentar(id):

    dados = request.json

    usuario_id = dados["usuario_id"]
    conteudo = dados["conteudo"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comentarios (
            usuario_id,
            post_id,
            conteudo
        )
        VALUES (?, ?, ?)
    """, (
        usuario_id,
        id,
        conteudo
    ))

    cursor.execute("""
        UPDATE posts
        SET comentarios = comentarios + 1
        WHERE id = ?
    """, (id,))

    conn.commit()

    cursor.execute("""
        SELECT comentarios
        FROM posts
        WHERE id = ?
    """, (id,))

    total = cursor.fetchone()["comentarios"]

    conn.close()

    return jsonify({
        "mensagem": "comentário criado",
        "comentarios": total
    })


# =========================
# LISTAR COMENTÁRIOS
# =========================

@app.route("/posts/<int:id>/comentarios", methods=["GET"])
def listar_comentarios(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            comentarios.id,
            comentarios.conteudo,
            comentarios.data_comentario,
            usuario.usuario
        FROM comentarios

        JOIN usuario
        ON comentarios.usuario_id = usuario.id

        WHERE comentarios.post_id = ?

        ORDER BY comentarios.id DESC
    """, (id,))

    comentarios = [
        dict(comentario)
        for comentario in cursor.fetchall()
    ]

    conn.close()

    return jsonify(comentarios)


# =========================
# SEGUIR
# =========================

@app.route("/usuarios/<int:id>/seguir", methods=["POST"])
def seguir(id):

    dados = request.json

    seguidor_id = dados["seguidor_id"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM seguidores
        WHERE seguidor_id = ?
        AND seguindo_id = ?
    """, (
        seguidor_id,
        id
    ))

    seguindo = cursor.fetchone()

    # DEIXAR DE SEGUIR

    if seguindo:

        cursor.execute("""
            DELETE FROM seguidores
            WHERE seguidor_id = ?
            AND seguindo_id = ?
        """, (
            seguidor_id,
            id
        ))

        cursor.execute("""
            UPDATE usuario
            SET seguidores = seguidores - 1
            WHERE id = ?
            AND seguidores > 0
        """, (id,))

        cursor.execute("""
            UPDATE usuario
            SET seguindo = seguindo - 1
            WHERE id = ?
            AND seguindo > 0
        """, (seguidor_id,))

        conn.commit()

        conn.close()

        return jsonify({
            "seguindo": False,
            "mensagem": "usuário desseguido"
        })

    # SEGUIR

    cursor.execute("""
        INSERT INTO seguidores (
            seguidor_id,
            seguindo_id
        )
        VALUES (?, ?)
    """, (
        seguidor_id,
        id
    ))

    cursor.execute("""
        UPDATE usuario
        SET seguidores = seguidores + 1
        WHERE id = ?
    """, (id,))

    cursor.execute("""
        UPDATE usuario
        SET seguindo = seguindo + 1
        WHERE id = ?
    """, (seguidor_id,))

    conn.commit()

    conn.close()

    return jsonify({
        "seguindo": True,
        "mensagem": "usuário seguido"
    })


# =========================
# FEED
# =========================

@app.route("/feed", methods=["GET"])
def feed():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
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

        JOIN usuario
        ON posts.usuario_id = usuario.id

        ORDER BY posts.id DESC
    """)

    posts = [
        dict(post)
        for post in cursor.fetchall()
    ]

    conn.close()

    return jsonify(posts)


# =========================
# PERFIL
# =========================

@app.route("/usuarios/<int:id>", methods=["GET"])
def buscar_usuario(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            usuario,
            bio,
            foto_perfil,
            banner,
            seguidores,
            seguindo,
            postagens,
            verificado,
            data_criacao
        FROM usuario
        WHERE id = ?
    """, (id,))

    usuario = cursor.fetchone()

    conn.close()

    if not usuario:

        return jsonify({
            "erro": "usuário não encontrado"
        }), 404

    return jsonify(dict(usuario))


# =========================
# POSTS DO PERFIL
# =========================

@app.route("/usuarios/<int:id>/posts", methods=["GET"])
def posts_usuario(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            posts.*,
            usuario.nome,
            usuario.usuario

        FROM posts

        JOIN usuario
        ON posts.usuario_id = usuario.id

        WHERE usuario.id = ?

        ORDER BY posts.id DESC
    """, (id,))

    posts = [
        dict(post)
        for post in cursor.fetchall()
    ]

    conn.close()

    return jsonify(posts)


# =========================

if __name__ == "__main__":

    app.run(debug=True)