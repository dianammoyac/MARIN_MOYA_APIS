function toggleChat() {
  var chat = document.getElementById("chat");
  chat.style.display = chat.style.display === "block" ? "none" : "block";
}

function sendMessage() {
  var input = document.getElementById("userInput").value.toLowerCase();
  var messages = document.getElementById("messages");

  messages.innerHTML += "<div class='user'>" + input + "</div>";

  var response = "";

  // NEGOCIO
  if (input.includes("empresa")) {
    response = "Marín Moya Inversiones (M²) es un portal inmobiliario que centraliza la publicación y gestión de inmuebles para facilitar la búsqueda y el contacto entre compradores e inversionistas.";
  }
  else if (input.includes("inmuebles")) {
    response = "Manejamos casas, apartamentos, lotes y proyectos en desarrollo. Cada inmueble incluye precio, ubicación, estado y descripción.";
  }
  else if (input.includes("ciudades")) {
    response = "Puedes encontrar inmuebles en ciudades como Bogotá, Armenia, Cartagena y Mosquera, entre otras.";
  }
  else if (input.includes("beneficios")) {
    response = "El portal organiza la información, permite filtrar inmuebles y facilita el contacto directo con asesores de manera estructurada.";
  }
  else if (input.includes("seguridad")) {
    response = "La plataforma aplica validación de formularios y buenas prácticas de seguridad para proteger la información enviada.";
  }

  // USO DE PLATAFORMA
  else if (input.includes("buscar")) {
    response = "Desde el listado principal puedes consultar los inmuebles disponibles y seleccionar uno para ver su información detallada.";
  }
  else if (input.includes("filtros")) {
    response = "Puedes filtrar por ciudad, tipo de inmueble y rango de precio para encontrar opciones más específicas.";
  }
  else if (input.includes("detalle")) {
    response = "En el detalle encontrarás título, ubicación, precio, estado y descripción completa del inmueble.";
  }
  else if (input.includes("contacto")) {
    response = "En el detalle del inmueble encontrarás el botón 'Solicitar información' para enviar tus datos y recibir asesoría.";
  }
  else if (input.includes("blog")) {
    response = "El blog ofrece consejos para compradores e inversionistas, tendencias del mercado y recomendaciones inmobiliarias.";
  }
  else if (input.includes("login") || input.includes("sesion") || input.includes("entrar")) {
    response = "Para acceder a tu cuenta y gestionar inmuebles, por favor utiliza la opción de 'Inicio de sesión' en el menú principal.";
  }
  else {
    response = "No entendí tu mensaje. Porfavor vuelve a hacerme la pregunta.";
  }

  messages.innerHTML += "<div class='bot'>" + response + "</div>";
  document.getElementById("userInput").value = "";
  messages.scrollTop = messages.scrollHeight;

}

// Funcionalidad para ver/ocultar contraseña en formularios
document.addEventListener('DOMContentLoaded', function() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    passwordInputs.forEach(function(input) {
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

// Lógica del Carrusel
let slideIndex = 1;

// Hacemos las funciones globales para que el 'onclick' del HTML las encuentre
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

// Iniciar carrusel al cargar
document.addEventListener('DOMContentLoaded', function() {
    showSlides(slideIndex);
});
