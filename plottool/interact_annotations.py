"""
Interactive tool to draw mask on an image or image-like array.

TODO:
    * need concept of subannotation
    * need to take options on a right click of an annotation
    * add support for arbitrary polygons back in .
    * rename species_list to label_list or category_list

Notes:
    3. Change bounding box and update continuously to the original image the
    new ANNOTATIONs

    2. Make new window and frames inside, double click to pull up normal window
    with editing start with just taking in 6 images and ANNOTATIONs

    1. ANNOTATION ID number, then list of 4 tuples

References:
    Adapted from matplotlib/examples/event_handling/poly_editor.py
    Jan 9 2014: taken from: https://gist.github.com/tonysyu/3090704

CommandLine:
    python -m utool.util_inspect check_module_usage --pat="interact_annotations.py"
    python -m plottool.interact_annotations --test-test_interact_annots --show
"""
from __future__ import absolute_import, division, print_function
import six
import re
import numpy as np
import vtool as vt
import utool as ut
import matplotlib as mpl
from functools import partial
from six.moves import zip, range
from plottool import draw_func2 as df2
from plottool import abstract_interaction
print, rrr, profile = ut.inject2(__name__, '[interact_annotations]')


DEFAULT_SPECIES_TAG = '____'
# FIXE THESE TO BE GENERIC
ACCEPT_SAVE_HOTKEY        = None  # 'ctrl+a'
ADD_RECTANGLE_HOTKEY      = 'ctrl+a'  # 'ctrl+d'
ADD_RECTANGLE_FULL_HOTKEY = 'ctrl+f'
DEL_RECTANGLE_HOTKEY      = 'ctrl+d'  # 'ctrl+r'
TOGGLE_LABEL_HOTKEY       = 'ctrl+t'

HACK_OFF_SPECIES_TYPING = True
if HACK_OFF_SPECIES_TYPING:
    ADD_RECTANGLE_HOTKEY      = 'a'  # 'ctrl+d'
    ADD_RECTANGLE_FULL_HOTKEY = 'f'
    DEL_RECTANGLE_HOTKEY      = 'd'  # 'ctrl+r'
    TOGGLE_LABEL_HOTKEY       = 't'

NEXT_IMAGE_HOTKEYS  = ['right', 'pagedown']
PREV_IMAGE_HOTKEYS  = ['left', 'pageup']

TAU = np.pi * 2

AbstractInteraction = abstract_interaction.AbstractInteraction
BASE_CLASS = AbstractInteraction



