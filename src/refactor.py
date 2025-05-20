# Clase base para manejar documentos PDF
class PDFDocumentHandler:
    def __init__(self, viewer):
        self.viewer = viewer
        self.document = None
        self.file_path = None
        self.current_page = 0
        
    def open_document(self, file_path):
        """Abre un documento PDF."""
        if self.document:
            self.document.close()
        
        self.document = fitz.open(file_path)
        self.file_path = file_path
        self.current_page = 0
        return True
    
    def close_document(self):
        """Cierra el documento actual."""
        if self.document:
            self.document.close()
            self.document = None

# Clase para rastrear cambios
class ChangeTracker:
    def __init__(self):
        self.rotations_by_page = {}
        self.circles_by_page = {}
        
    def add_rotation(self, page_index, degrees):
        """Registra una rotación para una página."""
        self.rotations_by_page[page_index] = degrees
        
    def set_circles(self, page_index, circles):
        """Establece los círculos para una página."""
        self.circles_by_page[page_index] = circles
        
    def get_data(self):
        """Obtiene todos los datos de cambios."""
        return {
            "rotations": self.rotations_by_page,
            "circles": self.circles_by_page
        }

# Clase para manejar rotaciones
class PDFRotator:
    def __init__(self, document_handler, change_tracker):
        self.document_handler = document_handler
        self.change_tracker = change_tracker
        
    def rotate_page(self, page_index, degrees):
        """Rota una página específica del PDF."""
        if not self.document_handler.document:
            return False
        
        try:
            # Obtener la página
            page = self.document_handler.document[page_index]
            
            # Obtener rotación actual y calcular nueva
            current_rotation = page.rotation
            new_rotation = (current_rotation + degrees) % 360
            
            # Aplicar rotación
            page.set_rotation(new_rotation)
            
            # Registrar el cambio
            self.change_tracker.add_rotation(page_index, degrees)
            
            # Actualizar visualización
            self._update_display(page_index)
            
            return True
        except Exception as e:
            print(f"Error al rotar página: {str(e)}")
            return False
    
    def _update_display(self, page_index):
        """Actualiza la visualización de la página."""
        # Código para actualizar la vista (similar a lo que ya tienes)
        pass

# Clase para guardar documentos
class PDFSaver:
    def __init__(self, document_handler):
        self.document_handler = document_handler
        
    def save_document(self, file_path=None):
        """Guarda el documento en la ruta especificada."""
        if not self.document_handler.document:
            return False, None
        
        # Si no se especifica ruta, usar la actual
        target_path = file_path or self.document_handler.file_path
        current_page = self.document_handler.current_page
        
        try:
            # Crear un archivo temporal
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Guardar en el archivo temporal
            self.document_handler.document.save(
                temp_path,
                garbage=4,
                deflate=True,
                clean=True
            )
            
            # Cerrar el documento para liberar el archivo
            self.document_handler.close_document()
            
            # Copiar el temporal al destino
            shutil.copy2(temp_path, target_path)
            
            # Eliminar el temporal
            os.unlink(temp_path)
            
            # Reabrir el documento
            self.document_handler.open_document(target_path)
            
            # Restaurar la página actual
            if current_page < len(self.document_handler.document):
                self.document_handler.current_page = current_page
            
            return True, current_page
        except Exception as e:
            print(f"Error al guardar documento: {str(e)}")
            # Intentar reabrir el documento original si falló
            if self.document_handler.file_path:
                try:
                    self.document_handler.open_document(self.document_handler.file_path)
                except:
                    pass
            return False, None

# Clase para exportar a JSON
class JSONExporter:
    def export_changes(self, original_pdf, change_tracker, output_path=None):
        """Exporta los cambios a un archivo JSON."""
        # Similar a tu función save_changes_to_json pero usando change_tracker
        data = change_tracker.get_data()
        
        if not output_path:
            base_name = os.path.basename(original_pdf)
            output_path = os.path.join(
                os.path.dirname(original_pdf), 
                f"{os.path.splitext(base_name)[0]}_changes.json"
            )
        
        # Estructurar los datos (similar a tu código actual)
        json_data = {
            "metadata": {
                "original_pdf": original_pdf,
                "processed_date": datetime.datetime.now().isoformat(),
                "version": "1.0"
            },
            "pages": {}
        }
        
        # Añadir rotaciones y círculos (similar a tu código)
        # ...
        
        # Guardar el JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return output_path

# UI Handler refactorizado
class PDFUIHandler(QObject):
    save_completed = pyqtSignal(bool, str)  # Señal mejorada: éxito, ruta
    
    def __init__(self, main_window, document_handler):
        super().__init__()
        self.main_window = main_window
        self.document_handler = document_handler
        self.change_tracker = ChangeTracker()
        self.rotator = PDFRotator(document_handler, self.change_tracker)
        self.saver = PDFSaver(document_handler)
        self.json_exporter = JSONExporter()
        
        # Configurar la UI
        self.setup_ui()
    
    def save_document(self, file_path=None):
        """Guarda el documento y exporta los cambios a JSON."""
        # Lógica de guardado mejorada
        success, current_page = self.saver.save_document(file_path)
        
        if success:
            # Exportar cambios a JSON
            json_path = self.json_exporter.export_changes(
                file_path or self.document_handler.file_path,
                self.change_tracker
            )
            
            # Notificar éxito
            self.save_completed.emit(True, file_path)
            return True
        else:
            # Notificar error
            self.save_completed.emit(False, "")
            return False