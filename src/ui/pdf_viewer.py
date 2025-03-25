import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QScrollArea, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QByteArray

class PDFViewer(QWidget):
    def __init__(self, title="PDF Viewer"):
        super().__init__()  # No pasar argumentos aquí
        self.title = title  # Guardar el título como atributo
        self.document = None
        self.current_page = 0
        self.zoom_factor = 1.0
        
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