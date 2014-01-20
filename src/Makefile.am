bin_PROGRAMS = melodia-daemon
scriptsdir = $(pkglibdir)
scripts_SCRIPTS = interface.py playlist.py main.py
scripts_DATA = interface.glade
melodia_daemon_SOURCES = player.c

install-exec-hook:
	$(LN_S) $(scriptsdir)/main.py $(bindir)/melodia

uninstall-local:
	[ -f $(bindir)/melodia ] && rm $(bindir)/melodia
