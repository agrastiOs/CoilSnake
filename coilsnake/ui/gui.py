#! /usr/bin/env python
from functools import partial
from subprocess import Popen
from os.path import dirname, isdir, join
from threading import Thread
from time import time
from Tkinter import *
import tkFileDialog
import tkMessageBox
import ttk
import os

from PIL import ImageTk

from coilsnake import Project
from coilsnake.model.common.blocks import Rom
from coilsnake.ui import information, gui_util
from coilsnake.ui.common import decompile_rom, compile_project, upgrade_project, setup_logging
from coilsnake.ui.fun import get_fun_title
from coilsnake.ui.gui_preferences import CoilSnakePreferences
from coilsnake.ui.gui_util import browse_for_rom, browse_for_project, open_folder
from coilsnake.ui.information import coilsnake_about
from coilsnake.util.common.assets import asset_path



# Import CCScriptWriter from the submodule, if possible.

if isdir(join("tools", "CCScriptWriter")):
    sys.path.append(join("tools", "CCScriptWriter"))
    from CCScriptWriter import CCScriptWriter
else:
    CCScriptWriter = None


class CoilSnakeGui(object):
    def __init__(self):
        self.preferences = CoilSnakePreferences()
        self.preferences.load()
        self.buttons = []

    # Preferences functions

    def toggle_titles(self):
        self.preferences["title"] = not self.preferences["title"]
        self.preferences.save()

    def set_emulator_exe(self):
        emulator_exe = tkFileDialog.askopenfilename(
            parent=self.root,
            title="Select an Emulator Executable",
            initialfile=self.preferences["emulator"])
        if emulator_exe:
            self.preferences["emulator"] = emulator_exe
            self.preferences.save()

    # GUI update functions

    def clear_console(self):
        self.console.delete(1.0, END)
        self.console.see(END)

    def disable_all_buttons(self):
        for button in self.buttons:
            button["state"] = DISABLED

    def enable_all_buttons(self):
        for button in self.buttons:
            button["state"] = NORMAL

    # GUI popup functions

    def about_menu(self):
        about_menu = Toplevel(self.root)

        photo = ImageTk.PhotoImage(file=asset_path(["images", "logo.png"]))
        about_label = Label(about_menu, image=photo)
        about_label.photo = photo
        about_label.pack(side=LEFT, expand=1)

        about_right_frame = ttk.Frame(about_menu)
        Label(about_right_frame,
              text=coilsnake_about(),
              height=15,
              anchor="w",
              justify="left",
              bg="white",
              borderwidth=5,
              relief=GROOVE).pack(fill=BOTH, expand=1, side=TOP)
        Button(about_right_frame, text="Toggle Alternate Titles", command=self.toggle_titles).pack(fill=BOTH, expand=1)
        Button(about_right_frame, text="Close", command=about_menu.destroy).pack(fill=BOTH, expand=1)

        about_right_frame.pack(side=LEFT, fill=BOTH, expand=1)

        about_menu.resizable(False, False)
        about_menu.title("About CoilSnake {}".format(information.VERSION))

    def run_rom(self, entry):
        rom_filename = entry.get()
        if not self.preferences["emulator"]:
            tkMessageBox.showerror(parent=self.root,
                                   title="Error",
                                   message="""Emulator executable not specified.
Please specify it in the Preferences menu.""")
        elif rom_filename:
            Popen([self.preferences["emulator"], rom_filename])
    
    def edit_project(self, entry):
        project_path = entry.get()
        self.preferences["java"] = "/usr/bin/java"
        if not self.preferences["java"]:
            tkMessageBox.showerror(parent=self.root,
                                   title="Error",
                                   message="""Java executable not specified.
Please specify it in the Preferences menu.""")
        elif project_path:
            Popen([self.preferences["java"], "-jar", asset_path(["bin", "EbProjEdit.jar"]),
                   os.path.join(project_path, Project.PROJECT_FILENAME)])

    # Actions

    def do_decompile(self, rom_entry, project_entry):
        rom = rom_entry.get()
        project = project_entry.get()

        if rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_buttons()
            
            # Save the fields to preferences
            self.preferences["export_rom"] = rom
            self.preferences["export_proj"] = project
            self.preferences.save()

            self.progress_bar["value"] = 0
            thread = Thread(target=self._do_decompile_help,
                            args=(rom, project))
            thread.start()

    def _do_decompile_help(self, rom, project):
        try:
            decompile_rom(rom_filename=rom, project_path=project)
        except Exception as inst:
            # TODO
            pass

        self.progress_bar["value"] = 0
        self.enable_all_buttons()

    def do_compile(self, project_entry, base_rom_entry, rom_entry):
        base_rom = base_rom_entry.get()
        rom = rom_entry.get()
        project = project_entry.get()

        if base_rom and rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_buttons()

            # Save the fields to preferences
            self.preferences["import_proj"] = project
            self.preferences["import_baserom"] = base_rom
            self.preferences["import_rom"] = rom
            self.preferences.save()

            # Reset the progress bar
            self.progress_bar["value"] = 0

            thread = Thread(target=self._do_compile_help,
                            args=(project, base_rom, rom))
            thread.start()

    def _do_compile_help(self, project, base_rom, rom):
        try:
            compile_project(project, base_rom, rom)
        except Exception as inst:
            # TODO
            pass

        self.progress_bar["value"] = 0
        self.enable_all_buttons()

    def do_upgrade(self, rom_entry, project_entry):
        rom = rom_entry.get()
        project = project_entry.get()

        if rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_buttons()

            # Save the fields to preferences
            self.preferences["upgrade_rom"] = rom
            self.preferences["upgrade_proj"] = project
            self.preferences.save()

            self.progress_bar["value"] = 0
            self.progress_bar.step(10)
            thread = Thread(target=self._do_upgrade_help,
                            args=(rom_entry.get(), project_entry.get()))
            thread.start()

    def _do_upgrade_help(self, rom, project):
        try:
            upgrade_project(project_path=project, base_rom_filename=rom)
        except Exception as inst:
            pass
            # TODO

        self.progress_bar["value"] = 0
        self.enable_all_buttons()

    def extract_earthbound_dialogue(self):
        if not CCScriptWriter:
            tkMessageBox.showerror(
                "CCScriptWriter Not Installed",
                "You need to place CCScriptWriter.py in the tools/CCScriptWriter folder.",
                parent=self.root)
            return
        rom_filename = tkFileDialog.askopenfilename(
            parent=self.root, title="Select an EarthBound ROM from which to extract the dialogue text",
            filetypes=[('SNES ROMs', '*.smc'), ('SNES ROMs', '*.sfc'), ('All files', '*.*')])
        if not rom_filename:
            return
        rom = Rom()
        rom.from_file(rom_filename)
        if rom.type() != "Earthbound":
            tkMessageBox.showerror(
                "Invalid EarthBound ROM",
                "You have specified an invalid EarthBound ROM.",
                parent=self.root)
            return
        del rom
        project_filename = tkFileDialog.askopenfilename(
            parent=self.root, title="Select a CoilSnake project to modify",
            filetypes=[('CoilSnake Project', 'Project.snake')])
        if not project_filename:
            return
        project_ccscript_path = join(dirname(project_filename), "ccscript")
        thread = Thread(
            target=self._run_CCScriptWriter,
            args=(project_ccscript_path, rom_filename))
        thread.start()

    def _run_CCScriptWriter(self, project_dir, rom_name):
        start = time()
        rom_file = open(rom_name, "rb")
        try:
            ccsw = CCScriptWriter(rom_file, project_dir, False)
            ccsw.loadDialogue(True)
            ccsw.processDialogue()
            ccsw.outputDialogue(True)
        except Exception as inst:
            pass  # TODO
        else:
            print "Complete. Time: {:.2f}s".format(float(time() - start))
            tkMessageBox.showinfo(
                title="Dialogue Extraction Successful",
                message="Successfully extracted EarthBound dialogue.",
                parent=self.root)
        finally:
            rom_file.close()

    # GUI

    def main(self):
        self.create_gui()
        self.root.mainloop()

    def create_gui(self):
        self.root = Tk()
        if self.preferences["title"]:
            self.root.wm_title(get_fun_title() + " " + information.VERSION)
        else:
            self.root.wm_title("CoilSnake " + information.VERSION)

        self.create_menubar()

        notebook = ttk.Notebook(self.root)

        decompile_frame = self.create_decompile_frame(notebook)
        notebook.add(decompile_frame, text="Decompile")

        compile_frame = self.create_compile_frame(notebook)
        notebook.add(compile_frame, text="Compile")

        upgrade_frame = self.create_upgrade_frame(notebook)
        notebook.add(upgrade_frame, text="Upgrade")

        decompile_script_frame = self.create_decompile_script_frame(notebook)
        notebook.add(decompile_script_frame, text="Decompile Script")

        notebook.pack(fill=BOTH, expand=1)

        self.progress_bar = ttk.Progressbar(self.root, orient=HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=BOTH, expand=1)

        console_frame = Frame(self.root)
        scrollbar = Scrollbar(console_frame)
        self.console = Text(console_frame, width=80, height=8)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.console.pack(fill=X)
        scrollbar.config(command=self.console.yview)
        self.console.config(yscrollcommand=scrollbar.set)
        console_frame.pack(fill=X, expand=1)

        class StdoutRedirector(object):
            def __init__(self, textarea):
                self.textarea = textarea

            def write(self, str):
                self.textarea.insert(END, str)
                self.textarea.see(END)

            def flush(self):
                pass

        self.console_stream = StdoutRedirector(self.console)
        sys.stdout = self.console_stream
        sys.stderr = self.console_stream

        setup_logging(quiet=False, verbose=False)

    def create_menubar(self):
        menubar = Menu(self.root)

        # Preferences pulldown menu
        prefMenu = Menu(menubar, tearoff=0)
        prefMenu.add_command(label="Emulator Executable",
                             command=self.set_emulator_exe)
        menubar.add_cascade(label="Preferences", menu=prefMenu)

        # Tools pulldown menu
        toolsMenu = Menu(menubar, tearoff=0)
        toolsMenu.add_command(label="Expand ROM to 32 MBit",
                              command=partial(gui_util.expand_rom, self.root))
        toolsMenu.add_command(label="Expand ROM to 48 MBit",
                              command=partial(gui_util.expand_rom_ex, self.root))
        toolsMenu.add_command(label="Add Header to ROM",
                              command=partial(gui_util.add_header_to_rom, self.root))
        toolsMenu.add_command(label="Remove Header from ROM",
                              command=partial(gui_util.strip_header_from_rom, self.root))
        toolsMenu.add_command(label="Extract EarthBound Dialogue to Project",
                              command=self.extract_earthbound_dialogue)
        menubar.add_cascade(label="Tools", menu=toolsMenu)

        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.about_menu)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def create_decompile_frame(self, notebook):
        decompile_frame = ttk.Frame(notebook)
        self.add_title_fields_to_frame(text="Decompile a ROM to create a new project.", frame=decompile_frame)

        input_rom_entry = self.add_rom_fields_to_frame(name="ROM", frame=decompile_frame)
        project_entry = self.add_project_fields_to_frame(name="Output Directory", frame=decompile_frame)

        def decompile_tmp():
            self.do_decompile(input_rom_entry, project_entry)

        decompile_button = Button(decompile_frame, text="Decompile", command=decompile_tmp)
        decompile_button.pack(fill=BOTH, expand=1)
        self.buttons.append(decompile_button)

        return decompile_frame

    def create_compile_frame(self, notebook):
        compile_frame = ttk.Frame(notebook)
        self.add_title_fields_to_frame(text="Compile a project to create a new ROM.", frame=compile_frame)

        base_rom_entry = self.add_rom_fields_to_frame(name="Base ROM", frame=compile_frame)
        project_entry = self.add_project_fields_to_frame(name="Project", frame=compile_frame)
        output_rom_entry = self.add_rom_fields_to_frame(name="Output ROM", frame=compile_frame)

        def compile_tmp():
            self.do_compile(project_entry, base_rom_entry, output_rom_entry)

        compile_button = Button(compile_frame, text="Compile", command=compile_tmp)
        compile_button.pack(fill=BOTH, expand=1)
        self.buttons.append(compile_button)

        return compile_frame

    def create_upgrade_frame(self, notebook):
        upgrade_frame = ttk.Frame(notebook)
        self.add_title_fields_to_frame(text="Upgrade a project created using an older version of CoilSnake.",
                                       frame=upgrade_frame)

        rom_entry = self.add_rom_fields_to_frame(name="Base ROM", frame=upgrade_frame)
        project_entry = self.add_project_fields_to_frame(name="Project", frame=upgrade_frame)

        def upgrade_tmp():
            self.do_upgrade(rom_entry, project_entry)

        self.upgrade_button = Button(upgrade_frame, text="Upgrade", command=upgrade_tmp)
        self.upgrade_button.pack(fill=BOTH, expand=1)
        self.buttons.append(self.upgrade_button)

        return upgrade_frame

    def create_decompile_script_frame(self, notebook):
        decompile_script_frame = ttk.Frame(notebook)
        self.add_title_fields_to_frame(text="Decompile a ROM's script to an already existing project.",
                                       frame=decompile_script_frame)

        input_rom_entry = self.add_rom_fields_to_frame(name="ROM", frame=decompile_script_frame)
        project_entry = self.add_project_fields_to_frame(name="Project", frame=decompile_script_frame)

        def decompile_script_tmp():
            self.do_decompile(input_rom_entry, project_entry)

        button = Button(decompile_script_frame, text="Decompile Script", command=decompile_script_tmp)
        button.pack(fill=BOTH, expand=1)
        self.buttons.append(button)

        return decompile_script_frame

    def add_title_fields_to_frame(self, text, frame):
        Label(frame, text=text, justify=CENTER, height=2).pack(fill=BOTH, expand=1)

    def add_rom_fields_to_frame(self, name, frame):
        rom_frame = ttk.Frame(frame)

        Label(rom_frame, text="{}:".format(name), width=13, justify=RIGHT).pack(side=LEFT, fill=BOTH, expand=1)
        rom_entry = Entry(rom_frame, width=30)
        rom_entry.pack(side=LEFT, fill=BOTH, expand=1)

        def browse_tmp():
            browse_for_rom(self.root, rom_entry)

        def run_tmp():
            self.run_rom(rom_entry)

        button = Button(rom_frame, text="Browse...", command=browse_tmp, width=6)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.buttons.append(button)

        button = Button(rom_frame, text="Run", command=run_tmp, width=5)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.buttons.append(button)

        button = Button(rom_frame, text="", width=5, state=DISABLED, takefocus=False, border=0)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        button.lower()

        rom_frame.pack()

        return rom_entry

    def add_project_fields_to_frame(self, name, frame):
        project_frame = ttk.Frame(frame)

        Label(project_frame, text="{}:".format(name), width=13, justify=RIGHT).pack(side=LEFT)
        project_entry = Entry(project_frame, width=30)
        project_entry.pack(side=LEFT, fill=BOTH, expand=1)

        def browse_tmp():
            browse_for_project(self.root, project_entry, save=True)

        def open_tmp():
            open_folder(project_entry)

        def edit_tmp():
            self.edit_project(project_entry)

        button = Button(project_frame, text="Browse...", command=browse_tmp, width=6)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.buttons.append(button)

        button = Button(project_frame, text="Open", command=open_tmp, width=5)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.buttons.append(button)

        button = Button(project_frame, text="Edit", command=edit_tmp, width=5)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.buttons.append(button)

        project_frame.pack()

        return project_entry



def main():
    gui = CoilSnakeGui()
    sys.exit(gui.main())