/* ─── CURSOR ─── */
const cursor = document.getElementById('cursor');
if (cursor) {
    document.addEventListener('mousemove', e => { 
        cursor.style.left = e.clientX + 'px'; 
        cursor.style.top = e.clientY + 'px'; 
    });
    document.querySelectorAll('a, button, textarea, .chip').forEach(el => {
        el.addEventListener('mouseenter', () => cursor.classList.add('grow'));
        el.addEventListener('mouseleave', () => cursor.classList.remove('grow'));
    });
}

/* ─── CHATBOT STATE ─── */
let messages = [];
let isOpen = false;

/* ─── TIME ─── */
function now() {
    return new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
}

/* ─── TOGGLE ─── */
function toggleChat() {
    isOpen = !isOpen;
    const win = document.getElementById('chatWindow');
    const btn = document.getElementById('chatToggle');
    const dot = document.getElementById('toggleDot');
    
    if (win && btn) {
        if (isOpen) {
            win.classList.add('open');
            btn.classList.add('open');
            if (dot) dot.classList.add('hidden');
            if (messages.length === 0) {
                setTimeout(() => botMessage('¡Hola! Soy el asistente de Marín Moya Inversiones. ¿En qué puedo ayudarte hoy?'), 400);
            }
        } else {
            win.classList.remove('open');
            btn.classList.remove('open');
        }
    }
}

/* ─── ADD MESSAGE TO DOM ─── */
function appendMessage(text, type) {
    const container = document.getElementById('chatMessages');
    const welcome = document.getElementById('welcomeMsg');
    if (welcome) welcome.remove();

    const row = document.createElement('div');
    row.className = 'msg ' + type;

    if (type === 'bot') {
        row.innerHTML = `
            <div class="bot-avatar">M²</div>
            <div>
                <div class="bot-bubble">${text}</div>
                <div class="msg-time">${now()}</div>
            </div>
        `;
    } else {
        row.innerHTML = `
            <div>
                <div class="user-bubble">${text}</div>
                <div class="msg-time">${now()}</div>
            </div>
        `;
    }

    if (container) {
        container.appendChild(row);
        container.scrollTop = container.scrollHeight;
    }
    return row;
}

