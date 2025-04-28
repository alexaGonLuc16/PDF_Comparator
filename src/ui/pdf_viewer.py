import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QSizePolicy, QListWidget, 
                            QListWidgetItem, QFrame, QTreeWidget,QTreeWidgetItem, QToolTip, QRubberBand, QFileDialog, QSlider, QDialog)
from PyQt5.QtGui import QPixmap, QImage, QKeyEvent
from PyQt5.QtCore import Qt, QByteArray, pyqtSignal, QEvent, QPoint, QRect, QSize
from src.pdf_rotation import PDFRotationUIHandler

from math import sqrt

class OpacityDialog(QDialog):
    """Diálogo para seleccionar la opacidad de la marca de agua"""
    def __init__(self, parent=None):
        super(OpacityDialog, self).__init__(parent)
        self.setWindowTitle("Seleccionar Opacidad")
        self.opacity_value = 30  # Valor predeterminado: 30%
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Etiqueta para mostrar el valor actual
        self.opacity_label = QLabel(f"Opacidad: {self.opacity_value}%")
        layout.addWidget(self.opacity_label)
        
        # Slider para seleccionar la opacidad
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(self.opacity_value)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        layout.addWidget(self.opacity_slider)
        
        # Ejemplos predefinidos
        presets_layout = QHBoxLayout()
        presets = [(10, "Muy sutil"), (30, "Sutil"), (50, "Media"), (70, "Fuerte"), (90, "Muy fuerte")]
        
        for value, name in presets:
            preset_button = QPushButton(name)
            preset_button.clicked.connect(lambda checked, v=value: self.set_preset(v))
            presets_layout.addWidget(preset_button)
        
        layout.addLayout(presets_layout)
        
        # Botones de aceptar/cancelar
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Aceptar")
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def update_opacity_label(self, value):
        self.opacity_value = value
        self.opacity_label.setText(f"Opacidad: {value}%")
    
    def set_preset(self, value):
        self.opacity_slider.setValue(value)
        self.update_opacity_label(value)
    
    def get_opacity(self):
        """Devuelve el valor de opacidad como decimal (0-1)"""
        return self.opacity_value / 100.0

class ChangesListWidget(QWidget):
    change_selected = pyqtSignal(int, dict, bool)  # Página, cambio, activado
    
    def __init__(self, parent=None):
        super(ChangesListWidget, self).__init__(parent)
        self.changes_by_page = {}
        self.setMouseTracking(True)  # Importante: habilita el seguimiento del mouse incluso sin clic
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Árbol para mostrar cambios de forma jerárquica
        self.changes_tree = QTreeWidget(self)
        self.changes_tree.setHeaderLabels(["Página/Cambio", "Activado"])
        self.changes_tree.setColumnWidth(0, 150)
        self.changes_tree.itemClicked.connect(self.on_item_clicked)
        
        #layout.addWidget(title_label)
        layout.addWidget(self.changes_tree)
    
    def update_changes_list(self, formatted_circles_by_page):
        """Actualiza la lista completa de cambios por página"""
        print("Update changes list ------------------------------->")
        if not hasattr(self, 'changes_tree') or self.changes_tree is None:
            print("Error: changes_tree no está inicializado")
            return

        self.changes_tree.clear()
        self.changes_by_page = formatted_circles_by_page
        
        # Crear un elemento en el árbol para cada página con cambios
        for page_num, changes in sorted(formatted_circles_by_page.items()):
            if changes:
                page_item = QTreeWidgetItem(self.changes_tree)
                page_item.setText(0, f"Página {page_num + 1} ({len(changes)} cambios)")
                page_item.setData(0, 256 , {"type": "page", "page": page_num})
                
                # Crear sub-elementos para cada cambio en la página
                for i, change in enumerate(changes):
                    change_item = QTreeWidgetItem(page_item)
                    change_item.setText(0, f"Cambio {i+1}")
                    change_item.setData(0, 256, {"type": "change", "page": page_num, "index": i})
                    
                    # Agregar checkbox para activar/desactivar
                    change_item.setCheckState(1, 2 if change.get("selected", True) else 0)
        
        # Expandir el primer nivel
        for i in range(self.changes_tree.topLevelItemCount()):
            self.changes_tree.topLevelItem(i).setExpanded(True)
    
    def on_item_clicked(self, item, column):
        """Maneja el clic en un elemento del árbol"""
        data = item.data(0, 256)
        
        if not data:
            return
            
        if data["type"] == "change":
            page_num = data["page"]
            change_idx = data["index"]
            
            if page_num in self.changes_by_page and change_idx < len(self.changes_by_page[page_num]):
                change = self.changes_by_page[page_num][change_idx]
                
                # Si se hizo clic en la columna del checkbox, actualizar el estado
                if column == 1:
                    is_checked = item.checkState(1) == 2
                    change["selected"] = is_checked
                    self.change_selected.emit(page_num, change, is_checked)
                else:
                    # Si se hizo clic en el nombre, navegar al cambio
                    self.change_selected.emit(page_num, change, change.get("selected", True))
        
        # Si se hace clic en un elemento de página, expandir/contraer
        elif data["type"] == "page" and column == 0:
            item.setExpanded(not item.isExpanded())

