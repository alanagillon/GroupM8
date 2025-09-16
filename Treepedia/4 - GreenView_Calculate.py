# This program is used to calculate the green view index based on the collected metadata.
# The Object based images classification algorithm is used to classify the greenery from
# the GSV imgs. In the original code, the meanshift algorithm implemented by pymeanshift
# was used to segment image first, but here we replace it with OpenCV pyrMeanShiftFiltering
# (since pymeanshift is not maintained).
#
# Based on the segmented image, we further use the Otsu's method to find threshold from
# ExG image to extract the greenery pixels.

# -------------------------------------------------------------------
# Gray thresholding using Otsu's method
# -------------------------------------------------------------------
def graythresh(array, level):
    '''
    array: is the numpy array waiting for processing
    return thresh: is the result got by OTSU algorithm
    if the threshold is less than level, then set the level as the threshold
    '''
    import numpy as np

    maxVal = np.max(array)
    minVal = np.min(array)

    # scale data into 0–255 if needed
    if maxVal <= 1:
        array = array * 255
    elif maxVal >= 256:
        array = np.int_((array - minVal) / (maxVal - minVal) * 255)

    # turn the negative to natural number
    array[array < 0] = 0

    # calculate histogram
    hist = np.histogram(array, range(257))
    P_hist = hist[0] * 1.0 / np.sum(hist[0])
    omega = P_hist.cumsum()

    temp = np.arange(256)
    mu = (P_hist * (temp + 1)).cumsum()

    mu_t = mu[-1]
    sigma_b_squared = (mu_t * omega - mu) ** 2 / (omega * (1 - omega))

    sigma_b_squared = np.nan_to_num(sigma_b_squared, nan=0.0, posinf=0.0, neginf=0.0)
    maxval = np.max(sigma_b_squared)

    if maxval > 0:
        idx = np.mean(np.where(sigma_b_squared == maxval))
        threshold = (idx - 1) / 255.0
    else:
        threshold = level

    if np.isnan(threshold):
        threshold = level

    return threshold


# -------------------------------------------------------------------
# Vegetation classification
# -------------------------------------------------------------------
def VegetationClassification(Img):
    '''
    Classify the green vegetation from GSV image,
    based on object-based segmentation and Otsu automatic thresholding.
    Img: numpy array image (e.g. from PIL.Image.open)
    return: percentage of green vegetation pixels
    '''
    import cv2
    import numpy as np

    # --- segmentation (replacement for pymeanshift) ---
    segmented_image = cv2.pyrMeanShiftFiltering(Img, sp=6, sr=7)

    # normalize
    I = segmented_image / 255.0
    red = I[:, :, 0]
    green = I[:, :, 1]
    blue = I[:, :, 2]

    # Excess Green Index (ExG)
    green_red_Diff = green - red
    green_blue_Diff = green - blue
    ExG = green_red_Diff + green_blue_Diff
    diffImg = green_red_Diff * green_blue_Diff

    # thresholds
    redThreImgU = red < 0.6
    greenThreImgU = green < 0.9
    blueThreImgU = blue < 0.6

    shadowRedU = red < 0.3
    shadowGreenU = green < 0.3
    shadowBlueU = blue < 0.3

    greenImg1 = redThreImgU * blueThreImgU * greenThreImgU
    greenImgShadow1 = shadowRedU * shadowGreenU * shadowBlueU

    greenImg3 = diffImg > 0.0
    greenImg4 = green_red_Diff > 0

    threshold = graythresh(ExG, 0.1)
    if threshold > 0.1:
        threshold = 0.1
    elif threshold < 0.05:
        threshold = 0.05

    greenImg2 = ExG > threshold
    greenImgShadow2 = ExG > 0.05
    greenImg = greenImg1 * greenImg2 + greenImgShadow2 * greenImgShadow1

    # calculate percentage of green pixels
    greenPxlNum = len(np.where(greenImg != 0)[0])
    greenPercent = greenPxlNum / (400.0 * 400) * 100

    return greenPercent


