(() => {
  const api = '/api/perfilador/';
  const $ = id => document.getElementById(id);
  const estado = mensaje => { $('estado').textContent = mensaje; };
  const cookie = () => document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
  let respuestas = {}, preguntas = {}, versionPreguntas = null;
  let lista = [], indice = 0, resultado = null, inmuebleElegido = null, claveSolicitud = crypto.randomUUID();
  let ubicaciones = {}, referenciaCambio = null;
  let datosCliente = {nombre:'', celular:''};
  const valor = clave => respuestas[clave]?.estado === 'RESPONDIDA' ? respuestas[clave].valor : null;
  const monedaPerfil = () => valor('presupuesto')?.moneda || 'COP';
  const formatear = (numero, moneda = monedaPerfil(), cambio = referenciaCambio) => {
    if (numero == null) return 'Pendiente';
    if (moneda === 'USD' && !cambio) return 'Conversión a USD pendiente: falta tasa verificada';
    const valorNumero = Number(numero) / (moneda === 'USD' ? Number(cambio.cop_por_usd) : 1);
    return new Intl.NumberFormat('es-CO', {style:'currency', currency:moneda, maximumFractionDigits:0}).format(valorNumero);
  };
  const mostrarIngresado = (numero, moneda) => new Intl.NumberFormat('es-CO', {style:'currency',currency:moneda,maximumFractionDigits:0}).format(Number(numero));
  const nombresResumen = {
    proposito:'Propósito', objetivo_inversion:'Objetivo de inversión', horizonte_inversion:'Horizonte de inversión',
    prioridad_inversion:'Prioridad de inversión', experiencia_inversion:'Experiencia', gestion_inversion:'Administración',
    ciudad:'Ubicación', entrega:'Entrega deseada', habitaciones:'Habitaciones', familia:'Hogar', area_m2:'Área mínima',
    parqueadero:'Parqueadero', presupuesto:'Presupuesto máximo', pago:'Forma de pago', recursos:'Recursos actuales',
    fuentes_recursos:'Origen de recursos', aporte_mensual:'Aporte mensual adicional', ingresos:'Ingresos del hogar',
    obligaciones:'Otras obligaciones'
  };
  const nombresOpciones = {
    VIVIR:'Vivir', INVERTIR:'Invertir', AMBAS:'Vivir e invertir', INGRESOS_ARRIENDO:'Arriendo a largo plazo',
    RENTA_CORTA:'Renta corta tipo Airbnb', VALORIZACION:'Valorización', REVENTA:'Vender en el futuro',
    DIVERSIFICACION:'Diversificar patrimonio', MENOS_3:'Menos de 3 años', DE_3_A_7:'Entre 3 y 7 años',
    MAS_7:'Más de 7 años', MENOR_INVERSION:'Menor valor de compra', UBICACION:'Ubicación', ESPACIO:'Área',
    AUN_NO_SE:'Aún por definir', PRIMERA:'Primera inversión', YA_INVIERTO:'Ya ha invertido',
    DIRECTA:'Administración directa', DELEGADA:'Administración delegada', POR_DEFINIR:'Por definir',
    CONTADO:'Recursos propios', CREDITO:'Crédito hipotecario', SI:'Sí', NO:'No'
  };
  function textoResumen(clave, respuesta){
    if(respuesta.estado!=='RESPONDIDA'){
      if(respuesta.estado==='SIN_PREFERENCIA')return clave==='ciudad'?'Sin preferencia de ubicación':'Sin preferencia';
      return {NO_SE:'No lo sabe aún', PREFIERO_DESPUES:'Prefiere responder después', OMITIDA:'Sin respuesta'}[respuesta.estado]||'Pendiente';
    }
    const dato=respuesta.valor;
    if(clave==='ciudad')return dato.ciudad?`${dato.ciudad}, ${dato.departamento}`:`Cualquier ciudad de ${dato.departamento}`;
    if(clave==='familia')return `${dato.adultos} adultos, ${dato.menores} menores, ${dato.adultos_mayores} adultos mayores`;
    if(clave==='presupuesto')return mostrarIngresado(dato.monto,dato.moneda);
    if(clave==='fuentes_recursos')return ['cesantias','cdt','cuenta','otros'].map((k,i)=>
      `${['Cesantías','CDT','Cuenta','Otros'][i]}: ${mostrarIngresado(dato.montos[k],dato.moneda)} (${dato.porcentajes[k]} %)`
    ).join(' · ');
    if(['recursos','aporte_mensual','ingresos','obligaciones'].includes(clave))return mostrarIngresado(dato,monedaPerfil());
    if(clave==='entrega')return Number(dato)===0?'Entrega inmediata':`En ${dato} meses`;
    if(clave==='habitaciones')return `${dato} habitaciones`;
    if(clave==='area_m2')return `${dato} m²`;
    return nombresOpciones[dato]||String(dato);
  }
  function mostrarResumen(){
    const contenedor=$('datos-perfil');contenedor.replaceChildren();
    $('titulo-resumen-perfil').textContent=datosCliente.nombre?`Perfil de ${datosCliente.nombre}`:'Resumen del perfil';
    const aplicables=listaAplicable();
    const registradas=aplicables.filter(k=>respuestas[k]);
    $('avance-perfil').textContent=registradas.length
      ? `${registradas.length} de ${aplicables.length} preguntas atendidas. El resumen se actualiza con cada respuesta.`
      : 'Todavía no has respondido preguntas.';
    registradas.forEach(clave=>{
      const respuesta=respuestas[clave];
      const etiqueta=document.createElement('dt');etiqueta.textContent=nombresResumen[clave]||preguntas[clave]?.texto||clave;
      const contenido=document.createElement('dd');
      contenido.textContent=textoResumen(clave,respuesta)+(respuesta.indispensable?' · Indispensable':'');
      contenedor.append(etiqueta,contenido);
    });
  }
  const precioOpcion = (opcion, cambio) => opcion.moneda==='USD'
    ? (monedaPerfil()==='USD' ? mostrarIngresado(opcion.precio,'USD') : cambio ? mostrarIngresado(Number(opcion.precio)*Number(cambio.cop_por_usd),'COP') : 'Conversión a COP pendiente: falta tasa verificada')
    : formatear(opcion.precio,monedaPerfil(),cambio);
  async function pedir(ruta, metodo='GET', cuerpo) {
    const r = await fetch(api + ruta, {method:metodo, credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':decodeURIComponent(cookie())}, body:cuerpo ? JSON.stringify(cuerpo):undefined});
    let data; try {data = await r.json();} catch {throw Error('No se pudo leer la respuesta. Intenta otra vez.');}
    if (!r.ok) throw Error(data.error || `No se pudo completar la acción (${r.status}).`);
    return data;
  }
  function listaAplicable() {
    const proposito = valor('proposito');
    return Object.keys(preguntas).filter(k =>
      (k !== 'familia' || ['VIVIR','AMBAS'].includes(proposito) && respuestas.habitaciones?.estado==='NO_SE') &&
      (!['objetivo_inversion','horizonte_inversion','prioridad_inversion','experiencia_inversion','gestion_inversion'].includes(k) || ['INVERTIR','AMBAS'].includes(proposito)) &&
      (k !== 'fuentes_recursos' || Number(valor('recursos')) > 0 && valor('recursos') !== null) &&
      (!['ingresos','obligaciones'].includes(k) || respuestas.aporte_mensual?.estado === 'NO_SE'));
  }
  function pendientes() {return listaAplicable().filter(k => preguntas[k].obligatoria && !['RESPONDIDA','SIN_PREFERENCIA','NO_SE'].includes(respuestas[k]?.estado));}
  function actualizarLista() {
    const actual = lista[indice]; lista=listaAplicable();
    if (actual && lista.includes(actual)) indice=lista.indexOf(actual);
    else indice=Math.min(indice,lista.length);
  }
  async function iniciar() {
    try {
      datosCliente={nombre:'',celular:''};
      $('form-datos-opcionales').reset();$('estado-datos-opcionales').textContent='';
      $('form-asesoria').reset();$('confirmacion').textContent='';
      const def=await pedir('preguntas/'); preguntas=def.preguntas;versionPreguntas=def.version;
      ubicaciones=(await pedir('ubicaciones/')).departamentos;
      referenciaCambio=(await pedir('cambio/')).referencia;
      try {const refs=(await pedir('referencias/')).referencias;$('referencia').replaceChildren(new Option('Sin referencia verificada',''));refs.forEach(r=>$('referencia').add(new Option(`${r.entidad} · ${r.producto} · ${Number(r.tasa_ea)*100} % E.A. (${r.verificada})`,r.id)));} catch { /* Se permite hipótesis personal. */ }
      respuestas={};resultado=null;inmuebleElegido=null;claveSolicitud=crypto.randomUUID();
      lista=listaAplicable();indice=0;
      actualizarLista();mostrarPregunta();mostrarResumen();estado('Cada visita empieza una búsqueda nueva: responde y te mostramos la recomendación.');
    }catch(e){estado(`No pudimos iniciar: ${e.message}. Recarga la página para reintentar.`);}
  }
  const etiquetar = (texto, elemento) => {const label=document.createElement('label');label.textContent=texto;label.append(elemento);return label;};
  const entradaNumerica = (nombre, cantidad=0, maximo) => {const input=document.createElement('input');input.type='number';input.min='0';input.step='1';input.name=nombre;input.value=cantidad;if(maximo)input.max=maximo;return input;};
  function mostrarPregunta() {
    actualizarLista();
    if(indice>=lista.length){
      $('form-pregunta').hidden=true;$('completado').hidden=false;
      $('progreso').textContent='RECORRIDO COMPLETADO';
      $('titulo-pregunta').textContent='Ya respondiste todo lo necesario.';
      return;
    }
    $('form-pregunta').hidden=false;$('completado').hidden=true;
    const clave=lista[indice], pregunta=preguntas[clave];
    let previo=valor(clave);
    $('progreso').textContent=`PREGUNTA ${indice+1} DE ${lista.length}${pregunta.obligatoria?' · NECESARIA':''}`;
    $('titulo-pregunta').textContent=pregunta.texto;$('campo').replaceChildren();$('error-campo').textContent='';
    const campo=$('campo');let control;
    if(pregunta.tipo==='opcion') {
      if(clave==='objetivo_inversion'){
        const grupo=document.createElement('div');grupo.className='grupo-opciones';grupo.setAttribute('role','radiogroup');grupo.setAttribute('aria-label',pregunta.texto);
        const etiquetas={INGRESOS_ARRIENDO:'Ingresos por arriendo a largo plazo',RENTA_CORTA:'Renta corta tipo Airbnb',VALORIZACION:'Potencial de valorización',REVENTA:'Vender en el futuro',DIVERSIFICACION:'Diversificar mi patrimonio'};
        pregunta.opciones.forEach(o=>{
          const radio=document.createElement('input');radio.type='radio';radio.name='respuesta';radio.id=`opt-${o}`;radio.value=o;
          if(previo===o)radio.checked=true;
          const lab=document.createElement('label');lab.htmlFor=`opt-${o}`;lab.textContent=etiquetas[o]||o;
          const fila=document.createElement('div');fila.className='opcion-fila';fila.append(radio,lab);grupo.append(fila);
        });
        campo.append(etiquetar('Tu respuesta',grupo));
        const nota=document.createElement('p');nota.className='nota';nota.textContent='La renta corta y la valorización requieren verificación (reglamento, autorización y datos del inmueble) antes de decidir.';campo.append(nota);
      }else{
      control=document.createElement('select');control.id='valor';control.add(new Option('Selecciona una opción',''));
      const etiquetas={VIVIR:'Para vivir',INVERTIR:'Para invertir',AMBAS:'Para vivir e invertir',CONTADO:'Recursos propios (contado)',CREDITO:'Crédito hipotecario',SI:'Sí',NO:'No',INGRESOS_ARRIENDO:'Ingresos por arriendo a largo plazo',RENTA_CORTA:'Renta corta tipo Airbnb',VALORIZACION:'Potencial de valorización',REVENTA:'Vender en el futuro',DIVERSIFICACION:'Diversificar mi patrimonio',MENOS_3:'Menos de 3 años',DE_3_A_7:'Entre 3 y 7 años',MAS_7:'Más de 7 años',MENOR_INVERSION:'Menor valor de compra',UBICACION:'Ubicación',ESPACIO:'Área',AUN_NO_SE:'Aún no lo sé',PRIMERA:'Sí, sería mi primera inversión',YA_INVIERTO:'No, ya tengo experiencia',DIRECTA:'Administrarla personalmente',DELEGADA:'Delegar la administración',POR_DEFINIR:'Todavía no lo he decidido'};
      pregunta.opciones.forEach(o=>control.add(new Option(etiquetas[o]||o,o)));control.value=previo||'';campo.append(etiquetar('Tu respuesta',control));
      }
    }else if(pregunta.tipo==='ubicacion') {
      const departamentos=Object.keys(ubicaciones);
      const dep=document.createElement('select');dep.id='departamento';dep.add(new Option('Selecciona un departamento',''));
      departamentos.forEach(d=>dep.add(new Option(d,d)));dep.value=previo?.departamento||'';
      const ciudad=document.createElement('select');ciudad.id='valor';
      let departamentoCargado=null;
      const ciudades=()=>{
        ciudad.replaceChildren(new Option(dep.value?`Cualquier ciudad de ${dep.value}`:'Primero selecciona un departamento',''));
        (ubicaciones[dep.value]||[]).forEach(c=>ciudad.add(new Option(c,c)));
        ciudad.value=previo?.departamento===dep.value?previo?.ciudad||'':'';
        departamentoCargado=dep.value;
      };
      const sincronizar=abrir=>{
        if(dep.value===departamentoCargado)return;
        previo=null;ciudades();
        if(abrir && dep.value){ciudad.size=Math.min(ciudad.options.length,7);ciudad.focus();}
      };
      dep.oninput=()=>sincronizar(true);
      dep.onchange=()=>sincronizar(true);
      dep.onblur=()=>sincronizar(false);
      ciudad.onfocus=()=>sincronizar(false);
      ciudad.onchange=()=>{ciudad.size=1;};
      ciudad.onblur=()=>{ciudad.size=1;};
      ciudad.onkeydown=e=>{if(e.key==='Escape'){ciudad.size=1;dep.focus();}};
      ciudades();campo.append(etiquetar('Departamento',dep),etiquetar('Ciudad (puede dejarla abierta)',ciudad));
      // Firefox puede restaurar el valor del departamento sin emitir change.
      setTimeout(()=>{if(dep.isConnected)sincronizar(true);},150);
      const nota=document.createElement('p');nota.className='nota';nota.textContent='Puedes elegir cualquier departamento y ciudad de Colombia, aunque hoy no haya inmuebles publicados allí. Deja abierta la ciudad para explorar un departamento entero, o usa «Sin preferencia» para todo el país.';campo.append(nota);
    }else if(pregunta.tipo==='familia'){
      [['adultos','Personas adultas'],['menores','Niños, niñas o adolescentes'],['adultos_mayores','Adultos mayores']].forEach(([key,label])=>campo.append(etiquetar(label,entradaNumerica(key,previo?.[key] ?? (key==='adultos'?1:0),20))));
    }else if(pregunta.tipo==='montos'){
      const totalRecursos=valor('recursos'); const monedaRecursos=monedaPerfil();
      const nota=document.createElement('p');nota.className='nota';nota.textContent=`Escriba el monto que tiene en cada opción, en ${monedaRecursos}. El porcentaje se calcula solo. Deben sumar exactamente el total declarado${totalRecursos!=null&&totalRecursos!==''?` (${mostrarIngresado(totalRecursos,monedaRecursos)})`:''}. Si no conoce el detalle, seleccione «No lo sé».`;campo.append(nota);
      const resumen=document.createElement('p');resumen.id='resumen-fuentes';resumen.className='resumen-fuentes';resumen.setAttribute('aria-live','polite');
      [['cesantias','Cesantías'],['cdt','CDT'],['cuenta','Cuenta o ahorros'],['otros','Otros recursos']].forEach(([key,label])=>{
        const bloque=document.createElement('div');bloque.className='campo-dinero';
        const input=document.createElement('input');input.type='text';input.inputMode='numeric';input.autocomplete='off';input.name=key;input.placeholder='0';input.value=previo?.montos?.[key] ?? '';
        const vista=document.createElement('p');vista.className='vista-moneda';vista.dataset.fuente=key;
        bloque.append(etiquetar(label,input),vista);campo.append(bloque);
      });
      campo.append(resumen);
      const actualizarFuentes=()=>{
        const partes=[['cesantias','Cesantías'],['cdt','CDT'],['cuenta','Cuenta o ahorros'],['otros','Otros recursos']].map(([key,label])=>{
          const caja=campo.querySelector(`[name=${key}]`);
          const limpio=(caja.value||'').replace(/\D/g,'').replace(/^0+(?=\d)/,'');
          caja.value=limpio;
          const vista=caja.closest('.campo-dinero').querySelector('.vista-moneda');
          const total=totalRecursos==null||totalRecursos==='' ? null : Number(totalRecursos);
          const monto=limpio===''?0:Number(limpio);
          const pct=total?Math.round(monto*1000/total)/10:0;
          vista.textContent=limpio?`Equivale a ${mostrarIngresado(monto,monedaRecursos)} (${pct} % del total)`:`Monto en ${monedaRecursos}`;
          return {etiqueta:label,monto:monto};
        });
        const suma=partes.reduce((a,b)=>a+b.monto,0);
        const total=totalRecursos==null||totalRecursos==='' ? null : Number(totalRecursos);
        if(total==null){resumen.textContent=`Suma actual: ${mostrarIngresado(suma,monedaRecursos)}.`;}
        else if(suma===total){resumen.textContent=`Listo: cuadra con el total declarado (${mostrarIngresado(total,monedaRecursos)}).`;}
        else if(suma<total){resumen.textContent=`Llevas ${mostrarIngresado(suma,monedaRecursos)}. Te faltan ${mostrarIngresado(total-suma,monedaRecursos)} para llegar al total.`;}
        else{resumen.textContent=`Te pasaste por ${mostrarIngresado(suma-total,monedaRecursos)}. Deben sumar exactamente el total.`;}
        resumen.dataset.suma=suma;
        if($('error-campo').textContent){
          $('error-campo').textContent='';
          if(total!==null && suma===total)estado('Los montos ya cuadran. Puedes continuar.');
        }
      };
      campo.querySelectorAll('input').forEach(el=>el.addEventListener('input',actualizarFuentes));
      actualizarFuentes();
    }else if(pregunta.tipo==='dinero' || pregunta.tipo==='dinero_perfil'){
      let moneda=monedaPerfil();
      if(pregunta.tipo==='dinero'){const selector=document.createElement('select');selector.id='moneda';['COP','USD'].forEach(c=>selector.add(new Option(c==='COP'?'Pesos colombianos (COP)':'Dólares estadounidenses (USD)',c)));selector.value=previo?.moneda||'COP';moneda=selector.value;campo.append(etiquetar('Moneda para toda la perfilación',selector));selector.onchange=()=>{vistaMoneda();};}
      const bloque=document.createElement('div');bloque.className='campo-dinero';
      control=document.createElement('input');control.id='valor';control.type='text';control.inputMode='numeric';control.autocomplete='off';control.value=pregunta.tipo==='dinero'?previo?.monto||'':previo||'';
      const vista=document.createElement('p');vista.id='vista-moneda';vista.className='vista-moneda';vista.setAttribute('aria-live','polite');
      const vistaMoneda=()=>{const seleccion=$('moneda')?.value||monedaPerfil();const cifra=control.value.replace(/\D/g,'').replace(/^0+(?=\d)/,'');control.value=cifra;vista.textContent=cifra?`Equivale a ${mostrarIngresado(cifra,seleccion)}`:`Escribe el importe en ${seleccion}`;};
      control.addEventListener('input',vistaMoneda);control.addEventListener('change',vistaMoneda);
      bloque.append(etiquetar('Valor',control),vista);campo.append(bloque);vistaMoneda();
      if(clave==='recursos'){const cero=document.createElement('button');cero.type='button';cero.className='secundario';cero.textContent='No cuento con dinero para la cuota inicial';cero.onclick=()=>guardar('RESPONDIDA','0');campo.append(cero);}
      if(clave==='aporte_mensual'){const nota=document.createElement('p');nota.className='nota';nota.textContent='Si no sabes qué aportar, elige «No lo sé»: preguntaremos por ingresos del hogar para explorar una referencia del 30 %. No es una regla legal ni una aprobación bancaria.';campo.append(nota);}
    }else{
      control=document.createElement('input');control.id='valor';control.type='number';control.min='0';control.step=['habitaciones','entrega'].includes(clave)?'1':'any';control.value=previo||'';
      campo.append(etiquetar('Tu respuesta',control));
      if(clave==='entrega'){const ya=document.createElement('button');ya.type='button';ya.className='secundario';ya.textContent='La necesito con entrega inmediata';ya.onclick=()=>guardar('RESPONDIDA','0');campo.append(ya);}
    }
    $('indispensable').checked=!!respuestas[clave]?.indispensable;
    $('envoltorio-indispensable').hidden=!['ciudad','habitaciones','area_m2','parqueadero','presupuesto','entrega'].includes(clave);
    document.querySelectorAll('[data-estado]').forEach(b=>{
      b.hidden=!pregunta.alternativas.includes(b.dataset.estado);
      if(clave==='ciudad' && b.dataset.estado==='SIN_PREFERENCIA')b.textContent='Sin preferencia de ciudad: quiero ver opciones en cualquier lugar';
      else if(b.dataset.estado==='SIN_PREFERENCIA')b.textContent='Sin preferencia';
    });
    $('anterior').disabled=indice===0;
  }
  function capturar() {
    const clave=lista[indice], tipo=preguntas[clave].tipo;
    if(tipo==='ubicacion'){
      if($('departamento').value && $('valor').options.length<2)$('departamento').dispatchEvent(new Event('change'));
      return {departamento:$('departamento').value,ciudad:$('valor').value};
    }
    if(tipo==='familia')return Object.fromEntries(['adultos','menores','adultos_mayores'].map(k=>[k,$(`campo`).querySelector(`[name=${k}]`).value]));
    if(tipo==='montos')return Object.fromEntries(['cesantias','cdt','cuenta','otros'].map(k=>{const v=$('campo').querySelector(`[name=${k}]`).value.replace(/\D/g,'');return [k,v===''?'0':v];}));
    if(tipo==='opcion' && clave==='objetivo_inversion')return $('campo').querySelector('input[name=respuesta]:checked')?.value || '';
    if(tipo==='dinero')return {monto:$('valor').value,moneda:$('moneda').value};
    return $('valor').value;
  }
  async function guardar(estadoRespuesta, entradaValor) {
    const clave=lista[indice];
    if(estadoRespuesta==='RESPONDIDA' && preguntas[clave]?.tipo==='montos'){
      const total=Number(valor('recursos'));
      const suma=['cesantias','cdt','cuenta','otros'].reduce((a,k)=>a+Number(String(entradaValor?.[k]??'').replace(/\D/g,'')||0),0);
      if(!(total>0) || suma!==total){
        $('error-campo').textContent=`Los montos deben sumar exactamente el total declarado (${total>0?mostrarIngresado(total,monedaPerfil()):'total no declarado'}). Ahora suman ${mostrarIngresado(suma,monedaPerfil())}.`;
        estado('Revisa los montos antes de continuar.');
        return;
      }
    }
    const entrada={estado:estadoRespuesta,fuente:'CLIENTE',indispensable:estadoRespuesta==='RESPONDIDA' && $('indispensable').checked && !$('envoltorio-indispensable').hidden};
    if(estadoRespuesta==='RESPONDIDA')entrada.valor=entradaValor;
    const botones=$('form-pregunta').querySelectorAll('button');botones.forEach(b=>b.disabled=true);estado('Guardando respuesta…');
    try{
      const r=await pedir('respuestas/','POST',{version:versionPreguntas,respuestas,clave,respuesta:entrada});
      respuestas=r.respuestas;resultado=null;inmuebleElegido=null;
      $('opciones').replaceChildren();$('resumen').textContent='Tus respuestas cambiaron. Consulta las recomendaciones actualizadas.';
      $('comparacion').hidden=$('simulador').hidden=$('asesoria').hidden=true;
      lista=listaAplicable();indice=lista.indexOf(clave)+1;
      estado('Respuesta incorporada a esta búsqueda.');mostrarPregunta();mostrarResumen();
      if(!pendientes().length) await actualizarRecomendaciones();
    }catch(e){$('error-campo').textContent=e.message;estado('No se pudo validar la respuesta. Corrige el campo e inténtalo de nuevo.');}
    finally{botones.forEach(b=>b.disabled=false);$('anterior').disabled=indice===0;}
  }
  $('form-pregunta').addEventListener('submit',e=>{e.preventDefault();guardar('RESPONDIDA',capturar());});
  $('form-datos-opcionales').addEventListener('submit',e=>{
    e.preventDefault();
    const nombre=$('nombre-perfil').value.trim().replace(/\s+/g,' ');
    const celular=$('celular-perfil').value.trim();
    const aviso=$('estado-datos-opcionales');
    if(celular && (!/^[+()\d\s.\-]{7,40}$/.test(celular) || celular.replace(/\D/g,'').length<7)){
      aviso.textContent='Revisa el celular: debe contener al menos 7 dígitos.';
      return;
    }
    datosCliente={nombre,celular};
    mostrarResumen();
    aviso.textContent=nombre?'Perfil personalizado. Puedes continuar con las preguntas.':celular?'Celular ingresado. Puedes continuar con las preguntas.':'Puedes continuar sin ingresar estos datos.';
  });
  document.querySelectorAll('[data-estado]').forEach(b=>b.addEventListener('click',()=>guardar(b.dataset.estado)));
  $('anterior').onclick=()=>{indice=Math.max(0,indice-1);mostrarPregunta();};
  $('revisar').onclick=()=>{indice=0;mostrarPregunta();};
  $('nuevo').onclick=async()=>{
    estado('Empezando una búsqueda nueva…');
    respuestas={};resultado=null;inmuebleElegido=null;
    datosCliente={nombre:'',celular:''};
    $('form-datos-opcionales').reset();$('estado-datos-opcionales').textContent='';
    $('form-asesoria').reset();$('confirmacion').textContent='';
    claveSolicitud=crypto.randomUUID();indice=0;
    $('opciones').replaceChildren();$('resumen').textContent='Responde lo que sepas para encontrar opciones.';
    $('comparacion').hidden=$('simulador').hidden=$('asesoria').hidden=true;
    mostrarResumen();
    lista=listaAplicable();mostrarPregunta();
    estado('Búsqueda nueva lista. Responde y te mostramos la recomendación.');
  };
  async function actualizarRecomendaciones(){
    estado('Evaluando todas las viviendas disponibles…');
    try{resultado=await pedir('evaluar/','POST',{version:versionPreguntas,respuestas});inmuebleElegido=null;dibujar();estado('Orientación calculada para esta visita. Consulta tus opciones o edita una respuesta.');}
    catch(e){estado(`No se pudo evaluar: ${e.message}`);}
  }
  function dibujar(){
    $('opciones').replaceChildren();$('comparacion').hidden=$('simulador').hidden=$('asesoria').hidden=true;
    if(resultado.estado==='CATALOGO_VACIO'){$('resumen').textContent='Ahora no hay apartamentos o casas disponibles en venta. Puedes empezar otra búsqueda o volver más adelante.';return;}
    if(resultado.estado==='SIN_COINCIDENCIAS_UBICACION'){
      const lugar=resultado.ubicacion_deseada;
      $('resumen').textContent=`No encontramos apartamentos o casas disponibles en ${lugar?.ciudad}, ${lugar?.departamento}. No vamos a recomendarte propiedades de ciudades lejanas como si coincidieran. Prueba ampliar la búsqueda a todo ${lugar?.departamento} o elegir otra ciudad.`;
      return;
    }
    if(resultado.estado==='SIN_COINCIDENCIAS'){$('resumen').textContent=`No hay coincidencias con tus requisitos indispensables (${resultado.excluidas_requisitos} opciones excluidas). Puedes revisar una preferencia.`;return;}
    const cambio=resultado.cambio;
    if(resultado.estado==='ALTERNATIVAS_UBICACION'){
      const lugar=resultado.ubicacion_deseada;
      $('resumen').textContent=`No encontramos opciones exactas en ${lugar?.ciudad}. Estas ${resultado.alternativas_mismo_departamento} alternativas están en otros municipios de ${lugar?.departamento}; no contamos con distancias o tiempos de viaje, así que verifica si la ubicación te sirve. Cobertura: ${resultado.cobertura} %.`;
    }else{
      const resumenUbicacion=resultado.ubicacion_deseada?.ciudad
        ? `Encontramos ${resultado.coincidencias_ubicacion} opciones en ${resultado.ubicacion_deseada.ciudad}${resultado.alternativas_mismo_departamento?` y ${resultado.alternativas_mismo_departamento} alternativas en otros municipios de ${resultado.ubicacion_deseada.departamento} (distancia por verificar)`:''}.`
        : `Encontramos ${resultado.total_opciones} viviendas de ${resultado.total_catalogo} disponibles.`;
      $('resumen').textContent=`${resumenUbicacion} Cobertura: ${resultado.cobertura} %. ${resultado.pendientes_cliente.length?'Información pendiente: '+resultado.pendientes_cliente.join('; ')+'.':''}${monedaPerfil()==='USD'&&!cambio?' Sin una tasa COP/USD verificada no podemos comparar el presupuesto ni convertir precios.':''}`;
    }
    resultado.opciones.forEach((o,i)=>{
      const card=document.createElement('article');card.className='resultado'+(o.id===resultado.principal?' destacada':'');
      const linea=(contenido,clase)=>{const p=document.createElement('p');p.textContent=contenido;if(clase)p.className=clase;card.append(p);};
      if(o.imagen){const imagen=document.createElement('img');imagen.src=o.imagen;imagen.alt=`Imagen de ${o.titulo}`;imagen.loading='lazy';card.append(imagen);}
      const esAlternativaUbicacion=o.tipo_coincidencia_ubicacion==='ALTERNATIVA_DEPARTAMENTO';
      linea(esAlternativaUbicacion?'ALTERNATIVA EN OTRO MUNICIPIO · UBICACIÓN POR REVISAR':o.id===resultado.principal?'RECOMENDACIÓN EN TU CIUDAD':o.id===resultado.alternativa?'ALTERNATIVA EN TU CIUDAD':'OPCIÓN EN TU CIUDAD','etiqueta');
      const titulo=document.createElement('h3');titulo.textContent=o.titulo;card.append(titulo);
      linea(`${o.tipo} · ${o.ciudad} (${o.departamento}) · ${o.barrio}`);
      linea(`${precioOpcion(o,cambio)} · ${o.area_m2} m² · ${o.habitaciones} habitaciones · ${o.parqueaderos} parqueaderos`);
      linea(o.entrega_texto);
      if(o.origen_texto)linea(o.origen_texto);
      if(o.porcentaje_inicial_exigido!=null)linea(`Inicial exigida por el proyecto: ${o.porcentaje_inicial_exigido} %${o.valor_separacion!=null?` · Separación: ${formatear(o.valor_separacion,o.moneda,cambio)}`:''}`);
      linea(`Afinidad orientativa: ${o.afinidad==null?'No calculable':o.afinidad+' %'} · Cobertura: ${resultado.cobertura} %`);
      linea(`Por qué encaja: ${o.razones.filter(r=>r.puntuacion===1).map(r=>r.razon).join('; ') || 'Aún faltan datos comparables.'}`);
      const razonesCercanas=o.razones.filter(r=>r.puntuacion>=0.65&&r.puntuacion<1&&!(esAlternativaUbicacion&&r.criterio==='ciudad')).map(r=>r.razon);
      const diferencias=o.razones.filter(r=>r.puntuacion<0.65&&!(esAlternativaUbicacion&&r.criterio==='ciudad')).map(r=>r.razon);
      const pendientes=[...o.pendientes,...o.pendientes_catalogo];
      if(esAlternativaUbicacion)linea(`Ubicación por revisar: está en ${o.ciudad}, en ${o.departamento}; confirma si el trayecto hasta ${resultado.ubicacion_deseada?.ciudad} te funciona. No tenemos distancia geográfica verificada.`,'pendiente');
      if(razonesCercanas.length)linea(`Por revisar (se acerca a lo que buscas): ${razonesCercanas.join('; ')}`,'pendiente');
      if(diferencias.length)linea(`Diferencias importantes con tu búsqueda: ${diferencias.join('; ')}`,'pendiente');
      if(pendientes.length)linea(`Datos por confirmar: ${pendientes.join('; ')}`,'pendiente');
      const acciones=document.createElement('div');acciones.className='acciones';
      const detalle=document.createElement('a');detalle.href=o.url;detalle.textContent='Ver inmueble ↗';acciones.append(detalle);
      const sim=document.createElement('button');sim.type='button';sim.className='secundario';sim.textContent='Simular compra';sim.onclick=()=>{
        inmuebleElegido=o.id;$('simular-titulo').textContent=`${o.titulo} · ${precioOpcion(o,cambio)}`;
        $('porcentaje-es-proyecto').value=o.porcentaje_inicial_exigido!=null?'SI':'NO';
        if(o.porcentaje_inicial_exigido!=null)$('form-simular').elements.porcentaje_inicial.value=o.porcentaje_inicial_exigido;
        if(valor('pago')==='CONTADO'){$('form-simular').elements.porcentaje_inicial.value='100';$('porcentaje-es-proyecto').value='NO';}
        $('separacion-es-proyecto').value=o.valor_separacion!=null?'SI':'NO';
        let separacionPrefill=Number(o.valor_separacion||0);
        if(o.valor_separacion!=null&&o.moneda!==monedaPerfil()&&cambio){
          const separacionCop=o.moneda==='USD'?separacionPrefill*Number(cambio.cop_por_usd):separacionPrefill;
          separacionPrefill=monedaPerfil()==='USD'?separacionCop/Number(cambio.cop_por_usd):separacionCop;
        }
        $('form-simular').elements.separacion.value=o.valor_separacion!=null?separacionPrefill:'';
        $('form-simular').elements.recursos.value=valor('recursos')||'';
        actualizarPreguntaSeparacion(true);
        $('form-simular').elements.aporte_mensual.value=valor('aporte_mensual')||'';
        document.querySelectorAll('.sim-moneda').forEach(el=>el.textContent=`(${monedaPerfil()})`);
        $('meses-fijados').textContent=o.modalidad_entrega==='SOBRE_PLANOS'&&o.meses_entrega!=null?`Entrega declarada en ${o.meses_entrega} meses. Al calcular se usan los meses restantes en vivo (la fecha de entrega queda fija).`:'Entrega inmediata: la cuota inicial debe cubrirse con los recursos actuales (0 meses para aportar).';
        $('usar-guia-contenedor').hidden=!(respuestas.aporte_mensual?.estado==='NO_SE' && valor('ingresos')!=null);
        $('simulador').hidden=false;$('simulador').scrollIntoView({behavior:'smooth'});
      };acciones.append(sim);
      const comparar=document.createElement('label');comparar.textContent=' Comparar';const ch=document.createElement('input');ch.type='checkbox';ch.className='comparar';ch.value=o.id;comparar.prepend(ch);acciones.append(comparar);card.append(acciones);$('opciones').append(card);
    });
    const comparar=document.createElement('button');comparar.type='button';comparar.className='secundario';comparar.textContent='Comparar dos opciones seleccionadas';comparar.onclick=mostrarComparacion;$('opciones').append(comparar);
    if(datosCliente.nombre)$('form-asesoria').elements.nombre.value=datosCliente.nombre;
    if(datosCliente.celular){$('form-asesoria').elements.telefono.value=datosCliente.celular;$('form-asesoria').elements.preferencia_contacto.value='TELEFONO';}
    $('asesoria').hidden=false;
  }
  $('form-simular').elements.porcentaje_inicial.addEventListener('input',()=>{$('porcentaje-es-proyecto').value='NO';});
  $('form-simular').elements.separacion.addEventListener('input',()=>{$('separacion-es-proyecto').value='NO';actualizarPreguntaSeparacion(true);});
  $('form-simular').elements.recursos.addEventListener('input',()=>actualizarPreguntaSeparacion());
  function actualizarPreguntaSeparacion(limpiarRespuesta=false){
    const form=$('form-simular');
    if(!form)return;
    const aplica=Number(form.elements.separacion.value||0)>0 && Number(form.elements.recursos.value||0)>0;
    const selector=form.elements.separacion_incluida_en_recursos;
    $('incluye-separacion-contenedor').hidden=!aplica;
    selector.required=aplica;
    if(!aplica||limpiarRespuesta)selector.value='';
  }
  function mostrarComparacion(){
    const ids=[...document.querySelectorAll('.comparar:checked')].map(x=>Number(x.value));
    if(ids.length!==2){estado('Selecciona exactamente dos opciones para comparar.');return;}
    const opciones=ids.map(x=>resultado.opciones.find(o=>o.id===x));const div=$('comparacion');div.replaceChildren();
    const h=document.createElement('h3');h.textContent='Comparación con las mismas respuestas';div.append(h);const tabla=document.createElement('table');tabla.className='tabla';
    [['Criterio',...opciones.map(o=>o.titulo)],['Precio',...opciones.map(o=>precioOpcion(o,resultado.cambio))],['Área',...opciones.map(o=>o.area_m2+' m²')],['Habitaciones',...opciones.map(o=>o.habitaciones)],['Ciudad',...opciones.map(o=>o.ciudad)],['Entrega',...opciones.map(o=>o.entrega_texto)],['Afinidad',...opciones.map(o=>o.afinidad==null?'No calculable':o.afinidad+' %')],['Pendientes',...opciones.map(o=>o.pendientes_catalogo.join('; '))]].forEach(fila=>{const tr=document.createElement('tr');fila.forEach(c=>{const celda=document.createElement('td');celda.textContent=c;tr.append(celda);});tabla.append(tr);});div.append(tabla);div.hidden=false;div.scrollIntoView({behavior:'smooth'});
  }
  $('form-simular').onsubmit=async e=>{
    e.preventDefault();const f=new FormData(e.target);const datos={version:versionPreguntas,respuestas,inmueble:inmuebleElegido,precio_visto:resultado.opciones.find(o=>o.id===inmuebleElegido)?.precio,...Object.fromEntries(f.entries())};
    delete datos.meses_inicial;
    datos.usar_aporte_orientativo=f.has('usar_aporte_orientativo');
    if(datos.usar_aporte_orientativo && !datos.aporte_mensual)delete datos.aporte_mensual;
    if(!datos.tasa_ea||datos.referencia)delete datos.tasa_ea;if(!datos.referencia)delete datos.referencia;
    if(!datos.recursos)delete datos.recursos;if(!datos.aporte_mensual)delete datos.aporte_mensual;if(!datos.separacion){delete datos.separacion;delete datos.separacion_incluida_en_recursos;}if(!datos.porcentaje_inicial)delete datos.porcentaje_inicial;
    estado('Calculando el escenario…');
    try{const r=await pedir('simular/','POST',datos),x=r.resultado;
      const money=v=>formatear(v,x.moneda_perfil,x.cambio);
      const origenMeses=x.origen_meses_inicial==='REMANENTE_EN_VIVO'?'meses restantes en vivo según la entrega declarada':x.origen_meses_inicial==='ENTREGA_INMUEBLE'?'fijados por la entrega declarada del inmueble':'según tu deseo; entrega del inmueble por confirmar';
      const box=$('resultado-simulacion');box.replaceChildren();
      const titulo=document.createElement('h4');titulo.textContent='Mini-cotización del plan de compra';box.append(titulo);
      const tabla=document.createElement('table');tabla.className='tabla';
      const fila=(c,v)=>{const tr=document.createElement('tr');const a=document.createElement('td');a.textContent=c;const b=document.createElement('td');b.textContent=v;tr.append(a,b);tabla.append(tr);};
      fila('Meses para la inicial',`${x.meses_inicial} (${origenMeses})`);
      fila(x.origen_porcentaje_inicial==='EXIGIDO_PROYECTO'?'Inicial exigida por el proyecto':'Inicial hipotética',money(x.inicial.cuota_inicial));
      fila('(−) Separación (cuota 0)',money(x.inicial.separacion_incluida_en_inicial)+(x.origen_separacion==='EXIGIDO_PROYECTO'?' (exigida por el proyecto)':''));
      if(Number(x.inicial.recursos_declarados)===0){
        fila('Recursos disponibles',money(0));
      }else if(x.inicial.separacion_incluida_en_recursos){
        fila('Recursos declarados (incluyen separación)',money(x.inicial.recursos_declarados));
        fila('(−) Separación cubierta con esos recursos',money(x.inicial.separacion_desde_recursos));
        fila('Recursos restantes para las cuotas',money(x.inicial.recursos_aplicables));
      }else{
        fila('(−) Recursos disponibles aparte de la separación',money(x.inicial.recursos_aplicables));
      }
      fila('Cuota mensual requerida',money(x.inicial.cuota_mensual)+(x.meses_inicial==='0'?' (pago único)':` durante ${x.meses_inicial} meses`));
      fila('Faltante mensual con tu aporte',money(x.inicial.faltante_mensual));
      fila('Faltante de la inicial a la entrega',money(x.inicial.faltante));
      if(Number(x.porcentaje_restante)>0)fila(`Saldo a financiar a la entrega (${x.porcentaje_restante} %)`,money(x.saldo_a_financiar));
      if(x.credito)fila('Cuota estimada banco',money(x.credito.cuota_capital_intereses)+' al mes (sin seguros ni gastos)');
      else fila('Crédito hipotecario','Sin cálculo: falta una referencia de tasa o es compra de contado.');
      box.append(tabla);
      const nota=document.createElement('p');nota.className='nota';
      nota.textContent=`${x.aporte_orientativo_30?'El aporte del 30 % es una hipótesis elegida expresamente, no un límite legal. ':''}No es una aprobación bancaria. Seguros, gastos y condiciones requieren confirmación.`;
      box.append(nota);
      estado('Escenario calculado para esta visita.');
    }catch(err){estado(`No se pudo simular: ${err.message}`);}
  };
  $('form-asesoria').onsubmit=async e=>{
    e.preventDefault();const f=new FormData(e.target);const datos={version:versionPreguntas,respuestas,inmueble:inmuebleElegido,...Object.fromEntries(f.entries()),consentimiento:f.has('consentimiento'),clave_idempotencia:claveSolicitud};const boton=e.target.querySelector('[type=submit]');boton.disabled=true;estado('Registrando tu solicitud…');
    try{await pedir('solicitudes/','POST',datos);$('confirmacion').textContent='Solicitud registrada. Una asesora podrá revisar tu información y contactarte por el medio elegido.';estado('Solicitud guardada correctamente.');}
    catch(err){estado(`No se pudo registrar: ${err.message}. Puedes volver a intentar.`);boton.disabled=false;}
  };
  iniciar();
})();
