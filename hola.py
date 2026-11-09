import sqlite3
import datetime
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# Puerto o nombre de la impresora física en Windows (ej: "COM1", "LPT1" o el nombre compartido)
DESTINO_IMPRESORA = "COM1" 

class DatabaseManager:
    def __init__(self, db_name="caja_local.db"):
        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = Path(__file__).resolve().parent / db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_categoria TEXT UNIQUE NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                id_categoria INTEGER,
                precio REAL NOT NULL,
                imagen BLOB,
                FOREIGN KEY (id_categoria) REFERENCES categorias(id) ON DELETE CASCADE
            )
        """)
        columnas_productos = {
            fila[1] for fila in cursor.execute("PRAGMA table_info(productos)")
        }
        if "imagen" not in columnas_productos:
            cursor.execute("ALTER TABLE productos ADD COLUMN imagen BLOB")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                total REAL NOT NULL,
                metodo_pago TEXT NOT NULL,
                cerrado INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_venta INTEGER,
                id_producto INTEGER,
                cantidad INTEGER,
                precio_unitario REAL,
                FOREIGN KEY (id_venta) REFERENCES ventas(id) ON DELETE CASCADE,
                FOREIGN KEY (id_producto) REFERENCES productos(id)
            )
        """)
        self.conn.commit()

    def query(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()
        return cursor

    def close(self):
        self.conn.close()


class POSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema POS Ultraligero - Local (PySide6)")
        self.resize(1024, 720)
        
        self.db = DatabaseManager()
        self.cart = [] # Estructura: [producto_id, nombre, precio, cantidad]

        QApplication.instance().setStyleSheet("""
            QWidget {
                background-color: #FFF7E8;
                color: #29485A;
                font-family: "Segoe UI";
                font-size: 10pt;
            }
            QMainWindow, QDialog {
                background-color: #FFF7E8;
            }
            QWidget#categoryPanel {
                background-color: #FFF7E8;
                border: 1px solid #E5D8C2;
                border-radius: 12px;
            }
            QWidget#appBackground {
                background-color: #FFF7E8;
            }
            QWidget#ticketPanel {
                background-color: #E5F2F6;
                border: 1px solid #B6D7E3;
                border-radius: 12px;
            }
            QSplitter::handle {
                background-color: #91C5D8;
                width: 4px;
            }
            QTabWidget::pane {
                background-color: #FFF7E8;
                border: 1px solid #E5D8C2;
                border-radius: 12px;
            }
            QTabBar::tab {
                background-color: #D8EDF3;
                color: #29485A;
                border: 1px solid #A8CFDD;
                border-radius: 14px;
                padding: 9px 18px;
                margin: 3px 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #659BB3;
                color: #FFFFFF;
                border: 2px solid #A8CFDD;
            }
            QPushButton {
                background-color: #659BB3;
                color: #FFFFFF;
                border: 1px solid #4F8299;
                border-radius: 9px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4F8299;
                border-color: #37677D;
            }
            QPushButton:pressed {
                background-color: #37677D;
                border-color: #29485A;
            }
            QPushButton:disabled {
                background-color: #D8E9ED;
                color: #526F7D;
                border-color: #B6D7E3;
            }
            QPushButton#checkoutButton {
                background-color: #4F8299;
                border: 2px solid #91C5D8;
                padding: 10px;
            }
            QPushButton#checkoutButton:hover {
                background-color: #37677D;
                border-color: #B6D7E3;
            }
            QPushButton#productButton {
                background-color: #78AFC5;
                border: 2px solid #A8CFDD;
                min-height: 78px;
            }
            QPushButton#productButton:hover {
                background-color: #659BB3;
                border-color: #4F8299;
            }
            QPushButton#emptyProductButton {
                background-color: #F7EEDC;
                border: 1px dashed #C5B99F;
                color: #657985;
                min-height: 78px;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #29485A;
                border: 1px solid #A8CFDD;
                border-radius: 5px;
                padding: 7px;
                selection-background-color: #659BB3;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #659BB3;
            }
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #EAF4F6;
                color: #29485A;
                gridline-color: #C4DDE5;
                border: 1px solid #A8CFDD;
                selection-background-color: #659BB3;
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #659BB3;
                color: #FFFFFF;
                border: 1px solid #4F8299;
                padding: 7px;
                font-weight: bold;
            }
            QTableCornerButton::section {
                background-color: #659BB3;
                border: 1px solid #4F8299;
            }
            QMenuBar {
                background-color: #F7EEDC;
                color: #29485A;
            }
            QMenuBar::item:selected {
                background-color: #D8EDF3;
                color: #29485A;
            }
            QMenu::item:selected {
                background-color: #659BB3;
                color: #FFFFFF;
            }
            QMenu {
                background-color: #FFF7E8;
                color: #29485A;
                border: 1px solid #A8CFDD;
            }
            QLabel#summaryLabel {
                background-color: #D8EDF3;
                color: #29485A;
                border-left: 4px solid #659BB3;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel#imagePreview {
                background-color: #EAF4F6;
                color: #526F7D;
                border: 1px solid #A8CFDD;
                border-radius: 5px;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background-color: #F7EEDC;
                border: none;
                width: 12px;
                height: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background-color: #91C5D8;
                border-radius: 5px;
                min-height: 24px;
                min-width: 24px;
            }
            QScrollBar::handle:hover {
                background-color: #659BB3;
            }
        """)

        self.create_widgets()
        self.load_categories()
       

                        

    def create_widgets(self):
        # Contenedor principal con divisor (equivalente a Panedwindow)
        main_splitter = QSplitter(Qt.Horizontal)

        # Panel izquierdo para la grilla de productos y pestañas de categorías
        left_widget = QWidget()
        left_widget.setObjectName("categoryPanel")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        self.notebook_categorias = QTabWidget()
        left_layout.addWidget(self.notebook_categorias)
        main_splitter.addWidget(left_widget)

        # Panel derecho para el ticket actual
        right_widget = QWidget()
        right_widget.setObjectName("ticketPanel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        lbl_ticket = QLabel("TICKET ACTUAL")
        lbl_ticket.setAlignment(Qt.AlignCenter)
        lbl_ticket.setStyleSheet("font-size: 11px; font-weight: bold; background-color: #B6D7E3; color: #29485A; padding: 8px;")
        right_layout.addWidget(lbl_ticket)

        # Tabla del carrito (Treeview equivalente)
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(3)
        self.cart_table.setHorizontalHeaderLabels(["Cant", "Producto", "Subtotal"])
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cart_table.setColumnWidth(0, 45)
        self.cart_table.setColumnWidth(2, 75)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cart_table.setAlternatingRowColors(True)
        right_layout.addWidget(self.cart_table)

        self.lbl_total_val = QLabel("$ 0.00")
        self.lbl_total_val.setAlignment(Qt.AlignCenter)
        self.lbl_total_val.setStyleSheet("font-size: 18px; font-weight: bold; background-color: #D8EDF3; color: #29485A; padding: 8px;")
        right_layout.addWidget(self.lbl_total_val)

        # Botones inferiores del ticket
        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_borrar = QPushButton("Borrar Ítem")
        btn_borrar.clicked.connect(self.quitar_item_carrito)
        btn_layout.addWidget(btn_borrar)

        btn_cobrar = QPushButton("COBRAR [F6]")
        btn_cobrar.setObjectName("checkoutButton")
        btn_cobrar.clicked.connect(self.pedir_metodo_pago)
        btn_layout.addWidget(btn_cobrar)

        right_layout.addWidget(btn_frame)
        main_splitter.addWidget(right_widget)

        # Ajustar proporciones del divisor (4 a 1)
        main_splitter.setSizes([800, 224])

        central_widget = QWidget()
        central_widget.setObjectName("appBackground")
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(main_splitter, 1)

        barra_inferior = QHBoxLayout()
        barra_inferior.setContentsMargins(8, 4, 8, 8)
        central_layout.addLayout(barra_inferior)

        btn_ventas = QPushButton("Ventas del turno")
        btn_ventas.clicked.connect(self.abrir_ventana_ventas)
        barra_inferior.addWidget(btn_ventas)

        btn_mas_vendidos = QPushButton("Productos más vendidos")
        btn_mas_vendidos.clicked.connect(self.abrir_ventana_mas_vendidos)
        barra_inferior.addWidget(btn_mas_vendidos)

        # TODO: Definir la función de la tercera opción de la barra inferior.
        btn_opcion_tres = QPushButton("Próximamente")
        btn_opcion_tres.setEnabled(False)
        barra_inferior.addWidget(btn_opcion_tres)

        # TODO: Definir la función de la cuarta opción de la barra inferior.
        btn_opcion_cuatro = QPushButton("Próximamente")
        btn_opcion_cuatro.setEnabled(False)
        barra_inferior.addWidget(btn_opcion_cuatro)

        self.setCentralWidget(central_widget)

        # Barra de menú superior (Administración)
        menu_bar = self.menuBar()
        admin_menu = menu_bar.addMenu("Administración")

        act_cat = QAction("Gestionar Categorías", self)
        act_cat.triggered.connect(self.abrir_ventana_categorias)
        admin_menu.addAction(act_cat)

        # 3. Crear la acción (el botón dentro del menú)
        act_inv = QAction("Gestionar Inventario", self)
                                
                                # 4. Conectar la acción con tu método (aquí es donde lo "llamas")
        act_inv.triggered.connect(self.abrir_ventana_inventario)
                                
                                # 5. Agregar la acción al menú desplegable
        admin_menu.addAction(act_inv)

        act_infx = QAction("Imprimir Informe X (Parcial)", self)
        act_infx.triggered.connect(self.imprimir_informe_x)
        admin_menu.addAction(act_infx)

        act_cierre = QAction("Imprimir Cierre de Caja y Resetear", self)
        act_cierre.triggered.connect(self.imprimir_cierre_caja)
        admin_menu.addAction(act_cierre)

        # Atajo de teclado F6 para Cobrar
        self.shortcut_f6 = QAction(self)
        self.shortcut_f6.setShortcut(QKeySequence(Qt.Key_F6))
        self.shortcut_f6.triggered.connect(self.pedir_metodo_pago)
        self.addAction(self.shortcut_f6)

    def load_categories(self):
        # Limpiar pestañas actuales
        while self.notebook_categorias.count() > 0:
            self.notebook_categorias.removeTab(0)

        cursor = self.db.query("SELECT id, nombre_categoria FROM categorias")
        categorias = cursor.fetchall()

        if not categorias:
            frame_vacio = QWidget()
            v_layout = QVBoxLayout(frame_vacio)
            lbl = QLabel("Vaya a Administración > Gestionar Categorías para crear una.")
            lbl.setAlignment(Qt.AlignCenter)
            v_layout.addWidget(lbl)
            self.notebook_categorias.addTab(frame_vacio, "Sin Categorías")
            return

        for cat_id, cat_nombre in categorias:
            cat_frame = QWidget()
            self.notebook_categorias.addTab(cat_frame, cat_nombre)
            self.cargar_slots_productos(cat_frame, cat_id)

    def cargar_slots_productos(self, parent_widget, categoria_id):
        cursor = self.db.query(
            "SELECT id, nombre, precio, imagen FROM productos WHERE id_categoria = ?",
            (categoria_id,),
        )
        productos = cursor.fetchall()

        grid_layout = QGridLayout(parent_widget)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        # Grilla de 20 slots (4 filas x 5 columnas)
        for i in range(20):
            row = i // 5
            col = i % 5
            
            if i < len(productos):
                prod_id, nombre, precio, imagen = productos[i]
                btn_text = f"{nombre}\n${precio:.0f}"
                btn = QPushButton(btn_text)
                btn.setObjectName("productButton")
                if imagen:
                    pixmap = QPixmap()
                    if pixmap.loadFromData(imagen):
                        btn.setIcon(QIcon(pixmap))
                        btn.setIconSize(pixmap.size().scaled(100, 65, Qt.KeepAspectRatio))
                btn.clicked.connect(lambda checked, pid=prod_id, pnom=nombre, pprec=precio: self.agregar_al_carrito(pid, pnom, pprec))
            else:
                btn = QPushButton(f"Slot Vacío {i+1}")
                btn.setObjectName("emptyProductButton")
                btn.setEnabled(False)
            
            grid_layout.addWidget(btn, row, col)

    def agregar_al_carrito(self, producto_id, nombre, precio):
        for item in self.cart:
            if item[0] == producto_id:
                item[3] += 1
                self.actualizar_vista_carrito()
                return
        
        self.cart.append([producto_id, nombre, precio, 1])
        self.actualizar_vista_carrito()

    def quitar_item_carrito(self):
        selected_rows = self.cart_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Aviso", "Seleccione un ítem del ticket para borrar.")
            return
        row = selected_rows[0].row()
        del self.cart[row]
        self.actualizar_vista_carrito()

    def actualizar_vista_carrito(self):
        self.cart_table.setRowCount(0)
        total = 0.0
        
        for item in self.cart:
            _, nombre, precio, cantidad = item
            subtotal = precio * cantidad
            total += subtotal
            
            row_pos = self.cart_table.rowCount()
            self.cart_table.insertRow(row_pos)
            
            self.cart_table.setItem(row_pos, 0, QTableWidgetItem(str(cantidad)))
            self.cart_table.setItem(row_pos, 1, QTableWidgetItem(nombre))
            
            item_sub = QTableWidgetItem(f"${subtotal:.0f}")
            item_sub.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.cart_table.setItem(row_pos, 2, item_sub)
        
        self.lbl_total_val.setText(f"$ {total:.0f}")

    def pedir_metodo_pago(self):
        if not self.cart:
            QMessageBox.warning(self, "Carrito Vacío", "No hay productos en el ticket actual.")
            return

        total_venta = sum(item[2] * item[3] for item in self.cart)

        # Diálogo personalizado de pago
        pago_dialog = QDialog(self)
        pago_dialog.setWindowTitle("Seleccionar Método de Pago")
        pago_dialog.resize(320, 220)
        pago_dialog.setModal(True)

        layout = QVBoxLayout(pago_dialog)

        lbl_tot = QLabel(f"TOTAL A PAGAR: ${total_venta:.0f}")
        lbl_tot.setAlignment(Qt.AlignCenter)
        lbl_tot.setStyleSheet("font-size: 11pt; font-weight: bold; background-color: #D8EDF3; color: #29485A; padding: 8px;")
        layout.addWidget(lbl_tot)

        lbl_sel = QLabel("Seleccione el método de pago:")
        lbl_sel.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_sel)

        def seleccionar(metodo):
            efectivo_recibido = 0.0
            vuelto = 0.0

            if metodo == "EFECTIVO":
                from PySide6.QtWidgets import QInputDialog
                monto_str, ok = QInputDialog.getText(
                    pago_dialog, "Pago en Efectivo", 
                    f"Total a pagar: ${total_venta:.0f}\nIngrese con cuánto dinero paga:"
                )
                if not ok or not monto_str.strip():
                    return 
                try:
                    efectivo_recibido = float(monto_str)
                    if efectivo_recibido < total_venta:
                        QMessageBox.showerror("Error", "El monto ingresado es menor al total de la venta.") if hasattr(QMessageBox, 'showerror') else QMessageBox.critical(pago_dialog, "Error", "El monto ingresado es menor al total de la venta.")
                        return
                    vuelto = efectivo_recibido - total_venta
                    QMessageBox.information(
                        pago_dialog, "Cálculo de Vuelto", 
                        f"Total: ${total_venta:.0f}\nPago: ${efectivo_recibido:.0f}\n\n>>> VUELTO A DAR: ${vuelto:.0f} <<<"
                    )
                except ValueError:
                    QMessageBox.critical(pago_dialog, "Error", "Ingrese un valor numérico válido.")
                    return

            pago_dialog.accept()
            self.procesar_cobro(metodo, efectivo_recibido, vuelto)

        btn_efectivo = QPushButton("EFECTIVO")
        btn_efectivo.clicked.connect(lambda: seleccionar("EFECTIVO"))
        layout.addWidget(btn_efectivo)

        btn_debito = QPushButton("DEBITO")
        btn_debito.clicked.connect(lambda: seleccionar("DEBITO"))
        layout.addWidget(btn_debito)

        btn_credito = QPushButton("CREDITO")
        btn_credito.clicked.connect(lambda: seleccionar("CREDITO"))
        layout.addWidget(btn_credito)

        pago_dialog.exec()

    def procesar_cobro(self, metodo_pago, efectivo_recibido, vuelto):
        total_venta = sum(item[2] * item[3] for item in self.cart)
        ahora = datetime.datetime.now()
        fecha_actual = ahora.strftime("%d/%m/%Y %H:%M") + " Hrs."

        cursor = self.db.query("INSERT INTO ventas (fecha, total, metodo_pago, cerrado) VALUES (?, ?, ?, 0)", 
                               (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_venta, metodo_pago))
        venta_id = cursor.lastrowid

        for item in self.cart:
            prod_id, _, _, cantidad = item
            self.db.query("INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                          (venta_id, prod_id, cantidad, item[2]))

        self.enviar_impresion_ticket(venta_id, fecha_actual, total_venta, metodo_pago, efectivo_recibido, vuelto, metodo_pago == "EFECTIVO")

        self.cart = []
        self.actualizar_vista_carrito()
        QMessageBox.information(self, "Éxito", "Venta procesada e impresa correctamente.")

    def enviar_impresion_ticket(self, venta_id, fecha, total, metodo_pago, efectivo_recibido, vuelto, es_efectivo=False):
        try:
            lineas = []
            lineas.append("\n\n") 
            
            lineas.append("--------------------------------\n")
            lineas.append(">>   GELATERIA  MERY  MOLOY  <<\n")
            lineas.append("     GRACIAS POR SU VISITA\n")
            lineas.append("-------- VALE DE CONTROL INTERNO --------\n\n")
            
            lineas.append(f"CAJA 0001   VEND: 1 MERY MOLOY\n")
            lineas.append(f"VALE {venta_id:06d}    {fecha}\n\n")
            
            for item in self.cart:
                _, nombre, precio, cantidad = item
                subtotal = precio * cantidad
                lineas.append(f"{nombre[:16]:16} x{cantidad:<2}    $ {subtotal:5.0f}\n")
            
            lineas.append(f"\n{metodo_pago:<15}    $ {total:6.0f}\n")
            
            if metodo_pago == "EFECTIVO":
                lineas.append(f"EFECTIVO REC.     $ {efectivo_recibido:6.0f}\n")
                lineas.append(f"SU VUELTO         $ {vuelto:6.0f}\n")
            
            lineas.append(f"\nTOTAL  $ {total:.0f}\n\n")
            lineas.append("\n\n\n") 
            
            contenido_texto = "".join(lineas).encode("latin-1")
            
            comando_corte = b'\x1d\x56\x41\x00'
            comando_cajon = b'\x1b\x70\x00\x19\xfa'
            
            with open("print_temp.txt", "wb") as f:
                f.write(contenido_texto)
                if es_efectivo:
                    f.write(comando_cajon)
                f.write(comando_corte)
            
            os.system(f'copy /b print_temp.txt {DESTINO_IMPRESORA}')
            
        except Exception as e:
            QMessageBox.warning(self, "Aviso de Impresión", f"Venta guardada, pero hubo un problema al imprimir:\n{str(e)}")

    def imprimir_informe_x(self):
        self._generar_reporte(resetear=False, titulo_reporte="Informe X (Parcial)")

    def imprimir_cierre_caja(self):
        self._generar_reporte(resetear=True, titulo_reporte="Cierre de Caja (Informe Z)")

    def _generar_reporte(self, resetear=False, titulo_reporte="Informe"):
        try:
            cursor = self.db.query("""
                SELECT metodo_pago, COUNT(id), SUM(total) 
                FROM ventas 
                WHERE cerrado = 0 
                GROUP BY metodo_pago
            """)
            resultados = cursor.fetchall()
            
            datos_pagos = {"EFECTIVO": {"ops": 0, "total": 0.0}, "DEBITO": {"ops": 0, "total": 0.0}, "CREDITO": {"ops": 0, "total": 0.0}}
            total_general = 0.0
            
            for metodo, ops, tot in resultados:
                m_upper = metodo.upper()
                if m_upper in datos_pagos:
                    datos_pagos[m_upper]["ops"] = ops
                    datos_pagos[m_upper]["total"] = tot
                total_general += tot

            fecha_informe = datetime.datetime.now().strftime("%d/%m/%Y %H:%M") + " Hrs."
            
            lineas = []
            lineas.append("\n\n")
            lineas.append("--------------------------------\n")
            lineas.append(">>   GELATERIA  MERY  MOLOY  <<\n")
            lineas.append(f"-------- {titulo_reporte} --------\n\n")
            
            lineas.append("LOCAL 1   CAJA 0001\n")
            lineas.append("Usuario : Supervisor Caja\n\n")
            lineas.append(f"Fecha: {fecha_informe}\n\n")
            
            lineas.append("EFECTIVO\n")
            lineas.append(f"( {datos_pagos['EFECTIVO']['ops']} operaciones )\n")
            lineas.append(f"           Total Venta      $    {datos_pagos['EFECTIVO']['total']:6.0f}\n\n")
            
            lineas.append("DEBITO\n")
            lineas.append(f"( {datos_pagos['DEBITO']['ops']} operaciones )\n")
            lineas.append(f"           Total Venta      $    {datos_pagos['DEBITO']['total']:6.0f}\n\n")

            lineas.append("CREDITO\n")
            lineas.append(f"( {datos_pagos['CREDITO']['ops']} operaciones )\n")
            lineas.append(f"           Total Venta      $    {datos_pagos['CREDITO']['total']:6.0f}\n\n")
            
            lineas.append("--------------------------------\n")
            lineas.append(f"*** VENTA TOTAL *** $    {total_general:.0f}\n")
            lineas.append("--------------------------------\n\n\n")
            lineas.append("\n\n\n")

            contenido_texto = "".join(lineas).encode("latin-1")
            comando_corte = b'\x1d\x56\x41\x00'

            with open("print_temp.txt", "wb") as f:
                f.write(contenido_texto)
                f.write(comando_corte)
            
            os.system(f'copy /b print_temp.txt {DESTINO_IMPRESORA}')

            if resetear:
                self.db.query("UPDATE ventas SET cerrado = 1 WHERE cerrado = 0")
                QMessageBox.information(self, "Éxito", "Cierre de caja impreso y acumulado reseteado correctamente.")
            else:
                QMessageBox.information(self, "Éxito", "Informe X impreso correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo imprimir el reporte:\n{str(e)}")

    def abrir_ventana_categorias(self):
        cat_win = QDialog(self)
        cat_win.setWindowTitle("Gestión de Categorías")
        cat_win.resize(300, 200)
        cat_win.setModal(True)

        layout = QVBoxLayout(cat_win)

        layout.addWidget(QLabel("Nombre de la Nueva Categoría:"))
        txt_nombre = QLineEdit()
        layout.addWidget(txt_nombre)

        def guardar_cat():
            nombre = txt_nombre.text().strip()
            if nombre:
                try:
                    self.db.query("INSERT INTO categorias (nombre_categoria) VALUES (?)", (nombre,))
                    self.load_categories()
                    QMessageBox.information(cat_win, "Éxito", f"Categoría '{nombre}' creada.")
                    cat_win.destroy()
                except Exception as e:
                    QMessageBox.critical(cat_win, "Error", f"No se pudo crear: {e}")

        btn_guardar = QPushButton("Guardar Categoría")
        btn_guardar.clicked.connect(guardar_cat)
        layout.addWidget(btn_guardar)

        cat_win.exec()

    def abrir_ventana_ventas(self):
        cursor = self.db.query("""
            SELECT id, fecha, metodo_pago, total
            FROM ventas
            WHERE cerrado = 0
            ORDER BY id DESC
        """)
        ventas = cursor.fetchall()
        total_turno = sum(venta[3] for venta in ventas)

        ventana = QDialog(self)
        ventana.setWindowTitle("Ventas del turno actual")
        ventana.resize(680, 420)
        layout = QVBoxLayout(ventana)

        resumen = QLabel(
            f"Operaciones: {len(ventas)}    |    Total del turno: ${total_turno:.2f}"
        )
        resumen.setObjectName("summaryLabel")
        resumen.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(resumen)
        if not ventas:
            layout.addWidget(QLabel("Todavía no hay ventas registradas en este turno."))

        tabla = QTableWidget()
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Venta", "Fecha", "Pago", "Total"])
        tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.setRowCount(len(ventas))
        for fila, venta in enumerate(ventas):
            for columna, valor in enumerate(venta):
                texto = f"${valor:.2f}" if columna == 3 else str(valor)
                tabla.setItem(fila, columna, QTableWidgetItem(texto))
        layout.addWidget(tabla)
        ventana.exec()

    def abrir_ventana_mas_vendidos(self):
        cursor = self.db.query("""
            SELECT p.nombre,
                   SUM(d.cantidad) AS unidades,
                   SUM(d.cantidad * d.precio_unitario) AS total_vendido
            FROM detalle_ventas AS d
            JOIN productos AS p ON p.id = d.id_producto
            JOIN ventas AS v ON v.id = d.id_venta
            GROUP BY p.id, p.nombre
            ORDER BY unidades DESC, total_vendido DESC
        """)
        productos = cursor.fetchall()

        ventana = QDialog(self)
        ventana.setWindowTitle("Productos más vendidos")
        ventana.resize(600, 400)
        layout = QVBoxLayout(ventana)
        layout.addWidget(QLabel("Ranking histórico de productos vendidos"))
        if not productos:
            layout.addWidget(QLabel("Todavía no hay productos vendidos."))

        tabla = QTableWidget()
        tabla.setColumnCount(3)
        tabla.setHorizontalHeaderLabels(["Producto", "Unidades", "Total vendido"])
        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.setRowCount(len(productos))
        for fila, producto in enumerate(productos):
            tabla.setItem(fila, 0, QTableWidgetItem(str(producto[0])))
            tabla.setItem(fila, 1, QTableWidgetItem(str(producto[1])))
            tabla.setItem(fila, 2, QTableWidgetItem(f"${producto[2]:.2f}"))
        layout.addWidget(tabla)
        ventana.exec()

    def abrir_ventana_inventario(self):
        inv_win = QDialog(self)
        inv_win.setWindowTitle("Gestión de Inventario y Precios")
        inv_win.resize(850, 560)

        layout = QVBoxLayout(inv_win)

        tree = QTableWidget()
        tree.setColumnCount(6)
        tree.setHorizontalHeaderLabels(["ID", "Código", "Nombre", "Cat ID", "Precio", "Imagen"])
        tree.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        tree.setSelectionBehavior(QTableWidget.SelectRows)
        tree.setEditTriggers(QTableWidget.NoEditTriggers)
        tree.setAlternatingRowColors(True)
        layout.addWidget(tree)

        def cargar_inv():
            tree.setRowCount(0)
            cursor = self.db.query("""
                SELECT id, codigo, nombre, id_categoria, precio,
                       CASE WHEN imagen IS NULL THEN 'No' ELSE 'Sí' END
                FROM productos
            """)
            for row in cursor.fetchall():
                row_pos = tree.rowCount()
                tree.insertRow(row_pos)
                for col_idx, val in enumerate(row):
                    tree.setItem(row_pos, col_idx, QTableWidgetItem(str(val)))

        cargar_inv()

        # Formulario inferior
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)

        id_producto_editando = [0]
        imagen_seleccionada = [None]

        form_layout.addWidget(QLabel("Código:"), 0, 0)
        e_cod = QLineEdit()
        form_layout.addWidget(e_cod, 0, 1)

        form_layout.addWidget(QLabel("Nombre:"), 0, 2)
        e_nom = QLineEdit()
        form_layout.addWidget(e_nom, 0, 3)

        form_layout.addWidget(QLabel("Cat ID:"), 0, 4)
        e_cat = QLineEdit()
        form_layout.addWidget(e_cat, 0, 5)

        form_layout.addWidget(QLabel("Precio:"), 1, 0)
        e_pre = QLineEdit()
        form_layout.addWidget(e_pre, 1, 1)

        preview_imagen = QLabel("Sin imagen (opcional)")
        preview_imagen.setObjectName("imagePreview")
        preview_imagen.setAlignment(Qt.AlignCenter)
        preview_imagen.setFixedSize(140, 90)
        form_layout.addWidget(preview_imagen, 1, 2, 2, 1)

        def mostrar_imagen(datos):
            imagen_seleccionada[0] = datos
            pixmap = QPixmap()
            if datos and pixmap.loadFromData(datos):
                preview_imagen.setPixmap(
                    pixmap.scaled(140, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                preview_imagen.setPixmap(QPixmap())
                preview_imagen.setText("Sin imagen (opcional)")

        def seleccionar_imagen():
            ruta, _ = QFileDialog.getOpenFileName(
                inv_win,
                "Seleccionar imagen del producto",
                "",
                "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)",
            )
            if not ruta:
                return
            try:
                datos = Path(ruta).read_bytes()
                pixmap = QPixmap()
                if not pixmap.loadFromData(datos):
                    QMessageBox.warning(inv_win, "Imagen inválida", "No se pudo leer la imagen seleccionada.")
                    return
                mostrar_imagen(datos)
            except OSError as error:
                QMessageBox.critical(inv_win, "Error", f"No se pudo abrir la imagen: {error}")

        btn_imagen = QPushButton("Elegir imagen (opcional)")
        btn_imagen.clicked.connect(seleccionar_imagen)
        form_layout.addWidget(btn_imagen, 1, 3, 1, 2)

        def seleccionar_fila(row, col):
            if row < 0 or col < 0:
                return
            selected_row = row
            id_producto_editando[0] = int(tree.item(selected_row, 0).text())
            e_cod.setText(tree.item(selected_row, 1).text())
            e_nom.setText(tree.item(selected_row, 2).text())
            e_cat.setText(tree.item(selected_row, 3).text())
            e_pre.setText(tree.item(selected_row, 4).text())
            cursor = self.db.query(
                "SELECT imagen FROM productos WHERE id = ?",
                (id_producto_editando[0],),
            )
            resultado = cursor.fetchone()
            mostrar_imagen(resultado[0] if resultado else None)

        tree.cellClicked.connect(seleccionar_fila)

        def guardar_o_actualizar_prod():
            try:
                codigo = e_cod.text().strip()
                nombre = e_nom.text().strip()
                id_cat = int(e_cat.text())
                precio = float(e_pre.text())
                prod_id = id_producto_editando[0]

                if not codigo or not nombre:
                    QMessageBox.warning(inv_win, "Aviso", "Complete el código y el nombre del producto.")
                    return

                if prod_id == 0:
                    self.db.query(
                        """INSERT INTO productos
                           (codigo, nombre, id_categoria, precio, imagen)
                           VALUES (?, ?, ?, ?, ?)""",
                        (codigo, nombre, id_cat, precio, imagen_seleccionada[0]),
                    )
                    QMessageBox.information(inv_win, "Éxito", "Producto registrado en el inventario.")
                else:
                    self.db.query(
                        """UPDATE productos
                           SET codigo = ?, nombre = ?, id_categoria = ?, precio = ?, imagen = ?
                           WHERE id = ?""",
                        (codigo, nombre, id_cat, precio, imagen_seleccionada[0], prod_id),
                    )
                    QMessageBox.information(inv_win, "Éxito", "Producto actualizado correctamente.")

                limpiar_formulario()

                cargar_inv()
                self.load_categories()
            except Exception as e:
                QMessageBox.critical(inv_win, "Error", f"No se pudo guardar: {e}")

        def limpiar_formulario():
            id_producto_editando[0] = 0
            e_cod.clear()
            e_nom.clear()
            e_cat.clear()
            e_pre.clear()
            mostrar_imagen(None)

        btn_guardar = QPushButton("Guardar / Actualizar")
        btn_guardar.clicked.connect(guardar_o_actualizar_prod)
        form_layout.addWidget(btn_guardar, 1, 4)

        btn_limpiar = QPushButton("Limpiar Form")
        btn_limpiar.clicked.connect(limpiar_formulario)
        form_layout.addWidget(btn_limpiar, 1, 5)

        layout.addWidget(form_widget)
        inv_win.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = POSApp()
    window.show()
    sys.exit(app.exec())
