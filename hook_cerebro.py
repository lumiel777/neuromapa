import os
import sys

try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import hook_evento
    hook_evento.main()
except Exception:
    pass
sys.exit(0)
