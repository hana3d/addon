# Hana3D

Store, manage and search your 3D assets easily.

### Getting started

Run the following command and restart Blender. The addon will be updated.

```
# export STAGE=dev (or local) to build to a target other than `production`

make clean build install
```

### Development

#### Asyncio workflow

To start an asynchronous task and be notified when it is done, use the
following. This uses the Blender-specific `async_loop` module.

```
lang=python,name=async_example.py
from src.async_loop import run_async_function()

async def some_async_func(x, y):
    return x + y

def done_callback(task):
    print('Task result: ', task.result())

run_async_function(some_async_function, done_callback, x=1, y=1)
```

To start an asynchronous task and block until it is done, use the
following.

```
lang=python,name=blocking_example.py
import asyncio

async def some_async_func():
    return 1 + 1

loop = asyncio.get_event_loop()
res = loop.run_until_complete(some_async_func())
print('Task result:', res)
```

To make an operator run asynchronously use `async_mixin`.

```
lang=python,name=mixin_example.py
import bpy
from src.async_loop.async_mixin import AsyncModalOperatorMixin

async def some_async_func():
    return 1 + 1

class SomeOperator(AsyncModalOperatorMixin, bpy.types.Operator):
    async def async_execute(self, context):
        result = await some_async_func()
        print(result)
```

### Testing

##### Automated

```
make lint
make test
```

##### Manual

See [release template](https://www.notion.so/r2u/Template-de-release-2efb5ad59bc24a53a78f02662371a51e)
for relevant manual testing

### Release

Create a branch with the name `release-x.y.z` where `x.y.z` is the addon version on the intended commit,
then trigger the `Create release` workflow to actually create a release. Remember to duplicate the
release template page on notion and to run all the manual testing before releasing!
