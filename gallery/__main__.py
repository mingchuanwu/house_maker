"""python -m house_maker.gallery [OUT_DIR]: build the house gallery (default: the gallery directory itself)."""

import sys

from .build import HERE, build_gallery


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    index = build_gallery(argv[0] if argv else HERE)
    print(f"Gallery: {index}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
