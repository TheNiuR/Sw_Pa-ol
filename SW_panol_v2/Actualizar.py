import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
import pymongo.errors
from bson import ObjectId
from validaciones import rut_valido, codigo_valido

class ActualizarFrame(ttk.Frame):
    def __init__(self, parent, db_refs):
        super().__init__(parent)
        # Inyección de dependencias MongoDB
        self.cliente, self.db, self.inventario, self.transacciones, self.usuarios = db_refs
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- HEADER ---
        header = tk.Label(self, text="Módulo de Actualizaciones y Modificaciones", 
                          font=("Arial", 16, "bold"), bg="#f8fafc")
        header.pack(pady=15)

        # --- SECTOR DE NAVEGACIÓN INTERNA ---
        selector_frame = ttk.Frame(self)
        selector_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(selector_frame, text="Seleccione Operación de Modificación:").pack(side=tk.LEFT, padx=5)
        
        self.combo_operacion = ttk.Combobox(selector_frame, width=50, state="readonly")
        self.combo_operacion['values'] = [
            "Modificar Estado de Herramienta",
            "Registrar Mantenimiento Técnico",
            "Ajustar Stock de Consumibles (sin negativos)",
            "Agregar un Atributo Dinámico Nuevo",
            "Actualizar Rol de un Usuario (RBAC)",
            "Activar / Desactivar un Usuario",
            "Anular una Transacción (Reversión de Inventario)"
        ]
        self.combo_operacion.pack(side=tk.LEFT, padx=5)
        self.combo_operacion.bind("<<ComboboxSelected>>", self.on_operacion_cambiada)

        # --- CONTENEDOR DE CAMPOS ---
        self.form_frame = ttk.LabelFrame(self, text=" Parámetros de Actualización ")
        self.form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.inputs = {}
        self.combo_operacion.current(0)
        self.on_operacion_cambiada(None)

    def on_operacion_cambiada(self, event):
        """Maneja la reconfiguración visual de los widgets del formulario."""
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.inputs.clear()

        opcion = self.combo_operacion.get()

        if "Modificar Estado de Herramienta" in opcion:
            self.crear_campo("Código de la Herramienta:", "codigo")
            self.crear_combo("Nuevo Estado Técnico:", "estado", ["Bodega", "En Terreno", "En Reparación", "Dado de Baja"])
            self.crear_boton_ejecutar(self.ejecutar_actualizar_estado)

        elif "Registrar Mantenimiento Técnico" in opcion:
            self.crear_campo("Código de la Herramienta:", "codigo")
            self.crear_campo("Descripción del Trabajo Técnico Realizado:", "accion")
            self.crear_boton_ejecutar(self.ejecutar_registrar_mantenimiento)

        elif "Ajustar Stock de Consumibles" in opcion:
            self.crear_campo("Código del Consumible/EPP:", "codigo")
            self.crear_campo("Variación de Unidades (Use número negativo '-' para restar):", "cantidad")
            self.crear_boton_ejecutar(self.ejecutar_ajustar_stock)

        elif "Agregar un Atributo Dinámico" in opcion:
            self.crear_campo("Código Único del Activo:", "codigo")
            self.crear_campo("Nombre de la Nueva Propiedad (Ej. certificacion):", "nombre_campo")
            self.crear_campo("Valor a Asignar al Atributo:", "valor_campo")
            self.crear_boton_ejecutar(self.ejecutar_atributo_dinamico)

        elif "Actualizar Rol de un Usuario" in opcion:
            self.crear_campo("RUT del Usuario:", "rut")
            self.crear_combo("Nuevo Perfil Corporativo:", "rol", ["Pañolero", "Jefe de Obra", "Prevencionista", "Administrador"])
            self.crear_boton_ejecutar(self.ejecutar_actualizar_rol)

        elif "Activar / Desactivar un Usuario" in opcion:
            self.crear_campo("RUT del Usuario:", "rut")
            self.crear_boton_ejecutar(self.ejecutar_conmutar_usuario, texto_btn="Conmutar Estado (On/Off)")

        elif "Anular una Transacción" in opcion:
            self.crear_campo("ID único de Transacción (ObjectId de 24 caracteres):", "id_transaccion")
            self.crear_boton_ejecutar(self.ejecutar_anular_transaccion, texto_btn="Anular y Revertir Stock Atómicamente")

    # --- ELEMENTOS AUXILIARES ---
    def crear_campo(self, etiqueta, clave):
        row = len(self.inputs)
        ttk.Label(self.form_frame, text=etiqueta).grid(row=row, column=0, padx=10, pady=8, sticky="w")
        var = tk.StringVar()
        entry = ttk.Entry(self.form_frame, textvariable=var, width=45)
        entry.grid(row=row, column=1, padx=10, pady=8, sticky="w")
        self.inputs[clave] = var

    def crear_combo(self, etiqueta, clave, valores):
        row = len(self.inputs)
        ttk.Label(self.form_frame, text=etiqueta).grid(row=row, column=0, padx=10, pady=8, sticky="w")
        var = tk.StringVar()
        combo = ttk.Combobox(self.form_frame, textvariable=var, values=valores, state="readonly", width=42)
        combo.grid(row=row, column=1, padx=10, pady=8, sticky="w")
        combo.current(0)
        self.inputs[clave] = var

    def crear_boton_ejecutar(self, comando, texto_btn="Aplicar Modificación"):
        row = len(self.inputs) + 1
        btn = ttk.Button(self.form_frame, text=texto_btn, command=comando)
        btn.grid(row=row, column=1, padx=10, pady=15, sticky="e")

    def limpiar_campos(self):
        for var in self.inputs.values():
            var.set("")

    # --- LÓGICA DE ACTUALIZACIÓN MONGO ---
    def ejecutar_actualizar_estado(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        nuevo_est = self.inputs["estado"].get()

        if not codigo_valido(codigo):
            messagebox.showwarning("Validación", "Código de activo mal estructurado.")
            return

        act = {"$set": {"estado": nuevo_est}}
        if nuevo_est == "Bodega":
            act["$unset"] = {"asignado_a": ""}

        res = self.inventario.update_one({"_id": codigo, "tipo_activo": "Herramienta"}, act)
        if res.matched_count > 0:
            messagebox.showinfo("Éxito", f"Herramienta {codigo} modificada al estado '{nuevo_est}'.")
            self.limpiar_campos()
        else:
            messagebox.showerror("Error", "No se halló la herramienta o el tipo de activo no corresponde.")

    def ejecutar_registrar_mantenimiento(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        accion = self.inputs["accion"].get().strip()

        if not codigo_valido(codigo) or not accion:
            messagebox.showwarning("Validación", "Complete el código y la descripción técnica.")
            return

        registro = {"fecha": datetime.now(timezone.utc), "accion": accion}
        act = {"$push": {"historial_mantenimiento": registro}, "$set": {"estado": "En Reparación"}}

        res = self.inventario.update_one({"_id": codigo, "tipo_activo": "Herramienta"}, act)
        if res.matched_count > 0:
            messagebox.showinfo("Historial Actualizado", "Ficha técnica inyectada. Estado fijado 'En Reparación'.")
            self.limpiar_campos()
        else:
            messagebox.showerror("Error", "Fallo de localización del equipo técnico.")

    def ejecutar_ajustar_stock(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        try:
            cantidad = int(self.inputs["cantidad"].get().strip())
        except ValueError:
            messagebox.showwarning("Validación", "Debe ingresar obligatoriamente un número entero.")
            return

        if not codigo_valido(codigo): return

        filtro = {"_id": codigo, "tipo_activo": "Consumible"}
        if cantidad < 0:
            filtro["stock_actual"] = {"$gte": -cantidad}  # Restricción atómica de negocio

        res = self.inventario.find_one_and_update(
            filtro, {"$inc": {"stock_actual": cantidad}}, return_document=pymongo.ReturnDocument.AFTER
        )

        if res:
            messagebox.showinfo("Stock Ajustado", f"Modificación atómica exitosa. Stock actual de {codigo}: {res['stock_actual']} uds.")
            self.limpiar_campos()
        else:
            existe = self.inventario.find_one({"_id": codigo, "tipo_activo": "Consumible"})
            if not existe:
                messagebox.showerror("Error", "Consumible no mapeado en base de datos.")
            else:
                messagebox.showerror("Alerta de Operación", f"La rebaja pedida rompe el stock físico disponible ({existe.get('stock_actual')}).")

    def ejecutar_atributo_dinamico(self):
        codigo = self.inputs["codigo"].get().strip().upper()
        campo = self.inputs["nombre_campo"].get().strip()
        valor = self.inputs["valor_campo"].get().strip()

        if not codigo_valido(codigo) or not campo or not valor:
            messagebox.showwarning("Validación", "Rellene la totalidad de los parámetros dinámicos.")
            return

        if campo in {"_id", "tipo_activo", "descripcion"}:
            messagebox.showerror("Restricción", f"El campo '{campo}' es pilar del esquema y está protegido de reescritura.")
            return

        res = self.inventario.update_one({"_id": codigo}, {"$set": {campo: valor}})
        if res.matched_count > 0:
            messagebox.showinfo("Flexibilidad NoSQL", f"Propiedad extendida '{campo}' indexada con éxito al documento {codigo}.")
            self.limpiar_campos()
        else:
            messagebox.showerror("Error", "ID del activo inexistente.")

    def ejecutar_actualizar_rol(self):
        rut = self.inputs["rut"].get().strip()
        rol = self.inputs["rol"].get()

        if not rut_valido(rut): return

        res = self.usuarios.update_one({"_id": rut}, {"$set": {"rol": rol}})
        if res.matched_count > 0:
            messagebox.showinfo("RBAC", f"Privilegios actualizados del rut {rut} a: {rol}.")
            self.limpiar_campos()
        else:
            messagebox.showerror("Error", "Usuario no localizado.")

    def ejecutar_conmutar_usuario(self):
        rut = self.inputs["rut"].get().strip()
        if not rut_valido(rut): return

        usr = self.usuarios.find_one({"_id": rut})
        if not usr:
            messagebox.showerror("Error", "Usuario inexistente.")
            return

        nuevo_estado = not usr.get("activo", True)
        self.usuarios.update_one({"_id": rut}, {"$set": {"activo": nuevo_estado}})
        msg = "ACTIVADO" if nuevo_estado else "DESACTIVADO"
        messagebox.showinfo("RBAC Actualizado", f"El acceso del usuario {rut} ahora se encuentra: {msg}.")
        self.limpiar_campos()

    def ejecutar_anular_transaccion(self):
        id_t = self.inputs["id_transaccion"].get().strip()
        try:
            oid = ObjectId(id_t)
        except Exception:
            messagebox.showerror("Error de entrada", "La cadena provista no cumple con los 24 caracteres hexadecimales de un ObjectId de MongoDB.")
            return

        trans = self.transacciones.find_one({"_id": oid})
        if not trans:
            messagebox.showerror("Error", "Ninguna transacción responde al ID ingresado.")
            return

        if trans.get("tipo_movimiento") == "Anulado":
            messagebox.showwarning("Aviso", "Esta operación ya fue revertida y cuenta con sello de anulación.")
            return

        if messagebox.askyesno("Confirmación Auditoría", "¿Está completamente seguro de anular la transacción y realizar el rollback de stocks en el inventario?"):
            signo = -1 if trans["tipo_movimiento"] == "Salida" else 1

            for item in trans.get("items", []):
                activo = self.inventario.find_one({"_id": item["item_id"]})
                if not activo: continue

                if activo["tipo_activo"] == "Consumible":
                    self.inventario.update_one({"_id": item["item_id"]}, {"$inc": {"stock_actual": signo * item["cantidad"]}})
                elif activo["tipo_activo"] == "Material Trazable":
                    self.inventario.update_one({"_id": item["item_id"]}, {"$inc": {"cantidad_disponible": signo * item["cantidad"]}})
                elif activo["tipo_activo"] == "Herramienta":
                    reverso = "Bodega" if trans["tipo_movimiento"] == "Salida" else "En Terreno"
                    self.inventario.update_one({"_id": item["item_id"]}, {"$set": {"estado": reverso}})

            self.transacciones.update_one({"_id": oid}, {"$set": {"tipo_movimiento": "Anulado"}})
            messagebox.showinfo("Éxito de Auditoría", "Transacción anulada. Los stocks físicos han sido reajustados de manera segura.")
            self.limpiar_campos()