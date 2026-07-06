"""
Módulo Agregar y Eliminar (CREATE / DELETE) - Sistema de Control de Pañol
============================================================================
Cambios respecto a la versión original:
  - Conexión y validaciones centralizadas en conexion.py / validaciones.py.
  - Se agregó soporte para el tercer tipo de activo del esquema:
    "Material Trazable" (RF del enunciado), que antes no tenía CRUD.
  - Se agregó CRUD de usuarios (colección "usuarios", RBAC), inexistente
    en la versión original pese a estar definida en el esquema.
  - agregar_transaccion_salida ahora valida que el ítem exista, que haya
    stock suficiente (consumibles) o que la herramienta esté disponible,
    y actualiza el inventario de forma consistente con la transacción.
  - Se agregó el movimiento de "Entrada" (devolución), que faltaba por
    completo: sin él, una herramienta que salía a terreno jamás podía
    volver a quedar disponible en el sistema.
  - Manejo de errores más específico (DuplicateKeyError, WriteError por
    validación de esquema, y una captura genérica de PyMongoError).
"""
from datetime import datetime, timezone

import pymongo.errors

from conexion import conectar
from validaciones import pedir_codigo, pedir_entero, pedir_rut, pedir_opcion

cliente, db, inventario, transacciones, usuarios = conectar("Módulo Agregar y Eliminar")


# ==========================================
# 1. FUNCIONES DE INSERCIÓN (CREATE)
# ==========================================

def agregar_herramienta():
    print("\n--- Agregar Nueva Herramienta al Inventario ---")
    codigo = pedir_codigo("Ingrese el Código único (Ej. HERR-1001): ")
    descripcion = input("Ingrese la descripción (Ej. Sierra Circular): ").strip()
    marca = input("Ingrese la marca: ").strip()

    nuevo_documento = {
        "_id": codigo,
        "tipo_activo": "Herramienta",
        "descripcion": descripcion,
        "marca": marca,
        "estado": "Bodega",
        "historial_mantenimiento": [],
    }

    try:
        inventario.insert_one(nuevo_documento)
        print(f"Éxito: Herramienta {codigo} agregada correctamente.")
    except pymongo.errors.DuplicateKeyError:
        print(f"Error: El código {codigo} ya existe en la base de datos.")
    except pymongo.errors.WriteError as error_esquema:
        print(f"Error de validación de esquema: {error_esquema}")


def agregar_consumible():
    print("\n--- Agregar Nuevo Consumible o EPP ---")
    codigo = pedir_codigo("Ingrese el Código único (Ej. CONS-2001): ")
    descripcion = input("Ingrese la descripción (Ej. Casco de Seguridad): ").strip()
    stock = pedir_entero("Ingrese el stock inicial: ", minimo=0)
    alerta = pedir_entero("Ingrese el stock mínimo para alertas: ", minimo=0)

    nuevo_documento = {
        "_id": codigo,
        "tipo_activo": "Consumible",
        "descripcion": descripcion,
        "stock_actual": stock,
        "alerta_minima": alerta,
    }

    try:
        inventario.insert_one(nuevo_documento)
        print(f"Éxito: Consumible {codigo} agregado correctamente con {stock} unidades.")
    except pymongo.errors.DuplicateKeyError:
        print(f"Error: El código {codigo} ya existe en el sistema.")
    except pymongo.errors.WriteError as error_esquema:
        print(f"Error de validación de esquema: {error_esquema}")


def agregar_material_trazable():
    """Tercer tipo de activo definido en el esquema pero sin CRUD en la versión original."""
    print("\n--- Agregar Nuevo Material Trazable (con número de serie/lote) ---")
    codigo = pedir_codigo("Ingrese el Código único (Ej. MATR-3001): ")
    descripcion = input("Ingrese la descripción (Ej. Rollo de cable 5x10mm): ").strip()
    numero_serie = input("Ingrese el número de serie o lote: ").strip()
    unidad_medida = input("Ingrese la unidad de medida (Ej. metros, unidades, kg): ").strip()
    cantidad = pedir_entero("Ingrese la cantidad disponible: ", minimo=0)

    nuevo_documento = {
        "_id": codigo,
        "tipo_activo": "Material Trazable",
        "descripcion": descripcion,
        "numero_serie": numero_serie,
        "unidad_medida": unidad_medida,
        "cantidad_disponible": cantidad,
        "trazabilidad": [],  # historial de movimientos específicos del lote
    }

    try:
        inventario.insert_one(nuevo_documento)
        print(f"Éxito: Material trazable {codigo} agregado correctamente.")
    except pymongo.errors.DuplicateKeyError:
        print(f"Error: El código {codigo} ya existe en el sistema.")
    except pymongo.errors.WriteError as error_esquema:
        print(f"Error de validación de esquema: {error_esquema}")