class AnnotPoly(mpl.patches.Polygon):
    """
    Helper to represent an annotation polygon
    """

    def __init__(poly, ax, num, verts, theta, species, fc=(0, 0, 0),
                 line_color=(1, 1, 1), line_width=4, is_orig=False,
                 metadata=None, valid_species=None):

        super(AnnotPoly, poly).__init__(verts, animated=True, fc=fc, ec='none',
                                        alpha=0, picker=True)
        poly.num = num
        poly.is_orig = is_orig
        poly.theta = theta
        poly.basecoords = poly.xy

        poly.xy = calc_display_coords(poly.basecoords, poly.theta)
        poly.lines = poly._make_lines(line_color, line_width)
        poly.handle = poly._make_handle_line()
        #tagpos = calc_tag_position(poly)
        poly.species_tag = ax.text(
            #tagpos[0], tagpos[1],
            0, 0,
            species,
            bbox={'facecolor': 'white', 'alpha': .8},
            verticalalignment='top',
        )

        if isinstance(metadata, ut.LazyDict):
            """
            ibeis --aidcmd='Interact image' --aid=1
            """
            metadata_ = ut.dict_subset(metadata, metadata.cached_keys())
        else:
            metadata_ = metadata
            #metadata = metadata.asdict(False)
            #metadata

        poly.metadata_tag = ax.text(
            0, 0,
            #tagpos[0] + 5, tagpos[1] + 80,
            ut.repr3(metadata_, nobr=True),
            bbox={'facecolor': 'white', 'alpha': .7},
            verticalalignment='top',
        )
        set_display_coords(poly)
        poly.species_tag.remove()  # eliminate "leftover" copies
        poly.metadata_tag.remove()
        poly.metadata = metadata
        # put in previous text and tabcomplete list for autocompletion
        poly.tctext = ''
        poly.valid_species = valid_species
        poly.tab_list = valid_species
        poly.tcindex = 0
        poly.anchor_idx = 2

    def add_to_axis(poly, ax):
        ax.add_patch(poly)
        ax.add_line(poly.lines)
        ax.add_line(poly.handle)

    def draw_self(poly, ax, show_species_tags):
        ax.draw_artist(poly)
        ax.draw_artist(poly.lines)
        ax.draw_artist(poly.handle)
        if show_species_tags:
            # Hack to fix matplotlib 1.5 bug
            poly.species_tag.figure = ax.figure
            poly.metadata_tag.figure = ax.figure
            ax.draw_artist(poly.species_tag)
            ax.draw_artist(poly.metadata_tag)

    def _make_lines(poly, line_color, line_width):
        """ verts - list of (x, y) tuples """
        _xs, _ys = list(zip(*poly.xy))
        color = np.array(line_color)
        marker_face_color = line_color
        line_kwargs = {'lw': line_width, 'color': color,
                       'mfc': marker_face_color}
        lines = mpl.lines.Line2D(_xs, _ys, marker='o', alpha=1, animated=True,
                                 **line_kwargs)
        return lines

    def _make_handle_line(poly):
        _xs, _ys = list(zip(*calc_handle_display_coords(poly)))
        line_width = 4
        line_color = (0, 1, 0)
        color = np.array(line_color)
        marker_face_color = line_color
        line_kwargs = {'lw': line_width, 'color': color, 'mfc': marker_face_color}
        lines = mpl.lines.Line2D(_xs, _ys, marker='o', alpha=1, animated=True,
                                 **line_kwargs)
        return lines

    def update_color(poly, selected=False):
        if selected:
            # Add selected color
            sel_color = df2.ORANGE if poly.is_orig else df2.LIGHT_BLUE
            poly.lines.set_color(sel_color)
        else:
            line = poly.lines
            line_color = line.get_color()
            desel_color = df2.WHITE if poly.is_orig else df2.LIGHTGRAY
            if np.any(line_color != np.array(desel_color)):
                line.set_color(np.array(desel_color))

    def update_lines(poly):
        poly.lines.set_data(list(zip(*poly.xy)))
        poly.handle.set_data(list(zip(*calc_handle_display_coords(poly))))

    def set_species(poly, text):
        poly.tctext = text
        poly.species_tag.set_text(text)

    def increment_species(poly, amount=1):
        if len(poly.tab_list) > 0:
            tci = (poly.tcindex + amount) % len(poly.tab_list)
            poly.tcindex = tci
            # All tab is going to do is go through the possibilities
            poly.species_tag.set_text(poly.tab_list[poly.tcindex])

    def resize(poly, x, y, idx, ax):
        """
        Resize a rectangle using idx as the given anchor point. Respects
        current rotation.

        CommandLine:
            python -m plottool.interact_annotations --exec-resize --show

        Example:
            >>> # DISABLE_DOCTEST
            >>> from plottool.interact_annotations import *  # NOQA
            >>> (h, w) = img.shape[0:2]
            >>> x1, y1 = 10, 10
            >>> x2, y2 = w - 10,  h - 10
            >>> coords = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
            >>> x = 3 * w / 4
            >>> y = 3 * h / 4
            >>> idx = 3
            >>> resize(poly, x, y, idx)
            >>> update_UI()
            >>> import plottool as pt
            >>> pt.show_if_requested()
        """
        # TODO: allow resize by middle click to scale from the center
        if poly is None:
            return

        # the minus one is because the last coordinate is duplicated (by
        # matplotlib) to get a closed polygon
        tmpcoords = poly.xy[:-1]
        previdx = (idx - 1) % len(tmpcoords)
        nextidx = (idx + 1) % len(tmpcoords)
        (dx, dy) = (x - poly.xy[idx][0], y - poly.xy[idx][1])
        # Fudge factor is due to gravity vectors constants
        fudge_factor = (idx) * TAU / 4
        poly_theta = poly.theta + fudge_factor

        polar_idx2prev = polarDelta(tmpcoords[idx], tmpcoords[previdx])
        polar_idx2next = polarDelta(tmpcoords[idx], tmpcoords[nextidx])
        tmpcoords[idx] = (tmpcoords[idx][0] + dx, tmpcoords[idx][1] + dy)
        mag_delta = distance(dx, dy)
        theta_delta = np.arctan2(dy, dx)
        theta_rot = theta_delta - (poly_theta + TAU / 4)
        rotx = mag_delta * np.cos(theta_rot)
        roty = mag_delta * np.sin(theta_rot)
        polar_idx2prev[0] -= rotx
        polar_idx2next[0] += roty
        tmpcoords[previdx] = apply_polarDelta(polar_idx2prev, tmpcoords[idx])
        tmpcoords[nextidx] = apply_polarDelta(polar_idx2next, tmpcoords[idx])

        # rotate the points by -theta to get the "unrotated" points for use as
        # basecoords
        tmpcoords = rotate_points_around(tmpcoords, -poly.theta,
                                         *points_center(poly.xy))
        # ensure the poly is closed, matplotlib might do this, but I'm not sure
        # if it preserves the ordering we depend on, even if it does add the
        # point
        tmpcoords = tmpcoords[:] + [tmpcoords[0]]

        dispcoords = calc_display_coords(tmpcoords, poly.theta)

        if (check_valid_coords(ax, dispcoords) and
             meets_minimum_width_and_height(tmpcoords)):
            poly.basecoords = tmpcoords
        set_display_coords(poly)

    def rotate(poly, dtheta, ax):
        coords_lis = calc_display_coords(poly.basecoords, poly.theta + dtheta)
        if check_valid_coords(ax, coords_lis):
            poly.theta += dtheta
            set_display_coords(poly)

    def translate(poly, dx, dy, ax):
        new_coords = [(x + dx, y + dy) for (x, y) in poly.basecoords]
        coords_list = calc_display_coords(new_coords, poly.theta)
        if check_valid_coords(ax, coords_list):
            poly.basecoords = new_coords
            set_display_coords(poly)


