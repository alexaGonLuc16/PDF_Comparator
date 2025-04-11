import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QSizePolicy, QListWidget, 
                            QListWidgetItem, QFrame, QTreeWidget,QTreeWidgetItem)
from PyQt5.QtGui import QPixmap, QImage, QKeyEvent
from PyQt5.QtCore import Qt, QByteArray, pyqtSignal
from math import sqrt

class ChangesListWidget(QWidget):
    change_selected = pyqtSignal(int, dict, bool)  # Página, cambio, activado
    
    def __init__(self, parent=None):
        super(ChangesListWidget, self).__init__(parent)
        self.changes_by_page = {}
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Título
        title_label = QLabel("Cambios Detectados")
        title_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
        
        # Árbol para mostrar cambios de forma jerárquica
        self.changes_tree = QTreeWidget(self)
        self.changes_tree.setHeaderLabels(["Página/Cambio", "Activado"])
        self.changes_tree.setColumnWidth(0, 150)
        self.changes_tree.itemClicked.connect(self.on_item_clicked)
        
        layout.addWidget(title_label)
        layout.addWidget(self.changes_tree)
    
    def update_changes_list(self, formatted_circles_by_page):
        """Actualiza la lista completa de cambios por página"""
        print("Update changes list ------------------------------->")
        if not hasattr(self, 'changes_tree') or self.changes_tree is None:
            print("Error: changes_tree no está inicializado")
            return
        print("Si changes ------------------------------->")
        self.changes_tree.clear()
        self.changes_by_page = formatted_circles_by_page
        print("changes by page",self.changes_by_page)
        
        # Crear un elemento en el árbol para cada página con cambios
        for page_num, changes in sorted(formatted_circles_by_page.items()):
            print("Si changes ------------------------------->")
            if changes:
                print("No changes ------------------------------->")
                page_item = QTreeWidgetItem(self.changes_tree)
                page_item.setText(0, f"Página {page_num + 1} ({len(changes)} cambios)")
                page_item.setData(0, 256 , {"type": "page", "page": page_num})
                
                # Crear sub-elementos para cada cambio en la página
                for i, change in enumerate(changes):
                    change_item = QTreeWidgetItem(page_item)
                    change_item.setText(0, f"Cambio {i+1}")
                    change_item.setData(0, 256, {"type": "change", "page": page_num, "index": i})
                    
                    print("tipo change", type(change))
                    print("contenido de change", change)
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
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(nav_layout)
        
        # Agregamos una lista de cambios solo si este es el visor de PDF anotado
        if "PDF Anotado" in self.title:
            print("Inicializando lista de cambios para el PDF Anotado")
            self.changes_list_widget = ChangesListWidget(self)
            self.changes_list_widget.change_selected.connect(self.navigate_to_change)
            #layout.addWidget(self.changes_list_widget)
            
    
    def keyPressEvent(self, event):
        """Captura eventos de tecla presionada"""
        # Detectar si se presiona la tecla Q
        if event.key() == Qt.Key_Q and not event.isAutoRepeat():
            print("Tecla Q presionada - mostrando PDF original")
            self.show_pdf(is_original=True)
            return
        
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

    def load_pdf(self, pdf_path, original_pdf_path=None):
        """Carga un archivo PDF en el visor."""
        if pdf_path:
            # Cerrar documento previo si existe
            if self.document:
                self.document.close()
            
            # Abrir nuevo documento
            self.document = fitz.open(pdf_path)
            self.current_page = 0
            
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
        self.zoom_factor = 1.5
        #self.zoom_factor = 2.0

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
        
        #imprimir los cambios con zoom de 100
        print("Coordenadas del cambio en x: ", change['x']/total_scale)
        print("Coordenadas dle cambio en y: ", change['y']/total_scale)
        print("zoom de 100")

        # Calcular la posición del cambio en el pixmap con el zoom actual
        change_x = (change['x'] * self.zoom_factor)/total_scale
        change_y = (change['y'] * self.zoom_factor)/total_scal
        # 
        # Calcular la posición del cambio en el pixmap con el zoom actual
        #change_x = (change['x'])/total_scale
        #change_y = (change['y'])/total_scale

        #imprimir los cambios con zoom de 150
        print("zoom de 150")
        print("Coordenadas del cambio en x: ", change_x)
        print("Coordenadas dle cambio en y: ", change_y)
        
        # Ajustar el scroll para centrar el cambio
        h_value = max(0, int(change_x - self.scroll_area.width()))
        v_value = max(0, int(change_y - self.scroll_area.height()))

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
        pos = event.pos()
        print("Label Press event")
        print(f"Click en QLabel (sin desplazamiento): {pos}")
        page_num, clicked_circle = self.detect_circle_click(pos)
        if clicked_circle:
            self.circle_clicked.emit(page_num, clicked_circle)

    def set_clicks_enabled(self, enabled):
        #habilita o desabilita la deteccion de clicks en circulos
        self.clicks_enabled = enabled
    
    def update_page_info(self):
        """Actualiza la información de página actual."""
        if self.document:
            self.page_info.setText(f"Página {self.current_page + 1} de {self.document.page_count}")
            
            # Actualizar la lista de cambios para la página actual (solo si existe)
            if self.has_changes_list() and hasattr(self, 'formatted_circles_by_page'):
                if self.current_page in self.formatted_circles_by_page:
                    changes = self.formatted_circles_by_page[self.current_page]
                    print("formatted_circles",self.formatted_circles_by_page,">>>>>>>>>>>>>>>>>>>>>>>")
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
        if not self.showing_original:
            return

        # Obtener las coordenadas relativas al PDFViewer
        viewer_pos = event.pos()
        print("Mouse Press event")
        # Convertir a coordenadas relativas al QLabel (page_label)
        # Esto tiene en cuenta la posición del QLabel dentro del ScrollArea
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
            print("circulo en x", pos.x()," - circulo en y", pos.y())
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

    def set_circles(self, circles_by_page):
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
            
        self.render_current_page()
        
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
        self.zoom_factor /= 1.25
        self.render_current_page()
    
    def zoom_reset(self):
        """Restablece el zoom al 100%."""
        self.zoom_factor = 1.0
        self.render_current_page()