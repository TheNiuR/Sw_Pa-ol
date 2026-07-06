"""
Módulo de Consultas (READ) - Sistema de Control de Pañol
=============================================================
Cambios respecto a la versión original:
  - Conexión centralizada en conexion.py.
  - mostrar_transacciones_rango_fecha y mostrar_descripcion_regex ya no
    tienen valores fijos "quemados" en el código; ahora se piden por
    teclado, volviendo la consulta realmente reutilizable.
  - Se agregó mostrar_stock_bajo_alerta: una consulta de negocio clave
    (qué consumibles están por debajo de su stock mínimo) que no existía
    y que es fundamental para la operación real de un pañol.
  - Se agregó mostrar_usuarios y mostrar_herramientas_por_estado.
"""
from datetime import datetime, timezone

from conexion import conectar
from validaciones import pedir_opcion, pedir_rut

cliente, db, inventario, transacciones, usuarios = conectar("Sistema del Pañol")


# ==========================================
# 1. CONSULTAS SOBRE INVENTARIO
# ==========================================

def mostrar_todo_inventario():
    print("\n--- Muestra todo el inventario registrado ---")
    total = 0
    for documento in inventario.find():
        total += 1
        estado_o_stock = documento.get(
            "estado", documento.get("stock_actual", documento.get("cantidad_disponible", "N/A"))
        )
        print(f" Código: {documento.get('_id')} | Tipo: {documento.get('tipo_activo')} | "
              f"Descripción: {documento.get('descripcion')} | Estado/Stock: {estado_o_stock}")
    if total == 0:
        print("No hay activos registrados en el inventario.")


def mostrar_herramientas_por_estado():
    print("\n--- Buscar Herramientas por Estado ---")
    print("Estados: 1. Bodega | 2. En Terreno | 3. En Reparación | 4. Dado de Baja")
    estados = {"1": "Bodega", "2": "En Terreno", "3": "En Reparación", "4": "Dado de Baja"}
    opcion = pedir_opcion("Seleccione el estado a consultar (1-4): ", estados.keys())
    estado = estados[opcion]

    encontrados = 0
    for documento in inventario.find({"tipo_activo": "Herramienta", "estado": estado}):
        encontrados += 1
        asignado = documento.get("asignado_a", "-")
        print(f" {documento['_id']} | {documento.get('descripcion')} | Asignado a: {asignado}")
    if encontrados == 0:
        print(f"No hay herramientas en estado '{estado}'.")


def mostrar_stock_bajo_alerta():
    """Consulta de negocio clave: qué consumibles necesitan reposición."""
    print("\n--- Consumibles Bajo el Stock Mínimo de Alerta ---")
    filtro = {
        "tipo_activo": "Consumible",
        "$expr": {"$lte": ["$stock_actual", "$alerta_minima"]},
    }
    encontrados = 0
    for documento in inventario.find(filtro):
        encontrados += 1
        print(f" {documento['_id']} | {documento.get('descripcion')} | "
              f"Stock actual: {documento.get('stock_actual')} | Mínimo: {documento.get('alerta_minima')}")
    if encontrados == 0:
        print("Todos los consumibles están dentro de su nivel mínimo de stock.")


def mostrar_descripcion_regex():
    print("\n--- Buscar Activos por Coincidencia en la Descripción ---")
    termino = input("Ingrese el texto a buscar en la descripción (Ej. Rotomartillo): ").strip()

    encontrados = 0
    for documento in inventario.find({"descripcion": {"$regex": termino, "$options": "i"}}):
        encontrados += 1
        print(f" {documento['_id']} | {documento['tipo_activo']} | {documento['descripcion']} | "
              f"Marca: {documento.get('marca', 'N/A')}")
    if encontrados == 0:
        print(f"No se encontraron activos cuya descripción contenga '{termino}'.")


# ==========================================
# 2. CONSULTAS SOBRE TRANSACCIONES
# ==========================================

def mostrar_transacciones_rango_fecha():
    print("\n--- Transacciones en un Rango de Fechas ---")
    try:
        fecha_inicio_str = input("Fecha de inicio (AAAA-MM-DD): ").strip()
        fecha_fin_str = input("Fecha de término (AAAA-MM-DD): ").strip()
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    except ValueError:
        print("Error: Formato de fecha inválido. Use AAAA-MM-DD.")
        return

    filtro = {"fecha_hora": {"$gte": fecha_inicio, "$lte": fecha_fin}}
    encontrados = 0
    for documento in transacciones.find(filtro):
        encontrados += 1
        print(f" Fecha: {documento['fecha_hora']} | Tipo: {documento['tipo_movimiento']} | "
              f"Trabajador RUT: {documento['trabajador_rut']} | Ítems: {len(documento['items'])}")
    if encontrados == 0:
        print("No se encontraron transacciones en el rango indicado.")


def mostrar_lookup_union():
    print("\n--- Unión de 2 colecciones (Lookup): transacciones con detalle de ítems ---")
    pipeline = [
        {
            "$lookup": {
                "from": "inventario",
                "localField": "items.item_id",
                "foreignField": "_id",
                "as": "detalle_activos",
            }
        },
        {
            "$project": {
                "Fecha": "$fecha_hora",
                "Movimiento": "$tipo_movimiento",
                "Trabajador": "$trabajador_rut",
                "Activos_Involucrados": "$detalle_activos.descripcion",
                "_id": 0,
            }
        },
    ]

    resultados = list(transacciones.aggregate(pipeline))
    if not resultados:
        print("No hay transacciones registradas.")
    for resultado in resultados:
        print(resultado)


