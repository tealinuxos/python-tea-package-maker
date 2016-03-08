#!/usr/bin/python3

from shutil import copyfile, rmtree, move
from apt.progress.base import AcquireProgress
from gi.repository import Gtk, GLib, GObject
import threading
import apt
import apt_pkg
import os
import tarfile
import gc
from datetime import datetime

ui_file = '/home/mnirfan/Project/python-tea-package/tea-maker.ui'


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
        self.info.connect('clicked', self.on_about_clicked)

        self.help = self.builder.get_object('help')
        self.help.connect('clicked', self.on_help_clicked)
        # self.about_dialog = self.builder.get_object('about_dialog')

        # self.message_dialog = None
        # self.confirm_dialog = None
        # self.confirm_detail = None
        # self.confirm_list = None
        # self.confirm_summary = None
        # self.confirm_treeview = Gtk.TreeView()
        # self.scrolled_window = self.builder.get_object('scrolledwindow')

        self.file_chooser = self.builder.get_object('file_chooser')
        self.file_chooser.set_current_folder('/usr/share/TEA/profiles/')

        self.start()

        self.progress_window = Gtk.Window()
        self.progress_window.set_size_request(400, 0)
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

        self.progress_cancel = Gtk.Button().new_from_stock(Gtk.STOCK_CANCEL)
        self.vbox.pack_end(self.progress_cancel, True, True, 0)

        self.progress_window.add(self.vbox)

        self.progress_window.connect('delete-event', self.hide_progress_window)

    def start(self):
        cache = apt.Cache()
        list = Gtk.ListStore(str)
        self.package_entry.set_sensitive(False)
        self.package_entry.set_text('Loading...')
        self.ok.set_sensitive(False)
        self.info.set_sensitive(False)
        self.help.set_sensitive(False)
        self.file_chooser.set_sensitive(False)
        i = 0
        for item in cache:
            i += 1
            list.append([item.name])
            self.package_entry.set_progress_fraction(i/len(cache))
            while Gtk.events_pending():
                Gtk.main_iteration()
        self.package_entry.set_text('')
        self.package_entry.set_progress_fraction(0)
        completion = Gtk.EntryCompletion(model=list)
        completion.set_text_column(0)
        completion.set_popup_single_match(True)
        self.package_entry.set_completion(completion)
        completion.connect('match-selected', self.on_match_selected)
        self.package_entry.set_sensitive(True)
        self.ok.set_sensitive(True)
        self.info.set_sensitive(True)
        self.help.set_sensitive(True)
        self.file_chooser.set_sensitive(True)

    # action when user select an item from auto completion
    def on_match_selected(self, completion, treemodel, treeiter):
        self.package_entry.set_text(treemodel[treeiter][completion.get_text_column()])

    def on_ok_clicked(self, *args):
        pkg_name = self.package_entry.get_text()
        if pkg_name == '':
            self.show_message('Empty package name', 'Enter a valid package name')
        elif self.file_chooser.get_filename() is None:
            self.show_message('Empty Status File', 'Choose a status file')
        else:
            status_file = self.file_chooser.get_filename()
            apt_pkg.config.set("Dir:State::status", status_file)
            cache = apt.Cache()
            try:
                if cache[pkg_name].is_installed:
                    self.show_message('Package already installed',
                                      pkg_name+' is already installed in your status file')
                else:
                    cache[pkg_name].mark_install()
                    confirm_list = Gtk.ListStore(str, str)
                    download_size = 0
                    download_items = 0
                    for package in cache.get_changes():
                        if os.path.exists('/var/cache/apt/archives/' + package.name + '_' + package.candidate.version.replace(':', '%3a') + '_' + package.candidate.architecture + '.deb'):
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
                    column.set_min_width(280)
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

                    confirm_dialog = Gtk.Window(title="Confirmation")
                    confirm_dialog.set_transient_for(self.main_window)
                    confirm_dialog.set_modal(self.main_window)
                    confirm_dialog.set_default_size(400, 300)
                    box = Gtk.Box(spacing=18,
                                  margin_top=18,
                                  margin_bottom=18,
                                  margin_left=18,
                                  margin_right=18)
                    box.set_orientation(Gtk.Orientation.VERTICAL)
                    scroll = Gtk.ScrolledWindow()
                    scroll.add(confirm_treeview)
                    box.pack_start(scroll, 1, 1, 0)
                    label = Gtk.Label()
                    label.set_halign(Gtk.Align.START)
                    label.set_text(summary)
                    box.pack_start(label, 1, 1, 0)
                    box2 = Gtk.Box()
                    box2.set_orientation(Gtk.Orientation.HORIZONTAL)
                    ok_btn = Gtk.Button().new_from_stock(Gtk.STOCK_OK)
                    ok_btn.can_focus = True
                    ok_btn.has_focus = True
                    cancel_btn=Gtk.Button().new_from_stock(Gtk.STOCK_CANCEL)

                    def oke(*args):
                        self.on_confirmation_confirmed(confirm_dialog)

                    def cancel(*args):
                        confirm_dialog.hide()
                        return False

                    ok_btn.connect("clicked", oke)
                    cancel_btn.connect('clicked', cancel)
                    box2.pack_end(ok_btn, False, 0, 6)
                    box2.pack_end(cancel_btn, False, 0, 0)
                    box.pack_start(box2, 0, 0, 0)
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
                self.show_message('Package(s) not found', 'We can\'t find the package\nCheck again the package\'s name')
        gc.collect()

    def show_message(self, primary, secondary):
        self.message_dialog = Gtk.MessageDialog(self.main_window,
                                                Gtk.DialogFlags.MODAL,
                                                Gtk.MessageType.INFO,
                                                Gtk.ButtonsType.CLOSE, primary)

        self.message_dialog.format_secondary_text(secondary)
        self.message_dialog.run()
        self.message_dialog.destroy()

    def on_about_clicked(self, *args):
        about = Gtk.AboutDialog('About Tea Package Maker', self.main_window)
        about.set_program_name('Tea Maker')
        about.set_logo_icon_name('teamaker')
        about.set_version('1.0')
        about.set_comments('Make single file package installer for your friend\'s or your own OS\n'
                           'Currently developed for TeaLinuxOS')
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_authors(['Nurul Irfan'])
        about.run()
        about.destroy()
        gc.collect()

    def on_help_clicked(self, *args):
        help = Gtk.Dialog('FAQ', self.main_window, 0, (Gtk.STOCK_OK, Gtk.ResponseType.OK))
        help.set_size_request(400, 400)
        help.set_default_size(500, 400)
        content = help.get_content_area()
        label = Gtk.Label(margin_top=18,
                          margin_bottom=18,
                          margin_left=18,
                          margin_right=18)
        label.set_markup('<b>What is "Status File?"</b>\n'
                         'Status file is a file that contains information about installed packages. '
                         'It can be found in <i>/var/lib/dpkg/status</i>')
        label.set_line_wrap_mode(Gtk.WrapMode.WORD)
        label.set_line_wrap(True)
        label.set_max_width_chars(-1)
        label.set_width_chars(-1)
        label.set_line_wrap_mode(Gtk.WrapMode.WORD)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        view = Gtk.Viewport()
        view.add(label)
        scroll.add(view)
        content.add(scroll)
        help.show_all()
        help.run()
        help.destroy()
        gc.collect()

    def on_confirmation_confirmed(self, conf, *args):
        # self.progress_window.show_all()
        conf.hide()
        progress_window = Gtk.Window(title='Downloading Packages')
        progress_window.set_transient_for(self.main_window)
        progress_window.set_modal(self.main_window)
        progress_window.set_deletable(False)
        progress_window.set_default_size(300, 0)
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

        progress_cancel = Gtk.Button().new_from_stock(Gtk.STOCK_CANCEL)
        vbox.pack_end(progress_cancel, True, True, 0)

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
                # parse ':' char to '%3a', some packages have this condition
                file_names.append(package.name + '_' + package.candidate.version.replace(':', '%3a') + '_' + package.candidate.architecture + '.deb')
        package_error = []
        done = False

        def hide_confirm():
            conf.hide()
            return False

        def proceed():
            hide_progress()
            # self.on_confirmation_destroy()
            hide_confirm()
            for file in file_names:
                copyfile('/var/cache/apt/archives/' + file.replace(':', '%3a'), '/tmp/tea/workspace/archives/' + file)
            # compress, add description
            tar_dest = '/tmp/tea/workspace/' + self.package_entry.get_text() + '_' + \
                       cache[self.package_entry.get_text()].candidate.version.replace(':', '-') + '.tea'
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
                         str(self.file_chooser.get_filename().split('/')[-1])+"\n\nDibuat pada "+\
                         str(now.day) + '-' + str(now.month) + '-' + str(now.year) + \
                         ' ' + str(now.hour) + ':' + str(now.minute) + ':' + str(now.second)
            o.write(keterangan)
            o.close()
            # self.progress_window.show_all()
            for item in os.listdir('/tmp/tea/workspace/archives/'):
                tar.add('/tmp/tea/workspace/archives/' + item, arcname=item)
                self.progress_bar.pulse()
            tar.close()
            # save = Gtk.FileChooserDialog('Select a directory to save file',
            #                              self.main_window,
            #                              Gtk.FileChooserAction.SAVE,
            #                              (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            #                               Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
            global user
            # save.set_current_folder('/home/' + user)
            # response = save.run()
            # if response == Gtk.ResponseType.ACCEPT:
            filename = tar_dest.split('/')[-1]
            num = 2
            if os.path.exists('/home/' + user + '/' + filename):
                while os.path.exists('/home/' + user + '/' + filename.split('.tea')[0] + '_('+str(num)+').tea'):
                    num += 1
                filename = filename.split('.tea')[0] + '_('+str(num)+').tea'
            move(tar_dest, '/home/' + user + '/' + filename)
            # save.destroy()
            self.show_message('Done', filename + ' has been saved to your home directory')

            self.progress_window.destroy()

            gc.collect()

        def proceed2():
            hide_confirm()
            hide_progress()
            save = Gtk.FileChooserDialog('Select a directory to save file',
                                         self.main_window,
                                         Gtk.FileChooserAction.SAVE,
                                         (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                          Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

            response = save.run()
            tar_dest = save.get_filename()
            if response == Gtk.ResponseType.OK:
                allow = False
                print(save.get_filename())
                if os.path.exists(tar_dest):
                    rewrite_ask = Gtk.Dialog("Confirm overwrite", self.main_window, 0,
                                             (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                              Gtk.STOCK_OK, Gtk.ResponseType.OK))
                    box = rewrite_ask.get_content_area()
                    overwrite_warning = Gtk.Label(label="The file \""+ tar_dest.split('/')[-1] +"\" exist. Do you want to overwrite it?")
                    box.add(overwrite_warning)

                    resp = rewrite_ask.run()
                    if resp == Gtk.ResponseType.OK:
                        allow = True
                    else:
                        pass
                    save.destroy()
                    rewrite_ask.destroy()
                else:
                    allow = True

                if allow:
                    GLib.idle_add(save.destroy)
                    self.progress_window.show_all()
                    tar = tarfile.open(tar_dest, 'w:gz')
                    i = 0
                    for file in file_names:
                        print(file)
                        i += 1
                        self.progress_bar.set_fraction(i/len(file_names))
                        self.label.set_text('processing ' + file)
                        self.label.set_ellipsize(3)

                        tar.add('/var/cache/apt/archives/' + file.replace(':', '%3a'), arcname=file)
                        while Gtk.events_pending():
                            Gtk.main_iteration()
                    self.hide_progress_window()
                    self.show_message('Done', None)
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
                    tar.add('/tmp/tea/workspace/archives/keterangan.txt', arcname='keterangan.txt')

                    o = open('/tmp/tea/workspace/archives/keterangan_tea.txt', 'w', newline='\r\n')
                    keterangan = "# File tea #\nSatu file yang memuat file .deb beserta dependensinya."+\
                                 "\n\nDibuat untuk aplikasi & profil :\n\n\t\""+ self.package_entry.get_text() +"\""+\
                                 "\n\t(versi -"+cache[self.package_entry.get_text()].candidate.version+"-)\n\n"+\
                                 str(self.file_chooser.get_filename().split('/')[-1])+"\n\nDibuat pada "+\
                                 str(now.day) + '-' + str(now.month) + '-' + str(now.year) + \
                                 ' ' + str(now.hour) + ':' + str(now.minute) + ':' + str(now.second)
                    o.write(keterangan)
                    o.close()
                    tar.add('/tmp/tea/workspace/archives/keterangan_tea.txt', arcname='keterangan_tea.txt')
                    tar.close()
                else:
                    pass
            else:
                GLib.idle_add(save.destroy)

        class Fetch(AcquireProgress):
            def __init__(self):
                AcquireProgress.__init__(self)
                self.keep_the_download = True
                # self.outer.progress_window.show_all()

            def pulse(self, owner):
                AcquireProgress.pulse(self, owner)
                # print(dir(owner.items[0]))
                # print(owner.items[0].destfile)
                print(self.current_bytes / self.total_bytes)
                GLib.idle_add(progress_bar.set_fraction, self.current_bytes / self.total_bytes)
                text = 'Downloading ' + apt_pkg.size_to_str(self.current_bytes) + 'B of ' + apt_pkg.size_to_str(
                    self.total_bytes) + 'B' + \
                    '\n' + apt_pkg.size_to_str(self.current_cps) + 'B/s '
                GLib.idle_add(label_.set_text, text)
                print('keep_the_download '+str(self.keep_the_download))
                return self.keep_the_download
                # https://stuff.mit.edu/afs/athena/system/i386_deb50/os/usr/share/doc/python-apt/html/apt/progress.html

            def stop_download(self, *args):
                self.keep_the_download = False


            def stop(self):
                # label.set_text('Download Stopped')
                # report = 'Failed while downloading:\n'
                # for i in package_error:
                #     report += i+'\n'
                # label.set_text(report)
                global done
                # =======
                for pkg in changes:
                    if not pkg.name+'_'+pkg.candidate.version.replace(':', '%3a')+'_'+pkg.candidate.architecture+'.deb' in os.listdir('/var/cache/apt/archives/'):
                        package_error.append(pkg.name+'_'+pkg.candidate.version.replace(':', '%3a')+'_'+pkg.candidate.architecture+'.deb')
                # =======
                if package_error:
                    done = False
                    print("done false")

                else:
                    GLib.idle_add(proceed2)

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

            def stop(self, *args):
                self._stop()

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
                hide_progress()

        if cache.required_download != 0:
            progress = Fetch()
            apt_thread = Thread(progress)
            apt_thread.start()
            progress_cancel.connect('clicked', progress.stop_download)
        else:
            proceed2()
        gc.collect()

    def hide_progress_window(self, *args):
        # try:
        #     self.progress_window.remove(self.progress_window.get_children()[0])
        # except IndexError:
        #     pass

        self.progress_window.hide()
        return True


if __name__ == "__main__":
    user = os.path.expanduser('~').split('/')[-1]
    print('user: ' + user)
    GObject.threads_init()
    if os.getuid() is 0:
        try:
            TeaMaker()
            Gtk.main()
        except KeyboardInterrupt:
            exit()
    else:
        print('must be root')
        warning = Gtk.MessageDialog(None,
                                    Gtk.DialogFlags.MODAL,
                                    Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK,
                                    'Only superuser can summon the program')
        warning.run()
        warning.destroy()
