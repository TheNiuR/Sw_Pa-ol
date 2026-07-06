import tkinter as tk
from tkinter import ttk, messagebox
# Si necesitas validaciones específicas, impórtalas aquí:
# from validaciones import rut_valido

class ConsultasFrame(ttk.Frame):
    def __init__(self, parent, db_refs):
        super().__init__(parent)
        
        # Desempaquetar la conexión inyectada desde main.py
        self.cliente, self.db, self.inventario, self.transacciones, self.usuarios = db_refs
        
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- HEADER ---
        header = tk.Label(self, text="Módulo de Consultas y Reportes", font=("Arial", 16, "bold"), bg="#f8fafc")
        header.pack(pady=15)

        # --- PANEL DE CONTROLES ---
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(control_frame, text="Seleccione Consulta:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Selector de consultas
        self.combo_consultas = ttk.Combobox(control_frame, width=50, state="readonly")
        self.combo_consultas['values'] = (
            "Mostrar todo el inventario",
            "Consumibles bajo stock mínimo de alerta",
            "Buscar herramientas por estado",
            "Listado de usuarios del sistema"
        )
        self.combo_consultas.current(0)
        self.combo_consultas.grid(row=0, column=1, padx=5, pady=5)
        self.combo_consultas.bind("<<ComboboxSelected>>", self.on_consulta_seleccionada)

        # Frame dinámico para inputs (dependiendo de la consulta seleccionada)
        self.inputs_frame = ttk.Frame(control_frame)
        self.inputs_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky="w")
        self.generar_inputs_dinamicos() # Genera inputs iniciales

        # Botón Ejecutar
        btn_ejecutar = ttk.Button(control_frame, text="Ejecutar Consulta", command=self.ejecutar_consulta)
        btn_ejecutar.grid(row=0, column=2, padx=15, pady=5)

        # --- TREEVIEW (TABLA DE RESULTADOS) ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Scrollbar
        scroll = ttk.Scrollbar(tree_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_frame, yscrollcommand=scroll.set, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.tree.yview)

    def on_consulta_seleccionada(self, event):
        """Re-dibuja los campos de entrada según la consulta seleccionada."""
        for widget in self.inputs_frame.winfo_children():
            widget.destroy()
        self.generar_inputs_dinamicos()
        self.limpiar_tabla()

    def generar_inputs_dinamicos(self):
        """Genera Entrys o Combobox extra si la consulta lo requiere."""
        seleccion = self.combo_consultas.get()
        
        if "herramientas por estado" in seleccion:
            ttk.Label(self.inputs_frame, text="Estado:").pack(side=tk.LEFT, padx=5)
            self.combo_estado = ttk.Combobox(self.inputs_frame, values=["Bodega", "En Terreno", "En Reparación", "Dado de Baja"], state="readonly")
            self.combo_estado.current(0)
            self.combo_estado.pack(side=tk.LEFT, padx=5)

    def configurar_columnas_treeview(self, columnas):
        """Configura dinámicamente las columnas de la tabla."""
        self.tree["columns"] = columnas
        for col in columnas:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=150, anchor="center")

    def limpiar_tabla(self):
        for fila in self.tree.get_children():
            self.tree.delete(fila)

    def ejecutar_consulta(self):
        self.limpiar_tabla()
        seleccion = self.combo_consultas.get()

        try:
            if seleccion.startswith("1"):
                self.mostrar_todo_inventario()
            elif seleccion.startswith("2"):
                self.mostrar_stock_bajo_alerta()
            elif seleccion.startswith("3"):
                self.mostrar_herramientas_por_estado()
            elif seleccion.startswith("4"):
                self.mostrar_usuarios()
        except Exception as e:
            messagebox.showerror("Error de BD", f"Ocurrió un error al ejecutar la consulta:\n{str(e)}")

    # ==========================================
    # LÓGICA DE MONGODB ADAPTADA A TKINTER
    # ==========================================
    
    def mostrar_todo_inventario(self):
        self.configurar_columnas_treeview(("Código", "Tipo", "Descripción", "Estado / Stock"))
        documentos = list(self.inventario.find())
        
        if not documentos:
            messagebox.showinfo("Información", "No hay activos registrados en el inventario.")
            return

        for doc in documentos:
            estado_o_stock = doc.get("estado", doc.get("stock_actual", doc.get("cantidad_disponible", "N/A")))
            self.tree.insert("", tk.END, values=(
                doc.get("_id", "N/A"),
                doc.get("tipo_activo", "N/A"),
                doc.get("descripcion", "N/A"),
                estado_o_stock
            ))

    def mostrar_stock_bajo_alerta(self):
        self.configurar_columnas_treeview(("Código", "Descripción", "Stock Actual", "Mínimo Permitido"))
        filtro = {
            "tipo_activo": "Consumible",
            "$expr": {"$lte": ["$stock_actual", "$alerta_minima"]},
        }
        documentos = list(self.inventario.find(filtro))
        
        if not documentos:
            messagebox.showinfo("Todo en orden", "Todos los consumibles están dentro de su nivel mínimo.")
            return

        for doc in documentos:
            self.tree.insert("", tk.END, values=(
                doc.get("_id"), doc.get("descripcion"), doc.get("stock_actual"), doc.get("alerta_minima")
            ))

    def mostrar_herramientas_por_estado(self):
        estado_sel = self.combo_estado.get()
        self.configurar_columnas_treeview(("Código", "Descripción", "Asignado a"))
        
        documentos = list(self.inventario.find({"tipo_activo": "Herramienta", "estado": estado_sel}))
        
        if not documentos:
            messagebox.showinfo("Sin resultados", f"No hay herramientas en estado '{estado_sel}'.")
            return

        for doc in documentos:
            self.tree.insert("", tk.END, values=(
                doc.get("_id"), doc.get("descripcion"), doc.get("asignado_a", "-")
            ))

    def mostrar_usuarios(self):
        self.configurar_columnas_treeview(("RUT", "Nombre", "Rol", "Estado"))
        documentos = list(self.usuarios.find())
        
        if not documentos:
            messagebox.showinfo("Información", "No hay usuarios registrados.")
            return

        for doc in documentos:
            estado_texto = "Activo" if doc.get("activo") else "Inactivo"
            self.tree.insert("", tk.END, values=(
                doc.get("_id"), doc.get("nombre", "N/A"), doc.get("rol", "N/A"), estado_texto
            ))