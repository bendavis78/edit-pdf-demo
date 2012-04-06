#!/usr/bin/env python
#
# Example usage: 
# cat test.json | ./edit_pdf.py > output.pdf
# 
import os
import sys
import re
import json
import cairo
import poppler
import pango
import pangocairo

DEFAULT_FONT_FAMILY = 'Sans'
DEFAULT_FONT_SIZE = 12
DEFAULT_FONT_COLOR = '0,0,0'

DARK_MATTER = .75

if not cairo.HAS_PDF_SURFACE:
    raise SystemExit('cairo was not compiled with PDF support')

def strip_tags(value):
    return 

def edit_pdf(data, output):
    data = json.loads(data)
    source_path = data['template']
    if not source_path.startswith('/'):
        source_path = os.path.join(os.getcwd(), source_path)
    
    # Get source PDF
    document = poppler.document_new_from_file('file://{}'.format(source_path), None)
    page = document.get_page(0)
    width, height = page.get_size()

    # Create destination document
    output = cairo.PDFSurface(output, width, height)
    cr = cairo.Context(output)

    fmt = data.get('output_format', 'pdf')

    # If we're rendering to an image, set a white bg
    cr.set_source_rgb(1, 1, 1)
    cr.paint()

    # Render source PDF to destination
    cr.save()
    page.render(cr)
    cr.restore()

    
    # Render each area
    for area in data['areas']:
        cr.save()

        x = area['x']
        y = area['y']
        width = area.get('width', None)
        height = area.get('height', None)

        if area['type'] == 'image':
            img_src = area['src']
            if not img_src.startswith('/'):
                img_src = os.path.join(os.getcwd(), img_src)
            image = cairo.ImageSurface.create_from_png(img_src)
            # calculate proportional scaling
            # TODO: crop and center
            img_height = image.get_height()
            img_width = image.get_width()
            width_ratio = float(width) / float(img_width)
            height_ratio = float(height) / float(img_height)
            scale_xy = min(height_ratio, width_ratio)
            cr.translate(x, y)
            cr.scale(scale_xy, scale_xy)
            cr.set_source_surface(image)
            cr.paint()

        if area['type'] == 'text':
            cr.move_to(x,y)
            pc_context = pangocairo.CairoContext(cr)
            pc_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
            
            # setup layout
            layout = pc_context.create_layout()
            family = area.get('font_family', DEFAULT_FONT_FAMILY)
            font_size = area.get('font_size', DEFAULT_FONT_SIZE) * DARK_MATTER
            font_desc = '{} {}'.format(family, font_size)
            font = pango.FontDescription(font_desc)
            sys.stderr.write('Font: {}\n'.format(font.get_size()))
            layout.set_font_description(font)

            # if a width is given, set width and word wrap
            if width:
                layout.set_width(width * pango.SCALE)
                if area.get('wrap'):
                    wrap = {
                        'word': pango.WRAP_WORD,
                        'word_char': pango.WRAP_WORD_CHAR,
                        'char': pango.WRAP_CHAR
                    }.get(area['wrap'])
                    layout.set_wrap(wrap)

            content = area.get('content')
            if not area.get('allow_markup'):
                content = re.sub(r'<[^>]*?>', '', content)

            # construct surrounding span tag if any style attrs were given
            if area.get('style'):
                attrs = ['{}="{}"'.format(k,v) for k,v in area['style'].iteritems()]
                content = '<span {}>{}</span>'.format(' '.join(attrs), content)

            if area.get('justify', False):
                layout.set_justify(bool(area.get('justify')))

            layout.set_markup(content)
            rgb = area.get('color', DEFAULT_FONT_COLOR).split(',')
            cr.set_source_rgb(*[int(c) for c in rgb])
            pc_context.update_layout(layout)
            pc_context.show_layout(layout)
            

        cr.restore()
    
    # Finish
    if fmt == 'img':
        output.write_to_png(sys.stdout)
    else:
        output.show_page()


if __name__ == "__main__":
    edit_pdf(sys.stdin.read(), sys.stdout)
