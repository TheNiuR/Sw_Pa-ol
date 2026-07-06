"""
Validaciones y utilidades de entrada - Sistema de Control de Pañol
=====================================================================
Funciones reutilizables para validar formatos (RUT, código de activo)
y para pedir datos numéricos sin que el programa se caiga por un
ValueError cuando el usuario escribe texto en vez de números.
"""
import re

# RUT chileno con puntos y guión, ej: 15.123.456-7 o 9.876.543-K
PATRON_RUT = re.compile(r"^\d{1,2}\.\d{3}\.\d{3}-[0-9Kk]$")

# Código de activo tipo PREFIJO-NUMERO, ej: HERR-1001, CONS-2001
PATRON_CODIGO = re.compile(r"^[A-Za-z]+-\d+$")


def rut_valido(rut: str) -> bool:
    """Valida el formato de un RUT chileno (NN.NNN.NNN-D)."""
    return bool(PATRON_RUT.match(rut.strip()))


def codigo_valido(codigo: str) -> bool:
    """Valida el formato de un código de activo (PREFIJO-NUMERO)."""
    return bool(PATRON_CODIGO.match(codigo.strip()))


def pedir_rut(mensaje: str) -> str:
    """Solicita un RUT y reintenta hasta que el formato sea válido."""
    while True:
        rut = input(mensaje).strip()
        if rut_valido(rut):
            return rut
        print("Formato de RUT inválido. Use el formato NN.NNN.NNN-D (ej. 15.123.456-7).")


def pedir_codigo(mensaje: str) -> str:
    """Solicita un código de activo y reintenta hasta que el formato sea válido."""
    while True:
        codigo = input(mensaje).strip().upper()
        if codigo_valido(codigo):
            return codigo
        print("Formato de código inválido. Use el formato PREFIJO-NUMERO (ej. HERR-1001).")


def pedir_entero(mensaje: str, minimo: int = None) -> int:
    """Solicita un entero, reintentando si el valor no es válido o es menor al mínimo."""
    while True:
        valor = input(mensaje).strip()
        try:
            numero = int(valor)
        except ValueError:
            print("Debe ingresar un número entero válido.")
            continue
        if minimo is not None and numero < minimo:
            print(f"El valor debe ser mayor o igual a {minimo}.")
            continue
        return numero


def pedir_opcion(mensaje: str, opciones_validas) -> str:
    """Solicita una opción de menú, reintentando si no pertenece a las opciones válidas."""
    while True:
        opcion = input(mensaje).strip()
        if opcion in opciones_validas:
            return opcion
        print("Opción no válida, intente de nuevo.")
