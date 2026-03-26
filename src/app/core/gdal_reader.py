"""
GDAL Reader - Read various raster formats including virtual rasters
"""

from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import numpy as np

class GDALReader:
    """Reader for GDAL-supported raster formats and virtual rasters."""
    
    def __init__(self):
        pass
        
    def load_file(self, file_path: str) -> Tuple[Optional[np.ndarray], Optional[list], Optional[Dict]]:
        """Load a raster file using GDAL."""
        try:
            from osgeo import gdal, osr
            
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
                
            # Open the dataset
            dataset = gdal.Open(str(file_path))
            if dataset is None:
                raise ValueError(f"Could not open file with GDAL: {file_path}")
                
            # Get geotransform
            geotransform = dataset.GetGeoTransform()
            if geotransform is None:
                geotransform = [0, 1, 0, 0, 0, 1]  # Default identity transform
                
            # Read raster data
            bands = []
            for i in range(1, dataset.RasterCount + 1):
                band = dataset.GetRasterBand(i)
                band_data = band.ReadAsArray()
                bands.append(band_data)
                
            # Stack bands
            if len(bands) == 1:
                image_data = bands[0]
                # Convert single band to 3-channel for display
                image_data = np.stack([image_data] * 3, axis=-1)
            else:
                image_data = np.stack(bands, axis=-1)
                
            # Get metadata
            metadata = self._extract_metadata(dataset)
            
            # Clean up
            dataset = None
            
            return image_data, geotransform, metadata
            
        except ImportError:
            raise ImportError("GDAL is required for reading raster files")
        except Exception as e:
            raise RuntimeError(f"Failed to load raster file: {str(e)}")
            
    def _extract_metadata(self, dataset) -> Dict[str, Any]:
        """Extract metadata from GDAL dataset."""
        metadata = {}
        
        try:
            # Basic dataset info
            metadata['driver'] = dataset.GetDriver().ShortName
            metadata['width'] = dataset.RasterXSize
            metadata['height'] = dataset.RasterYSize
            metadata['band_count'] = dataset.RasterCount
            
            # Projection
            projection = dataset.GetProjection()
            if projection:
                metadata['projection'] = projection
                
                # Try to get EPSG code
                try:
                    from osgeo import osr
                    srs = osr.SpatialReference()
                    srs.ImportFromWkt(projection)
                    epsg_code = srs.GetAuthorityCode(None)
                    if epsg_code:
                        metadata['epsg'] = int(epsg_code)
                except:
                    pass
                    
            # Geotransform
            geotransform = dataset.GetGeoTransform()
            if geotransform:
                metadata['geotransform'] = geotransform
                
            # Metadata domains
            for domain_name in ['IMAGE_STRUCTURE', 'SUBDATASETS', 'RPC', 'GCP']:
                domain_metadata = dataset.GetMetadata(domain_name)
                if domain_metadata:
                    metadata[domain_name.lower()] = domain_metadata
                    
            # Band-specific metadata
            band_metadata = []
            for i in range(1, dataset.RasterCount + 1):
                band = dataset.GetRasterBand(i)
                band_info = {
                    'band': i,
                    'data_type': gdal.GetDataTypeName(band.DataType),
                    'color_interpretation': gdal.GetColorInterpretationName(band.GetColorInterpretation())
                }
                
                # Band statistics
                stats = band.GetStatistics(True, True)
                if stats and None not in stats:
                    band_info['min'] = stats[0]
                    band_info['max'] = stats[1]
                    band_info['mean'] = stats[2]
                    band_info['stddev'] = stats[3]
                    
                # No data value
                nodata = band.GetNoDataValue()
                if nodata is not None:
                    band_info['nodata'] = nodata
                    
                band_metadata.append(band_info)
                
            metadata['bands'] = band_metadata
            
            # GCPs
            gcps = dataset.GetGCPs()
            if gcps:
                metadata['gcp_count'] = len(gcps)
                metadata['gcps'] = [
                    {
                        'id': gcp.Id,
                        'pixel': (gcp.GCPPixel, gcp.GCPLine),
                        'geo': (gcp.GCPX, gcp.GCPY, gcp.GCPZ)
                    }
                    for gcp in gcps
                ]
                
        except Exception as e:
            metadata['error'] = str(e)
            
        return metadata
        
    def create_vrt(self, input_files: list, output_vrt: str) -> str:
        """Create a virtual raster from multiple files."""
        try:
            from osgeo import gdal
            
            # Build VRT
            vrt_options = gdal.BuildVRTOptions(
                resolution='user',
                xRes=1.0,  # Will be overridden by input resolution
                yRes=1.0,
                separate=False  # Bands from different files are stacked
            )
            
            vrt_dataset = gdal.BuildVRT(output_vrt, input_files, options=vrt_options)
            
            if vrt_dataset is None:
                raise RuntimeError(f"Failed to create VRT: {output_vrt}")
                
            # Clean up
            vrt_dataset = None
            
            return output_vrt
            
        except ImportError:
            raise ImportError("GDAL is required for creating virtual rasters")
        except Exception as e:
            raise RuntimeError(f"Failed to create VRT: {str(e)}")
            
    def get_overview_info(self, file_path: str) -> Dict[str, Any]:
        """Get overview (pyramid) information for a raster."""
        try:
            from osgeo import gdal
            
            dataset = gdal.Open(file_path)
            if dataset is None:
                raise ValueError(f"Could not open file: {file_path}")
                
            overview_info = {}
            
            # Check for overviews
            band = dataset.GetRasterBand(1)
            overviews = band.GetOverviewCount()
            
            if overviews > 0:
                overview_info['overview_count'] = overviews
                overview_sizes = []
                
                for i in range(overviews):
                    overview_band = band.GetOverview(i)
                    overview_sizes.append((overview_band.XSize, overview_band.YSize))
                    
                overview_info['overview_sizes'] = overview_sizes
            else:
                overview_info['overview_count'] = 0
                
            # Clean up
            dataset = None
            
            return overview_info
            
        except ImportError:
            raise ImportError("GDAL is required")
        except Exception as e:
            raise RuntimeError(f"Failed to get overview info: {str(e)}")
            
    def get_band_statistics(self, file_path: str, band: int = 1) -> Dict[str, float]:
        """Get statistics for a specific band."""
        try:
            from osgeo import gdal
            
            dataset = gdal.Open(file_path)
            if dataset is None:
                raise ValueError(f"Could not open file: {file_path}")
                
            if band < 1 or band > dataset.RasterCount:
                raise ValueError(f"Invalid band number: {band}")
                
            raster_band = dataset.GetRasterBand(band)
            stats = raster_band.GetStatistics(True, True)
            
            statistics = {}
            if stats and None not in stats:
                statistics = {
                    'min': stats[0],
                    'max': stats[1],
                    'mean': stats[2],
                    'stddev': stats[3]
                }
                
            # Clean up
            dataset = None
            
            return statistics
            
        except ImportError:
            raise ImportError("GDAL is required")
        except Exception as e:
            raise RuntimeError(f"Failed to get band statistics: {str(e)}")
