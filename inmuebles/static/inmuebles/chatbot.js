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
  else {
    response = "No entendí tu mensaje. Escribe una palabra como: empresa, buscar, contacto, blog o filtros.";
  }

  messages.innerHTML += "<div class='bot'>" + response + "</div>";
  document.getElementById("userInput").value = "";
  messages.scrollTop = messages.scrollHeight;
  
}
