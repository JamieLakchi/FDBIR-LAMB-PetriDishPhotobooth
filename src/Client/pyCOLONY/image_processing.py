import cv2
import itertools
import numpy as np
import pandas as pd

from skimage.color import rgb2gray,color_dict
from skimage.morphology import remove_small_objects
from skimage.segmentation import clear_border
from skimage.measure import label, regionprops

from PIL import Image
from pathlib import Path
from typing import Any

MIN_AREA_LABEL = 1000  # minimum area of a colony to be labelled

def simple_preprocess(arr: np.ndarray):
    """Faster processing functions"""
    
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    #eq = cv2.equalizeHist(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl1 = clahe.apply(gray)

    thresh, ret = cv2.threshold(cl1, 0, cl1.max(), cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    cleared = clear_border(ret)
    final = remove_small_objects(cleared)
    
    return final


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
        image = image.crop((2312, 1000, 6000, 4625)) # hardcoded position of petri dish when stencil is used
        width, height = image.size

        if width > 4000:
            ratio = width//4000
            height = height//ratio
            width = 4000

        if height > 4000:
            ratio = height//4000
            width = width//ratio
            height = 4000

        image = image.resize((width, height), Image.Resampling.LANCZOS)
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
    
def label2rgboverlay(labels: np.ndarray, image: np.ndarray) -> np.ndarray:
    DEFAULT_COLORS = (
        'red',
        'blue',
        'yellow',
        'magenta',
        'green',
        'indigo',
        'darkorange',
        'cyan',
        'pink',
        'yellowgreen',
    )

    colors = [color_dict[c] for c in DEFAULT_COLORS]

    grayscale_image = rgb2gray(image)
    grayscale_image = np.stack([grayscale_image,grayscale_image,grayscale_image], axis=-1)

    dense_labels, inverse_label_matrix = np.unique(labels, return_inverse=True)

    color_cycle = itertools.cycle(colors)
    color_cycle = itertools.chain([(0,0,0)], color_cycle)

    label_to_color = np.stack([c for i, c in zip(range(len(dense_labels)), color_cycle)])
    result = label_to_color[inverse_label_matrix] * 0.3 + grayscale_image * 0.7

    return result

    