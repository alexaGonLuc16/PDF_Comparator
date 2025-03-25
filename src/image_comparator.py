# image_comparator.py
import numpy as np
from PIL import Image
import cv2

class ImageComparator:
    def __init__(self, threshold=10):
        """
        Args:
            threshold: Umbral de diferencia para considerar diferentes dos píxeles (0-255)
        """
        self.threshold = threshold
    
    def compare_images(self, image_path1, image_path2):
        """
        Compara dos imágenes píxel por píxel y devuelve las coordenadas de las diferencias.
        
        Returns:
            diff_coords: Lista de tuplas (x, y) con las coordenadas de los píxeles diferentes
        """
        # Cargar imágenes
        img1 = cv2.imread(image_path1)
        img2 = cv2.imread(image_path2)
        
        # Asegurar que las imágenes tengan el mismo tamaño
        if img1.shape != img2.shape:
            raise ValueError("Las imágenes tienen diferentes dimensiones")
        
        # Calcular la diferencia absoluta
        diff = cv2.absdiff(img1, img2)
        
        # Convertir a escala de grises para simplificar
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # Encontrar píxeles que exceden el umbral
        _, thresholded = cv2.threshold(gray_diff, self.threshold, 255, cv2.THRESH_BINARY)
        
        # Obtener coordenadas de píxeles diferentes
        diff_coords = np.argwhere(thresholded > 0).tolist()
        
        # Convertir a formato (x, y) 
        diff_coords = [(coord[1], coord[0]) for coord in diff_coords]  # Intercambiar columna/fila a x/y
        
        return diff_coords