import tkinter as tk
from tkinter import ttk, messagebox
import sys

# Importar la conexión y los módulos (Frames)
from conexion import conectar
from Consultas import ConsultasFrame
# Aquí importarías los demás módulos cuando los adaptes:
from Agregar_Eliminar import AgregarEliminarFrame
from Actualizar import ActualizarFrame

class SistemaPanolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Control de Pañol - Obra")
        self.geometry("1024x720")
        self.minsize(800, 600)
        
        # Tema y estilos
        self.configure(bg="#1e293b")
        self.configurar_estilos()

        # 1. Iniciar Conexión a MongoDB
        try:
            # Retorna: (cliente, db, inventario, transacciones, usuarios)
            self.db_refs = conectar("GUI Principal")
        except SystemExit as e:
            messagebox.showerror("Error Crítico", str(e))
            sys.exit(1)

        # 2. Construir Interfaz
        self.crear_layout()
        
        # 3. Cargar vista inicial
        self.mostrar_frame("Consultas")

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("Menu.TFrame", background="#334155")
        style.configure("Menu.TButton", font=("Arial", 11, "bold"), padding=10)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#cbd5e1")

    def crear_layout(self):
        # Contenedor lateral (Menú)
        self.menu_frame = ttk.Frame(self, style="Menu.TFrame", width=250)
        self.menu_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.menu_frame.pack_propagate(False) # Evitar que se encoja

        lbl_titulo = tk.Label(self.menu_frame, text="MENÚ PAÑOL", font=("Arial", 14, "bold"), bg="#334155", fg="#f8fafc")
        lbl_titulo.pack(pady=20)

        # Botones de navegación
        ttk.Button(self.menu_frame, text="1. Altas y Bajas", style="Menu.TButton", 
                   command=lambda: self.mostrar_frame("Agregar_Eliminar")).pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(self.menu_frame, text="2. Actualizaciones", style="Menu.TButton", 
                   command=lambda: self.mostrar_frame("Actualizar")).pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(self.menu_frame, text="3. Consultas", style="Menu.TButton", 
                   command=lambda: self.mostrar_frame("Consultas")).pack(fill=tk.X, padx=10, pady=5)

        # Contenedor principal (donde se inyectan los módulos)
        self.main_frame = ttk.Frame(self, style="TFrame")
        self.main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Diccionario para almacenar las instancias de los frames
        self.frames = {}
        
        # Instanciar los módulos y guardarlos. Pasamos la conexión BD como dependencia.
        self.frames["Consultas"] = ConsultasFrame(self.main_frame, self.db_refs)
        
        self.frames["Agregar_Eliminar"] = AgregarEliminarFrame(self.main_frame, self.db_refs)
        self.frames["Actualizar"] = ActualizarFrame(self.main_frame, self.db_refs)

        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def mostrar_frame(self, nombre_frame):
        frame = self.frames.get(nombre_frame)
        if frame:
            frame.tkraise()
        else:
            messagebox.showinfo("En Construcción", f"El módulo {nombre_frame} aún no ha sido implementado.")

if __name__ == "__main__":
    app = SistemaPanolApp()
    app.mainloop()