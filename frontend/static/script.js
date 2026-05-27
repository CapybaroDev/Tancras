const API = "http://127.0.0.1:5000"
let usuario = null

try {
    const stored = localStorage.getItem("usuario")
    if (stored && stored !== "null") {
        usuario = JSON.parse(stored)
    }
} catch(e) {
    usuario = null
}

console.log("Usuário logado:", usuario)

// ========== FUNÇÕES DE API ==========

async function curtirPost(id) {
    console.log("curtirPost chamado para post:", id)
    if (!usuario) {
        alert("Faça login")
        return
    }
    try {
        const resp = await fetch(`${API}/posts/${id}/curtir`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id })
        })
        const dados = await resp.json()
        console.log("Resposta curtir:", dados)
        const botao = document.getElementById(`curtir-btn-${id}`)
        if (botao) {
            botao.innerHTML = `❤️ ${dados.curtidas}`
            botao.style.background = dados.curtido ? "#00ff88" : "#262626"
            botao.style.color = dados.curtido ? "black" : "white"
        }
    } catch(e) {
        console.error("Erro ao curtir:", e)
    }
}

async function comentarPost(id, texto) {
    console.log("comentarPost chamado para post:", id, texto)
    if (!usuario) {
        alert("Faça login")
        return
    }
    try {
        const resp = await fetch(`${API}/posts/${id}/comentarios`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id, conteudo: texto })
        })
        const dados = await resp.json()
        console.log("Resposta comentário:", dados)
        const botao = document.querySelector(`#post-${id} .comentar-btn`)
        if (botao && dados.comentarios) {
            botao.innerHTML = `💬 ${dados.comentarios}`
        }
        await carregarComentarios(id)
    } catch(e) {
        console.error("Erro ao comentar:", e)
    }
}

function abrirComentarios(id) {
    const texto = prompt("Digite seu comentário:")
    if (texto && texto.trim()) {
        comentarPost(id, texto.trim())
    }
}

async function carregarComentarios(id) {
    try {
        const resp = await fetch(`${API}/posts/${id}/comentarios`)
        const comentarios = await resp.json()
        const area = document.getElementById(`comentarios-${id}`)
        if (!area) return
        const recentes = comentarios.slice(0, 3)
        area.innerHTML = ""
        recentes.forEach(c => {
            area.innerHTML += `
                <div class="comentario">
                    <span class="comentario-usuario">@${c.usuario}</span>
                    <span class="comentario-texto">${c.conteudo}</span>
                </div>
            `
        })
        if (comentarios.length > 3) {
            area.innerHTML += `<button class="ver-mais" data-id="${id}">Ver mais comentários</button>`
        }
        const verMaisBtn = area.querySelector('.ver-mais')
        if (verMaisBtn) {
            verMaisBtn.addEventListener('click', (e) => {
                e.preventDefault()
                e.stopPropagation()
                verMaisComentarios(id)
            })
        }
    } catch(e) {
        console.error("Erro ao carregar comentários:", e)
    }
}

async function verMaisComentarios(id) {
    try {
        const resp = await fetch(`${API}/posts/${id}/comentarios`)
        const comentarios = await resp.json()
        const area = document.getElementById(`comentarios-${id}`)
        if (!area) return
        area.innerHTML = ""
        comentarios.forEach(c => {
            area.innerHTML += `
                <div class="comentario">
                    <span class="comentario-usuario">@${c.usuario}</span>
                    <span class="comentario-texto">${c.conteudo}</span>
                </div>
            `
        })
    } catch(e) {
        console.error("Erro ao ver mais comentários:", e)
    }
}

