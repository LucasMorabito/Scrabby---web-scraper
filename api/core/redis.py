import hashlib
from fastapi import Request, Response
from api.security import get_current_username

def user_aware_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
):
    """
    Construye una llave de caché única combinando la URL, los filtros de búsqueda 
    y la sesión del usuario para evitar cruce de datos entre sesiones.
    """
    username = "guest"
    if request:
        try:
            # Extraemos quién hace la petición
            user = get_current_username(request)
            if user:
                username = user
        except Exception:
            pass
            
    query = request.url.query if request else ""
    path = request.url.path if request else ""
    
    # Armamos la cadena única y la hasheamos
    raw_key = f"{namespace}:{func.__name__}:{username}:{path}?{query}"
    return hashlib.md5(raw_key.encode()).hexdigest()