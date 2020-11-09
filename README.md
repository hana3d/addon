# Hana3D

Store, manage and search your 3D assets easily.

### Getting started

Run the following command and restart Blender. The addon will be updated.

```
# export STAGE=dev (or locla) to build to a target other than `production`

make clean build install
```

### Testing

```
make lint
make test
```

Feature set:

- login/logout
- workspaces
- assets (model, material, scene)
  - upload
    - reupload
    - conversion pipeline (.blend -> .glb/.usdz)
    - webhooks
  - download
    - link
    - append
  - render
- libraries
- tags

