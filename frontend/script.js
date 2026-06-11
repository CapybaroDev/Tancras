const API = "https://tancras.onrender.com"
let usuario = null
let paginaAtual = 1
let carregando = false
let temMaisPosts = true
let feedElement = null
let imagemSelecionada = null

// ========== LOADING OVERLAY ==========
let requisicoesAtivas = 0
function mostrarCarregamento() {
    requisicoesAtivas++
    let overlay = document.getElementById("loadingOverlay")
    if (!overlay) {
        overlay = document.createElement("div")
        overlay.id = "loadingOverlay"
        overlay.style.position = "fixed"
        overlay.style.top = "0"
        overlay.style.left = "0"
        overlay.style.width = "100%"
        overlay.style.height = "100%"
        overlay.style.backgroundColor = "rgba(0,0,0,0.85)"
        overlay.style.display = "flex"
        overlay.style.alignItems = "center"
        overlay.style.justifyContent = "center"
        overlay.style.zIndex = "9999"
        overlay.style.flexDirection = "column"
        overlay.innerHTML = `
            <div style="color:white; font-size:24px; font-weight:bold;">⏳ Carregando...</div>
            <div style="width:50px; height:50px; border:5px solid #333; border-top:5px solid #00ff88; border-radius:50%; animation: spin 1s linear infinite; margin-top:15px;"></div>
        `
        if (!document.querySelector("#loadingStyles")) {
            const style = document.createElement("style")
            style.id = "loadingStyles"
            style.textContent = `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`
            document.head.appendChild(style)
        }
        document.body.appendChild(overlay)
    }
    overlay.style.display = "flex"
}
function esconderCarregamento() {
    requisicoesAtivas--
    if (requisicoesAtivas <= 0) {
        requisicoesAtivas = 0
        const overlay = document.getElementById("loadingOverlay")
        if (overlay) overlay.style.display = "none"
    }
}

// ========== UTILITÁRIOS ==========
function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        if (m === "&") return "&amp;";
        if (m === "<") return "&lt;";
        if (m === ">") return "&gt;";
        return m;
    });
}

function formatarData(dataISO) {
    if (!dataISO) return "";
    const data = new Date(dataISO);
    const agora = new Date();
    const diffMs = agora - data;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHoras = Math.floor(diffMs / 3600000);
    const diffDias = Math.floor(diffMs / 86400000);
    
    if (diffMin < 1) return "agora mesmo";
    if (diffMin < 60) return `há ${diffMin} min`;
    if (diffHoras < 24) return `há ${diffHoras} h`;
    if (diffDias < 7) return `há ${diffDias} d`;
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function gerarAvatarHtml(nome, tamanho = 28) {
    const letra = nome.charAt(0).toUpperCase();
    const cor = `hsl(${hashCode(nome) % 360}, 70%, 60%)`;
    return `<div class="avatar-mini" style="width:${tamanho}px;height:${tamanho}px;background:${cor};display:inline-flex;align-items:center;justify-content:center;border-radius:50%;font-weight:bold;font-size:${tamanho*0.5}px;color:black;margin-right:8px;">${letra}</div>`;
}

function atualizarBotaoPerfil() {
    const perfilBtn = document.getElementById("perfilNavBtn");
    if (!perfilBtn || !usuario) return;
    const nome = usuario.nome;
    const fotoUrl = usuario.foto_perfil;
    if (fotoUrl && fotoUrl.trim() !== "") {
        perfilBtn.innerHTML = `<img src="${fotoUrl}" class="avatar-mini-img" alt="perfil"> Perfil`;
    } else {
        perfilBtn.innerHTML = gerarAvatarHtml(nome, 28) + " Perfil";
    }
}

// ========== VERIFICA LOGIN (com fallback para admin id=1) ==========
try {
    const stored = localStorage.getItem("usuario")
    if (stored && stored !== "null") {
        usuario = JSON.parse(stored)
        // Fallback: se for o id 1 e admin não estiver definido, força true
        if (usuario.id === 1 && !usuario.admin) {
            usuario.admin = true
            localStorage.setItem("usuario", JSON.stringify(usuario))
            console.log("Fallback: usuário id=1 configurado como admin no frontend")
        }
    }
} catch(e) { usuario = null }

const paginaAtualPath = window.location.pathname
const paginasPublicas = ["login.html", "cadastro.html"]
const paginaLiberada = paginasPublicas.some(p => paginaAtualPath.includes(p))
if (!usuario && !paginaLiberada) window.location.href = "login.html"

console.log("Usuário logado:", usuario)

// ========== FUNÇÕES DE SEGUIR ==========
async function seguirUsuario(seguindo_id, botaoElement, isPerfilPage = false) {
    if (!usuario) { alert("Faça login"); return }
    try {
        const resp = await fetch(`${API}/usuarios/${seguindo_id}/seguir`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ seguidor_id: usuario.id })
        })
        const dados = await resp.json()
        if (resp.ok) {
            const seguindo = dados.seguindo
            if (botaoElement) {
                botaoElement.textContent = seguindo ? "✓ Seguindo" : "+ Seguir"
                if (seguindo) botaoElement.classList.add("seguindo")
                else botaoElement.classList.remove("seguindo")
            }
            if (isPerfilPage) carregarPerfilUsuario()
        } else alert(dados.erro || "Erro")
    } catch(e) { alert("Erro de conexão") }
}