def agregar_usuario():
    """CRUD de usuarios (RBAC) definido en el esquema pero ausente en el CRUD original."""
    print("\n--- Agregar Nuevo Usuario (Control de Acceso RBAC) ---")
    rut = pedir_rut("Ingrese el RUT del usuario (Ej. 15.123.456-7): ")
    nombre = input("Ingrese el nombre completo: ").strip()

    print("Roles: 1. Pañolero | 2. Jefe de Obra | 3. Prevencionista | 4. Administrador")
    roles = {"1": "Pañolero", "2": "Jefe de Obra", "3": "Prevencionista", "4": "Administrador"}
    opcion = pedir_opcion("Seleccione el rol (1-4): ", roles.keys())

    nuevo_documento = {
        "_id": rut,
        "nombre": nombre,
        "rol": roles[opcion],
        "activo": True,
    }

    try:
        usuarios.insert_one(nuevo_documento)
        print(f"Éxito: Usuario {nombre} ({roles[opcion]}) agregado correctamente.")
    except pymongo.errors.DuplicateKeyError:
        print(f"Error: Ya existe un usuario registrado con el RUT {rut}.")
    except pymongo.errors.WriteError as error_esquema:
        print(f"Error de validación de esquema: {error_esquema}")


def agregar_transaccion_salida():
    """
    Registra una entrega (Salida) y, a diferencia de la versión original,
    valida y descuenta el inventario en consecuencia:
      - Consumible: exige stock suficiente y lo descuenta.
      - Herramienta: exige que esté en "Bodega" y la pasa a "En Terreno".
    """
    print("\n--- Registrar Nueva Entrega (Salida) ---")
    rut_trabajador = pedir_rut("Ingrese RUT del trabajador (Ej. 15.123.456-7): ")
    rut_panolero = pedir_rut("Ingrese RUT del pañolero responsable: ")
    item_id = pedir_codigo("Ingrese el código del ítem a entregar: ")

    activo = inventario.find_one({"_id": item_id})
    if not activo:
        print(f"Error: El ítem {item_id} no existe en el inventario.")
        return

    cantidad = pedir_entero("Ingrese la cantidad: ", minimo=1)

    if activo["tipo_activo"] == "Consumible":
        if activo.get("stock_actual", 0) < cantidad:
            print(f"Error: Stock insuficiente. Disponible: {activo.get('stock_actual', 0)}.")
            return
        inventario.update_one({"_id": item_id}, {"$inc": {"stock_actual": -cantidad}})

    elif activo["tipo_activo"] == "Herramienta":
        if activo.get("estado") != "Bodega":
            print(f"Error: La herramienta {item_id} no está disponible (estado actual: {activo.get('estado')}).")
            return
        if cantidad != 1:
            print("Nota: las herramientas se entregan de a una unidad; se ajusta la cantidad a 1.")
            cantidad = 1
        inventario.update_one(
            {"_id": item_id},
            {"$set": {"estado": "En Terreno", "asignado_a": rut_trabajador}},
        )

    elif activo["tipo_activo"] == "Material Trazable":
        if activo.get("cantidad_disponible", 0) < cantidad:
            print(f"Error: Cantidad insuficiente. Disponible: {activo.get('cantidad_disponible', 0)}.")
            return
        inventario.update_one({"_id": item_id}, {"$inc": {"cantidad_disponible": -cantidad}})

    nueva_transaccion = {
        "fecha_hora": datetime.now(timezone.utc),
        "tipo_movimiento": "Salida",
        "trabajador_rut": rut_trabajador,
        "panolero_rut": rut_panolero,
        "items": [{"item_id": item_id, "cantidad": cantidad}],
    }

    resultado = transacciones.insert_one(nueva_transaccion)
    print(f"Éxito: Transacción registrada bajo el ID: {resultado.inserted_id}")


def agregar_transaccion_entrada():
    """
    Registra una devolución (Entrada). Faltaba por completo en la versión
    original: sin esto, ninguna herramienta entregada podía volver a
    quedar disponible ni un consumible sobrante podía reingresar a stock.
    """
    print("\n--- Registrar Nueva Devolución (Entrada) ---")
    rut_trabajador = pedir_rut("Ingrese RUT del trabajador que devuelve (Ej. 15.123.456-7): ")
    rut_panolero = pedir_rut("Ingrese RUT del pañolero que recibe: ")
    item_id = pedir_codigo("Ingrese el código del ítem devuelto: ")

    activo = inventario.find_one({"_id": item_id})
    if not activo:
        print(f"Error: El ítem {item_id} no existe en el inventario.")
        return

    cantidad = pedir_entero("Ingrese la cantidad devuelta: ", minimo=1)

    if activo["tipo_activo"] == "Consumible":
        inventario.update_one({"_id": item_id}, {"$inc": {"stock_actual": cantidad}})

    elif activo["tipo_activo"] == "Herramienta":
        if cantidad != 1:
            print("Nota: las herramientas se devuelven de a una unidad; se ajusta la cantidad a 1.")
            cantidad = 1
        print("Estado de la herramienta al devolver: 1. Bodega | 2. En Reparación")
        opcion = pedir_opcion("Seleccione (1-2): ", {"1", "2"})
        nuevo_estado = "Bodega" if opcion == "1" else "En Reparación"
        inventario.update_one(
            {"_id": item_id},
            {"$set": {"estado": nuevo_estado}, "$unset": {"asignado_a": ""}},
        )

    elif activo["tipo_activo"] == "Material Trazable":
        inventario.update_one({"_id": item_id}, {"$inc": {"cantidad_disponible": cantidad}})

    nueva_transaccion = {
        "fecha_hora": datetime.now(timezone.utc),
        "tipo_movimiento": "Entrada",
        "trabajador_rut": rut_trabajador,
        "panolero_rut": rut_panolero,
        "items": [{"item_id": item_id, "cantidad": cantidad}],
    }

    resultado = transacciones.insert_one(nueva_transaccion)
    print(f"Éxito: Devolución registrada bajo el ID: {resultado.inserted_id}")


