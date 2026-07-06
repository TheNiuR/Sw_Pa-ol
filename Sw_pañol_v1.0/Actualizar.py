"""
Módulo de Actualizaciones (UPDATE) - Sistema de Control de Pañol
====================================================================
Cambios respecto a la versión original:
  - Conexión y validaciones centralizadas en conexion.py / validaciones.py.
  - ajustar_stock_consumible ahora evita dejar el stock en negativo:
    la resta se hace de forma atómica y condicionada con find_one_and_update
    en vez de restar a ciegas con $inc.
  - Se agregó actualización de usuarios (cambiar rol / activar-desactivar),
    inexistente en la versión original pese a que el esquema define RBAC.
  - Se agregó anular_transaccion: revierte el efecto en inventario de una
    transacción (repone stock o vuelve la herramienta a Bodega) y marca
    la transacción como "Anulado" en vez de borrarla, preservando el
    historial para auditoría.
"""
import pymongo.errors

from conexion import conectar
from validaciones import pedir_codigo, pedir_entero, pedir_opcion, pedir_rut

cliente, db, inventario, transacciones, usuarios = conectar("Módulo de Actualizaciones del Pañol")


# ==========================================
# 1. FUNCIONES DE ACTUALIZACIÓN DE INVENTARIO
# ==========================================

def actualizar_estado_herramienta():
    """Modifica el estado actual de una herramienta usando $set."""
    print("\n--- Actualizar Estado de Herramienta ---")
    codigo = pedir_codigo("Ingrese el Código de la herramienta (Ej. HERR-5049): ")

    print("Estados: 1. Bodega | 2. En Terreno | 3. En Reparación | 4. Dado de Baja")
    estados = {"1": "Bodega", "2": "En Terreno", "3": "En Reparación", "4": "Dado de Baja"}
    opcion = pedir_opcion("Seleccione el nuevo estado (1-4): ", estados.keys())
    nuevo_estado = estados[opcion]

    actualizacion = {"$set": {"estado": nuevo_estado}}
    # Si vuelve a Bodega, ya no está asignada a nadie
    if nuevo_estado == "Bodega":
        actualizacion["$unset"] = {"asignado_a": ""}

    resultado = inventario.update_one(
        {"_id": codigo, "tipo_activo": "Herramienta"}, actualizacion
    )

    if resultado.matched_count > 0:
        print(f"Éxito: El estado de {codigo} se actualizó a '{nuevo_estado}'.")
    else:
        print(f"Error: No se encontró ninguna herramienta con el código {codigo}.")


def registrar_mantenimiento():
    """Agrega un nuevo registro al array de historial usando $push."""
    from datetime import datetime, timezone

    print("\n--- Registrar Mantenimiento de Equipo ---")
    codigo = pedir_codigo("Ingrese el Código de la herramienta: ")
    accion_realizada = input("Describa el mantenimiento (Ej. Cambio de rodamientos): ").strip()

    nuevo_registro = {"fecha": datetime.now(timezone.utc), "accion": accion_realizada}
    actualizacion = {
        "$push": {"historial_mantenimiento": nuevo_registro},
        "$set": {"estado": "En Reparación"},
    }

    resultado = inventario.update_one(
        {"_id": codigo, "tipo_activo": "Herramienta"}, actualizacion
    )

    if resultado.matched_count > 0:
        print(f"Éxito: Mantenimiento registrado en el historial de {codigo} (estado: En Reparación).")
    else:
        print("Error: Herramienta no encontrada.")


def ajustar_stock_consumible():
    """
    Suma o resta cantidades al stock actual usando $inc, evitando
    que el stock quede en negativo cuando se resta más de lo disponible.
    """
    print("\n--- Ajustar Stock de Consumibles / EPP ---")
    codigo = pedir_codigo("Ingrese el Código del consumible (Ej. CONS-9921): ")
    cantidad = pedir_entero("Ingrese la cantidad a sumar (use negativo para restar): ")

    filtro = {"_id": codigo, "tipo_activo": "Consumible"}

    if cantidad < 0:
        # Solo permite la resta si hay stock suficiente (operación atómica)
        filtro["stock_actual"] = {"$gte": -cantidad}

    resultado = inventario.find_one_and_update(
        filtro, {"$inc": {"stock_actual": cantidad}}, return_document=True
    )

    if resultado:
        print(f"Éxito: El stock de {codigo} ha sido ajustado en {cantidad} unidades. "
              f"Stock actual: {resultado['stock_actual']}.")
    else:
        existe = inventario.find_one({"_id": codigo, "tipo_activo": "Consumible"})
        if existe is None:
            print("Error: Consumible no encontrado o el código pertenece a otro tipo de activo.")
        else:
            print(f"Error: Stock insuficiente. Disponible: {existe.get('stock_actual', 0)}.")


def agregar_atributo_dinamico():
    """Aprovecha la flexibilidad NoSQL para agregar un campo que antes no existía."""
    print("\n--- Agregar Nuevo Atributo Dinámico (Flexibilidad NoSQL) ---")
    codigo = pedir_codigo("Ingrese el Código del activo: ")
    nombre_campo = input("Nombre del nuevo atributo (Ej. certificacion_nacional): ").strip()
    valor_campo = input(f"Ingrese el valor para '{nombre_campo}': ").strip()

    campos_protegidos = {"_id", "tipo_activo", "descripcion"}
    if nombre_campo in campos_protegidos:
        print(f"Error: '{nombre_campo}' es un campo protegido y no puede sobrescribirse por esta vía.")
        return

    resultado = inventario.update_one({"_id": codigo}, {"$set": {nombre_campo: valor_campo}})

    if resultado.matched_count > 0:
        print(f"Éxito: Atributo '{nombre_campo}' agregado al documento {codigo}.")
    else:
        print("Error: Activo no encontrado.")