class PDFViewer(QWidget):
    circle_clicked = pyqtSignal(int, dict)  # Señal para comunicar clics

    def __init__(self, title="PDF Viewer"):
        super(PDFViewer, self).__init__()
        self.title = title
        self.document = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.clicks_enabled = False
        self.dpi = 300
        self.changes_list_widget = None  # Inicializar a None
        self.original_document = None # para almacenal el pdf original
        self.showing_original = False # para mostrar el pdf anotado
        self.formatted_circles_page = {}
        self.init_ui()
        self.setMouseTracking(True)  # Importante: habilita el seguimiento del mouse incluso sin clic
        self.page_label.setMouseTracking(True)  # También habilítalo para el label del PDF
        self.page_width = 0
        self.page_height = 0
        self.matrix = fitz.Matrix(1, 1)  # Escala 1:1, sin transformación
        self.file_path = None
        self.highlighting = False  # Indica si estamos en modo subrayado
        self.highlight_start = None  # Coordenada inicial del subrayado
        self.highlight_end = None  # Coordenada final del subrayado
        self.temp_highlight_annot = None  # Para almacenar la anotación temporal

        # Para el subrayado de forma libre (ink annotation)
        self.ink_points = []  # Para almacenar los puntos de la trayectoria
        self.highlighting = False  # Si estamos en modo subrayado
        self.highlight_color = (1, 1, 0)  # Color amarillo (R, G, B)
        self.highlight_thickness = 2.0  # Grosor del trazo

        # Para rastrear la última posición
        self.last_cursor_pos = None
    
    def init_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Título
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
        # Área de visualización del PDF
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.page_label.setMouseTracking(True)  # Habilitar seguimiento del mouse
        self.page_label.mousePressEvent = self.label_mouse_press_event  # Sobrescribir evento
        self.page_label.installEventFilter(self)  # Instalar filtro de eventos
        # Instalar filtro de eventos en el widget principal también
        self.installEventFilter(self)

        self.scroll_area.setWidget(self.page_label)

        # Controles de navegación
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Anterior")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        
        self.page_info = QLabel("Página 0 de 0")
        self.page_info.setAlignment(Qt.AlignCenter)
        
        self.next_button = QPushButton("Siguiente")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        # Controles de zoom
        self.zoom_out_button = QPushButton("Zoom -")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        
        self.zoom_in_button = QPushButton("Zoom +")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        
        self.zoom_reset_button = QPushButton("100%")
        self.zoom_reset_button.clicked.connect(self.zoom_reset)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.page_info)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.zoom_out_button)
        nav_layout.addWidget(self.zoom_reset_button)
        nav_layout.addWidget(self.zoom_in_button)
        
        watermark_layout = QHBoxLayout()

        self.watermark_button = QPushButton("Marca de Agua (Página Actual)")
        self.watermark_button.clicked.connect(self.select_watermark_image)

        self.watermark_all_button = QPushButton("Marca de Agua (Todas las Páginas)")
        self.watermark_all_button.clicked.connect(self.select_watermark_for_all_pages)

        watermark_layout.addWidget(self.watermark_button)
        watermark_layout.addWidget(self.watermark_all_button)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(nav_layout)
        layout.addLayout(watermark_layout)  # Añadir el nuevo layout
        
        # Agregamos una lista de cambios solo si este es el visor de PDF anotado
        if "PDF Anotado" in self.title and self.current_page > 0:
            print("Inicializando lista de cambios para el PDF Anotado")
            self.changes_list_widget = ChangesListWidget(self)
            self.changes_list_widget.change_selected.connect(self.navigate_to_change)

    def select_watermark_image(self):
        """Abre un diálogo para seleccionar una imagen y su opacidad"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Marca de Agua", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            # Abrir diálogo de opacidad
            opacity_dialog = OpacityDialog(self)
            if opacity_dialog.exec_() == QDialog.Accepted:
                opacity = opacity_dialog.get_opacity()
                self.apply_watermark_image(file_path, opacity)
                return True
        return False
        
    def select_watermark_for_all_pages(self):
        """Abre un diálogo para seleccionar una imagen y aplicarla a todas las páginas"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Marca de Agua (Todas las Páginas)", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            self.apply_watermark_to_all_pages(file_path)
            return True
        return False

    def apply_watermark_image(self, image_path, opacity=0.3):
        """Aplica la imagen seleccionada como marca de agua al PDF actual con opacidad ajustable"""
        if not self.document:
            print("No hay documento abierto para aplicar la marca de agua")
            return False
            
        try:
            # Obtener la página actual
            page = self.document[self.current_page]
            page_rect = page.rect
            
            # Crear una nueva imagen para mantener la transparencia
            # En versiones recientes de PyMuPDF podemos usar alpha directamente
            try:
                # Intenta usar el método directo con parámetro alpha (versiones recientes)
                page.insert_image(page_rect, filename=image_path, overlay=False, alpha=opacity)
            except TypeError:
                # Si la versión no soporta alpha, usamos un enfoque alternativo
                img = fitz.open(image_path)
                pix = img[0].get_pixmap(alpha=True)
                
                # Ajustar opacidad manualmente
                import numpy as np
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.alpha:  # Si la imagen tiene canal alfa
                    alpha_channel = samples[:, :, -1]
                    alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                    samples[:, :, -1] = alpha_channel
                
                # Crear un nuevo pixmap con los samples modificados
                new_pix = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                page.insert_image(page_rect, pixmap=new_pix, overlay=False)
                
                # Limpiar
                img.close()
            
            # Renderizar la página actualizada
            self.render_current_page()
            print(f"Marca de agua aplicada desde: {image_path} con opacidad {opacity:.1%}")
            return True
        
        except Exception as e:
            print(f"Error al aplicar la marca de agua: {e}")
            return False
    
    def select_watermark_for_all_pages(self):
        """Abre un diálogo para seleccionar una imagen y aplicarla a todas las páginas con opacidad ajustable"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen para Marca de Agua (Todas las Páginas)", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)", 
            options=options
        )
        
        if file_path:
            # Abrir diálogo de opacidad
            opacity_dialog = OpacityDialog(self)
            if opacity_dialog.exec_() == QDialog.Accepted:
                opacity = opacity_dialog.get_opacity()
                self.apply_watermark_to_all_pages(file_path, opacity)
                return True
        return False
    
    def apply_watermark_to_all_pages(self, image_path, opacity=0.3):
        """Aplica la marca de agua a todas las páginas del documento con opacidad ajustable"""
        if not self.document:
            print("No hay documento abierto para aplicar la marca de agua")
            return False
            
        try:
            # Verificar si podemos usar alpha directamente
            supports_alpha = True
            try:
                # Prueba si la versión de PyMuPDF soporta alpha
                page = self.document[0]
                page.insert_image(fitz.Rect(0, 0, 1, 1), filename=image_path, overlay=False, alpha=0.5)
                # Si llegamos aquí, soporta alpha
            except TypeError:
                supports_alpha = False
            
            # Crear pixmap una sola vez para reutilizarlo (si es necesario)
            modified_pixmap = None
            if not supports_alpha:
                img = fitz.open(image_path)
                pix = img[0].get_pixmap(alpha=True)
                
                # Ajustar opacidad manualmente
                import numpy as np
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.alpha:  # Si la imagen tiene canal alfa
                    alpha_channel = samples[:, :, -1]
                    alpha_channel = (alpha_channel * opacity).astype(np.uint8)
                    samples[:, :, -1] = alpha_channel
                
                # Crear un nuevo pixmap con los samples modificados
                modified_pixmap = fitz.Pixmap(pix.colorspace, pix.width, pix.height, samples.tobytes(), alpha=pix.alpha)
                img.close()
            
            # Aplicar a todas las páginas
            for page_num in range(self.document.page_count):
                page = self.document[page_num]
                page_rect = page.rect
                
                # Insertar la imagen como marca de agua
                if supports_alpha:
                    page.insert_image(page_rect, filename=image_path, overlay=False, alpha=opacity)
                else:
                    page.insert_image(page_rect, pixmap=modified_pixmap, overlay=False)
            
            # Limpiar si fue necesario
            if modified_pixmap:
                modified_pixmap = None
            
            # Renderizar la página actual
            self.render_current_page()
            print(f"Marca de agua aplicada a todas las páginas desde: {image_path} con opacidad {opacity:.1%}")
            return True
        
        except Exception as e:
            print(f"Error al aplicar la marca de agua a todas las páginas: {e}")
            return False
    
    def eventFilter(self, obj, event):
        """Filtro de eventos para capturar eventos del mouse"""
        
        # Código existente para tooltips (solo para MouseMove)
        if obj == self.page_label and event.type() == QEvent.MouseMove:
            # Obtener posición del mouse relativa al label
            mouse_pos = event.pos()

            # Verificar si el documento está cargado
            if hasattr(self, 'document') and self.document:
                # Si tenemos un documento, mostrar información de la página
                tooltip_text = f"Página {self.current_page + 1} de {self.document.page_count}"
                
                # Si tenemos círculos en la página actual, verificar si el cursor está sobre alguno
                if hasattr(self, 'formatted_circles_by_page') and self.current_page in self.formatted_circles_by_page:
                    # Convertir coordenadas del mouse a coordenadas del documento
                    dpi_scale = self.dpi / 72
                    zoom_scale = self.zoom_factor
                    total_scale = dpi_scale / zoom_scale
                    
                    doc_x = mouse_pos.x() * total_scale
                    doc_y = mouse_pos.y() * total_scale
                    
                    # Verificar cada círculo en la página actual
                    for i, circle in enumerate(self.formatted_circles_by_page[self.current_page]):
                        # Calcular distancia entre el cursor y el centro del círculo
                        distance = sqrt((doc_x - circle['x'])**2 + (doc_y - circle['y'])**2)
                        
                        # Si la distancia es menor o igual al radio, el cursor está sobre el círculo
                        if distance <= circle['radius']:
                            tooltip_text = f"Cambio {i+1} - Página {self.current_page+1}"
                            break
                
                QToolTip.showText(event.globalPos(), tooltip_text, self.page_label)
                
        return super(PDFViewer, self).eventFilter(obj, event)
    
    def mouseMoveEvent(self, event):
        """Maneja el movimiento del mouse sobre el visor de PDF"""
        # Si estamos en modo subrayado
        if self.highlighting and self.document and self.last_cursor_pos:
            # Convertir coordenadas a relativas al QLabel
            label_pos = self.page_label.mapFrom(self, event.pos())
            
            # Ajustar por desplazamiento del ScrollArea
            adjusted_x = label_pos.x() + self.scroll_area.horizontalScrollBar().value()
            adjusted_y = label_pos.y() + self.scroll_area.verticalScrollBar().value()
            
            # Obtener la distancia desde el último punto
            last_x, last_y = self.last_cursor_pos
            distance = ((adjusted_x - last_x)**2 + (adjusted_y - last_y)**2)**0.5
            
            # Solo añadir el punto si está a cierta distancia mínima del último
            # Esto evita acumular demasiados puntos cercanos
            if distance > 5:  # 5 píxeles de distancia mínima
                # Convertir a coordenadas PDF y añadir el punto
                pdf_point = self.convert_screen_to_pdf_coords(adjusted_x, adjusted_y)
                self.ink_points.append(pdf_point)
                
                # Actualizar la última posición
                self.last_cursor_pos = (adjusted_x, adjusted_y)
                
                # Mostrar el trazo en tiempo real (opcional)
                self.update_live_stroke()
        
        # Código existente para tooltips
        # ...
        
        super(PDFViewer, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Maneja el evento de soltar el botón del mouse"""
        # Si estábamos subrayando y es botón izquierdo
        if self.highlighting and event.button() == Qt.LeftButton and self.document:
            print("Finalizando subrayado de forma libre")
            self.highlighting = False
            
            # Si hay suficientes puntos, crear la anotación
            if len(self.ink_points) > 1:
                self.apply_ink_annotation()
            
            # Limpiar
            self.ink_points = []
            self.last_cursor_pos = None
        
        super(PDFViewer, self).mouseReleaseEvent(event)

    def convert_screen_to_pdf_coords(self, screen_x, screen_y):
        """Convierte coordenadas de pantalla a coordenadas de PDF"""
        if not self.document:
            return (0, 0)
        
        page = self.document[self.current_page]
        page_rect = page.rect
        
        # Obtener dimensiones del pixmap actual
        pixmap_width = self.page_label.pixmap().width()
        pixmap_height = self.page_label.pixmap().height()
        
        # Calcular relación entre pixmap y PDF
        x_ratio = page_rect.width / pixmap_width * self.zoom_factor
        y_ratio = page_rect.height / pixmap_height * self.zoom_factor
        
        # Convertir coordenadas
        pdf_x = screen_x * x_ratio
        pdf_y = screen_y * y_ratio
        
        return (pdf_x, pdf_y)
        
    def update_live_stroke(self):
        """Dibuja el trazo en tiempo real mientras el usuario mueve el cursor (opcional)"""
        # Esta función es opcional y más compleja de implementar correctamente
        # Requeriría un overlay sobre el PDF o modificar temporalmente el documento
        # Por simplicidad, podemos omitirla en la primera implementación
        pass

    def apply_ink_annotation(self):
        """Crea una anotación de tipo ink basada en los puntos recopilados"""
        if not self.document or len(self.ink_points) < 2:
            print("No hay suficientes puntos para crear una anotación de trazo")
            return
        
        try:
            page = self.document[self.current_page]
            
            # Crear la anotación de tipo ink con los puntos recolectados
            # PyMuPDF espera los puntos como una lista de listas (cada lista es un trazo)
            annot = page.add_ink_annot([self.ink_points])
            
            # Configurar propiedades de la anotación
            annot.set_border(width=self.highlight_thickness)
            annot.set_colors(stroke=self.highlight_color)
            annot.update(opacity=0.7)
            
            print(f"Trazo de forma libre añadido con {len(self.ink_points)} puntos")
            
            # Renderizar la página actualizada
            self.render_current_page()
        except Exception as e:
            print(f"Error al aplicar anotación de trazo: {e}")

    def add_highlight_controls(self):
        """Añade controles para el subrayado de forma libre"""
        highlight_layout = QHBoxLayout()
        
        # Botón para color amarillo
        yellow_button = QPushButton("Amarillo")
        yellow_button.clicked.connect(lambda: self.set_highlight_color((1, 1, 0)))
        
        # Botón para color rojo
        red_button = QPushButton("Rojo")
        red_button.clicked.connect(lambda: self.set_highlight_color((1, 0, 0)))
        
        # Botón para grosor fino
        thin_button = QPushButton("Fino")
        thin_button.clicked.connect(lambda: self.set_highlight_thickness(1.0))
        
        # Botón para grosor grueso
        thick_button = QPushButton("Grueso")
        thick_button.clicked.connect(lambda: self.set_highlight_thickness(3.0))
        
        highlight_layout.addWidget(yellow_button)
        highlight_layout.addWidget(red_button)
        highlight_layout.addWidget(thin_button)
        highlight_layout.addWidget(thick_button)
        
        return highlight_layout

    def set_highlight_color(self, color):
        """Establece el color del subrayado de forma libre"""
        self.highlight_color = color
        # Ejemplos de colores: (1,1,0) amarillo, (1,0,0) rojo, (0,1,0) verde, (0,0,1) azul

    # Método para cambiar el grosor del trazo (puedes añadirlo para dar más opciones)
    def set_highlight_thickness(self, thickness):
        """Establece el grosor del trazo de subrayado"""
        self.highlight_thickness = thickness

    def apply_highlight(self):
        if not self.document:
            print("No hay documento cargado.")
            return
        
        if not hasattr(self, 'highlight_start_pdf') or not hasattr(self, 'highlight_end_pdf'):
            print("No hay coordenadas de subrayado.")
            return
        
        page = self.document[self.current_page]
        
        # Obtener coordenadas en píxeles
        x0, y0 = self.highlight_start_pdf
        x1, y1 = self.highlight_end_pdf
        
        # Detectar si la ventana está maximizada
        is_maximized = self.window().isMaximized()
        
        # Calcula un offset dinámico basado en el ancho de la ventana
        window_width = self.window().width()
        offset_x = window_width * 0.02 if is_maximized else 0  # 2% del ancho de la ventana
        
        # Asegurarse que los valores están en orden
        x0, x1 = sorted([x0, x1])
        y0, y1 = sorted([y0, y1])
        
        # Obtener información de la página y la transformación
        page_rect = page.rect  # Rectángulo de la página en coordenadas de PDF
        
        # Calculamos factores de escala
        dpi_scale = self.dpi / 72.0
        zoom_scale = self.zoom_factor
        
        # Obtener el tamaño del pixmap actual para comprender la relación entre pantalla y PDF
        pixmap_width = self.page_label.pixmap().width()
        pixmap_height = self.page_label.pixmap().height()
        
        # Calcular relación entre pixmap y PDF
        x_ratio = page_rect.width / pixmap_width * zoom_scale
        y_ratio = page_rect.height / pixmap_height * zoom_scale
        
        # Convertir de coordenadas de pantalla a coordenadas de PDF
        pdf_x0 = x0 
        pdf_y0 = y0 
        pdf_x1 = x1 
        pdf_y1 = y1 
        
        # Crear rectángulo en coordenadas de PDF
        rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1 + 5)
        
        print(f"Ventana maximizada: {is_maximized}, Offset aplicado: {offset_x}")
        print(f"Coords pantalla (ajustadas): ({x0}, {y0}) a ({x1}, {y1})")
        print(f"Coords PDF: ({pdf_x0}, {pdf_y0}) a ({pdf_x1}, {pdf_y1})")
        print(f"Rectángulo PDF: {rect}")
        
        try:
            # Aplicar el subrayado
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=(1, 1, 0))  # Color amarillo
            annot.update()
            print("Subrayado aplicado con éxito")
        except Exception as e:
            print(f"Error al aplicar subrayado: {e}")
        
        # Limpiar las variables
        if hasattr(self, 'highlight_start_pdf'):
            del self.highlight_start_pdf
        if hasattr(self, 'highlight_end_pdf'):
            del self.highlight_end_pdf
        if hasattr(self, 'highlight_start_pixels'):
            del self.highlight_start_pixels
        
        # Renderizar la página actualizada
        self.render_current_page()

    def update_temp_highlight(self):
        """Actualiza el subrayado temporal mientras se arrastra el mouse"""
        if not self.document or not self.highlight_start or not self.highlight_end:
            return
        
        page = self.document[self.current_page]
        
        # Eliminar anotación temporal anterior si existe
        if self.temp_highlight_annot:
            try:
                # Verificar si la anotación todavía está vinculada a la página
                # Esto evitará el error "Annot is not bound to a page"
                if hasattr(self.temp_highlight_annot, 'parent') and self.temp_highlight_annot.parent:
                    page.delete_annot(self.temp_highlight_annot)
            except Exception as e:
                print(f"Error al eliminar anotación temporal: {e}")
            finally:
                self.temp_highlight_annot = None
        
        # Obtener coordenadas
        x0, y0 = self.highlight_start
        x1, y1 = self.highlight_end
        
        # Asegurarse que los valores están en orden
        x0, x1 = sorted([x0, x1])
        y0, y1 = sorted([y0, y1])
        
        # Crear rectángulo para el subrayado
        rect = fitz.Rect(x0, y0, x1, y1 + 10.0)
        
        try:
            # Crear anotación temporal con un estilo diferente para distinguirla
            self.temp_highlight_annot = page.add_highlight_annot(rect)
            self.temp_highlight_annot.set_colors(stroke=(0.5, 0.5, 1))  # Color azul claro
            self.temp_highlight_annot.set_opacity(0.5)  # Semi-transparente
            self.temp_highlight_annot.update()
            
            # Renderizar la página para mostrar el cambio
            self.render_current_page()
        except Exception as e:
            print(f"Error al crear anotación temporal: {e}")
            self.temp_highlight_annot = None

    def keyPressEvent(self, event):
        """Captura eventos de tecla presionada"""
        # Detectar si se presiona la tecla Q
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Tecla Q presionada - mostrando PDF original")
            self.show_pdf(is_original=True)
            return
        
        # Cancelar subrayado si se presiona Escape
        if event.key() == Qt.Key_Escape and self.highlighting:
            self.highlighting = False
            self.highlight_start = None
            self.highlight_end = None
        
        # Eliminar anotación temporal si existe
        if self.temp_highlight_annot:
            page = self.document[self.current_page]
            page.delete_annot(self.temp_highlight_annot)
            self.temp_highlight_annot = None
            self.render_current_page()
        
        # Dejar que el evento siga su procesamiento normal para otras teclas
        super(PDFViewer, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Captura eventos de tecla liberada"""
        # Detectar si se suelta la tecla Q
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Tecla Q liberada - volviendo a PDF anotado")
            self.show_pdf(is_original=False)
            return
        
        # Dejar que el evento siga su procesamiento normal para otras teclas
        super(PDFViewer, self).keyReleaseEvent(event)

    def show_pdf(self, is_original=False):
        """Muestra el PDF original o anotado según el parámetro"""
        if not self.document or (is_original and not self.original_document):
            print("No hay documentos cargados para mostrar")
            return
            
        self.showing_original = is_original
        
        # Cambiar el título según el PDF que se está mostrando
        if hasattr(self, 'title_label'):
            if is_original:
                self.title_label.setText("PDF Original")
            else:
                self.title_label.setText("PDF Anotado")

        # Guardar la posición actual del scroll
        h_value = self.scroll_area.horizontalScrollBar().value()
        v_value = self.scroll_area.verticalScrollBar().value()
        
        # Renderizar la página correspondiente
        self.render_current_page()
        
        # Actualizar estado de los botones de navegación
        doc_to_check = self.original_document if is_original else self.document
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < doc_to_check.page_count - 1)
        
        # Restaurar la posición del scroll
        self.scroll_area.horizontalScrollBar().setValue(h_value)
        self.scroll_area.verticalScrollBar().setValue(v_value)

    def load_pdf(self, pdf_path, original_pdf_path=None, c_page = 0):
        """Carga un archivo PDF en el visor."""
        if pdf_path:
            # Cerrar documento previo si existe
            if self.document:
                self.document.close()

            # Abrir nuevo documento
            self.document = fitz.open(pdf_path)
            self.current_page = c_page
            
            #Cargar PDF original
            if original_pdf_path:
                if self.original_document:
                    self.original_document.close()
                self.original_document = fitz.open(original_pdf_path)

            # Actualizar interfaz
            self.update_page_info()
            self.render_current_page()
            
            # Habilitar/deshabilitar botones
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(self.document.page_count > 1 )

    #Añade un método para recargar el documento (útil después de una rotación):
    def reload_document(self):
        """
        Recarga el documento actual manteniendo la página actual.
        Útil después de realizar modificaciones como rotaciones.
        """
        print("Entrando a reload document")
        if not self.document:
            return
        
        # Guardar la página actual
        current_page = self.current_page
        
        # Cerrar el documento
        self.document.close()

        # Reabrir el documento
        self.document = fitz.open(self)

        # Asegurarse de que la página actual sea válida
        self.current_page = min(current_page, len(self.document) - 1)
        
        # Actualizar la visualización
        self.update_display()
        
        # Actualizar información de la página si es necesario
        self.update_page_info()

    def has_changes_list(self):
        """Verifica si este visor tiene lista de cambios"""
        return self.changes_list_widget is not None
    
    def navigate_to_change(self, page_num, change):
        """Navega a un cambio específico cuando se selecciona de la lista"""
        print("Navegando a un cambio especifico ----",change)
        # Cambiar a la página correspondiente si es necesario
        if self.current_page != page_num:
            self.current_page = page_num
            self.update_page_info()
            
            # Actualizar estado de los botones
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(self.current_page < self.document.page_count - 1)
        
        # Establecer zoom al 150%
        #self.zoom_factor = 1.5
        self.zoom_factor = 2.0

        # Renderizar la página con el nuevo zoom
        self.render_current_page()
        
        # Calcular la posición del scroll para centrar el cambio
        self.scroll_to_change(change)
    
    def scroll_to_change(self, change):

        dpi_scale = self.dpi / 72.0  # Escala por DPI (72 es el valor base)
        zoom_scale = self.zoom_factor
        total_scale = dpi_scale / zoom_scale

        """Desplaza la vista para centrar el cambio seleccionado"""
        if not self.document:
            return
            
        # Obtener dimensiones del pixmap actual
        if self.page_label.pixmap() is None:
            print("Error: No hay pixmap en page_label")
            return
            
        pixmap_width = self.page_label.pixmap().width()
        pixmap_height = self.page_label.pixmap().height()

        print("Page label dim----------------------")
        print("width",self.page_label.width())
        print("height",self.page_label.height())

        # Calcular la posición del cambio en el pixmap con el zoom actual
        change_x = change['x']
        change_y = change['y']

        print("Change dimensions----------------------")
        print("En x",change_x)
        print("En y",change_y)
        
        #calcular scroll
        scroll_x = (change_x / self.page_width)
        scroll_y = (change_y / self.page_height)

        print("Proporcion---------------")
        print("Calculated scroll x",scroll_x)
        print("Calculated scroll y",scroll_y)

        print("Scroll bar max values-------------------")
        print("Width max",self.scroll_area.horizontalScrollBar().maximum())
        print("Height max",self.scroll_area.verticalScrollBar().maximum())

        print("Scroll bar dimensions------------------")
        print("Width",self.scroll_area.horizontalScrollBar().width())
        print("Height",self.scroll_area.verticalScrollBar().height())
        
        #scroll area dimensions
        h_scroll = self.scroll_area.horizontalScrollBar().width() + self.scroll_area.horizontalScrollBar().maximum()
        v_scroll = self.scroll_area.verticalScrollBar().height() + self.scroll_area.verticalScrollBar().maximum()
        print("Scroll total dimensions")
        print("en x: ", h_scroll)
        print("en y: ", v_scroll)

        # Ajustar el scroll para centrar el cambio
        h_value = max(0, int(h_scroll*scroll_x-self.width()/2))
        v_value = max(0, int(v_scroll*scroll_y-self.height()/2))

        print("Scroll")
        print("en x: ", h_value)
        print("en y: ", v_value)
        
        # Limitar los valores de scroll a los máximos permitidos
        h_value = min(h_value, self.scroll_area.horizontalScrollBar().maximum())
        v_value = min(v_value, self.scroll_area.verticalScrollBar().maximum())
        
        # Establecer los valores de scroll
        self.scroll_area.horizontalScrollBar().setValue(h_value)
        self.scroll_area.verticalScrollBar().setValue(v_value)
    
    def label_mouse_press_event(self, event):
        """Maneja los clics en el label del PDF"""
        pos = event.pos()
        print("Label Press event")
        print(f"Click en QLabel (sin desplazamiento): {pos}")
        
        # Si es botón izquierdo y estamos en PDF anotado, iniciar subrayado
        if event.button() == Qt.LeftButton and not self.showing_original and self.document:
            print("Iniciando modo subrayado de forma libre")
            self.highlighting = True
            
            # Ajustar por desplazamiento del ScrollArea
            adjusted_x = pos.x() + self.scroll_area.horizontalScrollBar().value()
            adjusted_y = pos.y() + self.scroll_area.verticalScrollBar().value()
            
            # Limpiar la lista de puntos anteriores e iniciar una nueva
            self.ink_points = []
            
            # Agregar el primer punto (convertido a coordenadas de PDF)
            pdf_point = self.convert_screen_to_pdf_coords(adjusted_x, adjusted_y)
            self.ink_points.append(pdf_point)
            
            # Guardar la última posición
            self.last_cursor_pos = (adjusted_x, adjusted_y)
        
        # Código existente para detección de círculos (solo para PDF original)
        elif self.showing_original:
            # Usar estas coordenadas para detectar clics
            page_num, clicked_circle = self.detect_circle_click(pos)
            if clicked_circle:
                self.circle_clicked.emit(page_num, clicked_circle)

    def set_clicks_enabled(self, enabled):
        #habilita o desabilita la deteccion de clicks en circulos
        self.clicks_enabled = enabled
    
    # Actualizar la visualización 
    # después de una rotación:

    def update_display(self):
        """
        Actualiza la visualización del PDF después de realizar modificaciones como rotaciones.
        """
        if not self.document or self.current_page >= len(self.document):
            return
        
        # Obtener la página actual
        page = self.document[self.current_page]
        
        # Renderizar la página nuevamente
        pix = page.get_pixmap(matrix=self.matrix)
        
        # Convertir a QImage y actualizar el QLabel
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        # Asumiendo que tienes un QLabel llamado image_label
        if hasattr(self, 'image_label'):
            self.page_label.setPixmap(pixmap)
        
        # Actualizar información de la página en la UI si es necesario
        self.update_page_info()

    def update_page_info(self):
        """Actualiza la información de página actual."""
        if self.document:
            self.page_info.setText(f"Página {self.current_page + 1} de {self.document.page_count}")
            
            # Actualizar la lista de cambios para la página actual (solo si existe)
            if self.has_changes_list() and hasattr(self, 'formatted_circles_by_page'):
                if self.current_page in self.formatted_circles_by_page:
                    changes = self.formatted_circles_by_page[self.current_page]
                    self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
                else:
                    self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
    
    def render_current_page(self):
        """Renderiza la página actual del PDF."""
        if not self.document:
            print("Error: No hay documento principal para renderizar")
            return
        
        # Determinar qué documento renderizar
        doc_to_render = self.original_document if self.showing_original else self.document
        
        # Verificar que el documento a renderizar existe
        if not doc_to_render:
            print("Error: No hay documento disponible para renderizar")
            return
        
        print(f"Renderizando página {self.current_page} de documento: {doc_to_render}")
        
        # Obtener página actual
        page = doc_to_render[self.current_page]
        
        # Aplicar zoom
        matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=matrix)
        
        print(f"Pixmap creado: {pix.width}x{pix.height}")
        
        # Convertir a QImage/QPixmap
        img_data = QByteArray(pix.samples)
        qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        
        print(f"QPixmap creado: {pixmap.width()}x{pixmap.height()}")
        
        # Mostrar en el label
        self.page_label.setPixmap(pixmap)
        self.page_label.resize(pixmap.size())


    def mousePressEvent(self, event):
        """Maneja el evento de presionar el botón del mouse"""
        print("mousePressEvent - Botón:", event.button(), "- PDF original:", self.showing_original)
        
        # Si es botón izquierdo y no estamos en modo de mostrar original, iniciar subrayado
        if event.button() == Qt.LeftButton and not self.showing_original and self.document:
            print("Iniciando modo subrayado de forma libre")
            self.highlighting = True
            
            # Convertir coordenadas a relativas al QLabel
            label_pos = self.page_label.mapFrom(self, event.pos())
            
            # Ajustar por desplazamiento del ScrollArea
            adjusted_x = label_pos.x() + self.scroll_area.horizontalScrollBar().value()
            adjusted_y = label_pos.y() + self.scroll_area.verticalScrollBar().value()
            
            # Limpiar la lista de puntos anteriores e iniciar una nueva
            self.ink_points = []
            
            # Agregar el primer punto (convertido a coordenadas de PDF)
            pdf_point = self.convert_screen_to_pdf_coords(adjusted_x, adjusted_y)
            self.ink_points.append(pdf_point)
            
            # Guardar la última posición
            self.last_cursor_pos = (adjusted_x, adjusted_y)
        
        # Código existente para detección de círculos (solo para PDF original)
        elif self.showing_original:
            # Obtener las coordenadas relativas al PDFViewer
            viewer_pos = event.pos()
            print("Mouse Press event")
            # Convertir a coordenadas relativas al QLabel (page_label)
            label_pos = self.page_label.mapFrom(self, viewer_pos)
            
            # Ajustar por desplazamiento del ScrollArea
            label_pos.setX(label_pos.x() + self.scroll_area.horizontalScrollBar().value())
            label_pos.setY(label_pos.y() + self.scroll_area.verticalScrollBar().value())
            
            print("Posición en viewer:", viewer_pos)
            print("Posición en label:", label_pos)
            
            # Usar estas coordenadas para detectar clics
            page_num, clicked_circle = self.detect_circle_click(label_pos)
            if clicked_circle:
                self.circle_clicked.emit(page_num, clicked_circle)
        
        # Propagar el evento para otros casos
        super(PDFViewer, self).mousePressEvent(event)

    def modify_annotations(self, page_num, clicked_circle, is_checked=None):
        """Modifica las anotaciones al hacer clic en un círculo."""
        if not hasattr(self, 'formatted_circles_by_page') or page_num not in self.formatted_circles_by_page:
            return []

        updated_annotations = []

        for circle in self.formatted_circles_by_page[page_num]:
            if circle == clicked_circle:
                # Modificar el círculo
                modified_circle = circle.copy()
                
                # Si se proporciona un valor explícito para is_checked, usarlo
                if is_checked is not None:
                    modified_circle["selected"] = is_checked
                else:
                    # De lo contrario, alternar el estado actual
                    modified_circle["selected"] = not circle.get("selected", True)
                    
                updated_annotations.append(modified_circle)
                print(f"Círculo en página {page_num} - Selected: {modified_circle['selected']}")
            else:
                updated_annotations.append(circle)

        # Guardar los cambios en la estructura de datos
        self.formatted_circles_by_page[page_num] = updated_annotations
        
        return updated_annotations
    
    def detect_circle_click(self, pos):
        if self.current_page not in self.formatted_circles_by_page:
            print("No hay círculos en esta página.")
            return None, None

        dpi_scale = self.dpi / 72.0  # Escala por DPI (72 es el valor base)
        zoom_scale = self.zoom_factor
        total_scale = dpi_scale / zoom_scale

        for circle in self.formatted_circles_by_page[self.current_page]:
            scaled_x = pos.x() * total_scale
            scaled_y = pos.y() * total_scale
            print("circulo en x", circle['x']," - circulo en y", circle['y'])
            print("Scaled x", scaled_x," - Scaled y", scaled_y)

            scaled_radius = circle['radius']

            # Calcular distancia real
            distance = sqrt((scaled_x - circle['x'])**2 + (scaled_y - circle['y'])**2)

            if distance <= scaled_radius:
                print("¡Click dentro del círculo!")
                return self.current_page, circle
            
        print(f"Click en: {pos.x()}, {pos.y()}")
        
        print("No se hizo clic en ningún círculo.")
        return None, None

    def set_circles(self, circles_by_page, page_width, page_height):
        self.page_width = page_width
        self.page_height = page_height

        print("Page width", self.page_width)
        print("Page height", self.page_height)

        """Establece los círculos detectados por página."""
        self.circles_by_page = circles_by_page
        self.formatted_circles_by_page = {}

        for page, circles in circles_by_page.items():
            # Primero formatear todos los círculos
            formatted_circles = []
            for circle in circles:
                formatted_circles.append({
                    "x": circle[0],
                    "y": circle[1],
                    "radius": circle[2],
                    "selected": True,
                })
            
            # Filtrar círculos usando el método 1 (filtrado por contenimiento completo)
            filtered_circles = self.filter_contained_circles(formatted_circles)
            self.formatted_circles_by_page[page] = filtered_circles
            
            print(f"Página {page}: {len(circles)} círculos originales, {len(self.formatted_circles_by_page[page])} después del filtrado")
        
        # Actualizar la lista de cambios si estamos en una página con cambios y si existe la lista
        if self.has_changes_list() and self.current_page in self.formatted_circles_by_page:
            print("formatted_circles",self.formatted_circles_by_page,">>>>>>>>>>>>>>>>>>>>>>>")
            self.changes_list_widget.update_changes_list(self.formatted_circles_by_page)
            
        # Agregamos una lista de cambios solo si este es el visor de PDF anotado
        if "PDF Anotado" in self.title and self.current_page >= 0:
            print("Inicializando lista de cambios para el PDF Anotado")
            self.changes_list_widget = ChangesListWidget(self)
            self.changes_list_widget.change_selected.connect(self.navigate_to_change)
            
        self.render_current_page()
        self.update_page_info()
        
    def filter_contained_circles(self, circles):
        """
        Filtra los círculos, descartando aquellos que están contenidos en otros círculos más grandes.
        Devuelve solo los círculos "contenedores" más grandes.
        """
        if not circles:
            return []
        
        # Crear una copia para no modificar la lista original
        result = circles.copy()
        circles_to_remove = set()
        
        # Comparar cada par de círculos
        for i, circle1 in enumerate(circles):
            for j, circle2 in enumerate(circles):
                if i == j:
                    continue  # No comparar un círculo consigo mismo
                
                # Calcular la distancia entre los centros
                distance = sqrt((circle1['x'] - circle2['x'])**2 + (circle1['y'] - circle2['y'])**2)
                
                # Si la distancia es menor que la diferencia de radios, un círculo está dentro del otro
                if distance <= abs(circle1['radius'] - circle2['radius']):
                    # Determinar cuál es el círculo más pequeño (contenido)
                    if circle1['radius'] < circle2['radius']:
                        circles_to_remove.add(i)  # El círculo 1 está contenido en el 2
                    elif circle2['radius'] < circle1['radius']:
                        circles_to_remove.add(j)  # El círculo 2 está contenido en el 1
        
        # Crear una nueva lista sin los círculos contenidos
        filtered_result = [circle for i, circle in enumerate(result) if i not in circles_to_remove]
        
        print(f"Se filtraron {len(circles) - len(filtered_result)} círculos contenidos.")
        return filtered_result
    
    def reload_page(self):
        """Recarga la página actual (útil cuando cambian las anotaciones)."""
        self.render_current_page()

    def next_page(self):
        """Navega a la siguiente página."""
        if self.document and self.current_page < self.document.page_count - 1:
            self.current_page += 1
            self.render_current_page()
            self.update_page_info()
            
            # Actualizar estado de los botones
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(self.current_page < self.document.page_count - 1)
    
    def prev_page(self):
        """Navega a la página anterior."""
        if self.document and self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()
            self.update_page_info()
            
            # Actualizar estado de los botones
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(True)
    
    def zoom_in(self):
        """Aumenta el zoom."""
        self.zoom_factor *= 1.25
        self.render_current_page()
    
    def zoom_out(self):
        """Reduce el zoom."""
        if self.zoom_factor > 1.0:
            self.zoom_factor /= 1.25
            self.render_current_page()
    
    def zoom_reset(self):
        """Restablece el zoom al 100%."""
        self.zoom_factor = 1.0
        self.render_current_page()