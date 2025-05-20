import tempfile
import os
import shutil
import datetime
import json

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