async function criarPost() {
    console.log("criarPost chamado")
    if (!usuario) {
        alert("Faça login")
        return
    }
    const textarea = document.getElementById("conteudoPost")
    const conteudo = textarea.value.trim()
    if (!conteudo) {
        alert("Digite algo para postar!")
        return
    }
    try {
        const resp = await fetch(`${API}/posts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id, conteudo })
        })
        if (resp.ok) {
            textarea.value = ""
            await carregarFeed()
        }
    } catch(e) {
        console.error("Erro ao criar post:", e)
    }
}

async function carregarFeed() {
    console.log("carregarFeed chamado")
    const feed = document.getElementById("feed")
    if (!feed) return
    feed.innerHTML = '<div style="text-align:center;padding:20px;">Carregando...</div>'
    try {
        const resp = await fetch(`${API}/feed`)
        const posts = await resp.json()
        feed.innerHTML = ""
        for (const post of posts) {
            let comentarios = []
            try {
                const respComent = await fetch(`${API}/posts/${post.id}/comentarios`)
                comentarios = await respComent.json()
            } catch(e) {}
            const tresRecentes = comentarios.slice(0, 3)
            let comentariosHTML = ""
            tresRecentes.forEach(c => {
                comentariosHTML += `
                    <div class="comentario">
                        <span class="comentario-usuario">@${c.usuario}</span>
                        <span class="comentario-texto">${c.conteudo}</span>
                    </div>
                `
            })
            if (comentarios.length > 3) {
                comentariosHTML += `<button class="ver-mais" data-id="${post.id}">Ver mais comentários</button>`
            }
            const postDiv = document.createElement('div')
            postDiv.className = 'post'
            postDiv.id = `post-${post.id}`
            postDiv.innerHTML = `
                <div class="post-topo">
                    <div class="foto"></div>
                    <div>
                        <div class="post-nome">${post.nome}</div>
                        <div class="post-usuario">@${post.usuario}</div>
                    </div>
                </div>
                <div class="post-conteudo">${post.conteudo}</div>
                <div class="post-acoes">
                    <button id="curtir-btn-${post.id}" class="curtir-btn">❤️ ${post.curtidas}</button>
                    <button class="comentar-btn">💬 ${post.comentarios}</button>
                </div>
                <div class="comentarios-area" id="comentarios-${post.id}">${comentariosHTML}</div>
            `
            feed.appendChild(postDiv)
        }
        for (const post of posts) {
            const curtirBtn = document.getElementById(`curtir-btn-${post.id}`)
            if (curtirBtn) {
                curtirBtn.addEventListener('click', (e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    curtirPost(post.id)
                })
            }
            const comentarBtn = document.querySelector(`#post-${post.id} .comentar-btn`)
            if (comentarBtn) {
                comentarBtn.addEventListener('click', (e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    abrirComentarios(post.id)
                })
            }
            const verMaisBtn = document.querySelector(`#post-${post.id} .ver-mais`)
            if (verMaisBtn) {
                verMaisBtn.addEventListener('click', (e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    verMaisComentarios(post.id)
                })
            }
        }
    } catch(e) {
        console.error("Erro ao carregar feed:", e)
        feed.innerHTML = '<div style="text-align:center;padding:20px;color:red;">Erro ao carregar feed. Verifique backend.</div>'
    }
}

// ========== PERFIL E LOGOUT ==========
function abrirPerfil() {
    if (!usuario) return
    const modal = document.getElementById("modalPerfil")
    const conteudo = document.getElementById("perfilConteudo")
    modal.style.display = "flex"
    conteudo.innerHTML = `<h2>${usuario.nome}</h2><p style="color:gray;margin-top:5px;">@${usuario.usuario}</p>`
}

function fecharPerfil() {
    document.getElementById("modalPerfil").style.display = "none"
}

function logout() {
    localStorage.removeItem("usuario")
    window.location.href = "login.html"
}

// ========== INICIALIZAÇÃO ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM carregado - inicializando sem onclick")
    try {
        const stored = localStorage.getItem("usuario")
        if (stored && stored !== "null") {
            usuario = JSON.parse(stored)
        }
    } catch(e) {
        usuario = null
    }
    if (document.getElementById("feed")) {
        carregarFeed()
    }
    const postarBtn = document.getElementById("postarBtn")
    if (postarBtn) {
        postarBtn.addEventListener('click', (e) => {
            e.preventDefault()
            e.stopPropagation()
            criarPost()
        })
    }
    const perfilBtn = document.getElementById("perfilBtn")
    if (perfilBtn) {
        perfilBtn.addEventListener('click', (e) => {
            e.preventDefault()
            e.stopPropagation()
            abrirPerfil()
        })
    }
    const logoutBtn = document.getElementById("logoutBtn")
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault()
            e.stopPropagation()
            logout()
        })
    }
    const fecharBtn = document.getElementById("fecharPerfilBtn")
    if (fecharBtn) {
        fecharBtn.addEventListener('click', (e) => {
            e.preventDefault()
            e.stopPropagation()
            fecharPerfil()
        })
    }
})

// ========== LOGIN (corrigido) ==========
const loginForm = document.getElementById("loginForm")
if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault()
        const email = document.getElementById("loginEmail")?.value.trim()
        const senha = document.getElementById("loginSenha")?.value.trim()
        if (!email || !senha) {
            alert("Preencha todos os campos")
            return
        }
        try {
            const resp = await fetch(`${API}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, senha })
            })
            const dados = await resp.json()
            if (!resp.ok) {
                alert(dados.erro || "Erro ao fazer login")
                return
            }
            localStorage.setItem("usuario", JSON.stringify(dados.usuario))
            usuario = dados.usuario
            alert("Login realizado com sucesso")
            window.location.href = "index.html"
        } catch (e) {
            console.error("Erro no login:", e)
            alert("Erro ao conectar com o servidor")
        }
    })
}

// ========== CADASTRO (corrigido) ==========
const registerForm = document.getElementById("registerForm")
if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault()
        const nome = document.getElementById("registerNome")?.value.trim()
        const usuarioInput = document.getElementById("registerUsuario")?.value.trim()
        const email = document.getElementById("registerEmail")?.value.trim()
        const senha = document.getElementById("registerSenha")?.value.trim()
        if (!nome || !usuarioInput || !email || !senha) {
            alert("Preencha todos os campos")
            return
        }
        try {
            const resp = await fetch(`${API}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nome, usuario: usuarioInput, email, senha })
            })
            const dados = await resp.json()
            if (!resp.ok) {
                alert(dados.erro || "Erro ao cadastrar")
                return
            }
            alert("Conta criada com sucesso")
            window.location.href = "login.html"
        } catch (e) {
            console.error("Erro no cadastro:", e)
            alert("Erro ao conectar com o servidor")
        }
    })
}