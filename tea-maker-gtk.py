#!/usr/bin/python3

from shutil import copyfile, rmtree, move
# from subprocess import Popen, PIPE
from apt.progress.base import AcquireProgress
from gi.repository import Gtk, GLib, GObject
import threading
import apt
import apt_pkg
import os
import tarfile
from datetime import datetime

ui_file = 'tea-maker.ui'


class TeaMaker:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(ui_file)

        self.main_window = self.builder.get_object('main_window')
        self.main_window.connect('delete-event', Gtk.main_quit)
        self.main_window.set_title("Tea Package Maker v2")
        self.main_window.show()

        self.package_entry = self.builder.get_object('package_entry')

        self.ok = self.builder.get_object('ok')
        self.ok.connect('clicked', self.on_ok_clicked)

        self.info = self.builder.get_object('about')
        self.info.connect('clicked', self.on_info_clicked)

        self.help = self.builder.get_object('help')
        self.help.connect('clicked', self.on_help_clicked)

        self.about_dialog = self.builder.get_object('about_dialog')

        self.message_dialog = None
        self.confirm_dialog = None
        self.confirm_detail = None
        self.confirm_list = None
        self.confirm_summary = None
        self.confirm_treeview = Gtk.TreeView()
        self.scrolled_window = self.builder.get_object('scrolledwindow')

        self.file_chooser = self.builder.get_object('file_chooser')
        self.file_chooser.set_current_folder('/usr/share/TEA/profiles/')
        self.progress_window = Gtk.Window()
        self.progress_window.set_modal(True)
        self.progress_window.set_transient_for(self.main_window)

        self.check_pulse = True
        # ====
        self.vbox = Gtk.VBox(spacing=6)
        self.vbox.set_margin_bottom(18)
        self.vbox.set_margin_top(18)
        self.vbox.set_margin_left(18)
        self.vbox.set_margin_right(18)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_pulse_step(0.1)
        self.vbox.pack_start(self.progress_bar, True, True, 0)

        self.label = Gtk.Label()
        self.label.set_text('Downloading...')
        self.label.set_halign(Gtk.Align.START)
        self.vbox.pack_start(self.label, True, True, 0)

        self.progress_window.add(self.vbox)

        self.progress_window.connect('delete-event', self.hide_progress_window)

    def on_confirmation_destroy(self, *args):
        # self.confirm_dialog.hide()
        try:
            self.scrolled_window.remove(self.scrolled_window.get_children()[0])
        except IndexError:
            pass
        return True

    def on_ok_clicked(self, *args):
        pkg_name = self.package_entry.get_text()
        if pkg_name == '':
            self.show_message('Empty package name', 'Enter valid package(s) name')
        elif self.file_chooser.get_filename() is None:
            self.show_message('Empty Status File', 'Choose a status file')
        else:
            status_file = self.file_chooser.get_filename()
            apt_pkg.config.set("Dir:State::status", status_file)
            cache = apt.Cache()
            try:
                cache[pkg_name].mark_install()
                confirm_list = Gtk.ListStore(str, str)
                download_size = 0
                download_items = 0
                for package in cache.get_changes():
                    if os.path.exists('/var/cache/apt/archives/' + package.candidate.filename.split('/')[-1]):
                        downloaded = "Yes"
                    else:
                        downloaded = "No"
                        download_size += package.candidate.size
                        download_items += 1
                    confirm_list.append([package.fullname, downloaded])

                confirm_treeview = Gtk.TreeView()
                confirm_treeview.set_model(confirm_list)
                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn("Package", renderer, text=0)
                column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                column.set_resizable(True)
                column.set_min_width(300)
                confirm_treeview.append_column(column)

                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn("Cache", renderer, text=1)
                column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                column.set_resizable(True)
                column.set_min_width(50)
                confirm_treeview.append_column(column)

                # self.scrolled_window.add(confirm_treeview)

                if download_items > 0:
                    summary = str(download_items) + " File(s) not available in APT cache\n" + \
                              "Need to download " + apt_pkg.size_to_str(download_size) + "B"
                else:
                    summary = "All files Available in APT Cache\nNo need to download packages"

                # self.confirm_summary = self.builder.get_object('confirm_summary')
                # self.confirm_summary.set_text(summary)

                confirm_dialog = Gtk.Window()
                box = Gtk.Box()
                box.set_orientation(Gtk.Orientation.VERTICAL)
                scroll = Gtk.ScrolledWindow()
                scroll.add(confirm_treeview)
                box.add(scroll)
                label = Gtk.Label()
                label.set_text(summary)
                box.add(label)
                box2 = Gtk.Box()
                box2.set_orientation(Gtk.Orientation.HORIZONTAL)
                ok = Gtk.Button()
                ok.set_label('ok')
                ca=Gtk.Button()
                ca.set_label('cancl')
                def oke(*args):
                    self.on_confirmation_confirmed(confirm_dialog)
                def cancel(*args):
                    confirm_dialog.hide()
                    return False
                ok.connect("clicked", oke)
                ca.connect('clicked', cancel)
                box2.add(ok)
                box2.add(ca)
                box.add(box2)
                confirm_dialog.add(box)
                confirm_dialog.show_all()

                # self.confirm_dialog = self.builder.get_object('confirm_dialog')
                # self.confirm_dialog.show_all()
                # self.confirm_dialog.connect('delete-event', self.on_confirmation_destroy)
                #
                # self.confirm_cancel_button = self.builder.get_object('confirm_cancel')
                # self.confirm_cancel_button.connect('clicked', self.on_confirmation_destroy)
                # self.confirm_ok_button = self.builder.get_object('confirm_ok')
                # self.confirm_ok_button.connect('clicked', self.on_confirmation_confirmed)
            except KeyError:
                self.show_message('Package(s) not found', 'We can\'t find the package\nor it was already installed')

    def show_message(self, primary, secondary):
        self.message_dialog = Gtk.MessageDialog(None,
                                                Gtk.DialogFlags.MODAL,
                                                Gtk.MessageType.INFO,
                                                Gtk.ButtonsType.OK, primary)

        self.message_dialog.format_secondary_text(secondary)
        self.message_dialog.run()
        self.message_dialog.destroy()

    @staticmethod
    def on_info_clicked(*args):
        about = Gtk.AboutDialog()
        about.set_program_name('Tea Maker')
        about.set_logo_icon_name('teamaker')
        about.set_version('1.0')
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_authors(['Nurul Irfan'])
        about.run()
        about.destroy()

    def on_help_clicked(self, *args):
        help = Gtk.Dialog('FAQ', self.main_window, 0, (Gtk.STOCK_OK, Gtk.ResponseType.OK))
        content = help.get_content_area()
        label = Gtk.Label()
        label.set_markup('<b>Hello</b> <i>world</i>')
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(200)
        scroll.add(label)
        content.add(scroll)
        help.show_all()
        help.run()
        help.destroy()

    def on_info_destroy(self):
        self.about_dialog.hide()
        return True

    def on_confirmation_confirmed(self, conf, *args):
        # self.progress_window.show_all()
        progress_window = Gtk.Window()
        vbox = Gtk.VBox(spacing=6)
        vbox.set_margin_bottom(18)
        vbox.set_margin_top(18)
        vbox.set_margin_left(18)
        vbox.set_margin_right(18)

        progress_bar = Gtk.ProgressBar()
        progress_bar.set_show_text(True)
        progress_bar.set_fraction(0)
        progress_bar.set_pulse_step(0.1)
        vbox.pack_start(progress_bar, True, True, 0)

        label_ = Gtk.Label()
        label_.set_text('Downloading...')
        label_.set_halign(Gtk.Align.START)
        vbox.pack_start(label_, True, True, 0)

        progress_window.add(vbox)
        progress_window.show_all()
        def hide_progress():
            progress_window.hide()

        if os.path.exists('/tmp/tea/'):
            rmtree('/tmp/tea/')

        copyfile(self.file_chooser.get_filename(), '/tmp/' + str(self.file_chooser.get_filename()).split('/')[-1])
        apt_pkg.config.set("Dir::State::status", '/tmp/' + str(self.file_chooser.get_filename().split('/')[-1]))
        cache = apt.Cache()
        cache[str(self.package_entry.get_text()).replace(' ', '')].mark_install()  # replace: for security reason
        changes = cache.get_changes()
        file_names = []
        if not os.path.exists('/tmp/tea/workspace/archives'):
            os.makedirs('/tmp/tea/workspace/archives')
        for package in changes:
            if not package.marked_delete:
                file_names.append(package.candidate.filename.split('/')[-1])
        package_error = []
        done = False

        def proceed():
            hide_progress()
            self.on_confirmation_destroy()
            conf.hide()
            for file in file_names:
                copyfile('/var/cache/apt/archives/' + file, '/tmp/tea/workspace/archives/' + file)
            # compress, add description
            tar_dest = '/tmp/tea/workspace/' + self.package_entry.get_text() + '_' + \
                       cache[self.package_entry.get_text()].candidate.version + '.tea'
            tar = tarfile.open(tar_dest, 'w:gz')
            o = open('/tmp/tea/workspace/archives/keterangan.txt', 'w', newline='\r\n')
            now = datetime.now()
            keterangan = 'this package contains ' + self.package_entry.get_text() + ' version ' + \
                         cache[self.package_entry.get_text()].candidate.version + ' and it\'s dependencies\n' + \
                         'created with status file: ' + \
                         str(self.file_chooser.get_filename().split('/')[-1]) + '\n' + \
                         'timestamp: ' + str(now.day) + '-' + str(now.month) + '-' + str(now.year) + \
                         ' ' + str(now.hour) + ':' + str(now.minute) + ':' + str(now.second)

            o.write(keterangan)
            o.close()
            o = open('/tmp/tea/workspace/archives/keterangan_tea.txt', 'w', newline='\r\n')
            keterangan = "# File tea #\nSatu file yang memuat file .deb beserta dependensinya."+\
                         "\n\nDibuat untuk aplikasi & profil :\n\n\t\""+ self.package_entry.get_text() +"\""+\
                         "\n\t(versi -"+cache[self.package_entry.get_text()].candidate.version+"-)\n\n"+\
                         str(self.file_chooser.get_filename().split('/')[-1])+"\n\nDibuat pada "+ str(now.day) + '-' + str(now.month) + '-' + str(now.year) + \
                         ' ' + str(now.hour) + ':' + str(now.minute) + ':' + str(now.second)
            o.write(keterangan)
            o.close()
            # self.progress_window.show_all()
            for item in os.listdir('/tmp/tea/workspace/archives/'):
                tar.add('/tmp/tea/workspace/archives/' + item, arcname=item)
                self.progress_bar.pulse()
            tar.close()
            save = Gtk.FileChooserDialog('Select a directory to save file',
                                         self.main_window,
                                         Gtk.FileChooserAction.SELECT_FOLDER,
                                         )
            save.add_button('Save', Gtk.ResponseType.ACCEPT)
            global user
            save.set_current_folder('/home/' + user)
            save.run()
            dest = save.get_filename() + '/'
            save.destroy()
            move(tar_dest, dest)
            self.progress_window.destroy()

        class Fetch(AcquireProgress):
            def __init__(self):
                AcquireProgress.__init__(self)
                # self.outer.progress_window.show_all()

            def pulse(self, owner):
                AcquireProgress.pulse(self, owner)
                # print(dir(owner.items[0]))
                # print(owner.items[0].destfile)
                print(self.current_bytes / self.total_bytes)
                GLib.idle_add(progress_bar.set_fraction, self.current_bytes / self.total_bytes)
                text = 'Downloading ' + apt_pkg.size_to_str(self.current_bytes) + 'B of ' + apt_pkg.size_to_str(
                    self.total_bytes) + 'B' + \
                    '\n' + apt_pkg.size_to_str(self.current_cps) + 'B/s ) '
                GLib.idle_add(label_.set_text, text)

            def stop(self):
                # label.set_text('Download Stopped')
                # report = 'Failed while downloading:\n'
                # for i in package_error:
                #     report += i+'\n'
                # label.set_text(report)
                global done
                if package_error:
                    done = False
                    print("done false")

                else:
                    GLib.idle_add(proceed)

                print("stopped")

            def fail(self, item):
                package_error.append(item.shortdesc)

            def __del__(self):
                print("fetch deleted")

        class Thread(threading.Thread):
            # http://stackoverflow.com/questions/2829329/catch-a-threads-exception-in-the-caller-thread-in-python
            def __init__(self, fetch_progress):
                threading.Thread.__init__(self)
                self.fetch_progress = fetch_progress

            def run(self):
                try:
                    cache.fetch_archives(self.fetch_progress)
                except apt.cache.FetchFailedException:
                    GLib.idle_add(hide_progress)
                    # event = threading.Event()
                    # GLib.idle_add(self.outer.show_message,
                    #               "Download Error",
                    #               "Couldn't download packages\nCheck your internet connection")
                    # event.wait()
                    def message():
                        message_dialog = Gtk.MessageDialog(None,
                                                    Gtk.DialogFlags.MODAL,
                                                    Gtk.MessageType.INFO,
                                                    Gtk.ButtonsType.OK, "Error")

                        message_dialog.format_secondary_text("Error 2")
                        message_dialog.run()
                        message_dialog.destroy()
                    # event = threading.Event()
                    GLib.idle_add(message)
                    # event.wait()

            def __del__(self):
                print("thread deleted")

        if cache.required_download != 0:
            progress = Fetch()
            apt_thread = Thread(progress)
            apt_thread.start()
        else:
            proceed()

    def hide_progress_window(self, *args):
        # try:
        #     self.progress_window.remove(self.progress_window.get_children()[0])
        # except IndexError:
        #     pass

        self.progress_window.hide()
        return True


if __name__ == "__main__":
    user = os.path.expanduser('~').split('/')[-1]
    GObject.threads_init()
    if os.getuid() is 0:
        TeaMaker()
        Gtk.main()
    else:
        print('must be root')
        warning = Gtk.MessageDialog(None,
                                    Gtk.DialogFlags.MODAL,
                                    Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK,
                                    'Only superuser can summon the program')
        warning.run()
        warning.destroy()
