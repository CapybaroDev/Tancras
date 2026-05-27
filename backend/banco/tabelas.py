import sqlite3

conn = sqlite3.connect("backend/banco/banco.db")
cursor = conn.cursor()

# =========================
# USUÁRIOS
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL CHECK(length(nome) >= 3 AND length(nome) <= 24),
    usuario TEXT UNIQUE NOT NULL CHECK(length(usuario) >= 3 AND length(usuario) <= 20),
    email TEXT UNIQUE NOT NULL CHECK(length(email) <= 254),
    senha TEXT NOT NULL CHECK(length(senha) <= 500),
    bio TEXT DEFAULT '' CHECK(length(bio) <= 160),
    foto_perfil TEXT DEFAULT '',
    banner TEXT DEFAULT '',
    verificado INTEGER DEFAULT 0,
    seguidores INTEGER DEFAULT 0,
    seguindo INTEGER DEFAULT 0,
    postagens INTEGER DEFAULT 0,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# =========================
# POSTS
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    conteudo TEXT NOT NULL CHECK(length(conteudo) <= 280),
    imagem TEXT DEFAULT '',
    curtidas INTEGER DEFAULT 0,
    comentarios INTEGER DEFAULT 0,
    reposts INTEGER DEFAULT 0,
    data_post TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuario(id)
)
''')

# =========================
# CURTIDAS
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS curtidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    data_curtida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuario(id),
    FOREIGN KEY(post_id) REFERENCES posts(id)
)
''')

# =========================
# COMENTÁRIOS
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    conteudo TEXT NOT NULL CHECK(length(conteudo) <= 280),
    data_comentario TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuario(id),
    FOREIGN KEY(post_id) REFERENCES posts(id)
)
''')

# =========================
# SEGUIDORES
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS seguidores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seguidor_id INTEGER NOT NULL,
    seguindo_id INTEGER NOT NULL,
    data_seguidor TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(seguidor_id) REFERENCES usuario(id),
    FOREIGN KEY(seguindo_id) REFERENCES usuario(id)
)
''')

# =========================
# REPOSTS
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS reposts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    data_repost TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuario(id),
    FOREIGN KEY(post_id) REFERENCES posts(id)
)
''')

# =========================
# MENSAGENS
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remetente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    mensagem TEXT NOT NULL CHECK(length(mensagem) <= 1000),
    lida INTEGER DEFAULT 0,
    data_mensagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(remetente_id) REFERENCES usuario(id),
    FOREIGN KEY(destinatario_id) REFERENCES usuario(id)
)
''')

# =========================
# NOTIFICAÇÕES
# =========================

cursor.execute('''
CREATE TABLE IF NOT EXISTS notificacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_recebeu INTEGER NOT NULL,
    usuario_acao INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    post_id INTEGER,
    lida INTEGER DEFAULT 0,
    data_notificacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_recebeu) REFERENCES usuario(id),
    FOREIGN KEY(usuario_acao) REFERENCES usuario(id),
    FOREIGN KEY(post_id) REFERENCES posts(id)
)
''')

conn.commit()
conn.close()

print("Banco criado com sucesso!")