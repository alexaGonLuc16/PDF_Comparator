import tempfile
import os
import shutil
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QAction, QMenu, QToolBar, QToolButton, 
    QMessageBox, QDialog, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog
)
from PyQt5.QtGui import QIcon, QTransform, QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal, QByteArray

class PDFRotator:
    """Clase para manejar la rotación de archivos PDF."""
    
    def __init__(self, document_handler):
        """
        Inicializa el rotador de PDF.
        
        Args:
            document_handler: Objeto que maneja el documento PDF actual
                             (debe tener atributos doc y current_page)
        """
        self.document_handler = document_handler
        # Nueva variable para rastrear si hay cambios sin guardar
        self.has_unsaved_changes = False
        self.temp_path = None
    
    def rotate_page(self, page_index, degrees):
        """
        Rota una página específica del PDF.
        
        Args:
            page_index: Índice de la página (comenzando en 0)
            degrees: Grados de rotación (90, 180, 270)
        
        Returns:
            bool: True si la rotación fue exitosa, False en caso contrario
        """
        if not self.document_handler.document:
            return False
        
        try:
            # Obtiene el valor actual de rotación
            page = self.document_handler.document[page_index]
            current_rotation = page.rotation
            
            # Calcula la nueva rotación (suma y normaliza a 0, 90, 180, 270)
            new_rotation = (current_rotation + degrees) % 360
            
            # Establece la nueva rotación para la página
            page.set_rotation(new_rotation)

            # Aplicar zoom
            matrix = fitz.Matrix(self.document_handler.zoom_factor, self.document_handler.zoom_factor)
            # Get the pixmap of the rotated page
            pix = page.get_pixmap(matrix =  matrix)
            print(f"Pixmap creado: {pix.width}x{pix.height}")

            # Convertir a QImage/QPixmap
            img_data = QByteArray(pix.samples)
            qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            print(f"QPixmap creado: {pixmap.width()}x{pixmap.height()}")
            
            # Mostrar en el label
            self.document_handler.page_label.setPixmap(pixmap)
            self.document_handler.page_label.resize(pixmap.size())

            # Marcar que hay cambios sin guardar
            self.has_unsaved_changes = True

            return True
        except Exception as e:
            print(f"Error al rotar la página: {str(e)}")
            return False
    
    def rotate_all_pages(self, degrees):
        """
        Rota todas las páginas del PDF.
        
        Args:
            degrees: Grados de rotación (90, 180, 270)
        
        Returns:
            bool: True si la rotación fue exitosa, False en caso contrario
        """
        if not self.document_handler.document:
            return False
        
        try:
            for page_idx in range(len(self.document_handler.document)):
                self.rotate_page(page_idx, degrees)
            return True
        except Exception as e:
            print(f"Error al rotar todas las páginas: {str(e)}")
            return False
    
    def save_document(self, file_path=None):
        """
        Guarda el documento con las rotaciones aplicadas.
        
        Args:
            file_path: Ruta donde guardar el archivo. Si es None, 
                    se sobrescribe el archivo actual.
        
        Returns:
            bool: True si el guardado fue exitoso, False en caso contrario
        """
        if not self.document_handler.document:
            return False
        
        try:
            # Si no se proporciona ruta, usar la ruta actual del documento
            save_path = file_path or self.document_handler.file_path
            current_page = self.document_handler.current_page  # Guardar la página actual
            
            # Guardar en un archivo temporal primero
            # Crear un archivo temporal
            temp_fd, self.temp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(temp_fd)
            
            # Guardar en el archivo temporal
            self.document_handler.document.save(
                self.temp_path,
                garbage=4,  # Máxima limpieza
                deflate=True,  # Comprimir
                clean=True  # Limpiar y reducir tamaño
            )

            # Cerrar el documento actual (importante para liberar el archivo)
            self.document_handler.document.close()
            
            # Reemplazar el archivo de destino con el temporal
            shutil.copy2(self.temp_path, save_path)
            
            # Eliminar el archivo temporal
            os.unlink(self.temp_path)
            
            # Reiniciar la variable de cambios sin guardar
            self.has_unsaved_changes = False
            
            return True, current_page
        except Exception as e:
            print(f"Error al guardar el documento: {str(e)}")
            return False


