# Integración de la carga/guardado JSON en la aplicación principal

# Importaciones necesarias
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QSplitter, QHBoxLayout
from PyQt5.QtCore import Qt
import sys
import os

# Importar componentes de la aplicación
from ui.pdf_viewer import PDFViewer
from json_loader_ui import JsonLoaderUI
from image_comparator import ImageComparator
from pdf_annotator import PDFAnnotator

class PDFComparatorApp(QMainWindow):
    def __init__(self):
        super(PDFComparatorApp, self).__init__()
        self.setWindowTitle("PDF Comparator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Pestañas principales
        self.tabs = QTabWidget()
        
        # Pestaña de comparación
        self.comparison_tab = QWidget()
        self.setup_comparison_tab()
        self.tabs.addTab(self.comparison_tab, "Comparar PDFs")
        
        # Pestaña de carga/guardado JSON
        self.json_tab = QWidget()
        self.setup_json_tab()
        self.tabs.addTab(self.json_tab, "Cargar/Guardar Cambios")
        
        # Agregar pestañas al layout principal
        main_layout.addWidget(self.tabs)
    
    def setup_comparison_tab(self):
        """Configura la pestaña de comparación de PDFs."""
        layout = QVBoxLayout(self.comparison_tab)
        
        # Crear un divisor horizontal para los visores de PDF
        splitter = QSplitter(Qt.Horizontal)
        
        # Visor de PDF original
        self.original_viewer = PDFViewer("PDF Original")
        
        # Visor de PDF anotado
        self.annotated_viewer = PDFViewer("PDF Anotado")
        
        # Agregar visores al divisor
        splitter.addWidget(self.original_viewer)
        splitter.addWidget(self.annotated_viewer)
        
        # Configurar ancho relativo (60% original, 40% anotado)
        splitter.setSizes([600, 400])
        
        # Agregar divisor al layout
        layout.addWidget(splitter)
        
        # Layout para botones de control
        control_layout = QHBoxLayout()
        
        # Aquí irían botones para comparar PDFs, etc.
        # (Este código dependería de tu implementación específica)
        
        layout.addLayout(control_layout)
        
        # Conectar señales entre visores
        # (Por ejemplo, para sincronizar navegación)
        
    def setup_json_tab(self):
        """Configura la pestaña de carga/guardado de JSON."""
        layout = QVBoxLayout(self.json_tab)
        
        # Crear un divisor horizontal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo: Visor de PDF
        self.json_pdf_viewer = PDFViewer("PDF con Cambios Cargados")
        
        # Panel derecho: Controles de JSON
        json_control_widget = QWidget()
        self.json_loader_ui = JsonLoaderUI(self.json_pdf_viewer)
        
        # Configurar layout para el panel de control
        json_control_layout = QVBoxLayout(json_control_widget)
        json_control_layout.addWidget(self.json_loader_ui)
        
        # Agregar paneles al divisor
        splitter.addWidget(self.json_pdf_viewer)
        splitter.addWidget(json_control_widget)
        
        # Configurar ancho relativo (70% visor, 30% controles)
        splitter.setSizes([700, 300])
        
        # Agregar divisor al layout
        layout.addWidget(splitter)
    
    def load_pdf_for_comparison(self, pdf1_path, pdf2_path):
        """Carga dos PDFs para comparación."""
        # Cargar PDFs en los visores
        self.original_viewer.load_pdf(pdf1_path)
        self.annotated_viewer.load_pdf(pdf2_path)
        
        # Cambiar a la pestaña de comparación
        self.tabs.setCurrentIndex(0)
    
    def load_pdf_with_json(self, pdf_path, json_path):
        """Carga un PDF con sus cambios desde un archivo JSON."""
        # Esta función podría ser llamada desde fuera de la clase
        self.json_loader_ui.pdf_path = pdf_path
        self.json_loader_ui.json_path = json_path
        self.json_loader_ui.update_load_status()
        self.json_loader_ui.apply_changes()
        
        # Cambiar a la pestaña de JSON
        self.tabs.setCurrentIndex(1)

# Punto de entrada de la aplicación
def main():
    app = QApplication(sys.argv)
    window = PDFComparatorApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
