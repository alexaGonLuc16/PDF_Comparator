import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QByteArray, pyqtSignal
from math import sqrt

class PDFViewer(QWidget):
    circle_clicked = pyqtSignal(int, dict)  # Señal para comunicar clics

    def __init__(self, title="PDF Viewer"):
        super().__init__()  # No pasar argumentos aquí
        self.title = title  # Guardar el título como atributo
        self.document = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.clicks_enabled = False
        self.dpi = 300
        self.init_ui()
    
    def init_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
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
        
        layout.addWidget(title_label)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(nav_layout)
    
    def label_mouse_press_event(self, event):
        pos = event.pos()
        print("Label Press event")
        print(f"Click en QLabel (sin desplazamiento): {pos}")
        page_num, clicked_circle = self.detect_circle_click(pos)
        if clicked_circle:
            self.circle_clicked.emit(page_num, clicked_circle)

    def set_clicks_enabled(self ,enabled):
        #habilita o desabilita la deteccion de clicks en circulos
        self.clicks_enabled = enabled

    def load_pdf(self, pdf_path):
        """Carga un archivo PDF en el visor."""
        if pdf_path:
            # Cerrar documento previo si existe
            if self.document:
                self.document.close()
            
            # Abrir nuevo documento
            self.document = fitz.open(pdf_path)
            self.current_page = 0
            
            # Actualizar interfaz
            self.update_page_info()
            self.render_current_page()
            
            # Habilitar/deshabilitar botones
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(self.document.page_count > 1)
    
    def update_page_info(self):
        """Actualiza la información de página actual."""
        if self.document:
            self.page_info.setText(f"Página {self.current_page + 1} de {self.document.page_count}")
    
    def render_current_page(self):
        """Renderiza la página actual del PDF."""
        if not self.document:
            return
        
        # Obtener página actual
        page = self.document[self.current_page]
        
        # Aplicar zoom
        matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=matrix)
        
        # Convertir a QImage/QPixmap
        img_data = QByteArray(pix.samples)
        qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        
        # Mostrar en el label
        self.page_label.setPixmap(pixmap)
        self.page_label.resize(pixmap.size())

    def mousePressEvent(self, event):
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

    def modify_annotations(self, page_num, clicked_circle):
        """Modifica las anotaciones al hacer clic en un círculo."""
        if page_num not in self.formatted_circles_by_page:
            return []

        updated_annotations = []

        print(page_num)

        for circle in self.formatted_circles_by_page[page_num]:
            if circle == clicked_circle:
                # Modificar el círculo si es necesario (ejemplo: marcarlo como seleccionado)
                modified_circle = circle.copy()
                modified_circle["selected"] = not circle.get("selected", True)  # Alternar estado
                updated_annotations.append(modified_circle)
                print("--Selected",modified_circle["selected"])
            else:
                updated_annotations.append(circle)
                #circle["selected"] = True 
                print("Selected", circle["selected"])

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