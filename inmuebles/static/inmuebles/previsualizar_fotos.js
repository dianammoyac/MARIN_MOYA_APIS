(() => {
  document.querySelectorAll('[data-foto]').forEach(bloque => {
    const entrada = bloque.querySelector('input[type="file"]');
    const actual = bloque.querySelector('.foto-actual');
    const vacia = bloque.querySelector('.foto-vacia');
    const previa = bloque.querySelector('.foto-previa');
    const estado = bloque.querySelector('.foto-estado');
    const accion = bloque.querySelector('.foto-accion');
    const textoOriginal = estado.textContent;
    const accionOriginal = accion.textContent;
    let urlPrevia = null;

    const liberarPrevia = () => {
      if (urlPrevia) URL.revokeObjectURL(urlPrevia);
      urlPrevia = null;
    };
    const restaurar = () => {
      liberarPrevia();
      previa.onerror = null;
      previa.hidden = true;
      previa.removeAttribute('src');
      if (actual) actual.hidden = false;
      if (vacia) vacia.hidden = false;
      estado.textContent = textoOriginal;
      accion.textContent = accionOriginal;
    };

    entrada.addEventListener('change', () => {
      const archivo = entrada.files?.[0];
      if (!archivo) {
        restaurar();
        return;
      }
      if (!archivo.type.startsWith('image/')) {
        entrada.value = '';
        restaurar();
        estado.textContent = 'Seleccioná un archivo de imagen válido.';
        return;
      }

      liberarPrevia();
      urlPrevia = URL.createObjectURL(archivo);
      previa.onload = null;
      previa.onerror = () => {
        entrada.value = '';
        restaurar();
        estado.textContent = 'No se pudo mostrar la imagen. Elegí otro archivo.';
      };
      previa.src = urlPrevia;
      previa.hidden = false;
      if (actual) actual.hidden = true;
      if (vacia) vacia.hidden = true;
      accion.textContent = 'Elegir otra foto';
      estado.textContent = actual
        ? `Vista previa: ${archivo.name}. Reemplazará esta foto al guardar.`
        : `Vista previa: ${archivo.name}. Se agregará al guardar.`;
    });

    window.addEventListener('pagehide', liberarPrevia);
  });
})();
