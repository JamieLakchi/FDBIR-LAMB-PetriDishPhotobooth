import os
import datetime
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.figure as mfig

import cv2

from skimage.color import rgb2gray, label2rgb
from skimage.morphology import disk
from skimage.exposure import rescale_intensity
from skimage.morphology import remove_small_objects
from skimage.filters import threshold_multiotsu, gaussian, threshold_local, sobel
from skimage.segmentation import clear_border, watershed
from skimage.morphology import black_tophat, white_tophat
from skimage.measure import label, regionprops

from PIL import Image
from pathlib import Path
from typing import Any

from scipy import ndimage as ndi

MIN_AREA_LABEL = 200  # minimum area of a colony to be labelled

def remove_background(arr:np.ndarray, radius=50, light_background=False):
    
    grey = rgb2gray(arr)
    str_el = disk(radius)
    
    if light_background:
        tophat = white_tophat
    else: 
        tophat = black_tophat
    
    try:
        th = tophat(grey, str_el)
    except MemoryError:
        raise MemoryError("The image is too large for the black_tophat operation. Try reducing the size of the image or using a smaller radius.")
    th = 1 - th
    normalized = rescale_intensity(th)
    return normalized

def region_based_segmentation(arr:np.ndarray, debug=False):
    
    elevation_map = sobel(arr)
    thresholds = threshold_multiotsu(arr, classes=3)
    segmentation = watershed(elevation_map, thresholds)
    
    if debug:
        os.makedirs("debug", exist_ok=True)
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        fig, axs = plt.subplots(1, 4, figsize=(16, 4))
        
        axs[0].imshow(elevation_map, cmap='gray')
        axs[0].set_title('Elevation Map')
        axs[1].imshow(segmentation, cmap='gray')
        axs[1].set_title('Segmenation map')
        plt.tight_layout()
        plt.savefig(f"debug/{today}_region_segmentation.png")
        plt.close(fig)
    
    return segmentation


def threshold_based_segmentation(arr:np.ndarray, min_area, debug=False):
    
    th = round(math.sqrt(min_area))
    if th % 2 == 0:
        th += 1
    
    thresh = threshold_local(arr, block_size=th, offset=0.005)
    bw = arr > thresh
    
    if debug:
        os.makedirs("debug", exist_ok=True)
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        fig, axs = plt.subplots(1, 4, figsize=(16, 4))
        
        axs[0].imshow(bw, cmap='gray')
        axs[0].set_title('Segmentation map')
        plt.tight_layout()
        plt.savefig(f"debug/{today}_region_segmentation.png")
        plt.close(fig)
    
    return bw

def simple_preprocess(arr: np.ndarray, debug=False, *args, **kwargs):
    """Faster processing functions"""
    images_to_show = dict()
    
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    #eq = cv2.equalizeHist(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl1 = clahe.apply(gray)

    thresh, ret = cv2.threshold(cl1, 0, cl1.max(), cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    cleared = clear_border(ret)
    final = remove_small_objects(cleared)
    
    if debug:
        os.makedirs("debug", exist_ok=True)
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        images_to_show["Original"] = arr
        #images_to_show["Equalized"] = eq
        images_to_show["CLAHE"] = cl1
        
        images_to_show["Binary Segmentation"] = ret
        images_to_show["Cleared Border"] = cleared
        images_to_show["Removed Small Objects"] = final
        
        fig, axs = plt.subplots(1, len(images_to_show), figsize=(16, 4))
        for i,img in enumerate(images_to_show.keys()):
            axs[i].imshow(images_to_show[img], cmap="gray")
            axs[i].set_title(img)
        
        plt.tight_layout()
        plt.savefig(f"debug/{today}_preprocess.png")
        plt.close(fig)
    
    
    return final

    
def preprocess_arr(arr: np.ndarray, debug=False, min_area=MIN_AREA_LABEL, bubbles=False):
    """Turns the image array to greyscale does a rolling ball filter and does some thresholding"""
    
    images_to_show = dict()
    bg_removed = remove_background(arr)
    
    bw = threshold_based_segmentation(bg_removed, min_area=min_area, debug=debug)

    filled = ndi.binary_fill_holes(bw)
    bw_rem = remove_small_objects(filled, min_size=min_area//2)
    cleared = clear_border(bw_rem)
    
    if debug:
        os.makedirs("debug", exist_ok=True)
        today = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        
        images_to_show["Original"] = arr
        images_to_show["Background Removed"] = bg_removed
        images_to_show["Binary Segmentation"] = bw
        images_to_show["Filled Holes"] = filled
        images_to_show["Removed Small Objects"] = bw_rem
        images_to_show["Cleared Border"] = cleared
        
        fig, axs = plt.subplots(1, len(images_to_show), figsize=(16, 4))
        for i,img in enumerate(images_to_show.keys()):
            axs[i].imshow(images_to_show[img], cmap="gray")
            axs[i].set_title(img)
        
        plt.tight_layout()
        plt.savefig(f"debug/{today}_preprocess.png")
        plt.close(fig)
    return cleared


def label_colonies(preprocessed: np.ndarray) -> tuple[list, np.ndarray]:  # we want to be able to use the image name(s) as the input
    """Label a processed image array and return the labelled image and label data"""
    colony_labels = label(preprocessed)

    region_properties = regionprops(colony_labels)
    region_properties = [
        region for region in region_properties if region.area >= MIN_AREA_LABEL
    ]  # filter out small regions 

    for i,region in enumerate(region_properties):
        region.label = i
        region.circularity = 4 * np.pi * region.area / (region.perimeter ** 2 + 1e-5)

    return region_properties, colony_labels # type: ignore

def get_selected_properties(region_props) -> pd.DataFrame:
    """Extracts selected properties from region properties"""
    properties = []
    for region in region_props:
        props = {
            "label": region.label,
            "area": region.area,
            "centroid": f"{region.centroid[0]:.2f}, {region.centroid[1]:.2f}",
            "len_axis_major": region.axis_major_length,
            "len_axis_minor": region.axis_minor_length,
            "eccentricity": region.eccentricity,
            "circularity": region.circularity,
            #"bbox": region.bbox,
        }
        properties.append(props)
    
    return pd.DataFrame(properties)


def process1(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Process a single image; returns properties and labeled image
    """
    with Image.open(path) as image:
        image_array = np.array(image)
        processed = simple_preprocess(image_array)
        region_props, colony_labels = label_colonies(processed)
        properties = get_selected_properties(region_props)
        properties["dish"] = path.stem

        return properties, {
            "original": image_array,
            "processed": processed,
            "colony_labels": colony_labels,
            "region_properties": region_props
        }