@six.add_metaclass(ut.ReloadingMetaclass)
class AnnotationInteraction(BASE_CLASS):
    """
    An interactive polygon editor.

    SeeAlso:
        ibeis.viz.interact.interact_annotations2
        (ensure that any updates here are propogated there)

    Args:
        verts_list (list) : list of lists of (float, float)
            List of (x, y) coordinates used as vertices of the polygon.

        max_ds (float) : float
            Max pixel distance to count as a vertex hit.
    """
    # --- Initialization and Figure Widgets
    def __init__(self, img, img_ind=None, commit_callback=None,
                 verts_list=None,
                 bbox_list=None,
                 theta_list=None,
                 species_list=None,
                 metadata_list=None,
                 max_ds=10,
                 line_width=4, line_color=(1, 1, 1), face_color=(0, 0, 0),
                 fnum=None, default_species=DEFAULT_SPECIES_TAG,
                 next_callback=None, prev_callback=None, do_mask=False,
                 valid_species=[],
                 **kwargs):
        super(AnnotationInteraction, self).__init__(fnum=fnum, **kwargs)

        self.valid_species = valid_species
        self.commit_callback = commit_callback  # commit_callback
        self.but_width = .14
        #self.but_height = .08
        self.next_prev_but_height = .08
        self.but_height = self.next_prev_but_height - .01
        self.callback_funcs = dict([
            ('close_event', self.on_close),
            ('draw_event', self.draw_callback),
            ('button_press_event', self.on_click),
            ('button_release_event', self.on_click_release),
            ('figure_leave_event', self.on_figure_leave),
            ('key_press_event', self.on_key_press),
            ('motion_notify_event', self.on_motion),
            ('pick_event', self.onpick),
            #('resize_event', self.on_resize),
        ])
        self.mpl_callback_ids = {}
        self.img = img
        self.show_species_tags = True
        def _reinitialize_variables():
            self.do_mask = do_mask
            self.img_ind = img_ind
            self.species_tag = default_species
            self.showverts = True
            self.max_ds = max_ds
            self.fc_default = face_color
            self.mouseX = None  # mouse X coordinate
            self.mouseY = None  # mouse Y coordinate
            self.indX = None
            self.indY = None
            self.reset_mouse_state()
            self.canUncolor = False    # flag if the polygon SHOULD be active
            self._autoinc_polynum = 0  # num polys in image
            self._polyHeld = False                # if any poly is active
            self._current_sel_poly = None  # active polygon
            self.background = None  # Something Jon added
        _reinitialize_variables()
        # hack involving exploting lexical scoping to save defaults for a
        # restore operation
        self.reinitialize_variables = _reinitialize_variables
        self.handle_matplotlib_initialization(fnum=fnum)
        assert verts_list is None or bbox_list is None, 'only one can be specified'
        # bbox_list will get converted to verts_list
        if verts_list is not None:
            bbox_list = vt.bboxes_from_vert_list(verts_list)
        if bbox_list is not None:
            verts_list = [vt.verts_from_bbox(bbox) for bbox in bbox_list]
        if theta_list is None:
            theta_list = [0 for _ in verts_list]
        if species_list is None:
            species_list = [self.species_tag for _ in verts_list]
        if metadata_list is None:
            metadata_list = [None for _ in verts_list]

        # Create the list of polygons
        self.handle_polygon_creation(bbox_list, theta_list, species_list, metadata_list)
        self._ind = None  # the active vert
        self._current_rotate_poly = None

        self.mpl_callback_ids = {}
        assert self.fig.canvas is self.fig.ax.figure.canvas, 'wow. something is weird'
        self.connect_mpl_callbacks(self.fig.canvas)

        self.add_action_buttons()
        self.update_callbacks(next_callback, prev_callback)

    def handle_matplotlib_initialization(self, fnum=None,
                                         instantiate_window=True):
        if instantiate_window:
            self.fig = df2.figure(fnum=fnum, doclf=True, docla=True)
            df2.close_figure(self.fig)
            self.fig = df2.figure(fnum=fnum, doclf=True, docla=True)
        self.fig.clear()
        self.fig.clf()
        #self.fig.cla()
        #ut.qflag()
        self.fnum = fnum
        #print(self.fnum)
        ax = df2.gca()
        self.fig.ax = ax
        self.ax = ax
        df2.remove_patches(self.fig.ax)
        df2.imshow(self.img, fnum=fnum)

        ax.set_clip_on(False)
        ax.set_title(('\n'.join([
            'Click and drag to select/move/resize/orient an ANNOTATION',
            #'Press enter to clear the species tag of the selected ANNOTATION',
            'Press tab to cycle through annotation species',
            #'Type to edit the ANNOTATION species (press tab to autocomplete)'
        ])))

    def add_action_buttons(self):
        self.append_button(
            'Add Annotation\n' + pretty_hotkey_map(ADD_RECTANGLE_HOTKEY),
            rect=[0.18, 0.015, self.but_width, self.but_height],
            callback=self.add_new_annot
        )
        self.append_button(
            'Add Full Annotation\n' + pretty_hotkey_map(ADD_RECTANGLE_FULL_HOTKEY),
            rect=[0.34, 0.015, self.but_width, self.but_height],
            callback=partial(self.add_new_annot, full=True)
        )
        self.append_button(
            'Delete Annotation\n' + pretty_hotkey_map(DEL_RECTANGLE_HOTKEY),
            rect=[0.50, 0.015, self.but_width, self.but_height],
            callback=self.delete_current_annot
        )
        self.append_button(
            'Save and Exit\n' + pretty_hotkey_map(ACCEPT_SAVE_HOTKEY),
            rect=[0.66, 0.015, self.but_width, self.but_height],
            callback=self.save_and_exit
        )

    def disconnect_mpl_callbacks(self, canvas):
        """ disconnects all connected matplotlib callbacks """
        for name, callbackid in six.iteritems(self.mpl_callback_ids):
            canvas.mpl_disconnect(callbackid)
        self.mpl_callback_ids = {}

    def connect_mpl_callbacks(self, canvas):
        """ disconnects matplotlib callbacks specified in the
        self.mpl_callback_ids dict """
        #http://matplotlib.org/1.3.1/api/backend_bases_api.html
        # Create callback ids
        self.disconnect_mpl_callbacks(canvas)
        self.mpl_callback_ids = {
            name: canvas.mpl_connect(name, func)
            for name, func in six.iteritems(self.callback_funcs)
        }
        self.fig.canvas = canvas

    # --- Updates

    def update_callbacks(self, next_callback, prev_callback):
        self.prev_callback = prev_callback
        self.next_callback = next_callback
        # Hack because the callbacks actually need to be wrapped
        _next_callback = None if self.next_callback is None else self.next_image
        _prev_callback = None if self.prev_callback is None else self.prev_image
        self.append_button(
            'Previous Image\n' + pretty_hotkey_map(PREV_IMAGE_HOTKEYS),
            rect=[0.02, 0.01, self.but_width, self.next_prev_but_height],
            callback=_prev_callback,
        )
        self.append_button(
            'Next Image\n' + pretty_hotkey_map(NEXT_IMAGE_HOTKEYS),
            rect=[0.82, 0.01, self.but_width, self.next_prev_but_height],
            callback=_next_callback,
        )

    def update_image_and_callbacks(self, img, bbox_list, theta_list,
                                   species_list, metadata_list, next_callback,
                                   prev_callback):
        self.disconnect_mpl_callbacks(self.fig.canvas)
        for poly in six.itervalues(self.polys):
            poly.remove()
        self.polys = {}
        self.reinitialize_variables()
        self.img = img
        self.handle_matplotlib_initialization(
            fnum=self.fnum, instantiate_window=False)
        self.handle_polygon_creation(bbox_list, theta_list, species_list,
                                     metadata_list)
        self.add_action_buttons()
        self.draw()
        self.connect_mpl_callbacks(self.fig.canvas)
        self.update_callbacks(next_callback, prev_callback)
        print('[interact_annot] drawing')
        self.draw()
        self.update_UI()

    def update_UI(self):
        self._update_lines()
        self.fig.canvas.restore_region(self.background)
        self.draw_artists()
        self.fig.canvas.blit(self.fig.ax.bbox)

    def update_annot_colors(self, poly_ind):
        for ind, poly in six.iteritems(self.polys):
            assert poly.num == ind
            selected = ind == poly_ind
            poly.update_color(selected=selected)
        self.draw()

    def _update_lines(self):
        for poly in six.itervalues(self.polys):
            self.last_vert_ind = len(poly.xy) - 1
            poly.update_lines()

    # --- Data Matainence / Other

    def handle_polygon_creation(self, bbox_list, theta_list, species_list,
                                metadata_list):
        """ Maintain original input """
        assert bbox_list is not None
        if theta_list is None:
            theta_list = [0.0 for _ in range(len(bbox_list))]
        if species_list is None:
            species_list = ['' for _ in range(len(bbox_list))]
        assert len(bbox_list) == len(theta_list), 'inconconsitent data1'
        assert len(bbox_list) == len(species_list), 'inconconsitent data2'
        assert len(bbox_list) == len(metadata_list), 'inconconsitent data2'
        self.original_indices       = list(range(len(bbox_list)))
        self.original_bbox_list     = bbox_list
        self.original_theta_list    = theta_list
        self.original_species_list  = species_list
        self.original_metadata_list = metadata_list
        # Convert bbox to verticies
        verts_list = [vt.verts_from_bbox(bbox) for bbox in bbox_list]
        for verts in verts_list:
            for vert in verts:
                enforce_dims(self.fig.ax, vert)
        # Create polygons
        poly_list = [self.new_polygon(verts, theta, species, is_orig=True,
                                      metadata=metadata)
                     for (verts, theta, species, metadata) in
                     zip(verts_list, theta_list, species_list, metadata_list)]
        self.polys = {poly.num: poly for poly in poly_list}
        if len(self.polys) != 0:
            wh_list = np.array([vt.bbox_from_verts(poly.xy)[2:4] for poly in
                                six.itervalues(self.polys)])
            poly_index = list(self.polys.keys())[wh_list.prod(axis=1).argmax()]
            self._current_sel_poly = self.polys[poly_index]
            self.update_annot_colors(poly_index)
            self._update_lines()
        else:
            self._current_sel_poly = None
        # Add polygons and lines to the axis
        for poly in six.itervalues(self.polys):
            poly.add_to_axis(self.fig.ax)
        # Give polygons mpl change callbacks
        for poly in six.itervalues(self.polys):
            poly.add_callback(self.poly_changed)

    def get_ind_under_cursor(self, event):
        """
        get the index of the vertex under cursor if within max_ds tolerance
        """
        # Get mouse coords in figure space
        x, y = event.x, event.y
        # Remove any deleted polygons
        poly_dict = {k: v for k, v in self.polys.items() if v is not None}
        if len(poly_dict) > 0:
            poly_inds = list(poly_dict.keys())
            poly_list = ut.take(poly_dict, poly_inds)
            # Put polygon coords into figure space
            poly_pts = [poly.get_transform().transform(np.asarray(poly.xy))
                        for poly in poly_list]
            # Find the nearest vertex from the annotations
            ind_dist_list = [vt.nearest_point(x, y, polypts)
                             for polypts in poly_pts]
            dist_lists = ut.take_column(ind_dist_list, 1)
            min_idx = np.argmin(dist_lists)
            sel_polyind = poly_inds[min_idx]
            sel_vertx, sel_dist = ind_dist_list[min_idx]
            # Ensure nearest distance is within threshold
            if sel_dist >= self.max_ds ** 2:
                sel_polyind, sel_vertx = (None, None)
        else:
            sel_polyind, sel_vertx = (None, None)
        return sel_polyind, sel_vertx

    def _next_polynum(self):
        num = self._autoinc_polynum
        self._autoinc_polynum += 1
        return num

    def new_polygon(self, verts, theta, species, fc=(0, 0, 0),
                    line_color=(1, 1, 1), line_width=4, is_orig=False,
                    metadata=None):
        """ verts - list of (x, y) tuples """
        # create new polygon from verts
        num = self._next_polynum()
        poly = AnnotPoly(self.ax, num, verts, theta, species, fc, line_color,
                         line_width, is_orig, metadata, self.valid_species)
        return poly

    def get_mask(self, shape):
        """Return image mask given by mask creator"""
        mask_list = [verts_to_mask(shape, poly.xy)
                     for poly in six.itervalues(self.polys)]
        if len(mask_list) == 0:
            print('[interact_annot] No polygons to make mask out of')
            return 0
        mask = mask_list[0]
        for mask_ in mask_list:
            mask = np.maximum(mask, mask_)
        return mask

    def get_most_recently_added_poly(self):
        if len(self.polys) == 0:
            return (None, None)
        else:
            # most recently added polygon has the highest index
            poly_ind = max(list(self.polys.keys()))
            return poly_ind, self.polys[poly_ind]

    # --- Actions

    def delete_current_annot(self, event=None):
        """
        Removes an annotation
        """
        if self._current_sel_poly is None:
            print('[interact_annot] No polygon selected to delete')
            return
        poly = self._current_sel_poly
        lineNumber = poly.num
        print('[interact_annot] delete annot. length=%d num=%d' % (
            len(self.polys), lineNumber))
        self.polys.pop(lineNumber)
        # remove the poly from the figure itself
        poly.remove()
        #reset anything that has to do with current poly
        _tup = self.get_most_recently_added_poly()
        poly_ind, self._current_sel_poly = _tup
        self._polyHeld = False
        if poly_ind is not None:
            self.update_annot_colors(poly_ind)
        self.draw()

    def add_new_annot(self, event=None, full=False):
        """ Adds a new annotation to the image """
        if full:
            (h, w) = self.img.shape[0:2]
            x1, y1 = 1, 1
            x2, y2 = w - 1, h - 1
            coords = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
        else:
            if self._current_sel_poly is not None:
                defaultshape_polys = {
                    self._current_sel_poly.num:
                    self._current_sel_poly
                }
            else:
                defaultshape_polys = self.polys
            coords = default_vertices(self.img, defaultshape_polys,
                                      self.mouseX, self.mouseY)

        poly = self.new_polygon(coords, 0, self.species_tag)

        bbox = vt.bbox_from_verts(poly.basecoords)
        poly.basecoords = vt.verts_from_bbox(bbox)
        set_display_coords(poly)

        self.polys[poly.num] = poly
        poly.add_to_axis(self.ax)
        self._update_lines()

        poly.add_callback(self.poly_changed)
        self._ind = None  # the active vert
        poly_ind, poly_ = self.get_most_recently_added_poly()
        self._current_sel_poly = poly_
        self.update_annot_colors(poly_ind)
        self.draw()

    def toggle_species_label(self):
        print('[interact_annot] toggle_species_label()')
        self.show_species_tags = not self.show_species_tags
        self.update_UI()

    def next_image(self, event):
        if self.next_callback is not None:
            self.next_callback()

    def prev_image(self, event):
        if self.prev_callback is not None:
            self.prev_callback()

    def save_and_exit(self, event, do_close=True):
        """
        The Save and Exit Button

        write a callback to redraw viz for bbox_list
        """
        print('[interact_annot] Pressed Accept Button')

        def _get_annottup_list():
            annottup_list = []
            indices_list = []
            #theta_list = []
            for poly in six.itervalues(self.polys):
                assert poly is not None
                index   = poly.num
                bbox    = tuple(map(int, vt.bbox_from_verts(poly.basecoords)))
                theta   = poly.theta
                species = poly.species_tag.get_text()
                annottup = (bbox, theta, species)
                indices_list.append(index)
                annottup_list.append(annottup)
            return indices_list, annottup_list

        def _send_back_annotations():
            print('[interact_annot] _send_back_annotations')
            indices_list, annottup_list = _get_annottup_list()
            # Delete if index is in original_indices but no in indices_list
            deleted_indices   = list(set(self.original_indices) -
                                     set(indices_list))
            changed_indices   = []
            unchanged_indices = []  # sanity check
            changed_annottups = []
            new_annottups     = []
            original_annottup_list = list(zip(self.original_bbox_list,
                                              self.original_theta_list,
                                              self.original_species_list))
            for index, annottup in zip(indices_list, annottup_list):
                # If the index is not in the originals then it is new
                if index not in self.original_indices:
                    new_annottups.append(annottup)
                else:
                    if annottup not in original_annottup_list:
                        changed_annottups.append(annottup)
                        changed_indices.append(index)
                    else:
                        unchanged_indices.append(index)
            self.commit_callback(unchanged_indices, deleted_indices,
                                 changed_indices, changed_annottups,
                                 new_annottups)

        if self.commit_callback is not None:
            _send_back_annotations()
        # Make mask from selection
        if self.do_mask is True:
            self.fig.clf()
            self.ax = ax = self.fig.subplot(111)
            img = self.img
            mask = self.get_mask(img.shape)
            # User must close previous figure
            # Modify the image with the mask
            masked_img = apply_mask(img, mask)
            # show the modified image
            ax.imshow(masked_img)
            ax.title('Region outside of mask is darkened')

            ax.figure.show()
            return

        print('[interact_annot] Accept Over')
        if do_close:
            df2.close_figure(self.fig)

    # --- Connected Slots and Callbacks

    def show(self):
        self.draw()
        self.bring_to_front()

    def draw_callback(self, event):
        self.background = self.fig.canvas.copy_from_bbox(self.fig.ax.bbox)
        self.draw_artists()

    def draw_artists(self):
        for poly in six.itervalues(self.polys):
            poly.draw_self(self.fig.ax, self.show_species_tags)

    def _show_poly_context_menu(self, event):
        def _print_poly_info():
            print('self._current_sel_poly = %r' %
                  (self._current_sel_poly,))
            print('tag_text = %r' %
                  (self._current_sel_poly.species_tag.get_text(),))
            print('self._current_sel_poly.metadata = %r' %
                  (self._current_sel_poly.metadata,))
        def _make_options():
            metadata = self._current_sel_poly.metadata
            options = []
            options += [
                #('Foo: ',  functools.partial(print, 'bar')),
                ('PolyInfo: ',  _print_poly_info),
            ]
            if isinstance(metadata, ut.LazyDict):
                options += metadata.nocache_eval('annot_context_options')
            return options
        options = _make_options()
        self.show_popup_menu(options, event)

    def on_click(self, event):
        """
        python -m ibeis.viz.interact.interact_annotations2 --test-ishow_image2 --show
        """
        super(AnnotationInteraction, self).on_click(event)
        if self._ind is not None:
            self._ind = None
            return
        ignore = not self.showverts or event.inaxes is None
        if ignore:
            return

        # Right click - context menu
        if event.button == self.RIGHT_BUTTON:
            self._show_poly_context_menu(event)
        # Left click, indicate that a mouse button is down
        if event.button == self.LEFT_BUTTON:
            if event.key == 'shift':
                self._current_sel_poly
                self._current_rotate_poly = self._current_sel_poly
            else:
                # Determine if we are clicking the rotation line
                for poly in six.itervalues(self.polys):
                    near_line = is_within_distance_from_line(
                        self.max_ds, (event.xdata, event.ydata),
                        calc_handle_display_coords(poly))
                    if near_line:
                        self._current_rotate_poly = poly
                        break

        if self._current_sel_poly is None:
            print('[interact_annot] WARNING: Polygon unknown.'
                  ' Using last placed poly.')
            if len(self.polys) == 0:
                print('[interact_annot] No polygons on screen')
                return
            else:
                poly_ind, self._current_sel_poly = self.get_most_recently_added_poly()
                self.update_annot_colors(poly_ind)

        polyind, self._ind = self.get_ind_under_cursor(event)

        if event.dblclick:
            print("DOUBLECLICK")
            # On double click enter a single annotation to annotation parts

        if self._ind is not None and polyind is not None:
            self._current_sel_poly = self.polys[polyind]
            if self._current_sel_poly is None:
                return
            self.indX, self.indY = self._current_sel_poly.xy[self._ind]
            self._polyHeld = True
            self.update_annot_colors(polyind)
            self._current_sel_poly.anchor_idx = self._ind

        self.mouseX, self.mouseY = event.xdata, event.ydata

        if self._polyHeld is True or self._ind is not None:
            self._current_sel_poly.set_alpha(.2)
            self.update_annot_colors(self._current_sel_poly.num)

        self.canUncolor = False
        self._update_lines()
        if self.background is not None:
            self.fig.canvas.restore_region(self.background)
        else:
            print('[interact_annot] error: self.background is none.'
                  ' Trying refresh.')
            self.fig.canvas.restore_region(self.background)
            self.background = self.fig.canvas.copy_from_bbox(self.fig.ax.bbox)

        # Redraw blitted objects
        self.draw_artists()
        self.fig.canvas.blit(self.fig.ax.bbox)

    def on_click_release(self, event):
        super(AnnotationInteraction, self).on_click_release(event)

        if self._polyHeld is True:
            self._polyHeld = False

        self._current_rotate_poly = None

        ignore = not self.showverts or self._current_sel_poly is None
        if ignore:
            return

        _flag = (
            self._ind is None or
            self._polyHeld is False or
            (self._ind is not None and
             self.is_down['left'] is True and
             self._current_sel_poly is not None and
             self.canUncolor is True)
        )
        if _flag:
            self._current_sel_poly.set_alpha(0)
            #self._current_sel_poly.set_facecolor('white')

        self.update_UI()

        if self._ind is None:
            return
        if self._current_sel_poly is None:
            print('[interact_annot] WARNING: Polygon unknown.'
                  ' Using default. (2)')
            if len(self.polys) == 0:
                print('[interact_annot] No polygons on screen')
                return
            else:
                _tup = self.get_most_recently_added_poly()
                poly_ind, self._current_sel_poly = _tup
        currX, currY = self._current_sel_poly.xy[self._ind]

        if self.indX and self.indY:
            if (np.fabs(self.indX - currX) < 3 and
                 np.fabs(self.indY - currY) < 3):
                return

        self._ind = None
        self._polyHeld = False

        self.draw()

    def on_figure_leave(self, event):
        if self.debug > 0:
            print('[interact_annot] figure leave')
        #self.print_status()
        #self.on_click_release(event)
        self._polyHeld = False
        self._ind = None
        self.reset_mouse_state()
        #self.print_status()

    def on_key_press(self, event):
        if self.debug > 0:
            print('[interact_annot] on_key_press')
            print('[interact_annot] Got key: %r' % event.key)
        if not event.inaxes:
            return

        if event.key == ACCEPT_SAVE_HOTKEY:
            self.save_and_exit(event)
        elif event.key == ADD_RECTANGLE_HOTKEY:
            self.add_new_annot()
        elif event.key == ADD_RECTANGLE_FULL_HOTKEY:
            self.add_new_annot(full=True)
        elif event.key == DEL_RECTANGLE_HOTKEY:
            self.delete_current_annot()
        elif event.key == TOGGLE_LABEL_HOTKEY:
            self.toggle_species_label()

        if re.match('^backspace$', event.key):
            self._current_sel_poly.set_species(DEFAULT_SPECIES_TAG)
        if re.match('^tab$', event.key):
            self._current_sel_poly.increment_species(amount=1)
        if re.match('^ctrl\+tab$', event.key):
            self._current_sel_poly.increment_species(amount=-1)

        # NEXT ANND PREV COMMAND
        def _matches_hotkey(key, hotkeys):
            return any([re.match(hk,  key) is not None for hk in
                        ut.ensure_iterable(hotkeys)])

        if _matches_hotkey(event.key, PREV_IMAGE_HOTKEYS):
            self.prev_image(event)
        if _matches_hotkey(event.key, NEXT_IMAGE_HOTKEYS):
            self.next_image(event)
        self.draw()

    def on_motion(self, event):
        if ut.VERBOSE:
            print('[interact_annot] on_motion')
            print('[interact_annot] Got key: %r' % event.key)
        super(AnnotationInteraction, self).on_motion(event)
        ignore = (not self.showverts)
        # uses boolean punning for terseness
        lastX = self.mouseX or None
        lastY = self.mouseY or None
        # Allow for getting coordinates outside the axes
        ax = self.ax
        mousePos = [event.x, event.y]
        self.mouseX, self.mouseY = ax.transData.inverted().transform(mousePos)
        deltaX = lastX is not None and self.mouseX - lastX
        deltaY = lastY is not None and self.mouseY - lastY

        if ignore:
            return

        if self.is_down['left'] is True:
            self.canUncolor = True

        quick_resize = (self._polyHeld is True and (
            (event.button == self.MIDDLE_BUTTON) or
            (event.button == self.RIGHT_BUTTON) or
            (event.button == self.LEFT_BUTTON and event.key == 'ctrl')
        ))

        if self._polyHeld is True and self._ind is not None:
            # Resize by dragging corner
            self._current_sel_poly(self.mouseX, self.mouseY, self._ind,
                                   self.ax)
            self._current_sel_poly.anchor_idx = self._ind
        elif quick_resize:
            # Quick resize with special click
            anchor_idx = self._current_sel_poly.anchor_idx
            idx = (anchor_idx + 2) % 4
            self._current_sel_poly.resize(self.mouseX, self.mouseY, idx,
                                          self.ax)
        elif self._current_rotate_poly:
            cx, cy = points_center(self._current_rotate_poly.xy)
            theta = np.arctan2(cy - self.mouseY, cx - self.mouseX) - TAU / 4
            dtheta = theta - self._current_rotate_poly.theta
            self._current_rotate_poly.rotate(dtheta, self.ax)
        elif self._ind is None and event.button == self.LEFT_BUTTON:
            # move all vertices
            if (self._polyHeld is True and not (deltaX is None or deltaY is
                                                None)):
                self._current_sel_poly.translate(deltaX, deltaY, self.ax)
            self._ind = None
        else:
            return
        self.update_UI()

    def onpick(self, event):
        """ Makes selected polygon translucent """
        if self.debug > 0:
            print('[interact_annot] onpick')
        #x, y = event.mouseevent.xdata, event.mouseevent.xdata
        self._current_sel_poly = event.artist
        self._polyHeld = True

    def poly_changed(self, poly):
        """ this method is called whenever the polygon object is called """
        # only copy the artist props to the line (except visibility)
        vis = poly.lines.get_visible()
        vis = poly.handle.get_visible()
        poly.lines.set_visible(vis)
        poly.handle.set_visible(vis)


