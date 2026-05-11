import tkinter as tk
import tkinter.font as tkFont
import pandas as pd
import numpy as np

from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageTk
from typing import Optional
from skimage.color import label2rgb

from src.logs import  INFO, WARN, ERROR
from src.Client.imagerApp import ImagerApp
from src.Client.eventBus import CHANGED_CWD, FINISHED_ANALYSIS, SAVE_ANALYZED, SAVE_FINISHED
from src.Client.pyCOLONY.file_io import find_images, write_properties_to_file
from src.Client.pyCOLONY.image_processing import process1

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.figure as mfig

from matplotlib.text import Annotation
from matplotlib.image import AxesImage

#===========--- Helper classes for displaying analyzed image ---================
@dataclass
class AnalysisFigureRegion:
    rect: mpatches.Rectangle
    annotation: Annotation
    is_enabled: bool

    def set_visible(self, is_visible: bool) -> None:
        self.rect.set_visible(is_visible)
        self.annotation.set_visible(is_visible)
    
    def set_enabled(self, is_enabled: bool) -> None:
        self.is_enabled = is_enabled

@dataclass
class AnalysisFigure:
    figure: mfig.Figure
    currently_displaying_original: bool
    figure_original_image: AxesImage
    figure_labeled_image: AxesImage
    figure_regions: dict[int, AnalysisFigureRegion]

    def swap(self) -> None:
        self.currently_displaying_original = not self.currently_displaying_original
        self.figure_original_image.set_visible(self.currently_displaying_original)
        self.figure_labeled_image.set_visible(not self.currently_displaying_original)
        self.redraw()

    def set_background(self, original: bool= True) -> None:
        if original:
            self.currently_displaying_original = True
            self.figure_original_image.set_visible(True)
            self.figure_labeled_image.set_visible(False)
        else:
            self.currently_displaying_original = False
            self.figure_original_image.set_visible(False) 
            self.figure_labeled_image.set_visible(True)

    def redraw(self) -> None:
        self.figure.canvas.draw_idle()

    def set_all_regions_visible(self, are_visible: bool) -> None:
        for region in self.figure_regions.values():
            region.set_visible(are_visible)

    def set_all_enabled_regions_visible(self, are_visible: bool) -> None:
        for region in self.figure_regions.values():
            region.set_visible(region.is_enabled and are_visible)

@dataclass
class AnalysisData:
    marked_finished: bool
    region_properties: pd.DataFrame
    analysis_figure: AnalysisFigure

    def mark_finished(self, mark: bool) -> None:
        self.marked_finished = mark

#===============================================================================