// ========== CURTIR, COMENTAR, EXCLUIR POST ==========
async function curtirPost(id) {
    if (!usuario) { alert("Faça login"); return }
    try {
        const resp = await fetch(`${API}/posts/${id}/curtir`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id })
        })
        const dados = await resp.json()
        const botao = document.getElementById(`curtir-btn-${id}`)
        if (botao) {
            botao.innerHTML = `❤️ ${dados.curtidas}`
            botao.style.background = dados.curtido ? "#00ff88" : "#262626"
            botao.style.color = dados.curtido ? "black" : "white"
        }
    } catch(e) { console.error(e) }
}

async function comentarPost(id, texto) {
    if (!usuario) { alert("Faça login"); return }
    try {
        const resp = await fetch(`${API}/posts/${id}/comentarios`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id, conteudo: texto })
        })
        const dados = await resp.json()
        const botao = document.querySelector(`#post-${id} .comentar-btn`)
        if (botao && dados.comentarios) botao.innerHTML = `💬 ${dados.comentarios}`
        await carregarComentarios(id)
    } catch(e) { console.error(e) }
}

function abrirComentarios(id) {
    const texto = prompt("Digite seu comentário:")
    if (texto && texto.trim()) comentarPost(id, texto.trim())
}

async function carregarComentarios(id) {
    try {
        const resp = await fetch(`${API}/posts/${id}/comentarios`)
        const comentarios = await resp.json()
        const area = document.getElementById(`comentarios-${id}`)
        if (!area) return
        area.innerHTML = ""
        comentarios.forEach(c => {
            area.innerHTML += `<div class="comentario"><span class="comentario-usuario">@${c.usuario}</span><span class="comentario-texto">${c.conteudo}</span></div>`
        })
    } catch(e) { console.error(e) }
}

async function verMaisComentarios(id) {
    const area = document.getElementById(`comentarios-${id}`)
    if (!area) return
    area.innerHTML = '<div>Carregando...</div>'
    try {
        const resp = await fetch(`${API}/posts/${id}/comentarios`)
        const comentarios = await resp.json()
        area.innerHTML = ""
        comentarios.forEach(c => {
            area.innerHTML += `<div class="comentario"><span class="comentario-usuario">@${c.usuario}</span><span class="comentario-texto">${c.conteudo}</span></div>`
        })
    } catch(e) { area.innerHTML = '<div>Erro</div>' }
}

// ========== CRIAR POST ==========
async function criarPost() {
    if (!usuario) { alert("Faça login"); return }
    const textarea = document.getElementById("conteudoPost")
    const conteudo = textarea.value.trim()
    const imagem = imagemSelecionada || ""

    if (!conteudo && !imagem) {
        alert("Digite algo ou selecione uma imagem!")
        return
    }

    try {
        const resp = await fetch(`${API}/posts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id, conteudo, imagem })
        })
        if (resp.ok) {
            textarea.value = ""
            imagemSelecionada = null
            const previewDiv = document.getElementById("previewImagem")
            if (previewDiv) previewDiv.innerHTML = ""
            const inputImagem = document.getElementById("imagemPost")
            if (inputImagem) inputImagem.value = ""
            resetarFeed()
        } else {
            const erro = await resp.json()
            alert(erro.erro || "Erro ao criar post")
        }
    } catch(e) { alert("Erro de conexão") }
}

async function excluirPost(id) {
    if (!confirm("Excluir este post?")) return
    try {
        const resp = await fetch(`${API}/posts/${id}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id })
        })
        if (resp.ok) {
            document.getElementById(`post-${id}`)?.remove()
            alert("Post excluído")
        } else {
            const erro = await resp.json()
            alert(erro.erro || "Erro")
        }
    } catch(e) { alert("Erro de conexão") }
}