def mostrar_lookup_union_salidas():
    print("\n--- Unión de 2 colecciones (Lookup): solo movimientos de 'Salida' ---")
    pipeline = [
        {
            "$lookup": {
                "from": "inventario",
                "localField": "items.item_id",
                "foreignField": "_id",
                "as": "detalle_activos",
            }
        },
        {"$match": {"tipo_movimiento": "Salida"}},
        {
            "$project": {
                "Fecha": "$fecha_hora",
                "Movimiento": "$tipo_movimiento",
                "Trabajador": "$trabajador_rut",
                "Activos_Involucrados": "$detalle_activos.descripcion",
                "_id": 0,
            }
        },
    ]

    resultados = list(transacciones.aggregate(pipeline))
    if not resultados:
        print("No hay transacciones de tipo 'Salida'.")
    for resultado in resultados:
        print(resultado)


def mostrar_lookup_union_rut():
    print("\n--- Unión de 2 colecciones (Lookup) para un trabajador específico ---")
    rut_trabajador = pedir_rut("Ingrese el RUT del trabajador (Ej. 15.123.456-7): ")

    print("Filtrar por tipo de movimiento: 1. Salida | 2. Entrada | 3. Todos")
    tipos = {"1": "Salida", "2": "Entrada", "3": None}
    opcion = pedir_opcion("Seleccione (1-3): ", tipos.keys())
    tipo_movimiento = tipos[opcion]

    filtro_match = {"trabajador_rut": rut_trabajador}
    if tipo_movimiento:
        filtro_match["tipo_movimiento"] = tipo_movimiento

    pipeline = [
        {
            "$lookup": {
                "from": "inventario",
                "localField": "items.item_id",
                "foreignField": "_id",
                "as": "detalle_activos",
            }
        },
        {"$match": filtro_match},
        {
            "$project": {
                "Fecha": "$fecha_hora",
                "Movimiento": "$tipo_movimiento",
                "Activos_Involucrados": "$detalle_activos.descripcion",
                "_id": 0,
            }
        },
    ]

    resultados = list(transacciones.aggregate(pipeline))
    if not resultados:
        print(f"No se encontraron transacciones para el trabajador {rut_trabajador}.")
    for resultado in resultados:
        print(resultado)


def herramientas_mayor_mantenimiento():
    print("\n--- Top 3 Herramientas con más registros de mantenimiento ---")
    pipeline = [
        {"$match": {"historial_mantenimiento": {"$exists": True, "$not": {"$size": 0}}}},
        {"$addFields": {"cantidad_mantenimientos": {"$size": "$historial_mantenimiento"}}},
        {
            "$project": {
                "codigo": "$_id",
                "descripcion": 1,
                "cantidad_mantenimientos": 1,
                "_id": 0,
            }
        },
        {"$sort": {"cantidad_mantenimientos": -1}},
        {"$limit": 3},
    ]

    resultados = list(inventario.aggregate(pipeline))
    if not resultados:
        print("No hay herramientas con registros de mantenimiento.")
    else:
        for resultado in resultados:
            print(f"Código: {resultado['codigo']} | Descripción: {resultado['descripcion']} | "
                  f"Mantenimientos realizados: {resultado['cantidad_mantenimientos']}")


# ==========================================
# 3. CONSULTAS SOBRE USUARIOS
# ==========================================

def mostrar_usuarios():
    print("\n--- Listado de Usuarios del Sistema (RBAC) ---")
    encontrados = 0
    for documento in usuarios.find():
        encontrados += 1
        estado = "Activo" if documento.get("activo") else "Inactivo"
        print(f" RUT: {documento['_id']} | Nombre: {documento.get('nombre')} | "
              f"Rol: {documento.get('rol')} | Estado: {estado}")
    if encontrados == 0:
        print("No hay usuarios registrados.")


# ==========================================
# 4. MENÚ INTERACTIVO CLI
# ==========================================
def menu():
    opciones = {
        "1": mostrar_todo_inventario,
        "2": mostrar_transacciones_rango_fecha,
        "3": mostrar_descripcion_regex,
        "4": mostrar_lookup_union,
        "5": mostrar_lookup_union_salidas,
        "6": mostrar_lookup_union_rut,
        "7": herramientas_mayor_mantenimiento,
        "8": mostrar_stock_bajo_alerta,
        "9": mostrar_herramientas_por_estado,
        "10": mostrar_usuarios,
    }

    while True:
        print("\n==========================================")
        print("      MENÚ DE OPCIONES - PAÑOL OBRA")
        print("==========================================")
        print("1. Mostrar todo el inventario (Find general)")
        print("2. Filtros (Find): Transacciones por rango de fechas")
        print("3. Exp. Regulares (Regex): Buscar por texto en descripción")
        print("4. Colecciones (Lookup): Ver transacciones y detalle de ítems")
        print("5. Colecciones (Lookup): Mostrar solo entregas a terreno (Salida)")
        print("6. Colecciones (Lookup): Mostrar movimientos de un trabajador")
        print("7. Aggregate: Top 3 herramientas con más mantenimientos")
        print("8. Aggregate: Consumibles bajo el stock mínimo de alerta")
        print("9. Find: Herramientas filtradas por estado")
        print("10. Find: Listado de usuarios del sistema")
        print("11. Salir")

        opcion = input("\nSeleccione una opción (1-11): ").strip()

        if opcion == "11":
            print("Cerrando conexión y saliendo del sistema...")
            cliente.close()
            break
        elif opcion in opciones:
            opciones[opcion]()
        else:
            print("Opción no válida, intente de nuevo.")


if __name__ == "__main__":
    menu()
