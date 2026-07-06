import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
import pymongo.errors
from validaciones import rut_valido, codigo_valido

class AgregarEliminarFrame(ttk.Frame):
    def __init__(self, parent, db_refs):
        super().__init__(parent)
        # Desempaquetar la conexión centralizada inyectada desde main.py
        self.cliente, self.db, self.inventario, self.transacciones, self.usuarios = db_refs
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- HEADER ---
        header = tk.Label(self, text="Módulo de Altas, Bajas y Transacciones", 
                          font=("Arial", 16, "bold"), bg="#f8fafc")
        header.pack(pady=15)

        # --- PANEL DE SELECCIÓN DE OPERACIÓN ---
        selector_frame = ttk.Frame(self)
        selector_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(selector_frame, text="Seleccione Operación:").pack(side=tk.LEFT, padx=5)
        
        self.combo_operacion = ttk.Combobox(selector_frame, width=50, state="readonly")
        self.combo_operacion['values'] = [
            "Agregar Nueva Herramienta",
            "Agregar Nuevo Consumible/EPP",
            "Agregar Nuevo Material Trazable",
            "Agregar Nuevo Usuario (RBAC)",
            "Registrar Transacción de Salida (Entrega)",
            "Registrar Transacción de Entrada (Devolución)",
            "Eliminar un Activo del Inventario por Código",
            "Eliminar Historial de Transacciones de un Trabajador",
            "Eliminar un Usuario del Sistema"
        ]
        self.combo_operacion.pack(side=tk.LEFT, padx=5)
        self.combo_operacion.bind("<<ComboboxSelected>>", self.on_operacion_cambiada)

        # --- FORMULARIO DINÁMICO ---
        self.form_frame = ttk.LabelFrame(self, text=" Datos de la Operación ")
        self.form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Diccionario para almacenar referencias de los inputs activos
        self.inputs = {}

        # Cargar primera opción por defecto
        self.combo_operacion.current(0)
        self.on_operacion_cambiada(None)

    def on_operacion_cambiada(self, event):
        """Limpia el formulario y dibuja los campos según la opción elegida."""
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.inputs.clear()

        opcion = self.combo_operacion.get()

        if "Agregar Nueva Herramienta" in opcion:
            self.crear_campo("Código Único (Ej. HERR-1001):", "codigo")
            self.crear_campo("Descripción (Ej. Rotomartillo):", "descripcion")
            self.crear_campo("Marca:", "marca")
            self.crear_boton_accion(self.ejecutar_agregar_herramienta, "Agregar Herramienta")

        elif "Agregar Nuevo Consumible" in opcion:
            self.crear_campo("Código Único (Ej. CONS-2001):", "codigo")
            self.crear_campo("Descripción (Ej. Casco de Seguridad):", "descripcion")
            self.crear_campo("Stock Inicial:", "stock")
            self.crear_campo("Stock Mínimo para Alertas:", "alerta")
            self.crear_boton_accion(self.ejecutar_agregar_consumible, "Agregar Consumible")

        elif "Agregar Nuevo Material Trazable" in opcion:
            self.crear_campo("Código Único (Ej. MATR-3001):", "codigo")
            self.crear_campo("Descripción:", "descripcion")
            self.crear_campo("Número de Serie o Lote:", "numero_serie")
            self.crear_campo("Unidad de Medida (Ej. metros, kg):", "unidad_medida")
            self.crear_campo("Cantidad Disponible Inicial:", "cantidad")
            self.crear_boton_accion(self.ejecutar_agregar_material_trazable, "Agregar Material")

        elif "Agregar Nuevo Usuario" in opcion:
            self.crear_campo("RUT Usuario (Ej. 15.123.456-7):", "rut")
            self.crear_campo("Nombre Completo:", "nombre")
            self.crear_combo("Rol Asignado:", "rol", ["Pañolero", "Jefe de Obra", "Prevencionista", "Administrador"])
            self.crear_boton_accion(self.ejecutar_agregar_usuario, "Registrar Usuario")

        elif "Registrar Transacción de Salida" in opcion:
            self.crear_campo("RUT del Trabajador Receptor:", "rut_trabajador")
            self.crear_campo("RUT del Pañolero Responsable:", "rut_panolero")
            self.crear_campo("Código del Ítem a Entregar:", "item_id")
            self.crear_campo("Cantidad a Entregar:", "cantidad")
            self.crear_boton_accion(self.ejecutar_transaccion_salida, "Registrar Entrega (Salida)")

        elif "Registrar Transacción de Entrada" in opcion:
            self.crear_campo("RUT del Trabajador que Devuelve:", "rut_trabajador")
            self.crear_campo("RUT del Pañolero que Recibe:", "rut_panolero")
            self.crear_campo("Código del Ítem Devuelto:", "item_id")
            self.crear_campo("Cantidad Devuelta:", "cantidad")
            self.crear_combo("Estado al Devolver (Solo si es Herramienta):", "estado_herramienta", ["Bodega", "En Reparación"])
            self.crear_boton_accion(self.ejecutar_transaccion_entrada, "Registrar Devolución (Entrada)")

        elif "Eliminar un Activo" in opcion:
            self.crear_campo("Código Exacto del Activo a Eliminar:", "codigo")
            self.crear_boton_accion(self.ejecutar_eliminar_activo, "Eliminar Activo del Inventario")

        elif "Eliminar Historial de Transacciones" in opcion:
            self.crear_campo("RUT del Trabajador a Limpiar:", "rut_trabajador")
            self.crear_boton_accion(self.ejecutar_eliminar_transacciones, "Eliminar Todo el Historial")

        elif "Eliminar un Usuario" in opcion:
            self.crear_campo("RUT del Usuario a Eliminar:", "rut")
            self.crear_boton_accion(self.ejecutar_eliminar_usuario, "Eliminar Usuario del Sistema")

    # --- AYUDANTES DE INTERFAZ (WIDGETS GENERICS) ---
    def crear_campo(self, etiqueta, clave):
        row = len(self.inputs)
        ttk.Label(self.form_frame, text=etiqueta).grid(row=row, column=0, padx=10, pady=8, sticky="w")
        var = tk.StringVar()
        entry = ttk.Entry(self.form_frame, textvariable=var, width=40)
        entry.grid(row=row, column=1, padx=10, pady=8, sticky="w")
        self.inputs[clave] = var

    def crear_combo(self, etiqueta, clave, valores):
        row = len(self.inputs)
        ttk.Label(self.form_frame, text=etiqueta).grid(row=row, column=0, padx=10, pady=8, sticky="w")
        var = tk.StringVar()
        combo = ttk.Combobox(self.form_frame, textvariable=var, values=valores, state="readonly", width=37)
        combo.grid(row=row, column=1, padx=10, pady=8, sticky="w")
        combo.current(0)
        self.inputs[clave] = var

    def crear_boton_accion(self, comando, texto):
        row = len(self.inputs) + 1
        btn = ttk.Button(self.form_frame, text=texto, command=comando)
        btn.grid(row=row, column=1, padx=10, pady=15, sticky="e")

    def limpiar_campos(self):
        for var in self.inputs.values():
            var.set("")

    # --- CONTROLADORES DE BASE DE DATOS (CREATE / DELETE) ---
    def ejecutar_agregar_herramienta(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        descripcion = self.inputs["descripcion"].get().strip()
        marca = self.inputs["marca"].get().strip()

        if not codigo_valido(codigo) or not descripcion:
            messagebox.showwarning("Validación", "Código inválido (Debe ser PREFIJO-NUMERO) o Descripción vacía.")
            return

        nuevo_doc = {
            "_id": codigo, "tipo_activo": "Herramienta", "descripcion": descripcion,
            "marca": marca if marca else "N/A", "estado": "Bodega", "historial_mantenimiento": []
        }
        try:
            self.inventario.insert_one(nuevo_doc)
            messagebox.showinfo("Éxito", f"Herramienta {codigo} agregada correctamente.")
            self.limpiar_campos()
        except pymongo.errors.DuplicateKeyError:
            messagebox.showerror("Error", f"El código {codigo} ya existe en el inventario.")

    def ejecutar_agregar_consumible(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        descripcion = self.inputs["descripcion"].get().strip()
        try:
            stock = int(self.inputs["stock"].get().strip())
            alerta = int(self.inputs["alerta"].get().strip())
            if stock < 0 or alerta < 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Validación", "Stock y Alerta deben ser números enteros válidos (>= 0).")
            return

        if not codigo_valido(codigo) or not descripcion:
            messagebox.showwarning("Validación", "Por favor valide los campos obligatorios.")
            return

        nuevo_doc = {
            "_id": codigo, "tipo_activo": "Consumible", "descripcion": descripcion,
            "stock_actual": stock, "alerta_minima": alerta
        }
        try:
            self.inventario.insert_one(nuevo_doc)
            messagebox.showinfo("Éxito", f"Consumible {codigo} registrado con éxito.")
            self.limpiar_campos()
        except pymongo.errors.DuplicateKeyError:
            messagebox.showerror("Error", "El código ingresado ya existe.")

    def ejecutar_agregar_material_trazable(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        descripcion = self.inputs["descripcion"].get().strip()
        num_serie = self.inputs["numero_serie"].get().strip()
        unidad = self.inputs["unidad_medida"].get().strip()
        try:
            cantidad = int(self.inputs["cantidad"].get().strip())
            if cantidad < 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Validación", "La cantidad debe ser un entero mayor o igual a 0.")
            return

        if not codigo_valido(codigo) or not descripcion or not num_serie or not unidad:
            messagebox.showwarning("Validación", "Todos los campos de texto son de carácter obligatorio.")
            return

        nuevo_doc = {
            "_id": codigo, "tipo_activo": "Material Trazable", "descripcion": descripcion,
            "numero_serie": num_serie, "unidad_medida": unidad, "cantidad_disponible": cantidad, "trazabilidad": []
        }
        try:
            self.inventario.insert_one(nuevo_doc)
            messagebox.showinfo("Éxito", "Material trazable indexado al sistema.")
            self.limpiar_campos()
        except pymongo.errors.DuplicateKeyError:
            messagebox.showerror("Error", "El código único del lote ya existe.")

    def ejecutar_agregar_usuario(self):
        rut = self.inputs["rut"].get().strip()
        nombre = self.inputs["nombre"].get().strip()
        rol = self.inputs["rol"].get()

        if not rut_valido(rut) or not nombre:
            messagebox.showwarning("Validación", "RUT inválido (Use formato NN.NNN.NNN-D) o Nombre vacío.")
            return

        nuevo_doc = {"_id": rut, "nombre": nombre, "rol": rol, "activo": True}
        try:
            self.usuarios.insert_one(nuevo_doc)
            messagebox.showinfo("Éxito", f"Usuario '{nombre}' registrado bajo rol corporativo '{rol}'.")
            self.limpiar_campos()
        except pymongo.errors.DuplicateKeyError:
            messagebox.showerror("Error", "Este RUT ya se encuentra registrado.")

    def ejecutar_transaccion_salida(self):
        rut_t = self.inputs["rut_trabajador"].get().strip()
        rut_p = self.inputs["rut_panolero"].get().strip()
        item_id = self.inputs["item_id"].get().strip().upper()
        try:
            cantidad = int(self.inputs["cantidad"].get().strip())
            if cantidad < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Validación", "La cantidad de entrega debe ser un número entero mayor que cero.")
            return

        if not rut_valido(rut_t) or not rut_valido(rut_p) or not codigo_valido(item_id):
            messagebox.showwarning("Validación", "Formatos de RUT o Código inválidos.")
            return

        activo = self.inventario.find_one({"_id": item_id})
        if not activo:
            messagebox.showerror("Error", "El activo solicitado no se encuentra en el inventario.")
            return

        if activo["tipo_activo"] == "Consumible":
            if activo.get("stock_actual", 0) < cantidad:
                messagebox.showerror("Stock Insuficiente", f"No alcanza el stock. Disponible: {activo.get('stock_actual')}")
                return
            self.inventario.update_one({"_id": item_id}, {"$inc": {"stock_actual": -cantidad}})
        elif activo["tipo_activo"] == "Herramienta":
            if activo.get("estado") != "Bodega":
                messagebox.showerror("No Disponible", f"Herramienta no disponible en Bodega. Estado actual: {activo.get('estado')}")
                return
            cantidad = 1  # Ajuste estricto del negocio
            self.inventario.update_one({"_id": item_id}, {"$set": {"estado": "En Terreno", "asignado_a": rut_t}})
        elif activo["tipo_activo"] == "Material Trazable":
            if activo.get("cantidad_disponible", 0) < cantidad:
                messagebox.showerror("Cantidad Insuficiente", "No hay suficiente metraje/unidades del material en pañol.")
                return
            self.inventario.update_one({"_id": item_id}, {"$inc": {"cantidad_disponible": -cantidad}})

        nueva_trans = {
            "fecha_hora": datetime.now(timezone.utc), "tipo_movimiento": "Salida",
            "trabajador_rut": rut_t, "panolero_rut": rut_p, "items": [{"item_id": item_id, "cantidad": cantidad}]
        }
        res = self.transacciones.insert_one(nueva_trans)
        messagebox.showinfo("Éxito", f"Salida autorizada y registrada. ID: {res.inserted_id}")
        self.limpiar_campos()

    def ejecutar_transaccion_entrada(self):
        rut_t = self.inputs["rut_trabajador"].get().strip()
        rut_p = self.inputs["rut_panolero"].get().strip()
        item_id = self.inputs["item_id"].get().strip().upper()
        estado_h = self.inputs["estado_herramienta"].get()
        try:
            cantidad = int(self.inputs["cantidad"].get().strip())
            if cantidad < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Validación", "Cantidad devuelta no válida.")
            return

        activo = self.inventario.find_one({"_id": item_id})
        if not activo:
            messagebox.showerror("Error", "El activo no existe en el catálogo.")
            return

        if activo["tipo_activo"] == "Consumible":
            self.inventario.update_one({"_id": item_id}, {"$inc": {"stock_actual": cantidad}})
        elif activo["tipo_activo"] == "Herramienta":
            cantidad = 1
            self.inventario.update_one({"_id": item_id}, {"$set": {"estado": estado_h}, "$unset": {"asignado_a": ""}})
        elif activo["tipo_activo"] == "Material Trazable":
            self.inventario.update_one({"_id": item_id}, {"$inc": {"cantidad_disponible": cantidad}})

        nueva_trans = {
            "fecha_hora": datetime.now(timezone.utc), "tipo_movimiento": "Entrada",
            "trabajador_rut": rut_t, "panolero_rut": rut_p, "items": [{"item_id": item_id, "cantidad": cantidad}]
        }
        res = self.transacciones.insert_one(nueva_trans)
        messagebox.showinfo("Éxito", f"Devolución asentada en el libro de transacciones. ID: {res.inserted_id}")
        self.limpiar_campos()

    def ejecutar_eliminar_activo(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        if not codigo_valido(codigo):
            messagebox.showwarning("Validación", "Formato de código erróneo.")
            return
        if messagebox.askyesno("Confirmación Estricta", f"¿Seguro que desea eliminar permanentemente el activo {codigo}?"):
            res = self.inventario.delete_one({"_id": codigo})
            if res.deleted_count > 0:
                messagebox.showinfo("Eliminado", "El activo ha sido purgado del catálogo general.")
                self.limpiar_campos()
            else:
                messagebox.showerror("Error", "No se encontró coincidencia de borrado.")

    def ejecutar_eliminar_transacciones(self):
        rut = self.inputs["rut_trabajador"].get().strip()
        if not rut_valido(rut):
            messagebox.showwarning("Validación", "RUT inválido.")
            return
        if messagebox.askyesno("PELIGRO DE AUDITORÍA", f"¿Desea eliminar TODAS las transacciones ligadas a {rut}?\nEsta acción no se puede revertir."):
            res = self.transacciones.delete_many({"trabajador_rut": rut})
            messagebox.showinfo("Limpieza Completada", f"Se eliminaron {res.deleted_count} registros históricos.")
            self.limpiar_campos()

    def ejecutar_eliminar_usuario(self):
        rut = self.inputs["rut"].get().strip()
        if not rut_valido(rut): return
        if messagebox.askyesno("Confirmar", f"¿Dar de baja al usuario {rut} del sistema corporativo de acceso?"):
            res = self.usuarios.delete_one({"_id": rut})
            if res.deleted_count > 0:
                messagebox.showinfo("Éxito", "Usuario purgado del control RBAC.")
                self.limpiar_campos()
            else:
                messagebox.showerror("Error", "Usuario no encontrado.")