// ========== DELETAR USUÁRIO (ADMIN) ==========
async function deletarUsuario(userId) {
    if (!usuario || !usuario.admin) {
        alert("Apenas administradores podem deletar usuários.");
        return;
    }
    const confirmar = confirm(`Tem certeza que deseja deletar o usuário #${userId}? Esta ação é irreversível.`);
    if (!confirmar) return;

    try {
        const resp = await fetch(`${API}/usuarios/${userId}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuario.id })
        });
        const dados = await resp.json();
        if (resp.ok) {
            alert("Usuário deletado com sucesso!");
            if (window.location.pathname.includes('user.html')) {
                window.location.href = "index.html";
            } else {
                location.reload();
            }
        } else {
            alert(dados.erro || "Erro ao deletar usuário");
        }
    } catch (err) {
        alert("Erro de conexão ao deletar usuário");
        console.error(err);
    }
}

// ========== ADMIN: ALTERAR ADMIN/VERIFICADO ==========
async function alterarAdminStatus(userId, tornarAdmin) {
    if (!usuario || !usuario.admin) {
        alert("Apenas administradores podem realizar esta ação.");
        return;
    }
    try {
        const resp = await fetch(`${API}/admin/usuarios/${userId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ admin_id: usuario.id, admin: tornarAdmin })
        });
        const data = await resp.json();
        if (resp.ok) {
            alert(`Usuário ${tornarAdmin ? "agora é administrador" : "não é mais administrador"}`);
            carregarPerfilUsuario(); // recarrega a página do perfil
        } else {
            alert(data.erro || "Erro ao alterar status de admin");
        }
    } catch(e) {
        alert("Erro de conexão");
        console.error(e);
    }
}