# ==========================================
# 2. FUNCIONES DE ACTUALIZACIÓN DE USUARIOS (RBAC)
# ==========================================

def actualizar_rol_usuario():
    print("\n--- Actualizar Rol de Usuario ---")
    rut = pedir_rut("Ingrese el RUT del usuario (Ej. 15.123.456-7): ")

    print("Roles: 1. Pañolero | 2. Jefe de Obra | 3. Prevencionista | 4. Administrador")
    roles = {"1": "Pañolero", "2": "Jefe de Obra", "3": "Prevencionista", "4": "Administrador"}
    opcion = pedir_opcion("Seleccione el nuevo rol (1-4): ", roles.keys())

    resultado = usuarios.update_one({"_id": rut}, {"$set": {"rol": roles[opcion]}})

    if resultado.matched_count > 0:
        print(f"Éxito: El rol de {rut} se actualizó a '{roles[opcion]}'.")
    else:
        print(f"Error: No se encontró ningún usuario con el RUT {rut}.")


def activar_desactivar_usuario():
    print("\n--- Activar / Desactivar Usuario ---")
    rut = pedir_rut("Ingrese el RUT del usuario (Ej. 15.123.456-7): ")

    usuario = usuarios.find_one({"_id": rut})
    if not usuario:
        print(f"Error: No se encontró ningún usuario con el RUT {rut}.")
        return

    nuevo_estado = not usuario.get("activo", True)
    usuarios.update_one({"_id": rut}, {"$set": {"activo": nuevo_estado}})
    estado_texto = "activado" if nuevo_estado else "desactivado"
    print(f"Éxito: El usuario {rut} ha sido {estado_texto}.")


# ==========================================
# 3. ANULACIÓN DE TRANSACCIONES (con reversa de inventario)
# ==========================================

def anular_transaccion():
    """
    Marca una transacción como 'Anulado' y revierte su efecto en el
    inventario (repone stock si fue Salida, o lo vuelve a descontar si
    fue Entrada). Se mantiene el registro en vez de borrarlo, para
    conservar trazabilidad y auditoría.
    """
    print("\n--- Anular Transacción ---")
    id_transaccion = input("Ingrese el ID (_id) de la transacción a anular: ").strip()

    try:
        from bson import ObjectId
        filtro_id = ObjectId(id_transaccion)
    except Exception:
        print("Error: El ID ingresado no tiene un formato válido de ObjectId.")
        return

    transaccion = transacciones.find_one({"_id": filtro_id})
    if not transaccion:
        print("Error: No se encontró ninguna transacción con ese ID.")
        return

    if transaccion.get("tipo_movimiento") == "Anulado":
        print("Esta transacción ya se encuentra anulada.")
        return

    confirmacion = input("¿Confirma la anulación y reversión de esta transacción? (s/n): ").strip().lower()
    if confirmacion != "s":
        print("Operación cancelada.")
        return

    signo_reversa = -1 if transaccion["tipo_movimiento"] == "Salida" else 1

    for item in transaccion.get("items", []):
        activo = inventario.find_one({"_id": item["item_id"]})
        if not activo:
            continue  # el activo pudo haber sido eliminado desde entonces

        if activo["tipo_activo"] == "Consumible":
            inventario.update_one(
                {"_id": item["item_id"]},
                {"$inc": {"stock_actual": signo_reversa * item["cantidad"]}},
            )
        elif activo["tipo_activo"] == "Material Trazable":
            inventario.update_one(
                {"_id": item["item_id"]},
                {"$inc": {"cantidad_disponible": signo_reversa * item["cantidad"]}},
            )
        elif activo["tipo_activo"] == "Herramienta":
            # Si se anula una Salida, la herramienta vuelve a Bodega.
            # Si se anula una Entrada, vuelve a quedar En Terreno.
            estado_reverso = "Bodega" if transaccion["tipo_movimiento"] == "Salida" else "En Terreno"
            inventario.update_one({"_id": item["item_id"]}, {"$set": {"estado": estado_reverso}})

    transacciones.update_one({"_id": filtro_id}, {"$set": {"tipo_movimiento": "Anulado"}})
    print("Éxito: Transacción anulada y efectos revertidos en el inventario.")


# ==========================================
# 4. MENÚ INTERACTIVO CLI
# ==========================================
def menu():
    opciones = {
        "1": actualizar_estado_herramienta,
        "2": registrar_mantenimiento,
        "3": ajustar_stock_consumible,
        "4": agregar_atributo_dinamico,
        "5": actualizar_rol_usuario,
        "6": activar_desactivar_usuario,
        "7": anular_transaccion,
    }

    while True:
        print("\n==========================================")
        print("    MENÚ DE ACTUALIZACIONES (UPDATE)")
        print("==========================================")
        print("1. Modificar estado de herramienta ($set)")
        print("2. Registrar mantenimiento técnico ($push)")
        print("3. Ajustar stock de consumibles ($inc, sin negativos)")
        print("4. Agregar un atributo dinámico nuevo ($set)")
        print("5. Actualizar rol de un usuario (RBAC)")
        print("6. Activar / desactivar un usuario")
        print("7. Anular una transacción (revierte inventario)")
        print("8. Salir")

        opcion = input("\nSeleccione una opción (1-8): ").strip()

        if opcion == "8":
            print("Cerrando conexión y saliendo del módulo...")
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