def pretty_hotkey_map(hotkeys):
    if hotkeys is None:
        return ''
    hotkeys = [hotkeys] if not isinstance(hotkeys, list) else hotkeys
    mapping = {
        #'right': 'right arrow',
        #'left':  'left arrow',
    }
    mapped_hotkeys = [mapping.get(hk, hk) for hk in hotkeys]
    hotkey_str = '(' + ut.conj_phrase(mapped_hotkeys, 'or') + ')'
    return hotkey_str


def _nxutils_points_inside_poly(points, verts):
    """ nxutils is depricated """
    path = mpl.path.Path(verts)
    return path.contains_points(points)


def verts_to_mask(shape, verts):
    h, w = shape[0:2]
    y, x = np.mgrid[:h, :w]
    points = np.transpose((x.ravel(), y.ravel()))
    #mask = nxutils.points_inside_poly(points, verts)
    mask = _nxutils_points_inside_poly(points, verts)
    return mask.reshape(h, w)


def apply_mask(img, mask):
    masked_img = img.copy()
    masked_img[~mask] = np.uint8(np.clip(masked_img[~mask] - 100., 0, 255))
    return masked_img


def points_center(pts):
    # the polygons have the first point listed twice in order for them to be
    # drawn as closed, but that point shouldn't be counted twice for computing
    # the center (hence the [:-1] slice)
    return np.array(pts[:-1]).mean(axis=0)