async function alterarVerificadoStatus(userId, verificar) {
    if (!usuario || !usuario.admin) {
        alert("Apenas administradores podem realizar esta ação.");
        return;
    }
    try {
        const resp = await fetch(`${API}/admin/usuarios/${userId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ admin_id: usuario.id, verificado: verificar })
        });
        const data = await resp.json();
        if (resp.ok) {
            alert(`Usuário ${verificar ? "verificado" : "não verificado"}`);
            carregarPerfilUsuario();
        } else {
            alert(data.erro || "Erro ao alterar verificação");
        }
    } catch(e) {
        alert("Erro de conexão");
        console.error(e);
    }
}

// ========== FEED COM BOTÃO "CARREGAR MAIS" ==========
function resetarFeed() {
    if (feedElement) feedElement.innerHTML = ""
    paginaAtual = 1
    temMaisPosts = true
    carregando = false
    const oldBtn = document.getElementById("loadMoreBtn")
    if (oldBtn) oldBtn.remove()
    carregarFeed()
}

async function carregarFeed() {
    if (!feedElement) return
    if (carregando || !temMaisPosts) return
    carregando = true

    const loadingDiv = document.createElement('div')
    loadingDiv.id = "feed-loading"
    loadingDiv.innerHTML = '<div style="text-align:center;padding:20px;">⏳ Carregando posts...</div>'
    feedElement.appendChild(loadingDiv)

    try {
        const usuarioIdParam = usuario ? `&usuario_id=${usuario.id}` : ''
        const url = `${API}/feed?page=${paginaAtual}&limit=20${usuarioIdParam}`
        console.log("Buscando:", url)
        const resp = await fetch(url)
        
        if (!resp.ok) {
            const errorText = await resp.text()
            throw new Error(`HTTP ${resp.status}: ${errorText.substring(0, 100)}`)
        }
        
        const data = await resp.json()
        console.log("Resposta:", data)
        
        if (!data.posts || !Array.isArray(data.posts)) {
            throw new Error("Resposta inválida: 'posts' não é um array")
        }
        
        const posts = data.posts
        temMaisPosts = data.has_more || false

        document.getElementById("feed-loading")?.remove()

        if (paginaAtual === 1) feedElement.innerHTML = ""

        if (posts.length === 0 && paginaAtual === 1) {
            feedElement.innerHTML = '<div style="text-align:center;padding:40px;">Nenhum post ainda. Seja o primeiro!</div>'
            carregando = false
            return
        }

        for (const post of posts) {
            const podeExcluir = usuario && (usuario.id === post.usuario_id || usuario.admin)
            let fotoPerfilHtml = ''
            if (post.foto_perfil && post.foto_perfil.trim() !== '') {
                fotoPerfilHtml = `<div class="foto" style="background-image: url(${post.foto_perfil}); background-size:cover;"></div>`
            } else {
                const letra = (post.nome || 'U').charAt(0).toUpperCase();
                const cor = `hsl(${hashCode(post.nome || '') % 360}, 70%, 60%)`;
                fotoPerfilHtml = `<div class="foto avatar-fallback" style="background:${cor}; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:20px; color:black;">${letra}</div>`;
            }
            const isOwnPost = usuario && (usuario.id === post.usuario_id)
            const botaoSeguirHtml = !isOwnPost ? `<button class="btn-seguir ${post.seguindo ? 'seguindo' : ''}" data-id="${post.usuario_id}">${post.seguindo ? '✓ Seguindo' : '+ Seguir'}</button>` : ''

            const verificadoBadge = post.verificado ? '<span class="verificado-badge" style="background:#00ff88; color:black; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; font-size:10px; margin-left:4px;">✓</span>' : '';

            const imagemHtml = post.imagem && post.imagem.trim() !== '' 
                ? `<div class="post-imagem"><img src="${post.imagem}" loading="lazy"></div>` 
                : '';

            const dataHtml = `<div class="post-data">${formatarData(post.data_post)}</div>`;
            const comentariosHTML = `<div class="comentarios-area" id="comentarios-${post.id}"><button class="ver-mais" data-id="${post.id}">Ver comentários (${post.comentarios})</button></div>`

            const postDiv = document.createElement('div')
            postDiv.className = 'post'
            postDiv.id = `post-${post.id}`
            postDiv.innerHTML = `
                <div class="post-topo">
                    ${fotoPerfilHtml}
                    <div style="flex:1; margin-left:12px;">
                        <div class="post-nome" data-id="${post.usuario_id}" style="cursor:pointer;">${post.nome} ${verificadoBadge}</div>
                        <div class="post-usuario" data-id="${post.usuario_id}" style="cursor:pointer;">@${post.usuario}</div>
                    </div>
                    ${botaoSeguirHtml}
                </div>
                ${post.conteudo ? `<div class="post-conteudo">${post.conteudo}</div>` : ''}
                ${imagemHtml}
                <div class="post-acoes">
                    <button id="curtir-btn-${post.id}" class="curtir-btn">❤️ ${post.curtidas}</button>
                    <button class="comentar-btn">💬 ${post.comentarios}</button>
                    ${podeExcluir ? `<button class="excluir-btn" data-id="${post.id}">🗑️ Excluir</button>` : ''}
                </div>
                ${dataHtml}
                ${comentariosHTML}
            `
            feedElement.appendChild(postDiv)
        }

        // Eventos
        for (const post of posts) {
            const postDiv = document.getElementById(`post-${post.id}`)
            if (!postDiv) continue
            document.getElementById(`curtir-btn-${post.id}`)?.addEventListener('click', () => curtirPost(post.id))
            postDiv.querySelector('.comentar-btn')?.addEventListener('click', () => abrirComentarios(post.id))
            const verMaisBtn = postDiv.querySelector('.ver-mais')
            if (verMaisBtn) verMaisBtn.addEventListener('click', () => verMaisComentarios(post.id))
            const excluirBtn = postDiv.querySelector('.excluir-btn')
            if (excluirBtn) excluirBtn.addEventListener('click', () => excluirPost(post.id))
            const nomeEl = postDiv.querySelector('.post-nome')
            const usuarioEl = postDiv.querySelector('.post-usuario')
            if (nomeEl) nomeEl.addEventListener('click', () => window.location.href = `user.html?id=${post.usuario_id}`)
            if (usuarioEl) usuarioEl.addEventListener('click', () => window.location.href = `user.html?id=${post.usuario_id}`)
            const seguirBtn = postDiv.querySelector('.btn-seguir')
            if (seguirBtn) {
                const uid = parseInt(seguirBtn.dataset.id)
                seguirBtn.addEventListener('click', (e) => { e.stopPropagation(); seguirUsuario(uid, seguirBtn, false) })
            }
        }

        paginaAtual++

        const existingBtn = document.getElementById("loadMoreBtn")
        if (existingBtn) existingBtn.remove()

        if (temMaisPosts) {
            const loadMoreDiv = document.createElement('div')
            loadMoreDiv.id = "loadMoreBtn"
            loadMoreDiv.style.textAlign = "center"
            loadMoreDiv.style.margin = "20px 0"
            loadMoreDiv.innerHTML = '<button style="background:#262626; color:#00ff88; border:1px solid #00ff88; padding:12px 24px; border-radius:30px;">📥 Carregar mais posts</button>'
            feedElement.appendChild(loadMoreDiv)
            loadMoreDiv.querySelector('button').addEventListener('click', () => {
                loadMoreDiv.remove()
                carregarFeed()
            })
        } else {
            const fimDiv = document.createElement('div')
            fimDiv.style.textAlign = "center"
            fimDiv.style.padding = "20px"
            fimDiv.style.color = "gray"
            fimDiv.innerHTML = "✨ Você já viu todos os posts! ✨"
            feedElement.appendChild(fimDiv)
        }

        carregando = false
    } catch (err) {
        console.error("Erro em carregarFeed:", err)
        document.getElementById("feed-loading")?.remove()
        feedElement.innerHTML += `<div style="color:red;text-align:center;padding:20px;">Erro ao carregar posts: ${err.message}</div>`
        carregando = false
        temMaisPosts = false
    }
}

// ========== BUSCA DE USUÁRIOS ==========
let searchTimeout = null;
const searchInput = document.getElementById("searchInput");
const searchResults = document.getElementById("searchResults");

if (searchInput && searchResults) {
    searchInput.addEventListener("input", function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.classList.remove("show");
            searchResults.innerHTML = "";
            return;
        }
        
        searchTimeout = setTimeout(async () => {
            try {
                const resp = await fetch(`${API}/usuarios/search?q=${encodeURIComponent(query)}`);
                const usuarios = await resp.json();
                renderSearchResults(usuarios);
            } catch(e) {
                console.error("Erro na busca:", e);
                searchResults.innerHTML = '<div class="search-result-item">Erro ao buscar</div>';
                searchResults.classList.add("show");
            }
        }, 300);
    });
    
    document.addEventListener("click", function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove("show");
        }
    });
}

function renderSearchResults(usuarios) {
    searchResults.innerHTML = "";
    if (!usuarios.length) {
        searchResults.innerHTML = '<div class="search-result-item">Nenhum usuário encontrado</div>';
        searchResults.classList.add("show");
        return;
    }
    
    usuarios.forEach(user => {
        const avatarHtml = user.foto_perfil 
            ? `<div class="search-result-avatar" style="background-image: url(${user.foto_perfil}); background-size:cover;"></div>`
            : `<div class="search-result-avatar" style="background: #00ff88; display:flex; align-items:center; justify-content:center; font-weight:bold;">${user.nome.charAt(0).toUpperCase()}</div>`;
        
        const item = document.createElement("div");
        item.className = "search-result-item";
        item.innerHTML = `
            ${avatarHtml}
            <div class="search-result-info">
                <div class="search-result-name">${escapeHtml(user.nome)}</div>
                <div class="search-result-username">@${escapeHtml(user.usuario)}</div>
            </div>
        `;
        item.addEventListener("click", () => {
            window.location.href = `user.html?id=${user.id}`;
        });
        searchResults.appendChild(item);
    });
    searchResults.classList.add("show");
}

// ========== LOGOUT E NAVEGAÇÃO ==========
function logout() { localStorage.removeItem("usuario"); window.location.href = "login.html" }
function navegarPara(destino) {
    if (destino === 'home') {
        if (!window.location.pathname.includes('index.html')) window.location.href = 'index.html'
        else resetarFeed()
    } else if (destino === 'perfil') {
        if (usuario) window.location.href = `user.html?id=${usuario.id}`
    }
}

// ========== INICIALIZAÇÃO INDEX ==========
document.addEventListener('DOMContentLoaded', () => {
    const stored = localStorage.getItem("usuario")
    if (stored && stored !== "null") {
        usuario = JSON.parse(stored)
        if (usuario.id === 1 && !usuario.admin) {
            usuario.admin = true
            localStorage.setItem("usuario", JSON.stringify(usuario))
        }
    }

    atualizarBotaoPerfil();

    const btnEscolherImagem = document.getElementById("btnEscolherImagem")
    const inputImagem = document.getElementById("imagemPost")
    const previewDiv = document.getElementById("previewImagem")

    if (btnEscolherImagem && inputImagem) {
        btnEscolherImagem.addEventListener("click", () => inputImagem.click())
        inputImagem.addEventListener("change", function(e) {
            const file = e.target.files[0]
            if (file) {
                const reader = new FileReader()
                reader.onload = function(ev) {
                    imagemSelecionada = ev.target.result
                    if (previewDiv) {
                        previewDiv.innerHTML = `<img src="${imagemSelecionada}" style="max-width:100%; max-height:200px; border-radius:12px;"> 
                                                 <button type="button" id="removerImagemBtn" style="margin-top:8px;">❌ Remover</button>`
                        const removerBtn = document.getElementById("removerImagemBtn")
                        if (removerBtn) {
                            removerBtn.addEventListener("click", () => {
                                imagemSelecionada = null
                                previewDiv.innerHTML = ""
                                inputImagem.value = ""
                            })
                        }
                    }
                }
                reader.readAsDataURL(file)
            }
        })
    }

    feedElement = document.getElementById("feed")
    if (feedElement) {
        resetarFeed()
        const postarBtn = document.getElementById("postarBtn")
        if (postarBtn) postarBtn.addEventListener('click', criarPost)

        const homeBtn = document.getElementById("homeBtn")
        const perfilNavBtn = document.getElementById("perfilNavBtn")
        const configNavBtn = document.getElementById("configNavBtn")
        const modalConfig = document.getElementById("modalConfig")
        const fecharConfig = document.getElementById("fecharConfigBtn")
        const sairBtn = document.getElementById("sairConfigBtn")

        if (homeBtn) homeBtn.addEventListener('click', () => navegarPara('home'))
        if (perfilNavBtn) perfilNavBtn.addEventListener('click', () => navegarPara('perfil'))
        if (configNavBtn) configNavBtn.addEventListener('click', () => modalConfig.style.display = 'flex')
        if (fecharConfig) fecharConfig.addEventListener('click', () => modalConfig.style.display = 'none')
        if (sairBtn) sairBtn.addEventListener('click', logout)
    }
})

// ========== PÁGINA user.html ==========
if (window.location.pathname.includes('user.html')) {
    const urlParams = new URLSearchParams(window.location.search)
    const userId = urlParams.get('id')
    if (!userId) window.location.href = 'index.html'

    async function carregarPerfilUsuario() {
        try {
            const usuarioIdParam = usuario ? `?usuario_id=${usuario.id}` : ''
            const resp = await fetch(`${API}/usuarios/${userId}${usuarioIdParam}`)
            if (!resp.ok) throw new Error()
            const user = await resp.json()
            const isOwnProfile = usuario && (usuario.id == userId)
            const isAdmin = usuario && usuario.admin

            const perfilNavBtn = document.getElementById("perfilNavBtn");
            if (perfilNavBtn) {
                if (isOwnProfile) {
                    perfilNavBtn.classList.add("active");
                } else {
                    perfilNavBtn.classList.remove("active");
                }
            }

            let fotoGrandeHtml = ''
            if (user.foto_perfil && user.foto_perfil.trim() !== '') {
                fotoGrandeHtml = `<div class="foto-grande" style="background-image: url(${user.foto_perfil}); background-size:cover;"></div>`
            } else {
                const letra = (user.nome || 'U').charAt(0).toUpperCase();
                const cor = `hsl(${hashCode(user.nome || '') % 360}, 70%, 60%)`;
                fotoGrandeHtml = `<div class="foto-grande avatar-fallback" style="background:${cor}; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:40px; color:black;">${letra}</div>`;
            }

            const verificadoBadge = user.verificado ? '<span class="verificado-badge">✓</span>' : '';

            let html = `
                <div class="perfil-container">
                    ${fotoGrandeHtml}
                    <h2>${user.nome} ${verificadoBadge}</h2>
                    <p style="color:gray;">@${user.usuario}</p>
                    <p class="bio">${user.bio || 'Sem bio ainda'}</p>
                    <div>📌 ${user.postagens} posts | 👥 ${user.seguidores} seguidores | 🔁 ${user.seguindo} seguindo</div>
            `
            if (isOwnProfile) {
                html += `<button id="editarPerfilBtn" class="btn-editar">✏️ Editar perfil</button>`
            } else if (usuario) {
                const seguindo = user.seguido_por_voce || false
                html += `<button id="seguirPerfilBtn" class="btn-seguir-perfil ${seguindo ? 'seguindo' : ''}">${seguindo ? '✓ Seguindo' : '+ Seguir'}</button>`
            }

            if (isAdmin && !isOwnProfile) {
                html += `<div class="admin-actions" style="margin-top:15px;">
                            <button id="tornarAdminBtn" class="btn-admin" style="background:#444; color:#fff; padding:8px 16px; margin-right:10px; border-radius:20px;">👑 ${user.admin ? 'Remover Admin' : 'Tornar Admin'}</button>
                            <button id="verificarBtn" class="btn-admin" style="background:#444; color:#fff; padding:8px 16px; border-radius:20px;">✅ ${user.verificado ? 'Remover Verificado' : 'Verificar Usuário'}</button>
                         </div>`;
            }

            if (isAdmin && !isOwnProfile) {
                html += `<button id="deletarUsuarioBtn" class="btn-deletar-usuario" style="margin-top:15px; background:#ff4444;">🗑️ Deletar Usuário</button>`
            }

            html += `</div>`
            document.getElementById('perfilInfo').innerHTML = html

            if (isOwnProfile) {
                document.getElementById('editarPerfilBtn')?.addEventListener('click', () => abrirModalEdicao(user))
            } else if (usuario) {
                const btn = document.getElementById('seguirPerfilBtn')
                if (btn) btn.addEventListener('click', () => seguirUsuario(userId, btn, true))
            }

            if (isAdmin && !isOwnProfile) {
                const adminBtn = document.getElementById('tornarAdminBtn')
                if (adminBtn) adminBtn.addEventListener('click', () => alterarAdminStatus(userId, !user.admin))
                const verificadoBtn = document.getElementById('verificarBtn')
                if (verificadoBtn) verificadoBtn.addEventListener('click', () => alterarVerificadoStatus(userId, !user.verificado))
                const deletarBtn = document.getElementById('deletarUsuarioBtn')
                if (deletarBtn) deletarBtn.addEventListener('click', () => deletarUsuario(userId))
            }

            const respPosts = await fetch(`${API}/usuarios/${userId}/posts?limit=20`)
            const posts = await respPosts.json()
            const container = document.getElementById('perfilPosts')
            container.innerHTML = '<h3>Posts</h3>'
            if (posts.length === 0) container.innerHTML += '<p>Nenhum post ainda.</p>'
            else {
                posts.forEach(post => {
                    let imagemHtml = ''
                    if (post.imagem && post.imagem.trim() !== '') {
                        imagemHtml = `<div class="post-imagem"><img src="${post.imagem}" style="max-width:100%; border-radius:12px;"></div>`
                    }
                    const dataHtml = `<div class="post-data">📅 ${formatarData(post.data_post)}</div>`;
                    container.innerHTML += `
                        <div class="post">
                            ${post.conteudo ? `<div class="post-conteudo">${post.conteudo}</div>` : ''}
                            ${imagemHtml}
                            <div class="post-acoes">❤️ ${post.curtidas} | 💬 ${post.comentarios}</div>
                            ${dataHtml}
                        </div>
                    `
                })
            }
        } catch(e) { console.error(e); document.getElementById('perfilInfo').innerHTML = '<p>Erro ao carregar perfil</p>' }
    }

    function abrirModalEdicao(user) {
        const modal = document.getElementById('modalEditarPerfil')
        const nomeInput = document.getElementById('editNome')
        const bioInput = document.getElementById('editBio')
        const fotoInput = document.getElementById('fotoPerfilInput')
        const preview = document.getElementById('previewFoto')
        nomeInput.value = user.nome
        bioInput.value = user.bio || ''
        preview.innerHTML = user.foto_perfil ? `<img src="${user.foto_perfil}" width="80" style="border-radius:50%;">` : ''
        modal.style.display = 'flex'

        fotoInput.onchange = function() {
            const file = this.files[0]
            if (file) {
                const reader = new FileReader()
                reader.onload = e => {
                    preview.innerHTML = `<img src="${e.target.result}" width="80" style="border-radius:50%;">`
                    preview.dataset.base64 = e.target.result
                }
                reader.readAsDataURL(file)
            }
        }

        document.getElementById('editarPerfilForm').onsubmit = async (e) => {
            e.preventDefault()
            const novoNome = nomeInput.value.trim()
            const novaBio = bioInput.value.trim()
            let fotoBase64 = preview.dataset.base64 || null
            if (!novoNome) return alert('Nome obrigatório')
            const body = { usuario_id: usuario.id, nome: novoNome, bio: novaBio }
            if (fotoBase64) body.foto_perfil = fotoBase64
            try {
                const resp = await fetch(`${API}/usuarios/${userId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                })
                if (resp.ok) {
                    const updated = await resp.json()
                    alert('Perfil atualizado!')
                    modal.style.display = 'none'
                    usuario.nome = updated.nome
                    usuario.bio = updated.bio
                    usuario.foto_perfil = updated.foto_perfil
                    usuario.admin = updated.admin
                    usuario.verificado = updated.verificado
                    localStorage.setItem('usuario', JSON.stringify(usuario))
                    atualizarBotaoPerfil()
                    carregarPerfilUsuario()
                    if (window.location.pathname.includes('index.html')) {
                        resetarFeed()
                    }
                } else { const erro = await resp.json(); alert(erro.erro || 'Erro') }
            } catch(err) { alert('Erro de conexão') }
        }
    }

    document.getElementById('fecharEditarBtn')?.addEventListener('click', () => document.getElementById('modalEditarPerfil').style.display = 'none')
    document.getElementById('voltarBtn')?.addEventListener('click', () => window.history.back())

    const homeBtn = document.getElementById('homeBtn')
    const perfilNavBtn = document.getElementById('perfilNavBtn')
    const configNavBtn = document.getElementById('configNavBtn')
    const modalConfig = document.getElementById('modalConfig')
    const fecharConfig = document.getElementById('fecharConfigBtn')
    const sairBtn = document.getElementById('sairConfigBtn')
    if (homeBtn) homeBtn.addEventListener('click', () => window.location.href = 'index.html')
    if (perfilNavBtn) perfilNavBtn.addEventListener('click', () => navegarPara('perfil'))
    if (configNavBtn) configNavBtn.addEventListener('click', () => modalConfig.style.display = 'flex')
    if (fecharConfig) fecharConfig.addEventListener('click', () => modalConfig.style.display = 'none')
    if (sairBtn) sairBtn.addEventListener('click', logout)

    atualizarBotaoPerfil();
    carregarPerfilUsuario()
}

