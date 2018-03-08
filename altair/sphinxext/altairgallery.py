import hashlib
import importlib
import os
import shutil
import warnings
import json
import random
from operator import itemgetter

import jinja2

from subprocess import CalledProcessError

from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import flag

from .utils import get_docstring_and_rest, prev_this_next, create_thumbnail
from altair.vegalite.v2.examples import iter_examples


EXAMPLE_MODULE = 'altair.vegalite.v2.examples'


GALLERY_TEMPLATE = jinja2.Template(u"""
.. This document is auto-generated by the altair-gallery extension. Do not modify directly.

.. _{{ gallery_ref }}:

{{ title }}
{% for char in title %}-{% endfor %}

The following examples are automatically generated from
`Vega-Lite's Examples <http://vega.github.io/vega-lite/examples>`_

{% for group in examples|groupby('category') %}
* :ref:`gallery-category-{{ group.grouper }}`
{% endfor %}

{% for group in examples|groupby('category') %}

.. _gallery-category-{{ group.grouper }}:

{{ group.grouper }}
{% for char in group.grouper %}~{% endfor %}

{% for example in group.list %}
.. figure:: {{ image_dir }}/{{ example.name }}-thumb.png
    :target: {{ example.name }}.html
    :align: center

    :ref:`gallery_{{ example.name }}`
{% endfor %}

.. raw:: html

   <div style='clear:both;'></div>

.. toctree::
  :hidden:
{% for example in group.list %}
  {{ example.name }}
{%- endfor %}

{% endfor %}
""")


EXAMPLE_TEMPLATE = jinja2.Template(u"""
.. This document is auto-generated by the altair-gallery extension. Do not modify directly.

.. _gallery_{{ name }}:

{{ docstring }}

.. altair-plot::
    :chart-var-name: chart
    {% if code_below %}:code-below:{% endif %}

    {{ code | indent(4) }}

.. toctree::
   :hidden:
""")


def save_example_pngs(examples, image_dir, make_thumbnails=True):
    """Save example pngs and (optionally) thumbnails"""
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    # store hashes so that we know whether images need to be generated
    hash_file = os.path.join(image_dir, '_image_hashes.json')

    if os.path.exists(hash_file):
        with open(hash_file) as f:
            hashes = json.load(f)
    else:
        hashes = {}

    for example in examples:
        filename = example['name'] + '.png'
        image_file = os.path.join(image_dir, filename)

        example_hash = hashlib.md5(example['code'].encode()).hexdigest()
        hashes_match = (hashes.get(filename, '') == example_hash)
        print('-> using cached {0}'.format(image_file))

        if not hashes_match or not os.path.exists(image_file):
            # the file changed or the image file does not exist. Generate it.
            print('-> saving {0}'.format(image_file))
            _globals = {}
            exec(example['code'], _globals)
            chart = _globals['chart']
            chart.savechart(image_file)
            hashes[filename] = example_hash

            with open(hash_file, 'w') as f:
                json.dump(hashes, f)

        if make_thumbnails:
            params = example.get('galleryParameters', {})
            thumb_file = os.path.join(image_dir, example['name'] + '-thumb.png')
            create_thumbnail(image_file, thumb_file, **params)

    # Save hashes so we know whether we need to re-generate plots
    with open(hash_file, 'w') as f:
        json.dump(hashes, f)


def populate_examples(**kwds):
    """Iterate through Altair examples and extract code"""

    examples = sorted(iter_examples(), key=itemgetter('name'))

    for example in examples:
        docstring, category, code, lineno =\
            get_docstring_and_rest(example['filename'])
        example.update(kwds)
        if category is None:
            category = 'general'
        example.update({'docstring': docstring,
                        'code': code,
                        'category': category.title(),
                        'lineno': lineno})

    return examples


def main(app):
    print('altair-gallery main')

    gallery_dir = app.builder.config.altair_gallery_dir
    target_dir = os.path.join(app.builder.srcdir, gallery_dir)
    image_dir = os.path.join(app.builder.srcdir, '_images')

    gallery_ref = app.builder.config.altair_gallery_ref
    gallery_title = app.builder.config.altair_gallery_title
    examples = populate_examples(gallery_ref=gallery_ref,
                                 code_below=True)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Write the gallery index file
    with open(os.path.join(target_dir, 'index.rst'), 'w') as f:
        f.write(GALLERY_TEMPLATE.render(title=gallery_title,
                                        examples=examples,
                                        image_dir='/_images',
                                        gallery_ref=gallery_ref))

    # save the images to file
    save_example_pngs(examples, image_dir)

    # Write the individual example files
    for prev_ex, example, next_ex in prev_this_next(examples):
        if prev_ex:
            example['prev_ref'] = "gallery_{name}".format(**prev_ex)
        if next_ex:
            example['next_ref'] = "gallery_{name}".format(**next_ex)
        target_filename = os.path.join(target_dir, example['name'] + '.rst')
        with open(os.path.join(target_filename), 'w') as f:
            f.write(EXAMPLE_TEMPLATE.render(example))


def setup(app):
    app.connect('builder-inited', main)
    app.add_stylesheet('altair-gallery.css')
    app.add_config_value('altair_gallery_dir', 'gallery', 'env')
    app.add_config_value('altair_gallery_ref', 'example-gallery', 'env')
    app.add_config_value('altair_gallery_title', 'Example Gallery', 'env')