def polygon_dims(poly):
    xs = [x for (x, y) in poly.basecoords]
    ys = [y for (x, y) in poly.basecoords]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    return (w, h)


def rotate_points_around(points, theta, ax, ay):
    """
    References:
        http://www.euclideanspace.com/maths/geometry/affine/aroundPoint/matrix2d/
    """
    # TODO: Can use vtool for this
    sin, cos, array = np.sin, np.cos, np.array
    augpts = array([array((x, y, 1)) for (x, y) in points])
    ct = cos(theta)
    st = sin(theta)
    # correct matrix obtained from
    rot_mat = array(
        [(ct, -st, ax - ct * ax + st * ay),
         (st,  ct, ay - st * ax - ct * ay),
         ( 0,   0,                      1)]
    )
    return [(x, y) for (x, y, z) in rot_mat.dot(augpts.T).T]


def calc_display_coords(oldcoords, theta):
    return rotate_points_around(oldcoords, theta, *points_center(oldcoords))


def set_display_coords(poly):
    poly.xy = calc_display_coords(poly.basecoords, poly.theta)
    tag_pos = calc_tag_position(poly)
    poly.species_tag.set_position((tag_pos[0] + 5, tag_pos[1]))
    poly.metadata_tag.set_position((tag_pos[0] + 5, tag_pos[1] + 50))

