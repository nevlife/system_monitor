"""GPS fix in a map frame that is UTM minus a datum (navsat_transform's), without localization."""

import pyproj


class UtmMapFrame:
    def __init__(self, datum_lat, datum_lon):
        zone = int((datum_lon + 180) // 6) + 1
        epsg = (32600 if datum_lat >= 0 else 32700) + zone
        self.to_utm = pyproj.Transformer.from_crs('EPSG:4326', f'EPSG:{epsg}', always_xy=True)
        self.x0, self.y0 = self.to_utm.transform(datum_lon, datum_lat)

    def to_map(self, lat, lon):
        x, y = self.to_utm.transform(lon, lat)
        return x - self.x0, y - self.y0