/* ─── TYPING INDICATOR ─── */
function showTyping() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const typing = document.createElement('div');
    typing.className = 'msg bot';
    typing.id = 'typingIndicator';
    typing.innerHTML = `
        <div class="bot-avatar">M²</div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    container.appendChild(typing);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    const t = document.getElementById('typingIndicator');
    if (t) t.remove();
}

/* ─── BOT RESPONSE ─── */
function botMessage(text) {
    showTyping();
    setTimeout(() => {
        hideTyping();
        appendMessage(text, 'bot');
        messages.push({ role: 'bot', text });
    }, 900 + Math.random() * 500);
}

/* ─── RESPONSE ENGINE ─── */
function getResponse(input) {
    const i = input.toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    if (/(empresa|portal|quienes|marin moya|plataforma|que es|quiénes)/.test(i))
        return 'Marín Moya Inversiones (M²) es un portal inmobiliario colombiano que centraliza la publicación y gestión de propiedades para conectar compradores, arrendatarios e inversores con los mejores inmuebles del país.';
    
    if (/(tipo|tipos|inmueble|que manejan|que tienen|que ofrecen|que vendes|que venden)/.test(i))
        return 'Manejamos <strong>apartamentos, casas, locales comerciales, oficinas, lotes y bodegas</strong>. Cada propiedad incluye precio en COP y USD, ubicación, fotos y descripción completa.';

    if (/(ciudad|ciudades|donde|municipio|disponible|armenia|pereira|bogota|medellin|cali)/.test(i))
        return 'Tenemos propiedades en <strong>Armenia, Pereira, Circasia, Bogotá, Medellín</strong> y otras ciudades. Podés filtrar por ciudad desde el portafolio.';

    if (/(venta|vender|comprar|arriendo|arrendar|alquiler|cesion|cesión)/.test(i))
        return 'Operamos en tres modalidades: <strong>Venta</strong> (inmuebles propios), <strong>Arriendo</strong> (contratos mensuales) y <strong>Cesión de derechos</strong> (traspaso de derechos sobre un inmueble). Podés filtrar en el portafolio por cualquiera.';

    if (/(precio|precios|cuanto|valor|costo|cuánto|pesos|dolares|usd|cop)/.test(i))
        return 'Los precios se muestran en <strong>pesos colombianos (COP)</strong> y con referencia en <strong>USD</strong>. Podés filtrar por rango de precio desde los filtros del portafolio.';

    if (/(buscar|busco|encontrar|como busco|busqueda|búsqueda|filtro|filtrar)/.test(i))
        return 'En la sección <strong>Portafolio</strong> podés buscar por nombre, ciudad o barrio, y filtrar por operación (venta/arriendo/cesión), tipo de inmueble, precio y estrato.';

    if (/(publicar|publicacion|publicación|agregar|subir inmueble|como publico|cómo publico|mis inmuebles)/.test(i))
        return 'Para publicar: <strong>1.</strong> Creá tu cuenta gratuita, <strong>2.</strong> Accedé a "Mis inmuebles", <strong>3.</strong> Hacé clic en "Publicar inmueble" y completá el formulario con fotos, precio y descripción.';

    if (/(registro|registrar|crear cuenta|como me registro|cómo me registro|nueva cuenta|sign up)/.test(i))
        return '¡El registro es gratuito! Solo necesitás un correo electrónico y una contraseña. Podés registrarte en la sección <strong>"Crear cuenta"</strong> del portal.';

    if (/(ingresar|iniciar sesion|iniciar sesión|login|acceder|contraseña|password)/.test(i))
        return 'Para acceder al portal usá el botón <strong>"Iniciar sesión"</strong> en la barra superior. Si olvidaste tu contraseña, hacé clic en "¿Olvidaste tu contraseña?" en el formulario de ingreso.';

    if (/(contacto|contactar|comunicar|asesoria|asesoría|asesor|llamar|whatsapp|tel[eé]fono)/.test(i))
        return 'En el detalle de cada inmueble encontrarás el formulario de contacto, el teléfono y el botón de <strong>WhatsApp directo</strong> con el asesor. También podés usar la sección "Contacto" del portal.';

    if (/(detalle|informacion|información|ver|descripcion|descripción|fotos|características)/.test(i))
        return 'En la ficha de cada inmueble encontrarás <strong>galería de fotos, precio COP y USD, habitaciones, baños, área, estrato, características adicionales, mapa de ubicación</strong> y formulario de contacto directo.';

    if (/(seguridad|seguro|privacidad|datos|informacion personal|proteccion)/.test(i))
        return 'La plataforma aplica validación de formularios y buenas prácticas de seguridad para proteger tu información. Tus datos personales solo son usados para gestionar tu cuenta y publicaciones.';

    if (/(admin|administrador|roles|permisos|usuario|cuenta)/.test(i))
        return 'La plataforma cuenta con roles de <strong>Administrador, Agente Comercial y Usuario</strong>. Los administradores gestionan usuarios, inmuebles y permisos desde el Panel de Administración.';

    if (/(gracias|muchas gracias|genial|excelente|perfecto|ok|listo|entendi|entendí)/.test(i))
        return '¡Con gusto! Si tenés más preguntas sobre propiedades o el portal, estoy aquí. 🏡';

    if (/(hola|buenas|buenos dias|buenos días|buenas tardes|buenas noches|hey|hi)/.test(i))
        return '¡Hola! Soy el asistente virtual de Marín Moya Inversiones. Podés preguntarme sobre inmuebles, precios, ciudades, cómo publicar o cómo registrarte.';

    return 'No entendí bien tu pregunta. Podés consultarme sobre: <strong>tipos de inmueble, ciudades, venta, arriendo, cesión, precios, cómo publicar, registro o contacto</strong>.';
}

/* ─── SEND MESSAGE ─── */
function sendMessage() {
    const input = document.getElementById('userInput');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    messages.push({ role: 'user', text });
    input.value = '';
    input.style.height = '42px';

    hideSuggestions();

    const response = getResponse(text);
    botMessage(response);
}

function sendChip(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        sendMessage();
    }
}

function hideSuggestions() {
    const s = document.getElementById('suggestions');
    if (s) { 
        s.style.transition = 'opacity .2s'; 
        s.style.opacity = '0'; 
        setTimeout(() => s.remove(), 200); 
    }
}

/* ─── KEY HANDLER ─── */
function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { 
        e.preventDefault(); 
        sendMessage(); 
    }
}

/* ─── AUTO RESIZE TEXTAREA ─── */
function autoResize(el) {
    el.style.height = '42px';
    el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

/* ─── PASSWORD TOGGLE (GLOBAL) ─── */
function initChatbot() {
    const input = document.getElementById('userInput');
    if (input) {
        input.addEventListener('keydown', handleKey);
        input.addEventListener('input', function() { autoResize(this); });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initChatbot();
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(function(input) {
        if (input.nextElementSibling && input.nextElementSibling.classList.contains('toggle-password')) return;
        const eye = document.createElement('span');
        eye.innerHTML = '👁️';
        eye.className = 'toggle-password';
        eye.style.cursor = 'pointer';
        input.after(eye);

        eye.addEventListener('click', function() {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            this.innerHTML = isPassword ? '🙈' : '👁️';
        });
    });
});

/* ─── CAROUSEL LOGIC (GLOBAL) ─── */
let slideIndex = 1;
window.plusSlides = function(n) {
    showSlides(slideIndex += n);
}
window.showSlides = function(n) {
    let slides = document.getElementsByClassName("carousel-slide");
    if (slides.length === 0) return;
    if (n > slides.length) {slideIndex = 1}
    if (n < 1) {slideIndex = slides.length}
    for (let i = 0; i < slides.length; i++) {
        slides[i].classList.remove("active");
    }
    slides[slideIndex-1].classList.add("active");
}
document.addEventListener('DOMContentLoaded', function() {
    showSlides(slideIndex);
});
