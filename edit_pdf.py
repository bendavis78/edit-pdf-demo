#!/usr/bin/env python
#
# Example usage: 
# cat test.json | ./edit_pdf.py > output.pdf
# 
import os
import sys
import cairo
import poppler
import json

DEFAULT_FONT = 'Sans'

if not cairo.HAS_PDF_SURFACE:
    raise SystemExit('cairo was not compiled with PDF support')

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

        if area['type'] == 'image':
            width = area.get('width', None)
            height = area.get('height', None)
            img_src = area['src']
            if not img_src.startswith('/'):
                img_src = os.path.join(os.getcwd(), img_src)
            image = cairo.ImageSurface.create_from_png(img_src)
            # calculate proportional scaling
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
            slant = {
                'normal': cairo.FONT_SLANT_NORMAL,
                'italic': cairo.FONT_SLANT_ITALIC,
                'oblique': cairo.FONT_SLANT_OBLIQUE
            }.get(area.get('font_slant'), cairo.FONT_SLANT_NORMAL)
            weight = {
                'normal': cairo.FONT_WEIGHT_NORMAL,
                'bold': cairo.FONT_WEIGHT_BOLD
            }.get(area.get('font_weight'), cairo.FONT_WEIGHT_NORMAL)
            family = area.get('font_family', DEFAULT_FONT)
            cr.select_font_face(family, slant, weight)
            cr.set_font_size(area.get('font_size', 12))
            cr.move_to(x, y)
            cr.show_text(area["content"])

        cr.restore()
    
    # Finish
    if fmt == 'img':
        output.write_to_png(sys.stdout)
    else:
        output.show_page()


if __name__ == "__main__":
    edit_pdf(sys.stdin.read(), sys.stdout)
