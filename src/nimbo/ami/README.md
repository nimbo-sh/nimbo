## Copying an image across regions and updating database

After creating a new image in `eu-west-1`, we can copy an AMI to all the regions with:
```
python src/nimbo/ami/copy_images.py <image-id>
```

This will assume the image `<image-id>` exists in `eu-west-1`, and that the image has tags:

```
{
    "CreatedBy": "nimbo",
    "Type": "production"
}
```

To update the firebase database with all the production images across regions, run:
```
python src/nimbo/ami/update_firebase_catalog.py
```
