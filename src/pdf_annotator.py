# pdf_annotator.py
import fitz  # PyMuPDF
import os
import json

class PDFAnnotator:
    def __init__(self, output_dir='data/output'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def add_circle_annotations(self, input_pdf, circles_by_page, output_pdf=None, dpi=300):
        """
        Añade círculos como anotaciones al PDF.
        
        Args:
            input_pdf: Ruta al PDF original
            circles_by_page: Diccionario {num_página: [(x, y, radio), ...]}
            output_pdf: Ruta donde guardar el PDF anotado
            dpi: DPI usados para la conversión a imagen (para escalar coordenadas)
        """
        if output_pdf is None:
            base_name = os.path.basename(input_pdf)
            output_pdf = os.path.join(self.output_dir, f"annotated_{base_name}")
        
        # Abrir documento
        doc = fitz.open(input_pdf)
        
        # Factor de escala para convertir de coordenadas de imagen a PDF
        scale_factor = 72 / dpi
        
        # Para cada página con círculos
        for page_num, circles in circles_by_page.items():
            page = doc[int(page_num)]
            
            for x, y, radius in circles:
                # Escalar coordenadas
                x_pdf = x * scale_factor
                y_pdf = y * scale_factor
                radius_pdf = radius * scale_factor
                
                # Crear anotación de círculo
                circle = page.add_circle_annot((x_pdf - radius_pdf, y_pdf - radius_pdf, 
                                              x_pdf + radius_pdf, y_pdf + radius_pdf))
                
                # Configurar propiedades
                circle.set_border(width=2)
                circle.set_colors(stroke=(1, 0, 0))  # Rojo
                circle.update(opacity=0.7)
                
                # Hacer la anotación toggle-able
                circle.set_flags(0)  # No ocultar por defecto
        
        # Guardar documento
        doc.save(output_pdf)
        image_file = "C:/PDF_Comparator/src/client_waterm.png"
        
        for page_index in range(len(doc)): # iterate over pdf pages
            page = doc[page_index] # get the page

            # insert an image watermark from a file name to fit the page bounds
            page.insert_image(page.bound(),filename=image_file, overlay=False)

        doc.save("C:/PDF_Comparator/src/watermarked-document.pdf") # save the document with a new filename
        doc.close()
        
        return output_pdf
            
    def save_circles_to_json(self, circles_by_page, output_path):
        """Guarda la información de los círculos en un archivo JSON."""
        with open(output_path, 'w') as f:
            json.dump(circles_by_page, f, indent=2)