"""Unit test tools."""
import os
import sys
import traceback
import types
from typing import Tuple


class LoadModule(object):
    """Load module.

    Adapted from Script Watcher Addon: https://github.com/wisaac407/blender-script-watcher
    """

    def __init__(self, filepath: str):
        """Init LoadModule.

        Parameters:
            filepath: path to the module
        """
        self.filepath = filepath
        self.remove_cached_mods()
        try:
            with open(filepath) as file_ref:
                paths, files = self.get_paths()

                # Get the module name and the root module path.
                mod_name, mod_root = self.get_mod_name()

                # Create the module and setup the basic properties.
                mod = types.ModuleType('__main__')
                mod.__file__ = filepath
                mod.__path__ = paths
                mod.__package__ = mod_name

                # Add the module to the system module cache.
                sys.modules[mod_name] = mod

                # Fianally, execute the module.
                exec(compile(file_ref.read(), filepath, 'exec'), mod.__dict__)
        except IOError:
            print('Could not open script file.')
        except Exception:
            sys.stderr.write('There was an error when running the script:\n')
            sys.stederr.write(traceback.format_exc())

    def get_paths(self) -> Tuple[list, list]:
        """Find all the python paths surrounding the given filepath.

        Returns:
            paths: list of directory paths
            filepaths: list of file paths
        """
        dirname = os.path.dirname(self.filepath)

        paths = []
        filepaths = []

        for root, dirs, files in os.walk(dirname, topdown=True):
            if '__init__.py' in files:
                paths.append(root)
                for filepath in files:
                    filepaths.append(os.path.join(root, filepath))
            else:
                dirs[:] = []  # No __init__ so we stop walking this dir.

        # If we just have one (non __init__) file then return just that file.
        return paths, filepaths or [self.filepath]

    def get_mod_name(self) -> Tuple[str, str]:
        """Return the module name and the root path of the given python file path.

        Returns:
            module: name of module
            directory: name of directory
        """
        directory, module = os.path.split(self.filepath)

        # Module is a package.
        if module == '__init__.py':
            module = os.path.basename(directory)
            directory = os.path.dirname(directory)

        # Module is a single file.
        else:
            module = os.path.splitext(module)[0]

        return module, directory

    def remove_cached_mods(self):
        """Remove all the script modules from the system cache."""
        paths, files = self.get_paths()
        for mod_name, mod in list(sys.modules.items()):
            try:
                if hasattr(mod, '__file__') and os.path.dirname(mod.__file__) in paths:
                    del sys.modules[mod_name]
            except TypeError:
                pass
