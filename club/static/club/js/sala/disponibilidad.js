/**
 * Punto de enlace para la disponibilidad en tiempo real.
 *
 * Hoy el club confirma cada reserva por WhatsApp y no hay ocupación en línea, así que esta función
 * devuelve null y la sala no muestra estados (no se simula nada).
 *
 * Cuando exista, debe devolver un Map { idMesa -> "libre" | "ocupada" | "reservada" | "mantenimiento" }
 * para la fecha y el horario pedidos; la escena 3D y el plano ligero ya saben pintarlos (marcarEstados).
 * Ejemplo futuro: fetch(`/api/disponibilidad/?fecha=${fecha}&inicio=${inicio}&duracion=${duracion}`).
 */
export async function consultarDisponibilidad(/* { fecha, inicioMin, duracionMin } */) {
  return null;
}

/**
 * Canales para enviar la reserva. Hoy solo WhatsApp; un pago en línea se agregaría aquí
 * como otro canal con la misma reserva armada (ver formulario.js → reservaActual()).
 */
export const CANALES = ["whatsapp"];
