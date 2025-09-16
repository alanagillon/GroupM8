# This function is used to collect the metadata of the GSV panoramas based on the sample point shapefile
# Updated version for modern Google Street View Metadata API
# Patched: includes radius=50 and progress counter

def GSVpanoMetadataCollector(samplesFeatureClass, num, outputTextFolder, apiKey):
    """
    Collect metadata of Google Street View Panoramas based on sample points shapefile.

    Parameters:
        samplesFeatureClass: shapefile of sample sites
        num: number of sites processed per batch
        outputTextFolder: folder to store output text files
        apiKey: Google Maps API key
    """
    import urllib.request
    import urllib.error
    import json
    from osgeo import ogr, osr
    import time
    import os

    if not os.path.exists(outputTextFolder):
        os.makedirs(outputTextFolder)

    driver = ogr.GetDriverByName('ESRI Shapefile')

    # Open the shapefile
    dataset = driver.Open(samplesFeatureClass)
    if dataset is None:
        print(f"❌ Could not open shapefile: {samplesFeatureClass}")
        return

    layer = dataset.GetLayer()

    # Transform projection to WGS84
    sourceProj = layer.GetSpatialRef()
    targetProj = osr.SpatialReference()
    targetProj.ImportFromEPSG(4326)
    transform = osr.CoordinateTransformation(sourceProj, targetProj)

    featureNum = layer.GetFeatureCount()
    print(f"✅ Found {featureNum} points in {samplesFeatureClass}")

    batch = featureNum // num + (1 if featureNum % num != 0 else 0)

    for b in range(batch):
        start = b * num
        end = min((b + 1) * num, featureNum)
        outputTextFile = f'Pnt_start{start}_end{end}.txt'
        outputGSVinfoFile = os.path.join(outputTextFolder, outputTextFile)

        # Skip existing files
        if os.path.exists(outputGSVinfoFile):
            print(f"⚠️ Skipping existing file: {outputTextFile}")
            continue

        time.sleep(1)

        with open(outputGSVinfoFile, 'w') as panoInfoText:
            found = 0
            checked = 0
            for i in range(start, end):
                feature = layer.GetFeature(i)
                geom = feature.GetGeometryRef()
                geom.Transform(transform)
                lon = geom.GetX()
                lat = geom.GetY()

                # Google Street View Metadata API URL with radius
                print(f"🔎 Checking {lat},{lon}")
                urlAddress = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lon},{lat}&radius=50&key={apiKey}"

                try:
                    time.sleep(0.05)
                    with urllib.request.urlopen(urlAddress) as response:
                        data = json.loads(response.read().decode())

                    checked += 1
                    if data.get('status') != 'OK':
                        panoInfoText.write(f'No pano at {lat},{lon} (status={data.get("status")})\n')
                    else:
                        found += 1
                        panoId = data['pano_id']
                        panoDate = data.get('date', 'NA')
                        panoLat = data['location']['lat']
                        panoLon = data['location']['lng']

                        print(f"📸 ({panoLon},{panoLat}) panoId={panoId} date={panoDate}")
                        lineTxt = f'panoID: {panoId} panoDate: {panoDate} longitude: {panoLon} latitude: {panoLat}\n'
                        panoInfoText.write(lineTxt)

                    # Progress every 100 points
                    if checked % 100 == 0:
                        print(f"Progress: {checked}/{end-start} points checked, {found} panos found")

                except Exception as e:
                    print(f"❌ Error at {lat},{lon}: {e}")
                    panoInfoText.write(f'Error at {lat},{lon}: {e}\n')


# ------------Main Function -------------------
if __name__ == "__main__":
    import os

    root = 'C:/Users/alana/PycharmProjects/Treepedia_Public/Treepedia/spatial-data'
    inputShp = os.path.join(root, 'SydneyCBD_points.shp')
    outputTxt = root

    Key = "AIzaSyBh0j6JPkDHfd4e0wTrPwAYulhtC_mSujs"  # <<-- put your key here

    GSVpanoMetadataCollector(inputShp, 1000, outputTxt, Key)
