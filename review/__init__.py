"""
Human-in-the-loop review tooling.

* ``python -m house_maker.review build DIR``    build DIR/review.html from the SVG+JSON written by
                                                  ``pytest --svg-dir DIR``
* ``python -m house_maker.review collect``       move downloaded feedback files from the inbox into
                                                  ``house_maker/review/feedback/`` and print a summary
* ``python -m house_maker.review summary [FILE]`` print a feedback file (or all collected ones)

The page itself is a single self-contained HTML file (no server, no network).
"""

import os

DEFAULT_INBOX = os.environ.get('HOUSE_REVIEW_INBOX', '/tmp/house_review_inbox')