def distance(x, y):
    return np.sqrt(x ** 2 + y ** 2)

def polarDelta(p1, p2):
    mag = distance(p2[0] - p1[0], p2[1] - p1[1])
    theta = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    return [mag, theta]

def apply_polarDelta(poldelt, cart):
    newx = cart[0] + (poldelt[0] * np.cos(poldelt[1]))
    newy = cart[1] + (poldelt[0] * np.sin(poldelt[1]))
    return (newx, newy)


def calc_tag_position(poly):
    r"""

    CommandLine:
        python -m plottool.interact_annotations --test-calc_tag_position --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from plottool.interact_annotations import *  # NOQA
        >>> poly = ut.DynStruct()
        >>> poly.basecoords = vt.verts_from_bbox([0, 0, 400, 400], True)
        >>> poly.theta = 0
        >>> poly.xy = vt.verts_from_bbox([0, 0, 400, 400], True)
        >>> tagpos = calc_tag_position(poly)
        >>> print('tagpos = %r' % (tagpos,))
    """
    points = [[
        max(list(zip(*poly.basecoords))[0]),
        min(list(zip(*poly.basecoords))[1])
    ]]
    tagpos = rotate_points_around(points, poly.theta, *points_center(poly.xy))[0]
    return tagpos


def is_within_distance_from_line(dist, pt, line):
    pt = np.array(pt)
    line = np.array(line)
    return vt.distance_to_lineseg(pt, line[0], line[1]) < dist


