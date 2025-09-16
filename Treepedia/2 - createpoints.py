# This program is used in the first step of the Treepedia project to get points along street
# network to feed into GSV python scripts for metadata generation.
# Copyright(C) Ian Seiferling, Xiaojiang Li, Marwa Abdulhai, Senseable City Lab, MIT
# First version July 21 2017
import warnings
warnings.filterwarnings("ignore")

def createPoints(inshp, outshp, mini_dist):
    '''
    This function will parse through the street network of the provided city and
    create points every mini_dist meters along the linestrings.

    Required modules: Fiona and Shapely

    Parameters:
        inshp: the input linear shapefile, must be in WGS84 projection (EPSG:4326)
        outshp: the result point shapefile
        mini_dist: the minimum distance (in meters) between two created points

    Last modified by Xiaojiang Li, MIT Senseable City Lab
    '''

    import fiona
    import os
    from shapely.geometry import shape, mapping
    from shapely.ops import transform
    from functools import partial
    import pyproj

    # Temporary cleaned file
    root = os.path.dirname(inshp)
    basename = 'clean_' + os.path.basename(inshp)
    temp_cleanedStreetmap = os.path.join(root, basename)

    # If tempfile exists, remove it
    if os.path.exists(temp_cleanedStreetmap):
        fiona.remove(temp_cleanedStreetmap, 'ESRI Shapefile')

    # Copy input shapefile into a "cleaned" temporary shapefile
    with fiona.open(inshp) as source, fiona.open(
        temp_cleanedStreetmap, 'w',
        driver=source.driver, crs=source.crs, schema=source.schema
    ) as dest:
        for feat in source:
            dest.write(feat)

    # Schema for output point shapefile
    schema = {
        'geometry': 'Point',
        'properties': {'id': 'int'},
    }

    # Create points along the streets
    with fiona.Env():
        with fiona.open(outshp, 'w', driver='ESRI Shapefile', crs=source.crs, schema=schema) as output:
            for line in fiona.open(temp_cleanedStreetmap):
                geom = shape(line['geometry'])

                # Skip non-line geometries (e.g., polygons, points)
                if not geom.geom_type.startswith("Line"):
                    continue

                try:
                    # Convert degrees to meters for distance splitting
                    project = partial(
                        pyproj.transform,
                        pyproj.Proj(init='EPSG:4326'),
                        pyproj.Proj(init='EPSG:3857')
                    )

                    line2 = transform(project, geom)
                    dist = mini_dist

                    for distance in range(0, int(line2.length), dist):
                        point = line2.interpolate(distance)

                        # Convert back to WGS84
                        project2 = partial(
                            pyproj.transform,
                            pyproj.Proj(init='EPSG:3857'),
                            pyproj.Proj(init='EPSG:4326')
                        )
                        point = transform(project2, point)

                        output.write({
                            'geometry': mapping(point),
                            'properties': {'id': 1}
                        })

                except Exception as e:
                    print("Error while processing line:", e)
                    return

    print("Process Complete")

    # Delete temporary cleaned shapefile
    fiona.remove(temp_cleanedStreetmap, 'ESRI Shapefile')


# ------------ MAIN ------------
if __name__ == "__main__":
    import os

    # Point to the actual folder where you put the shapefile
    inshp = "spatial-data/SydneyCBD_edges.shp"
    outshp = "spatial-data/SydneyCBD_points.shp"
    mini_dist = 50

    createPoints(inshp, outshp, mini_dist)
    print("Process Complete")
