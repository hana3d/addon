# Hana3D

Store, manage and search your 3D assets easily.

### Getting started

Run the following command and restart Blender. The addon will be updated.

```
# export STAGE=dev (or local) to build to a target other than `production`

make clean build install
```

### Testing

##### Automated

```
make lint
make test
```

##### Manual

| Feature | Action | Expected Result |
| ------- | ------ | --------------- |
| Login | Click the `Login` button | You log in and see the Worspace `Real2U` |
| Search | Search `cube` on search bar | Many models should appear |
| Search | Search `cube` on side bar | Many models should appear |
| Download | Download `Estante...` to the scene using import method `Link` | The object should be placed into the scene; You see the percentage growing on the sidebar & green box |
| Download | Change import method to `Append` and download the same model | Same as before (the object should be placed into the scene) |
| Download | Click on `Import first 20` | 20 models should be downloaded to the scene |
| Libraries | Choose the library `hana3d` and search with an empty string | Sample models, such as cubes, sould appear |
| Upload | Upload a new model to the library `hana3d` | Your model should appear on the search |
| Thumbnailer | Change the model `CUBE01` base color and generate a new thumbnail | Your model thumbnail should be updated |
| Tags | Add a tag to the model | Your model should be uploaded with the selected tag |
| Upload | Click `Reupload asset` to re-upload the model `CUBE01` with the new color | Your re-uploaded model should appear on the search |
| Upload | Click `Upload as new asset` to upload a new model | Your new model should appear on the search |
| Thumbnailer | Generate a thumbnail of your model's material | Your material thumbnail should be updated |
| Upload | Click `Upload material` to upload a new material | Your new material should appear on the search |
| Thumbnailer | Generate a thumbnail of your scene | Your scene thumbnail should be updated |
| Upload | Click `Upload scene` to upload a new scene | Your new scene should appear on the search |
| Render | Click on `Generate` to render your scene on Not Render Farm | You should receive an email about your render; The UI should display the render progress |
| Render | Click on `Import render to scene` | You render should appear in Blender's images (can be checked in `Rendering` tab and browsing the images) |
| Render | Click on `Remove render` | You render should be removed from the list. After re-downloading asset, render should still be removed from list |
| Logout | Click the `Logout` button | You log out of Hana3D |