# -------------------------------------------------------------------
# GreenView computation
# -------------------------------------------------------------------
def GreenViewComputing_ogr_6Horizon(GSVinfoFolder, outTXTRoot, greenmonth, key_file):
    """
    Download GSV images from metadata and compute Green View Index (GVI).
    """
    import os
    import time
    from PIL import Image
    import numpy as np
    import requests
    import io

    # read API keys
    with open(key_file, "r") as f:
        keylist = [line.strip() for line in f if line.strip()]
    print("The key list is:=============", keylist)

    # headings to check
    headingArr = [0, 60, 120, 180, 240, 300]
    numGSVImg = len(headingArr) * 1.0
    pitch = 0

    if not os.path.exists(outTXTRoot):
        os.makedirs(outTXTRoot)

    if not os.path.isdir(GSVinfoFolder):
        print('You should input a folder for GSV metadata')
        return
    else:
        allTxtFiles = os.listdir(GSVinfoFolder)
        for txtfile in allTxtFiles:
            if not txtfile.endswith('.txt'):
                continue

            txtfilename = os.path.join(GSVinfoFolder, txtfile)
            lines = open(txtfilename, "r")

            panoIDLst, panoDateLst, panoLonLst, panoLatLst = [], [], [], []

            for line in lines:
                metadata = line.split()
                if len(metadata) < 8:
                    continue
                panoID = metadata[1]
                panoDate = metadata[3]
                month = panoDate.split('-')[1] if '-' in panoDate else panoDate[4:6]
                lon = metadata[5]
                lat = metadata[7]

                if len(lon) < 3:
                    continue
                if month not in greenmonth:
                    continue

                panoIDLst.append(panoID)
                panoDateLst.append(panoDate)
                panoLonLst.append(lon)
                panoLatLst.append(lat)

            gvTxt = 'GV_' + os.path.basename(txtfile)
            GreenViewTxtFile = os.path.join(outTXTRoot, gvTxt)
            print(GreenViewTxtFile)
            if os.path.exists(GreenViewTxtFile):
                continue

            with open(GreenViewTxtFile, "w") as gvResTxt:
                for i in range(len(panoIDLst)):
                    panoDate = panoDateLst[i]
                    panoID = panoIDLst[i]
                    lat = panoLatLst[i]
                    lon = panoLonLst[i]

                    idx = i % len(keylist)
                    key = keylist[idx]

                    greenPercent = 0.0
                    for heading in headingArr:
                        print("Heading is: ", heading)
                        URL = f"https://maps.googleapis.com/maps/api/streetview?size=400x400&pano={panoID}&fov=60&heading={heading}&pitch={pitch}&key={key}"
                        time.sleep(0.05)

                        try:
                            response = requests.get(URL)
                            print("📷", URL, "Status:", response.status_code, "Length:", len(response.content))
                            im = Image.open(io.BytesIO(response.content)).convert("RGB")
                            im = np.array(im)
                            percent = VegetationClassification(im)
                            greenPercent = greenPercent + percent
                        except Exception as e:
                            print(f"❌ VegetationClassification failed for pano {panoID}: {e}")
                            greenPercent = -1000
                            break

                    greenViewVal = greenPercent / numGSVImg
                    print(f'The greenview: {greenViewVal}, pano: {panoID}, ({lat}, {lon})')
                    lineTxt = f'panoID: {panoID} panoDate: {panoDate} longitude: {lon} latitude: {lat}, greenview: {greenViewVal}\n'
                    gvResTxt.write(lineTxt)


# ------------------------------Main function-------------------------------
if __name__ == "__main__":
    import os

    GSVinfoRoot = r'C:\Users\alana\PycharmProjects\Treepedia_Public\Treepedia\spatial-data'
    outputTextPath = r'C:\Users\alana\PycharmProjects\Treepedia_Public\Treepedia\output'
    greenmonth = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    key_file = r'C:\Users\alana\PycharmProjects\Treepedia_Public\Treepedia\keys.txt'
    GreenViewComputing_ogr_6Horizon(GSVinfoRoot, outputTextPath, greenmonth, key_file)
