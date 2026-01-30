# jupyter_config/jupyter_server_config.py

c = get_config()

# Sicherheit abschalten (Token & Passwort leer lassen)
c.ServerApp.token = ''
c.ServerApp.password = ''

# Zugriff erlauben
c.ServerApp.ip = '127.0.0.1'
c.ServerApp.allow_origin = '*'
c.ServerApp.disable_check_xsrf = True

# Browser automatisch öffnen (optional, setze auf False wenn es nervt)
c.ServerApp.open_browser = True

# Root-Verzeichnis setzen (damit man nicht aus dem Projekt-Ordner raus kann)
# c.ServerApp.root_dir = '...' # Optional