"""
Class describes the behaviour of the pyCOLONY pane
"""
class PyCOLONYView:
    def __init__(self, app: ImagerApp, frame: tk.Frame) -> None:
        self.app = app
        self.frame = frame
        self.id = self.app.event_bus.getId()

        self.app.event_bus.register(CHANGED_CWD, self.id, lambda path:\
                                    self.app.task_frontend(self.__setup_ui))
        
        self.app.event_bus.register(FINISHED_ANALYSIS, self.id, lambda path:\
                                    self.app.task_frontend(lambda: self.__on_finished_analysis(path)))
        
        self.app.event_bus.register(SAVE_ANALYZED, self.id, lambda path: \
                                    self.app.task_backend(lambda: self.__save_analyzed(path)))
        
        self.app.event_bus.register(SAVE_FINISHED, self.id, lambda path: \
                            self.app.task_backend(lambda: self.__save_analyzed(path, True)))

        self.__setup_ui()

    def log(self, type: str, msg: str) -> None:
        """
        Log under pyCOLONY name
        """
        self.app.log(type, msg, "pyCOLONY")

    def __clear_view(self) -> None:
        """
        Clear entire element of data
        """
        for widget in self.frame.winfo_children():
            widget.destroy()

        self.loaded_images: list[Path] = []
        self.thumbnails: dict[Path, tk.Frame] = {}
        self.analysis_cache: dict[Path, AnalysisData] = {}

        self.current_selected: Optional[Path] = None

    def __setup_no_CWD(self) -> None:
        """
        Setup if no CWD is available
        """
        choose_dir_label = tk.Label(self.frame, text="No directory selected.")
        choose_dir_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def __setup_CWD(self) -> None:
        """
        Setup if a CWD is available
        """
        if self.app.state.CWD is not None:
            self.loaded_images = sorted(set(find_images(self.app.state.CWD)))

        # Setup up top image scroll bar
        self.bar_frame = tk.Frame(self.frame)
        self.bar_frame.pack(fill=tk.X, padx=5, pady=5)

        self.canvas = tk.Canvas(self.bar_frame, height=130, highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.X)

        h_scroll = tk.Scrollbar(self.bar_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(xscrollcommand=h_scroll.set)

        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.__gallery_make_scrollable(self.inner_frame)
        self.__gallery_make_scrollable(self.canvas)
        self.__gallery_make_scrollable(h_scroll)

        # Working image frame
        self.large_frame = tk.Frame(self.frame)
        self.large_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        large_image_label = tk.Label(self.large_frame, text="Click on an image.", bg="lightgray")
        large_image_label.pack(fill=tk.BOTH, expand=True)
        
        # Working image controls frame
        self.working_frame = tk.Frame(self.frame)
        self.working_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=10, ipadx=10, ipady=10)

        # analysis buttons
        analyze_button = tk.Button(self.working_frame, text="Analyze", state=tk.DISABLED)
        analyze_button.pack(pady=5)

        for path in self.loaded_images:
            self.__insert_thumbnail(path)

    def __gallery_make_scrollable(self, tkwidget) -> None:
        """Helper function for scrolling bindings """
        tkwidget.bind("<MouseWheel>", lambda e: self.canvas.xview_scroll(int(-1*(e.delta/120)), "units"))
        tkwidget.bind("<Button-4>", lambda e:  self.canvas.xview_scroll(-1, "units"))
        tkwidget.bind("<Button-5>", lambda e:  self.canvas.xview_scroll(1, "units"))

    def __insert_thumbnail(self, path: Path) -> None:
        """
        Adds a frame to the gallery, displays filename and a thumbnail
        """
        container = tk.Frame(self.inner_frame, padx=5, pady=5)
        container.pack(side=tk.LEFT, padx=5, pady=5)

        with Image.open(path) as img:
            img.thumbnail((120, 90), Image.Resampling.LANCZOS)
            thumbnail = ImageTk.PhotoImage(img)
            img_label = tk.Label(container, image=thumbnail, cursor="hand2")
            img_label.image = thumbnail # anti-garbage collection # type: ignore

        img_label.pack()

        img_label.bind("<Button-1>", lambda e: self.__select_image_from_gallery(path))

        name_label = tk.Label(container, text=path.stem)
        name_label.pack()

        self.__gallery_make_scrollable(img_label)
        self.__gallery_make_scrollable(name_label)
        self.__gallery_make_scrollable(container)

        self.thumbnails[path] = container

    def __select_image_from_gallery(self, path: Path, force: bool = False) -> None:
        """
        Places an image from the gallery in the large image display, loads analysis data if available
        """
        if not force and (path == self.current_selected):
            return
        
        # Clear large image from frame
        for widget in self.large_frame.winfo_children():
            widget.destroy()

        if path in self.analysis_cache.keys():
            # Setting up plot in large_frame
            fig = self.analysis_cache[path].analysis_figure.figure
            plot = FigureCanvasTkAgg(fig, self.large_frame)
            widget = plot.get_tk_widget()
            fig.patch.set_facecolor(color="lightgray")
            fig.set_layout_engine('constrained')
            widget.place(x=0, y=0, anchor="nw", relwidth=1, relheight=1)
        else:
            # Setting up image in large_frame
            with Image.open(path) as img:
                frame_width = self.large_frame.winfo_width()
                frame_height = self.large_frame.winfo_height()
                img.thumbnail((frame_width*.97, frame_height*.97), Image.Resampling.LANCZOS)
                large_image = ImageTk.PhotoImage(img)
                large_image_label = tk.Label(self.large_frame, image=large_image, bg="lightgray")
                large_image_label.image = large_image # else image gets garbage collected # type: ignore
                large_image_label.pack(fill=tk.BOTH, expand=True)

        # Un-highlighting image in gallery
        if not self.current_selected is None:
            current_selected_thumbnail = self.thumbnails[self.current_selected]
            current_selected_thumbnail.config(bg=current_selected_thumbnail.master.cget("bg"))

        self.current_selected = path
        self.thumbnails[path].config(bg="pink")
  
        self.log(INFO, f"Showing {path.stem}")

        self.__setup_working_controls(path)
        
    def __setup_region_checklist(self, frame: tk.Frame, path: Path):
        # Container for canvas + scrollbar
        container = tk.Frame(frame, width=100)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0, width=100)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Window
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configure canvas scrolling
        canvas.bind("<Configure>", lambda e, cf=canvas_frame: canvas.itemconfig(cf, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)  

        def __make_scrollable(tkwidget) -> None:
            tkwidget.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
            tkwidget.bind("<Button-4>", lambda e:  canvas.yview_scroll(-1, "units"))
            tkwidget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        __make_scrollable(scrollable_frame)

        for label, region in self.analysis_cache[path].analysis_figure.figure_regions.items():
            var = tk.IntVar(value=1 if region.is_enabled else 0)

            # Default arguments for closure
            def on_check(v=var, r=region, p=path):
                r.set_enabled(bool(v.get()))    # Hides from data
                r.set_visible(bool(v.get()))    # Hides on plot
                self.analysis_cache[p].analysis_figure.redraw()

            cb = tk.Checkbutton(
                scrollable_frame,
                text=str(label),
                variable=var,
                command=on_check
            )
            cb.pack(anchor="w", pady=1)
            __make_scrollable(cb)

    def __setup_working_controls(self, path: Path) -> None:
        """
        Loads required controls for given image
        """
        for widget in self.working_frame.winfo_children():
            widget.destroy()

        if path in self.analysis_cache.keys():
            analysis_data = self.analysis_cache[path]
            analysis_data.analysis_figure.set_all_enabled_regions_visible(True)
            analysis_data.analysis_figure.redraw()

            # Swap button
            swap_button = tk.Button(self.working_frame, text="Swap Background", command=analysis_data.analysis_figure.swap)
            swap_button.pack(pady=5)

            # Hide regions button
            hide_regions_button = tk.Button(self.working_frame, text="Hide Regions")

            def toggle_regions():
                if hide_regions_button.cget("text") == "Hide Regions":
                    hide_regions_button.config(text="Show Regions", command=toggle_regions)
                    analysis_data.analysis_figure.set_all_enabled_regions_visible(False)
                else:
                    hide_regions_button.config(text="Hide Regions", command=toggle_regions)
                    analysis_data.analysis_figure.set_all_enabled_regions_visible(True)
                analysis_data.analysis_figure.redraw()

            hide_regions_button.config(command=toggle_regions)
            hide_regions_button.pack(pady=5)

            # List of checkboxes for each label
            scroll_frame = tk.Frame(self.working_frame)
            self.__setup_region_checklist(scroll_frame, path)
            scroll_frame.pack(pady=5, fill=tk.BOTH, expand=True)

            # Mark as finished button
            swap_button = tk.Button(self.working_frame, text="Unmark" if analysis_data.marked_finished else "Mark Finished")

            def mark_finished():
                label = self.thumbnails[path].winfo_children()[-1] # get name label from thumbnail
                f = tkFont.Font(label, label.cget("font"))

                if swap_button.cget("text") == "Mark Finished":
                    swap_button.config(text="Unmark")
                    analysis_data.mark_finished(True)
                    f.configure(underline = True)
                else:
                    swap_button.config(text="Mark Finished")
                    analysis_data.mark_finished(False)
                    f.configure(underline = False)
                
                label.config(font=f) # type: ignore

            swap_button.config(command=mark_finished)
            swap_button.pack(pady=5)

        else:
            # Analysis buttons
            analyze_button = tk.Button(self.working_frame, text="Analyze")

            def on_analyze():
                analyze_button.config(state="disabled")
                self.app.task_backend(lambda: self.__analyze_image(path))
  
            analyze_button.config(command=on_analyze)
            analyze_button.pack(pady=5)

    def __on_finished_analysis(self, path: Path) -> None:
        """
        When an analysis finishes, layout should change if currently selected
        """
        self.log(INFO, f"Finished analysis for {path}")
        if self.current_selected == path:
            self.__select_image_from_gallery(path, True)

    def __create_fig(self, original: np.ndarray, region_properties: list, colony_labels: np.ndarray) -> AnalysisFigure:
        """
        Creates a labaled plot for display purposes;
        """
        image_label_overlay = label2rgb(colony_labels, image=original, bg_label=0)

        analysis_figure_regions = {}

        fig, ax = plt.subplots()
        fig.patch.set_alpha(1)
        axim_overlay = ax.imshow(image_label_overlay)
        axim_original = ax.imshow(original)
        axim_original.set_visible(False)

        for region in region_properties:
            minr, minc, maxr, maxc = region.bbox
            rect = mpatches.Rectangle(
                (minc, minr),
                maxc - minc,
                maxr - minr,
                fill=False,
                edgecolor="pink",  # change to pink :)
                linewidth=1.5,
            )
            ax.add_patch(rect)
            ann = ax.annotate(str(region.label), (0.8,0.8), xycoords=rect, annotation_clip=True, 
                        color="black", backgroundcolor="yellow",
                        fontsize=6)
            
            analysis_figure_regions[region.label] = AnalysisFigureRegion(rect, ann, True)
            
        ax.set_axis_off()

        return AnalysisFigure(fig, False, axim_original, axim_overlay, analysis_figure_regions)

    def __analyze_image(self, path: Path) -> None:
        """
        Performs pyCOLONY analysis on image, stores in cache
        """
        if path in self.analysis_cache.keys():
            return
        
        self.log(INFO, f"Starting analysis for {path}")
        props, aux = process1(path)

        def process_plot():
            analysis_figure = self.__create_fig(aux["original"], aux["region_properties"], aux["colony_labels"])

            self.analysis_cache[path] = AnalysisData(False, props, analysis_figure)

            self.app.emit(FINISHED_ANALYSIS, path=path)

        self.app.task_frontend(process_plot)

    def __save_analyzed(self, path: Path, only_finished: bool = False) -> None:
        properties_list = []
        save_opts = {
            "bbox_inches": "tight",
            "transparent": True
        }

        for img_path, data in self.analysis_cache.items():
            if only_finished and not data.marked_finished:
                continue
            
            save_path = path / img_path.stem
            save_path.mkdir()

            # Filter out only regions that were enabled
            properties = data.region_properties
            filtered_df = properties[properties["label"]
                                     .map(lambda label: data.analysis_figure.figure_regions[label].is_enabled) # type: ignore
                                     ]
            properties_list.append(filtered_df)

            data.analysis_figure.set_all_regions_visible(False)
            data.analysis_figure.set_background(original=False)
            data.analysis_figure.figure.savefig(save_path / f"regions.png", **save_opts)

            data.analysis_figure.set_all_enabled_regions_visible(True)
            data.analysis_figure.figure.savefig(save_path / f"enabledLabels.png", **save_opts)
            data.analysis_figure.set_background(original=True)
            data.analysis_figure.figure.savefig(save_path / f"enabledLabelsOriginal.png", **save_opts)     

            data.analysis_figure.set_background(original=False)
            data.analysis_figure.set_all_regions_visible(True)
            data.analysis_figure.figure.savefig(save_path / f"allLabels.png", **save_opts)
            data.analysis_figure.set_background(original=True)
            data.analysis_figure.figure.savefig(save_path / f"allLabelsOriginal.png", **save_opts)     

        write_properties_to_file(properties_list, path/"results.tsv")
        self.app.log(INFO, f"pyCOLONY results have been saved to {path}")

    def __setup_ui(self):
        self.log(INFO, "Setting pyCOLONY pane UI")
        self.__clear_view()
        if self.app.state.CWD is None:
            self.log(INFO, "No CWD available, starting...")
            self.__setup_no_CWD()
        else:
            self.log(INFO, f"Selected {self.app.state.CWD} as CWD, starting...")
            self.__setup_CWD()
