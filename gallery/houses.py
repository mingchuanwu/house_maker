"""
The gallery's houses: each is a `house-maker` command line plus a short description. `build.py` runs every command
through the CLI's own `build_house`, so the command shown next to a model is exactly what made it.

To add a house, append an entry; `make gallery` rebuilds the page and `tests/test_gallery.py` checks it still builds.
"""

HOUSES = [
    dict(name='cottage', title='Cottage',
         args='',
         description='The default house: 80 x 60 x 70 mm, 35 degree roof, 3 mm stock. Paned and framed windows, a door '
                     'whose frame reaches the ground, and a framed window up in each gable.'),
    dict(name='chimney-dormer', title='Cottage with chimney and dormer',
         args='--add-chimney --add-additional-gable',
         description='The cottage with a chimney on one roof and a small dormer on the other; the dormer uses its own '
                     'small fingers and tabs its face into the main roof.'),
    dict(name='alpine', title='Alpine house',
         args='--length 160 --width 110 --height 90 --angle 60 --dormer right:x=60:y=15:width=40 '
              '--chimney left:x=40:y=10',
         description='A steep 60 degree roof. The dormer stands on side walls (added automatically on roofs steeper '
                     'than 45 degrees), which lift it and give room for a six-pane window.'),
    dict(name='cape-cod', title='Cape Cod',
         args='--length 200 --width 140 --height 70 --angle 45 --dormers left:count=3:width=30 '
              '--chimney right:x=100:y=10',
         description='Long and low with three identical dormers in a row on the front roof, evenly spaced and set as '
                     'low as they fit; a chimney on the back.'),
    dict(name='twin-rows', title='Dormers both sides',
         args='--length 220 --width 140 --height 90 --angle 45 --dormers both:count=3:width=28',
         description='Three dormers on each roof, laid out the same way on both sides with one --dormers flag.'),
    dict(name='victorian', title='Victorian with cross gables',
         args='--length 180 --width 140 --height 120 --angle 55 --cross-gable left:x=30:width=50 '
              '--cross-gable right:x=100:width=50 --chimney left:x=40:y=10',
         description='Tall and steep, with a cross gable on each side: the wall rises into a gable with its own roof '
                     'running back into the main roof, which is notched at the eave there. Each gable has a window.'),
    dict(name='farmhouse', title='Farmhouse',
         args='--length 220 --width 150 --height 90 --angle 45 --cross-gable left:x=85:width=50 '
              '--dormer left:x=25:y=40:width=30 --dormer left:x=175:y=40:width=30',
         description='A central cross gable on the front, flanked by a dormer on either side.'),
    dict(name='townhouse', title='Townhouse',
         args='--length 80 --width 70 --height 190 --angle 50',
         description='Narrow and tall: three floors of windows, each floor laid out on its own.'),
    dict(name='barn', title='Long barn',
         args='--length 260 --width 120 --height 60 --angle 25',
         description='Long and low under a shallow 25 degree roof, one floor of 2 x 2 windows.'),
    dict(name='brick', title='Brick house with two chimneys',
         args='--length 160 --width 120 --height 90 --architectural-style brick '
              '--chimney left:x=20:y=15 --chimney right:x=25:y=15',
         description='Brick-pattern walls and a chimney on each roof, at opposite ends.'),
    dict(name='arched', title='Arched cottage',
         args='--length 140 --width 100 --height 90 --window-type arched --door-type arched',
         description='Arched windows and an arched door, each with its matching arched frame.'),
]
