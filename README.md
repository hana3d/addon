# Hana3D

Store, manage and search your 3D assets easily.

### Testing

##### Manual

| Feature | Action | Expected Result |
| ------- | ------ | --------------- |
| Login | Click the `Login` button | You log in and see the Worspace `Real2U` |
| Search | Search `cube` on search bar | Many models should appear |
| Search | Search `cube` on side bar | Many models should appear |
| Download | Download `Estante...` to the scene using import method `Link` | The object should be placed into the scene; You see the percentage growing on the sidebar & green box |
| Download | Change import method to `Append` and download the same model | Same as before (the object should be placed into the scene) |
| Download | Click on `Import first 20` | 20 models should be downloaded to the scene |
| Libraries | Choose the library `hana3d` and search with an empty string | Only a cube should appear |
| Upload | Upload a new model to the library `hana3d` | Your model should appear on the search |
| Thumbnailer | Change the model `CUBE01` base color and generate a new thumbnail | Your model thumbnail should be updated |
| Upload | Click `Reupload asset` to re-upload the model `CUBE01` with the new color | Your re-uploaded model should appear on the search |
| Upload | Click `Upload as new asset` to upload a new model | Your new model should appear on the search |
| Thumbnailer | Generate a thumbnail of your model's material | Your material thumbnail should be updated |
| Upload | Click `Upload material` to upload a new material | Your new material should appear on the search |
| Tags | Add a tag `cube` to the library `hana3d` | Your tag should appear on the tags search bar |
| Render | Click on `Generate` to render your scene on Not Render Farm | You should receive an email about your render; The UI should display the render progress |
| Render | Click on `Import render to scene` | You render should XXX |
| Render | Click on `Remove render` | You render should be removed from the list |
| Logout | Click the `Logout` button | You log out of Hana3D |
| Conversions | XXX | XXX |
| Webhooks | XXX | XXX |
