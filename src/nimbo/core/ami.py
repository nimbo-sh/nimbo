import requests


def get_image_id(config):
    if config["image"][:4] == "ami-":
        image_id = config["image"]
    else:
        response = requests.get("https://nimboami-default-rtdb.firebaseio.com/images.json")
        catalog = response.json()
        region = config["region_name"]
        if region in catalog:
            region_catalog = catalog[region]
            image_name = config["image"]
            if image_name in region_catalog:
                image_id = region_catalog[image_name]
            else:
                raise ValueError(f"The image {image_name} was not found in Nimbo's managed image catalog.\n"
                                 "Check https://docs.nimbo.sh/managed-images for a list of managed images.")
        else:
            raise ValueError(f"We currently do not support managed images in {region}. Please use another region.") 

    return image_id