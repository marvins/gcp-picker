"""
WMS Client - Fetch data from Web Map Services
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional, Dict
import numpy as np

class WMSClient:
    """Client for interacting with WMS/WMTS services."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GCP-Picker/1.0'
        })
        
    def get_layers(self, service_url: str) -> List[str]:
        """Get available layers from WMS service."""
        try:
            # Build GetCapabilities request
            params = {
                'SERVICE': 'WMS',
                'VERSION': '1.3.0',
                'REQUEST': 'GetCapabilities'
            }
            
            response = self.session.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Extract layer names
            layers = []
            
            # Handle different XML namespaces
            namespaces = {
                'wms': 'http://www.opengis.net/wms',
                'ows': 'http://www.opengis.net/ows'
            }
            
            # Try to find layers
            for layer_elem in root.findall('.//Layer', namespaces):
                name_elem = layer_elem.find('Name')
                if name_elem is not None and name_elem.text:
                    layers.append(name_elem.text)
                    
            # Fallback without namespace
            if not layers:
                for layer_elem in root.findall('.//Layer'):
                    name_elem = layer_elem.find('Name')
                    if name_elem is not None and name_elem.text:
                        layers.append(name_elem.text)
                        
            return layers
            
        except Exception as e:
            raise RuntimeError(f"Failed to get WMS layers: {str(e)}")
            
    def get_map(self, service_url: str, layer: str, crs: str, 
                bbox: List[float], width: int, height: int,
                format: str = 'image/png') -> Tuple[Optional[np.ndarray], Optional[List[float]]]:
        """Get a map from WMS service."""
        try:
            # Build GetMap request
            params = {
                'SERVICE': 'WMS',
                'VERSION': '1.3.0',
                'REQUEST': 'GetMap',
                'LAYERS': layer,
                'CRS': crs,
                'BBOX': ','.join(map(str, bbox)),
                'WIDTH': width,
                'HEIGHT': height,
                'FORMAT': format,
                'TRANSPARENT': 'TRUE'
            }
            
            response = self.session.get(service_url, params=params, timeout=60)
            response.raise_for_status()
            
            # Convert response to numpy array
            image_data = self._response_to_array(response.content, format)
            
            # Calculate pixel-to-map transformation
            transform = self._calculate_transform(bbox, width, height)
            
            return image_data, transform
            
        except Exception as e:
            raise RuntimeError(f"Failed to get WMS map: {str(e)}")
            
    def _response_to_array(self, content: bytes, format: str) -> np.ndarray:
        """Convert HTTP response to numpy array."""
        try:
            from PIL import Image
            import io
            
            # Create PIL image from bytes
            image = Image.open(io.BytesIO(content))
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Handle different formats
            if format == 'image/png' and image.mode == 'RGBA':
                # Keep alpha channel
                return image_array
            elif image.mode == 'RGB':
                return image_array
            elif image.mode == 'L':
                # Convert grayscale to RGB
                return np.stack([image_array] * 3, axis=-1)
            else:
                # Convert to RGB
                rgb_image = image.convert('RGB')
                return np.array(rgb_image)
                
        except Exception as e:
            raise RuntimeError(f"Failed to convert image data: {str(e)}")
            
    def _calculate_transform(self, bbox: List[float], width: int, height: int) -> List[float]:
        """Calculate pixel-to-map transformation matrix."""
        min_x, min_y, max_x, max_y = bbox
        
        # Calculate pixel sizes
        pixel_width = (max_x - min_x) / width
        pixel_height = (max_y - min_y) / height
        
        # GDAL-style transformation matrix
        # [origin_x, pixel_width, rotation_x, origin_y, rotation_y, -pixel_height]
        transform = [
            min_x,           # Origin X
            pixel_width,      # Pixel width
            0.0,             # Rotation X
            max_y,           # Origin Y (top-left)
            0.0,             # Rotation Y
            -pixel_height    # Pixel height (negative for Y-down)
        ]
        
        return transform
        
    def get_feature_info(self, service_url: str, layer: str, crs: str,
                        bbox: List[float], width: int, height: int,
                        x: int, y: int, query_layers: str = None) -> Dict:
        """Get feature information for a point."""
        try:
            params = {
                'SERVICE': 'WMS',
                'VERSION': '1.3.0',
                'REQUEST': 'GetFeatureInfo',
                'LAYERS': layer,
                'CRS': crs,
                'BBOX': ','.join(map(str, bbox)),
                'WIDTH': width,
                'HEIGHT': height,
                'QUERY_LAYERS': query_layers or layer,
                'INFO_FORMAT': 'application/json',
                'I': x,
                'J': y
            }
            
            response = self.session.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                return response.json()
            except:
                # Return as text if not JSON
                return {'text': response.text}
                
        except Exception as e:
            raise RuntimeError(f"Failed to get feature info: {str(e)}")
            
    def get_legend_graphic(self, service_url: str, layer: str, 
                          format: str = 'image/png') -> bytes:
        """Get legend graphic for a layer."""
        try:
            params = {
                'SERVICE': 'WMS',
                'VERSION': '1.3.0',
                'REQUEST': 'GetLegendGraphic',
                'LAYER': layer,
                'FORMAT': format
            }
            
            response = self.session.get(service_url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            raise RuntimeError(f"Failed to get legend graphic: {str(e)}")