class RotationDialog(QDialog):
    """Diálogo para confirmar y seleccionar opciones de rotación."""
    
    def __init__(self, parent=None, title ="Rotate PDF"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(300, 150)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Etiqueta informativa
        self.info_label = QLabel("Selecciona la rotación que deseas aplicar:")
        layout.addWidget(self.info_label)
        
        # Botones de rotación
        btn_layout = QHBoxLayout()
        
        self.rotate90_btn = QPushButton("Rotate 90° ↻")
        self.rotate180_btn = QPushButton("Rotate 180° ↻↻")
        self.rotate270_btn = QPushButton("Rotate 270° ↺")
        
        btn_layout.addWidget(self.rotate90_btn)
        btn_layout.addWidget(self.rotate180_btn)
        btn_layout.addWidget(self.rotate270_btn)
        
        layout.addLayout(btn_layout)
        
        # Opción para rotar todas las páginas o solo la actual
        self.scope_layout = QHBoxLayout()
        self.current_page_btn = QPushButton("Current page")
        self.all_pages_btn = QPushButton("All pages")
        
        self.scope_layout.addWidget(self.current_page_btn)
        self.scope_layout.addWidget(self.all_pages_btn)
        
        layout.addLayout(self.scope_layout)
        
        # Botón cancelar
        self.cancel_btn = QPushButton("Cancelar")
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        # Conectar señales
        self.rotate90_btn.clicked.connect(lambda: self.accept_rotation(90))
        self.rotate180_btn.clicked.connect(lambda: self.accept_rotation(180))
        self.rotate270_btn.clicked.connect(lambda: self.accept_rotation(270))
        self.current_page_btn.clicked.connect(lambda: self.set_scope("current"))
        self.all_pages_btn.clicked.connect(lambda: self.set_scope("all"))
        self.cancel_btn.clicked.connect(self.reject)
        
        # Valores iniciales
        self.rotation_degrees = None
        self.rotation_scope = None
    
    def accept_rotation(self, degrees):
        """Almacena el valor de rotación seleccionado."""
        self.rotation_degrees = degrees
        if self.rotation_scope:
            self.accept()
    
    def set_scope(self, scope):
        """Almacena el alcance de la rotación."""
        self.rotation_scope = scope
        if self.rotation_degrees:
            self.accept()
    
    def get_rotation_params(self):
        """Devuelve los parámetros de rotación seleccionados."""
        return self.rotation_degrees, self.rotation_scope


class PDFRotationUIHandler:
    """Manejador de la interfaz de usuario para la rotación de PDF."""
    
    def __init__(self, main_window, document_handler, secondary_pdf = None, title = "Rotate PDF"):
        """
        Inicializa el manejador de UI para rotación.
        
        Args:
            main_window: Ventana principal de la aplicación (donde añadir UI)
            document_handler: Objeto que maneja el documento PDF actual
        """
        self.main_window = main_window
        self.document_handler = document_handler
        self.secondary_pdf = secondary_pdf
        self.rotator = PDFRotator(document_handler)
        self.file_path = None
        self.title = title
        self.rotate_both = False

        # Inicializar elementos de UI
        self.setup_ui_elements()
    
    def setup_ui_elements(self):
        """Configura los elementos de UI para la rotación."""
        # Crear acciones
        self.rotate_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/rotate.png"), self.title , self.main_window)
        self.rotate_action.setStatusTip("Rotar páginas del PDF")
        self.rotate_action.triggered.connect(self.show_rotation_dialog)
        
        # Crear acción de guardar (nueva)
        self.save_action = QAction(QIcon("C:/PDF_Comparator/src/ui/icons/save.png"), "Save changes", self.main_window)
        self.save_action.setStatusTip("Guardar los cambios realizados al PDF")
        self.save_action.triggered.connect(self.save_document)
        
        # Añadir a menú (asumiendo que existe un menú 'Herramientas')
        # Si no existe, necesitarías crear el menú primero
        tools_menu = None
        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == "Tools":
                tools_menu = menu
                break
        
        if not tools_menu:
            tools_menu = self.main_window.menuBar().addMenu("Tools")
        
        tools_menu.addAction(self.rotate_action)
        
        # Añadir el botón de guardar al menú Archivo
        file_menu = None
        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == "File":
                file_menu = menu
                break
        
        if not file_menu:
            file_menu = self.main_window.menuBar().addMenu("File")
        
        file_menu.addAction(self.save_action)
        
        # Añadir a la barra de herramientas
        # Asumiendo que existe una barra de herramientas
        toolbar = self.main_window.findChild(QToolBar)
        if toolbar:
            toolbar.addAction(self.rotate_action)
        else:
            # Crear una barra de herramientas si no existe
            toolbar = self.main_window.addToolBar("Principal")
            toolbar.addAction(self.rotate_action)
    
    def show_rotation_dialog(self):
        """Muestra el diálogo de rotación."""
        if not self.document_handler.document:
            QMessageBox.warning(
                self.main_window,
                "Advertencia",
                "Debes abrir un documento PDF primero."
            )
            return
        
        # Verificar si estamos en modo de rotación conjunta
        dialog_title = "Rotar ambos PDFs" if self.rotate_both else self.title
        
        dialog = RotationDialog(self.main_window, self.title)
        # Ajustar mensaje según el modo
        if self.rotate_both:
            dialog.info_label.setText("Selecciona la rotación para ambos PDFs:")
        else:
            dialog.info_label.setText(f"Selecciona la rotación para {self.title}:")

        if dialog.exec_():
            degrees, scope = dialog.get_rotation_params()
            self.apply_rotation(degrees, scope)

    def apply_rotation(self, degrees, scope):
        """
        Aplica la rotación al documento según los parámetros.
        
        Args:
            degrees: Grados de rotación (90, 180, 270)
            scope: Alcance de la rotación ('current' o 'all')
        """
        success = False
        
        #revisar si hay que rotar ambos pdf o solo 1
        if self.rotate_both:
            if scope == "current":
                # Rotar solo la página actual
                current_page = self.secondary_pdf.document_handler.current_page
                success = self.secondary_pdf.rotator.rotate_page(current_page, degrees)

            else:  # scope == "all"
                # Rotar todas las páginas
                success = self.secondary_pdf.rotator.rotate_all_pages(degrees)
                print("Success",success)
            
            if success:
                pass
            else:
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    "No se pudo aplicar la rotación al documento."
                )

        if scope == "current":
            # Rotar solo la página actual
            current_page = self.document_handler.current_page
            success = self.rotator.rotate_page(current_page, degrees)

        else:  # scope == "all"
            # Rotar todas las páginas
            success = self.rotator.rotate_all_pages(degrees)
            print("Success",success)
        
        if success:
            # Actualizar la visualización sin guardar
            if hasattr(self.document_handler, 'update_display'):
                self.document_handler.update_display()

            # Notificar que hay cambios sin guardar
            self.mark_document_as_modified()
            
            QMessageBox.information(
                self.main_window,
                "Rotación aplicada",
                f"La rotación de {degrees}° se aplicó correctamente.\n\n"
                "Recuerda guardar los cambios con el botón 'Guardar cambios'."
            )
            print("Rotacion realizada",degrees)
        
        else:
            QMessageBox.critical(
                self.main_window,
                "Error",
                "No se pudo aplicar la rotación al documento."
            )
    
    def set_rotate_both(self, state):
        """Actualiza el estado de rotación conjunta."""
        self.rotate_both = state

    def save_document(self):
        """Guarda el documento con los cambios aplicados."""
        if not self.document_handler.document:
            QMessageBox.warning(
                self.main_window,
                "Advertencia",
                "No hay documento abierto para guardar."
            )
            return
        
        #if not self.rotator.has_unsaved_changes:
        #    QMessageBox.information(
        #        self.main_window,
        #        "Información",
        #        "No hay cambios pendientes para guardar."
        #    )
        #    return
        
        # Preguntar si quiere sobrescribir o guardar como
        reply = QMessageBox.question(
            self.main_window,
            "Save changes",
            "You want to overwrite the original file?\n\n"
            "Select 'No' to save as a new file",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        file_path = None
        
        if reply == QMessageBox.Yes:
            # Usar la ruta del archivo actual
            file_path = self.document_handler.file_path
            
            if not file_path:
                QMessageBox.warning(
                    self.main_window,
                    "Advertencia",
                    "No se conoce la ruta del archivo original."
                )
                return
        
        if reply == QMessageBox.No:
            # Guardar como nuevo archivo
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "Guardar PDF como",
                "",
                "Archivos PDF (*.pdf)"
            )
            
            if not file_path:
                return  # Usuario canceló el diálogo
        
        # Guardar el documento (esto cerrará el documento si es necesario)
        success, current_page = self.rotator.save_document(file_path)
        
        if success:
            # Importante: No intentar actualizar la visualización aquí
            # porque es responsabilidad del rotator reabrir el documento
            
            # Solo actualizar la referencia a la ruta del archivo
            self.document_handler.file_path = file_path

            # Reabrir el documento en la nueva ubicación
            self.document_handler.document = fitz.open(file_path)

            # Restaurar la página actual
            if self.document_handler.current_page >= len(self.document_handler.document):
                self.document_handler.current_page = 0
            
            # Actualizar la visualización
            if hasattr(self.document_handler, 'load_pdf'):
                self.document_handler.load_pdf(file_path, c_page = current_page)
                self.document_handler.prev_button.setEnabled(self.document_handler.current_page > 0)
            
            # Actualizar estado de la UI
            self.mark_document_as_saved()
            
            QMessageBox.information(
                self.main_window,
                "Éxito",
                "El documento se guardó correctamente."
            )
        else:
            QMessageBox.critical(
                self.main_window,
                "Error",
                "No se pudo guardar el documento."
            )
    
    def mark_document_as_modified(self):
        """Marca el documento como modificado en la UI."""
        # Notificar a la ventana principal que el documento ha sido modificado
        if hasattr(self.main_window, 'on_document_modified'):
            self.main_window.on_document_modified()
        
        # También podrías cambiar el título de la ventana
        import os
        filename = "Sin título"
        self.main_window.setWindowTitle(f"PDF Comparator - {filename} *")
    
    def mark_document_as_saved(self):
        """Marca el documento como guardado en la UI."""
        # Actualizar el título de la ventana para quitar el asterisco

        filename = os.path.basename(self.document_handler.file_path) if self.document_handler.file_path else "Sin título"
        self.main_window.setWindowTitle(f"PDF Comparator - {filename}")
        
        # Notificar a la ventana principal si es necesario
        if hasattr(self.main_window, 'on_document_saved'):
            self.main_window.on_document_saved()
