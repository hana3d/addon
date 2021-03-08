"""Update addon version."""
import argparse
import fileinput
import re


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('version')

    args = parser.parse_args()
    major, minor, patch = args.version.split('.')

    version_regex = re.compile(r"'version': \(\d+, \d+, \d+\),")
    with fileinput.input(files=('hana3d/__init__.py'), inplace=True) as init_file:
        for line in init_file:
            if version_regex.search(line):
                line = re.sub(r'\d+, \d+, \d+', f'{major}, {minor}, {patch}', line)
            print(line, end='')  # noqa: WPS421


if __name__ == '__main__':
    _main()