def calc_handle_display_coords(poly):
    cx, cy = points_center(poly.xy)
    w, h = polygon_dims(poly)
    x0, y0 = cx, (cy - (h / 2))  # start at top edge
    MIN_HANDLE_LENGTH = 25
    HANDLE_LENGTH = max(MIN_HANDLE_LENGTH, (h / 4))
    x1, y1 = (x0, y0 - HANDLE_LENGTH)
    pts = [(x0, y0), (x1, y1)]
    pts = rotate_points_around(pts, poly.theta, cx, cy)
    return pts


def meets_minimum_width_and_height(coords):
    """
    Depends on hardcoded indices, which is inelegant, but
    we're already depending on those for the FUDGE_FACTORS
    array above
    0----1
    |    |
    3----2
    """
    MIN_W = 5
    MIN_H = 5
    # the seperate 1 and 2 variables are not strictly necessary, but
    # provide a sanity check to ensure that we're dealing with the
    # right shape
    #w, h = vt.get_pointset_extent_wh(np.array(coords))
    w1 = coords[1][0] - coords[0][0]
    w2 = coords[2][0] - coords[3][0]
    h1 = coords[3][1] - coords[0][1]
    h2 = coords[2][1] - coords[1][1]
    assert np.isclose(w1, w2), ('w1: %r, w2: %r' % (w1, w2))
    assert np.isclose(h1, h2), ('h1: %r, h2: %r' % (h1, h2))
    w, h = w1, h1
    #print('w, h = (%r, %r)' % (w1, h1))
    return (MIN_W < w) and (MIN_H < h)


