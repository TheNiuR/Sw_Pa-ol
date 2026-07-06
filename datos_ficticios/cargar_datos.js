// ============================================================
// Script de carga de datos de ejemplo - control_panol
// ------------------------------------------------------------
// Uso:
//   mongosh "mongodb://localhost:27017/control_panol" --file cargar_datos.js
//
// Nota: los archivos JSON usan Extended JSON ({"$date": "..."})
// para representar fechas. EJSON.parse() las convierte en objetos
// Date reales antes de insertarlas; un JSON.parse() común las
// dejaría como texto plano y rompería el validador de esquema
// (bsonType: "date").
// ============================================================

const fs = require("fs");

use("control_panol");

function cargarColeccion(nombreArchivo, coleccion) {
  const contenido = fs.readFileSync(nombreArchivo, "utf8");
  const documentos = EJSON.parse(contenido);
  const resultado = db.getCollection(coleccion).insertMany(documentos);
  print(`${coleccion}: ${resultado.insertedIds ? Object.keys(resultado.insertedIds).length : 0} documentos insertados.`);
}

cargarColeccion("inventario.json", "inventario");
cargarColeccion("usuarios.json", "usuarios");
cargarColeccion("transacciones.json", "transacciones"); // al final: referencia ítems ya cargados
