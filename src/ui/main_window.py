import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QFileDialog, QLabel, QCheckBox,
                            QProgressBar, QSpinBox, QGroupBox, QRadioButton,QLineEdit,QButtonGroup)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import fitz  # PyMuPDF - importante para la función toggle_circle_visibility

from src.pdf_processor import PDFProcessor
from src.image_comparator import ImageComparator
from src.circle_detector import CircleDetector
from src.pdf_annotator import PDFAnnotator
from src.ui.pdf_viewer import PDFViewer

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, dict)
    
    def __init__(self, pdf1, pdf2, output_path, dpi, threshold, eps, min_samples, selected_pages = None):
        super().__init__()
        self.pdf1 = pdf1
        self.pdf2 = pdf2
        self.output_path = output_path
        self.dpi = dpi
        self.threshold = threshold
        self.eps = eps
        self.min_samples = min_samples
        self.selected_pages = selected_pages
        self.updated_annotations = {}

    def run(self):
        # Inicializar componentes
        # Usar rutas absolutas para los directorios
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(base_dir, 'data', 'temp')
        output_dir = os.path.join(base_dir, 'data', 'output')
        
        pdf_processor = PDFProcessor()
        image_comparator = ImageComparator(threshold=self.threshold)
        circle_detector = CircleDetector(eps=self.eps, min_samples=self.min_samples)
        pdf_annotator = PDFAnnotator(output_dir)

        source_pdf1 = self.pdf1
        source_pdf2 = self.pdf2

        # Paso 2: Convertir PDFs a imágenes (solo páginas seleccionadas)
        self.progress.emit(20)
        images1 = pdf_processor.pdf_to_images(source_pdf1, dpi=self.dpi, selected_pages=self.selected_pages)
        self.progress.emit(35)
        images2 = pdf_processor.pdf_to_images(source_pdf2, dpi=self.dpi, selected_pages=self.selected_pages)
        self.progress.emit(50)
        
        # El resto del código sigue igual...
        # Paso 3: Comparar imágenes y obtener diferencias
        circles_by_page = {}
        
        total_pages = min(len(images1), len(images2))
        for i, (img1, img2) in enumerate(zip(images1, images2)):
            # Comparar imágenes y obtener coordenadas de diferencias
            diff_coords,_ = image_comparator.find_differences(img1, img2)
            #print("Differences found: ", diff_coords[:5])  # Muestra solo 5 puntos para verificar

            # Paso 4: Agrupar diferencias en círculos
            if diff_coords:
                circles = circle_detector.group_points_into_circles(diff_coords)
                circles = circle_detector.merge_overlapping_circles(circles)
                
                
                if circles:
                    if self.selected_pages != None:
                        circles_by_page[self.selected_pages[i]] = circles
                    else:
                        circles_by_page[i] = circles

            # Actualizar progreso
            progress = 50 + int((i + 1) / total_pages * 40)
            self.progress.emit(progress)
        
        # Paso 5: Anotar el PDF con círculos
        # Usar el PDF2 reparado si está disponible
        pdf_annotator.add_circle_annotations(source_pdf2, circles_by_page, self.output_path, dpi=self.dpi)
        
        # Guardar información de círculos para uso en la UI
        pdf_annotator.save_circles_to_json(circles_by_page, f"{self.output_path}.json")
        
        self.progress.emit(100)
        self.finished.emit(self.output_path, circles_by_page)
        
        #habilitar click event para descarte de circulos
        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Diff Tool")
        self.setMinimumSize(1200, 800)

        #Limpiar directorio temporal a inicio de la ejecucion
        self.clean_temp_directory()
        
        print("Inicializando UI en MainWindow...")
        self.init_ui()
    
    def init_ui(self):
        # Crear layout principal
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Área de configuración
        config_layout = QHBoxLayout()
        
        # Selección de archivos
        file_group = QGroupBox("Selección de archivos")
        file_layout = QVBoxLayout(file_group)
        
        # PDF original
        pdf1_layout = QHBoxLayout()
        self.pdf1_label = QLabel("PDF Original:")
        self.pdf1_path = QLabel("No seleccionado")
        self.pdf1_button = QPushButton("Seleccionar")
        self.pdf1_button.clicked.connect(self.select_pdf1)
        
        pdf1_layout.addWidget(self.pdf1_label)
        pdf1_layout.addWidget(self.pdf1_path)
        pdf1_layout.addWidget(self.pdf1_button)
        
        # PDF modificado
        pdf2_layout = QHBoxLayout()
        self.pdf2_label = QLabel("PDF Modificado:")
        self.pdf2_path = QLabel("No seleccionado")
        self.pdf2_button = QPushButton("Seleccionar")
        self.pdf2_button.clicked.connect(self.select_pdf2)
        
        pdf2_layout.addWidget(self.pdf2_label)
        pdf2_layout.addWidget(self.pdf2_path)
        pdf2_layout.addWidget(self.pdf2_button)
        
        # Guardar como
        save_layout = QHBoxLayout()
        self.save_label = QLabel("Guardar como:")
        self.save_path = QLabel("No seleccionado")
        self.save_button = QPushButton("Seleccionar")
        self.save_button.clicked.connect(self.select_save_path)
        
        save_layout.addWidget(self.save_label)
        save_layout.addWidget(self.save_path)
        save_layout.addWidget(self.save_button)
        
        file_layout.addLayout(pdf1_layout)
        file_layout.addLayout(pdf2_layout)
        file_layout.addLayout(save_layout)
        
        # Parámetros
        param_group = QGroupBox("Parámetros")
        param_layout = QVBoxLayout(param_group)
        
        # DPI
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("DPI:"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        dpi_layout.addWidget(self.dpi_spin)
        
        # Umbral
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Umbral:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 50)
        self.threshold_spin.setValue(10)
        threshold_layout.addWidget(self.threshold_spin)
        
        # Epsilon
        eps_layout = QHBoxLayout()
        eps_layout.addWidget(QLabel("Epsilon:"))
        self.eps_spin = QSpinBox()
        self.eps_spin.setRange(1, 100)
        self.eps_spin.setValue(15)
        eps_layout.addWidget(self.eps_spin)
        
        # Min Samples
        min_samples_layout = QHBoxLayout()
        min_samples_layout.addWidget(QLabel("Min Samples:"))
        self.min_samples_spin = QSpinBox()
        self.min_samples_spin.setRange(1, 50)
        self.min_samples_spin.setValue(5)
        min_samples_layout.addWidget(self.min_samples_spin)
        
        param_layout.addLayout(dpi_layout)
        param_layout.addLayout(threshold_layout)
        param_layout.addLayout(eps_layout)
        param_layout.addLayout(min_samples_layout)
        
        page_select_layout = QHBoxLayout()
        page_select_layout.addWidget(QLabel("Páginas a comparar:"))

        self.all_pages_radio = QRadioButton("Todas")
        self.all_pages_radio.setChecked(True)
        self.specific_pages_radio = QRadioButton("Específicas")
        self.specific_pages_input = QLineEdit()
        self.specific_pages_input.setPlaceholderText("Ej: 1-5,8,10-12")
        self.specific_pages_input.setEnabled(False)

        page_select_group = QButtonGroup(self)
        page_select_group.addButton(self.all_pages_radio)
        page_select_group.addButton(self.specific_pages_radio)

        self.all_pages_radio.toggled.connect(self.toggle_pages_input)
        self.specific_pages_radio.toggled.connect(self.toggle_pages_input)

        page_select_layout.addWidget(self.all_pages_radio)
        page_select_layout.addWidget(self.specific_pages_radio)
        page_select_layout.addWidget(self.specific_pages_input)

        param_layout.addLayout(page_select_layout)


        # Botones de acción
        action_group = QGroupBox("Acciones")
        action_layout = QVBoxLayout(action_group)
        
        self.compare_button = QPushButton("Comparar PDFs")
        self.compare_button.clicked.connect(self.start_comparison)
        self.compare_button.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        action_layout.addWidget(self.compare_button)
        action_layout.addWidget(self.progress_bar)
        
        config_layout.addWidget(file_group, 3)
        config_layout.addWidget(param_group, 2)
        config_layout.addWidget(action_group, 1)
        
        # Área de visualización
        view_layout = QHBoxLayout()
        
        # Visor original
        self.original_viewer = PDFViewer("PDF Original")
        # Visor anotado
        self.annotated_viewer = PDFViewer("PDF Anotado")
        self.toggle_circles = QCheckBox("Mostrar círculos")
        self.toggle_circles.setChecked(True)
        self.toggle_circles.stateChanged.connect(self.toggle_circle_visibility)
        
        view_layout.addWidget(self.original_viewer, 1)
        
        annotated_container = QWidget()
        annotated_layout = QVBoxLayout(annotated_container)
        annotated_layout.addWidget(self.annotated_viewer)
        annotated_layout.addWidget(self.toggle_circles)
        
        view_layout.addWidget(annotated_container, 1)
        
        # Añadir layouts al layout principal
        main_layout.addLayout(config_layout, 1)
        main_layout.addLayout(view_layout, 4)
        
        self.setCentralWidget(central_widget)
        
        # Variables de estado
        self.pdf1_file = None
        self.pdf2_file = None
        self.output_file = None
        self.circles_by_page = {}
        
        #flag para habilitar circle_click event
        self.circle_clicked_flag = False
        self.annotated_viewer.circle_clicked.connect(self.handle_circle_click)
        self.annotated_viewer.set_clicks_enabled(False)#inicialmente desabilitado

        print("UI de MainWindow inicializada")
        
    def handle_circle_click(self, page_num, clicked_circle):
        """Maneja clics en círculos para actualizar anotaciones."""
        print(f"Círculo clickeado en página {page_num}: {clicked_circle}")
        
        # Modificación del círculo si es necesario o actualización
        self.updated_annotations = self.annotated_viewer.modify_annotations(page_num, clicked_circle)
        # Llamar a update_annotations para reflejar cambios
        self.update_annotations(page_num, self.updated_annotations)
    
    def update_annotations(self, page_num, new_annotations, dpi=300):
        """Actualiza las anotaciones del PDF según las modificaciones del usuario."""
        if not hasattr(self.annotated_viewer, 'document') or not self.annotated_viewer.document:
            print("No hay un documento cargado en annotated_viewer.")
            return

        try:
            page = self.annotated_viewer.document[page_num]
            
            # Verificar que page es un objeto válido
            print(f"Page type: {type(page)}")
            print(f"Available methods: {dir(page)}")

            # Factor de escala para convertir de coordenadas de imagen a PDF
            scale_factor = 72 / dpi

            # Eliminar anotaciones previas de tipo "Circle"
            annot = page.first_annot
            while annot:
                next_annot = annot.next  # Guardar referencia antes de eliminar
                if annot.type[1] == 'Circle':
                    page.delete_annot(annot)  # Método correcto para eliminar anotaciones
                annot = next_annot  # Pasar al siguiente

            # Agregar nuevas anotaciones con escala ajustada
            for circle in new_annotations:
                if circle["selected"] == False:
                    continue
                else:
                    x_pdf = circle['x'] * scale_factor
                    y_pdf = circle['y'] * scale_factor
                    radius_pdf = circle['radius'] * scale_factor

                    # Crear anotación de círculo
                    circle_annot = page.add_circle_annot(
                        (x_pdf - radius_pdf, y_pdf - radius_pdf, x_pdf + radius_pdf, y_pdf + radius_pdf)
                    )

                    # Configurar propiedades
                    circle_annot.set_border(width=2)
                    circle_annot.set_colors(stroke=(0, 0, 1))  # Azul
                    circle_annot.update(opacity=0.7)
                    print("Anotacion agregada")

            # Refrescar visor para mostrar actualizaciones
            self.annotated_viewer.reload_page()

        except Exception as e:
            print(f"Error al actualizar anotaciones: {e}")


    def clean_temp_directory(self):
        """Limpia el directorio temporal al inicio de la aplicación"""
        try:
            # Obtener la ruta del directorio temporal
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(base_dir, 'data', 'temp')
            
            print(f"Limpiando directorio temporal al inicio: {temp_dir}")
            
            # Borrar todas las imágenes JPG en el directorio temporal
            for filename in os.listdir(temp_dir):
                if filename.endswith('.jpg'):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Borrada imagen temporal anterior: {filename}")
                    except Exception as e:
                        print(f"Error al borrar {filename}: {e}")
        except Exception as e:
            print(f"Error durante la limpieza inicial: {e}")

    #metodo de alternancia para el campo de texto
    def toggle_pages_input(self, checked):
        self.specific_pages_input.setEnabled(self.specific_pages_radio.isChecked())
        
    #método para analizar la selección de páginas
    def parse_page_selection(self, selection_str):
        """
        Convierte una cadena como "1-5,8,10-12" en una lista de números de página [1,2,3,4,5,8,10,11,12]
        """
        pages = []
        
        if not selection_str.strip():
            return None  # Cadena vacía significa todas las páginas
        
        parts = selection_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Rango de páginas (ej: 1-5)
                start, end = part.split('-')
                try:
                    start_page = int(start.strip())
                    end_page = int(end.strip())
                    if start_page < 1 or end_page < start_page:
                        raise ValueError("Rango de páginas inválido")
                    pages.extend(range(start_page, end_page + 1))
                except ValueError:
                    raise ValueError(f"Rango inválido: {part}")
            else:
                # Página individual
                try:
                    page = int(part)
                    if page < 1:
                        raise ValueError("El número de página debe ser positivo")
                    pages.append(page)
                except ValueError:
                    raise ValueError(f"Número de página inválido: {part}")
        
        # Convertir a índices base-0 para uso interno
        return [p - 1 for p in pages]  # Restar 1 porque las páginas se indexan desde 0 internamente

    def select_pdf1(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF Original", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf1_file = file_path
            self.pdf1_path.setText(os.path.basename(file_path))
            self.original_viewer.load_pdf(file_path)
            self.update_compare_button()
    
    def select_pdf2(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF Modificado", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf2_file = file_path
            self.pdf2_path.setText(os.path.basename(file_path))
            self.update_compare_button()
    
    def select_save_path(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF Anotado", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_file = file_path
            self.save_path.setText(os.path.basename(file_path))
            self.update_compare_button()
    
    def update_compare_button(self):
        # Comprueba si ambas rutas existen y no son None
        if self.pdf1_file is not None and self.pdf2_file is not None:
            self.compare_button.setEnabled(True)
        else:
            self.compare_button.setEnabled(False)

    def start_comparison(self):
        if not self.pdf1_file or not self.pdf2_file:
            return
        
        # Si no se seleccionó una ruta de salida, crear una predeterminada
        if not self.output_file:
            # Usar ruta absoluta para salida
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, 'data', 'output')
            self.output_file = os.path.join(output_dir, f"annotated_{os.path.basename(self.pdf2_file)}")
            self.save_path.setText(os.path.basename(self.output_file))
        
        # Obtener las páginas a comparar
        selected_pages = None  # None significa todas las páginas
        if self.specific_pages_radio.isChecked():
            try:
                selected_pages = self.parse_page_selection(self.specific_pages_input.text())
                if not selected_pages:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Selección de páginas", 
                                    "Formato de páginas inválido. Utilizando todas las páginas.")
                    selected_pages = None
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", 
                                f"Error al interpretar la selección de páginas: {e}")
                selected_pages = None
        
        # Deshabilitar botones durante el procesamiento
        self.compare_button.setEnabled(False)
        self.pdf1_button.setEnabled(False)
        self.pdf2_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
        # Crear solo UNA instancia del WorkerThread
        self.worker = WorkerThread(
            self.pdf1_file, 
            self.pdf2_file, 
            self.output_file,
            self.dpi_spin.value(),
            self.threshold_spin.value(),
            self.eps_spin.value(),
            self.min_samples_spin.value(),
            selected_pages
        )
        
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.comparison_finished)
        self.worker.start()

    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def comparison_finished(self, output_path, circles_by_page):
        # Habilitar circle_clicked event
        self.circle_clicked_flag = True
        self.annotated_viewer.set_clicks_enabled(True)#habilitar los clicks
        # Habilitar botones
        self.compare_button.setEnabled(True)
        self.pdf1_button.setEnabled(True)
        self.pdf2_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        # Guardar datos de círculos
        self.circles_by_page = circles_by_page
        
        # Cargar PDF anotado
        self.annotated_viewer.load_pdf(output_path)
        
        # Actualizar visibilidad de círculos
        self.annotated_viewer.set_circles(circles_by_page)
        # IMPORTANTE: Aplicar inmediatamente el filtrado a las anotaciones visibles
        for page_num in self.annotated_viewer.formatted_circles_by_page:
            self.update_annotations(page_num, self.annotated_viewer.formatted_circles_by_page[page_num])
        
        # Actualizar visibilidad de círculos
        self.toggle_circle_visibility(self.toggle_circles.isChecked())
        
    
    def toggle_circle_visibility(self, state):
        if hasattr(self.annotated_viewer, 'document') and self.annotated_viewer.document:
            try:
                for page_num in range(self.annotated_viewer.document.page_count):
                    page = self.annotated_viewer.document[page_num]
                    for annot in page.annots():
                        if annot.type[1] == 'Circle':
                            if state: 
                                annot.set_flags(0)
                            else: 
                                annot.set_flags(3)
                            annot.update()
                
                # Refrescar vista
                current_page = self.annotated_viewer.current_page
                self.annotated_viewer.reload_page()
            except Exception as e:
                print(f"Error al cambiar visibilidad de círculos: {e}")
        
    def closeEvent(self, event):
        # Si hay un thread activo, detenerlo adecuadamente
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()  # Esperar a que termine
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(base_dir, 'data', 'temp')
            
            # Identificadores de archivos procesados
            pdf_identifiers = []
            if self.pdf1_file:
                pdf_identifiers.append(os.path.basename(self.pdf1_file))
            if self.pdf2_file:
                pdf_identifiers.append(os.path.basename(self.pdf2_file))
            
            # Solo borrar imágenes relacionadas con estos PDFs
            for filename in os.listdir(temp_dir):
                if filename.endswith('.jpg') and any(pdf_id in filename for pdf_id in pdf_identifiers):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Borrada imagen: {filename}")
                    except Exception as e:
                        print(f"Error al borrar {filename}: {e}")
            
            event.accept()
        except Exception as e:
            print(f"Error durante la limpieza: {e}")
            event.accept()