def default_vertices(img, polys=None, mouseX=None, mouseY=None):
    """Default to rectangle that has a quarter-width/height border."""
    (h, w) = img.shape[0:2]
    # Center the new verts around wherever the mouse is
    if mouseX is not None and mouseY is not None:
        center_x = mouseX
        center_h = mouseY
    else:
        center_x = w // 2
        center_h = h // 2

    if polys is not None and len(polys) > 0:
        # Use the largest polygon size as the default verts
        wh_list = np.array([vt.bbox_from_verts(poly.xy)[2:4]
                            for poly in six.itervalues(polys)])
        w_, h_ = wh_list.max(axis=0) // 2
    else:
        # If no poly exists use 1/4 of the image size
        w_, h_ = (w // 4, h // 4)
    # Get the x/y extents by offseting the centers
    x1, x2 = np.array([center_x, center_x]) + (w_ * np.array([-1, 1]))
    y1, y2 = np.array([center_h, center_h]) + (h_ * np.array([-1, 1]))
    # Clip to bounds
    x1 = max(x1, 1)
    y1 = max(y1, 1)
    x2 = min(x2, w - 1)
    y2 = min(y2, h - 1)
    return ((x1, y1), (x1, y2), (x2, y2), (x2, y1))


def check_valid_coords(ax, coords_list):
    return all([check_dims(ax, xy_pt) for xy_pt in coords_list])


def check_dims(ax, xy_pt, margin=0.5):
    """
    checks if bounding box dims are ok

    Allow the bounding box to go off the image
    so orientations can be done correctly
    """
    num_out = 0
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    if xy_pt[0] < xlim[0] + margin:
        num_out += 1
    if xy_pt[0] > xlim[1] - margin:
        num_out += 1
    if xy_pt[1] < ylim[1] + margin:
        num_out += 1
    if xy_pt[1] > ylim[0] - margin:
        num_out += 1
    return num_out <= 3


def enforce_dims(ax, xy_pt, margin=0.5):
    """
    ONLY USE THIS ON UNROTATED RECTANGLES, as to do otherwise may yield
    arbitrary polygons
    """
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    if xy_pt[0] < xlim[0] + margin:
        xy_pt[0] = xlim[0] + margin
    if xy_pt[0] > xlim[1] - margin:
        xy_pt[0] = xlim[1] - margin
    if xy_pt[1] < ylim[1] + margin:
        xy_pt[1] = ylim[1] + margin
    if xy_pt[1] > ylim[0] - margin:
        xy_pt[1] = ylim[0] - margin
    return True


def test_interact_annots():
    r"""
    CommandLine:
        python -m plottool.interact_annotations --test-test_interact_annots --show

    Example:
        >>> # ENABLE_DOCTEST
        >>> from plottool.interact_annotations import *  # NOQA
        >>> import plottool as pt
        >>> # build test data
        >>> # execute function
        >>> self = test_interact_annots()
        >>> # verify results
        >>> print(self)
        >>> pt.show_if_requested()
    """
    print('[interact_annot] *** START DEMO ***')
    verts_list = [
        ((0, 400), (400, 400), (400, 0), (0, 0), (0, 400)),
        ((400, 700), (700, 700), (700, 400), (400, 400), (400, 700))
    ]
    #if img is None:
    try:
        img_url = 'http://i.imgur.com/Vq9CLok.jpg'
        img_fpath = ut.grab_file_url(img_url)
        img = vt.imread(img_fpath)
    except Exception as ex:
        print('[interact_annot] cant read zebra: %r' % ex)
        img = np.random.uniform(0, 255, size=(100, 100))
    valid_species = ['species1', 'species2']
    metadata_list = [{'name': 'foo'}, None]
    self = AnnotationInteraction(img, verts_list=verts_list,
                                 valid_species=valid_species,
                                 metadata_list=metadata_list,
                                 fnum=0)  # NOQA
    return self


if __name__ == '__main__':
    """
    CommandLine:
        python -m plottool.interact_annotations --exec-test_interact_annots --show
    CommandLine:
        python -m plottool.interact_annotations
        python -m plottool.interact_annotations --allexamples
        python -m plottool.interact_annotations --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