// ========== LOGIN / CADASTRO ==========
const loginForm = document.getElementById("loginForm")
if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault()
        const email = document.getElementById("loginEmail")?.value.trim()
        const senha = document.getElementById("loginSenha")?.value.trim()
        if (!email || !senha) return alert("Preencha todos os campos")
        mostrarCarregamento()
        try {
            const resp = await fetch(`${API}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, senha })
            })
            const dados = await resp.json()
            if (!resp.ok) throw new Error(dados.erro)
            localStorage.setItem("usuario", JSON.stringify(dados.usuario))
            window.location.href = "index.html"
        } catch(e) { alert(e.message) }
        finally { esconderCarregamento() }
    })
}

const registerForm = document.getElementById("registerForm")
if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault()
        const nome = document.getElementById("registerNome")?.value.trim()
        const usuarioInput = document.getElementById("registerUsuario")?.value.trim()
        const email = document.getElementById("registerEmail")?.value.trim()
        const senha = document.getElementById("registerSenha")?.value.trim()
        if (!nome || !usuarioInput || !email || !senha) return alert("Preencha todos os campos")
        mostrarCarregamento()
        try {
            const resp = await fetch(`${API}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nome, usuario: usuarioInput, email, senha })
            })
            const dados = await resp.json()
            if (!resp.ok) throw new Error(dados.erro)
            alert("Conta criada! Faça login.")
            window.location.href = "login.html"
        } catch(e) { alert(e.message) }
        finally { esconderCarregamento() }
    })
}