# ==========================================
# 2. FUNCIONES DE ELIMINACIÓN (DELETE)
# ==========================================

def eliminar_activo_inventario():
    print("\n--- Eliminar un Activo del Inventario ---")
    codigo = pedir_codigo("Ingrese el Código exacto del ítem a eliminar (Ej. HERR-1001): ")

    confirmacion = input(f"¿Confirma eliminar el activo {codigo}? (s/n): ").strip().lower()
    if confirmacion != "s":
        print("Operación cancelada.")
        return

    resultado = inventario.delete_one({"_id": codigo})
    if resultado.deleted_count > 0:
        print(f"Éxito: El activo {codigo} ha sido eliminado de la base de datos.")
    else:
        print(f"Error: No se encontró ningún activo con el código {codigo}.")


def eliminar_transacciones_trabajador():
    print("\n--- Eliminar TODAS las transacciones de un Trabajador ---")
    print("Advertencia: Esta acción borrará el historial de entregas del trabajador ingresado.")
    rut_trabajador = pedir_rut("Ingrese el RUT del trabajador a limpiar (Ej. 15.123.456-7): ")

    confirmacion = input(f"¿Está seguro de eliminar los registros de {rut_trabajador}? (s/n): ").strip().lower()
    if confirmacion == "s":
        resultado = transacciones.delete_many({"trabajador_rut": rut_trabajador})
        print(f"Éxito: Se eliminaron {resultado.deleted_count} transacciones del trabajador {rut_trabajador}.")
    else:
        print("Operación cancelada.")


def eliminar_usuario():
    print("\n--- Eliminar Usuario del Sistema ---")
    rut = pedir_rut("Ingrese el RUT del usuario a eliminar (Ej. 15.123.456-7): ")

    confirmacion = input(f"¿Confirma eliminar al usuario {rut}? (s/n): ").strip().lower()
    if confirmacion != "s":
        print("Operación cancelada.")
        return

    resultado = usuarios.delete_one({"_id": rut})
    if resultado.deleted_count > 0:
        print(f"Éxito: El usuario {rut} ha sido eliminado.")
    else:
        print(f"Error: No se encontró ningún usuario con el RUT {rut}.")


# ==========================================
# 3. MENÚ INTERACTIVO CLI
# ==========================================
def menu():
    opciones = {
        "1": agregar_herramienta,
        "2": agregar_consumible,
        "3": agregar_material_trazable,
        "4": agregar_transaccion_salida,
        "5": agregar_transaccion_entrada,
        "6": agregar_usuario,
        "7": eliminar_activo_inventario,
        "8": eliminar_transacciones_trabajador,
        "9": eliminar_usuario,
    }

    while True:
        print("\n==========================================")
        print("   MENÚ DE OPCIONES: AGREGAR Y ELIMINAR")
        print("==========================================")
        print("1. Insert: Agregar nueva herramienta")
        print("2. Insert: Agregar nuevo consumible")
        print("3. Insert: Agregar nuevo material trazable")
        print("4. Insert: Registrar transacción de Salida")
        print("5. Insert: Registrar transacción de Entrada (devolución)")
        print("6. Insert: Agregar nuevo usuario (RBAC)")
        print("7. Delete: Eliminar un activo del inventario por ID")
        print("8. Delete: Eliminar historial de transacciones de un trabajador")
        print("9. Delete: Eliminar un usuario del sistema")
        print("10. Salir")

        opcion = input("\nSeleccione una opción (1-10): ").strip()

        if opcion == "10":
            print("Cerrando conexión y saliendo del programa...")
            cliente.close()
            break
        elif opcion in opciones:
            try:
                opciones[opcion]()
            except pymongo.errors.PyMongoError as error_bd:
                print(f"Ocurrió un error al comunicarse con la base de datos: {error_bd}")
        else:
            print("Opción no válida, intente de nuevo.")


if __name__ == "__main__":
    menu()
