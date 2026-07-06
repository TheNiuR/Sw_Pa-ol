import sys
import pymongo
import pymongo.errors

# ==========================================
# PARÁMETROS DE CONEXIÓN
# ==========================================
MONGO_HOST = "localhost"
MONGO_PUERTO = "27017"
MONGO_TIEMPO_MS = 3000  # tiempo máximo de espera para seleccionar servidor

MONGO_URL = f"mongodb://{MONGO_HOST}:{MONGO_PUERTO}/"
MONGO_BD = "control_panol"

COL_INVENTARIO = "inventario"
COL_TRANSACCIONES = "transacciones"
COL_USUARIOS = "usuarios"


def conectar(nombre_modulo="Sistema de Pañol"):
    """
    Establece la conexión con MongoDB y valida que el servidor
    esté realmente disponible (mediante un comando 'ping'), en vez
    de asumir que la conexión funciona con solo instanciar el cliente.

    Retorna una tupla:
        (cliente, db, inventario, transacciones, usuarios)

    Si la conexión falla, informa el error y finaliza el programa de
    forma controlada (evita que el resto del script truene con
    NameError al usar variables que nunca llegaron a crearse).
    """
    try:
        cliente = pymongo.MongoClient(
            MONGO_URL, serverSelectionTimeoutMS=MONGO_TIEMPO_MS
        )
        # 'ping' obliga a Mongo a confirmar la conexión de inmediato,
        # en lugar de esperar a la primera operación real para fallar.
        cliente.admin.command("ping")

        db = cliente[MONGO_BD]
        inventario = db[COL_INVENTARIO]
        transacciones = db[COL_TRANSACCIONES]
        usuarios = db[COL_USUARIOS]

        print(f"Conexión exitosa - {nombre_modulo}\n")
        return cliente, db, inventario, transacciones, usuarios

    except pymongo.errors.ServerSelectionTimeoutError as error_tiempo:
        print(f"Tiempo excedido al conectar con MongoDB: {error_tiempo}")
    except pymongo.errors.ConnectionFailure as error_conexion:
        print(f"Fallo al conectarse a MongoDB: {error_conexion}")
    except Exception as error_general:
        print(f"Error inesperado al conectar con MongoDB: {error_general}")

    sys.exit("No fue posible iniciar el módulo: revise que MongoDB esté activo.")
