# circle_detector.py
import numpy as np
from sklearn.cluster import DBSCAN
import miniball

class CircleDetector:
    def __init__(self, eps=10, min_samples=5):
        """
        Args:
            eps: Distancia máxima para considerar que dos puntos están en el mismo cluster
            min_samples: Número mínimo de puntos para formar un cluster
        """
        self.eps = eps
        self.min_samples = min_samples
    
    def group_points_into_circles(self, points):
        """
        Agrupa puntos en círculos usando DBSCAN para clustering y Miniball para encontrar
        el círculo mínimo que contiene cada grupo.
        
        Args:
            points: Lista de tuplas (x, y) con las coordenadas de los puntos
        
        Returns:
            circles: Lista de tuplas (x, y, radius) que representan los círculos
        """
        
        #print("Points: ", points[0])
        #print("Lenght: ", len(points))
        # Convertir lista de puntos a array numpy
        #points_array = np.array(points[0])
        
        # Validar que todos los puntos son tuplas/listas de 2 elementos
        valid_points = [p for p in points if isinstance(p, (list, tuple)) and len(p) == 2]
        
        # Verificar si hay puntos válidos
        if not valid_points:
            return []
        
        # Convertir lista de puntos a array numpy
        points_array = np.array(valid_points)
        
        # Si no hay suficientes puntos, devolver círculos vacíos
        if len(points_array) < self.min_samples:
            if len(points_array) > 0:
                # Si hay pocos puntos, crear un único círculo que los contenga todos
                center, squared_radius = miniball.get_bounding_ball(cluster_points)
                radius = np.sqrt(squared_radius)
                return [(center[0], center[1], radius)]
            return []
        
        # Aplicar DBSCAN para agrupar los puntos
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(points_array)
        labels = clustering.labels_
        
        # Encontrar círculos mínimos para cada cluster
        circles = []
        unique_labels = set(labels)
        
        for label in unique_labels:
            # Ignorar el ruido (etiqueta -1)
            if label == -1:
                continue
                
            # Obtener puntos de este cluster
            cluster_points = points_array[labels == label]
            
            # Calcular el círculo mínimo para este cluster
            center, squared_radius = miniball.get_bounding_ball(cluster_points)
            radius = np.sqrt(squared_radius)

            # Añadir un poco de margen al radio (5%)
            radius *= 1.05
            
            circles.append((center[0], center[1], radius))
        
        return circles
    
    def merge_overlapping_circles(self, circles, overlap_threshold=0.7):
        """
        Fusiona círculos que se solapan significativamente.
        
        Args:
            circles: Lista de tuplas (x, y, radius)
            overlap_threshold: Umbral de solapamiento para fusionar círculos
        
        Returns:
            merged_circles: Lista de círculos fusionados
        """
        if not circles:
            return []
            
        # Ordenar círculos por radio (de mayor a menor)
        sorted_circles = sorted(circles, key=lambda x: x[2], reverse=True)
        merged_circles = []
        
        while sorted_circles:
            # Tomar el círculo más grande
            current = sorted_circles.pop(0)
            merged_circles.append(current)
            
            # Filtrar círculos que no se solapan significativamente con el actual
            remaining_circles = []
            for circle in sorted_circles:
                # Calcular distancia entre centros
                distance = np.sqrt((circle[0] - current[0])**2 + (circle[1] - current[1])**2)
                
                # Si la distancia es mayor que la suma de radios, no hay solapamiento
                if distance > current[2] + circle[2]:
                    remaining_circles.append(circle)
                    continue
                    
                # Calcular solapamiento
                overlap_ratio = min(circle[2], current[2]) / max(circle[2], current[2])
                
                # Si el solapamiento es menor que el umbral, mantener el círculo
                if overlap_ratio < overlap_threshold:
                    remaining_circles.append(circle)
            
            sorted_circles = remaining_circles
            
        return merged_circles