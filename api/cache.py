"""Sistema de cache com Redis."""
import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from api.config import Settings


class CacheManager:
    """Gerenciador de cache com Redis."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = REDIS_AVAILABLE
        self._client: Optional[redis.Redis] = None
        
        if self.enabled:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # Testa conexão
                self._client.ping()
                print("✓ Cache Redis conectado")
            except Exception as e:
                print(f"⚠ Cache Redis indisponível: {e}")
                self.enabled = False
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Gera chave única para cache."""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"ans:{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Recupera valor do cache."""
        if not self.enabled or not self._client:
            return None
        
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"⚠ Erro ao ler cache: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Armazena valor no cache."""
        if not self.enabled or not self._client:
            return False
        
        try:
            ttl = ttl or self.settings.cache_ttl
            serialized = json.dumps(value)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"⚠ Erro ao gravar cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache."""
        if not self.enabled or not self._client:
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            print(f"⚠ Erro ao deletar cache: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão."""
        if not self.enabled or not self._client:
            return 0
        
        try:
            keys = self._client.keys(f"ans:{pattern}:*")
            if keys:
                return self._client.delete(*keys)
        except Exception as e:
            print(f"⚠ Erro ao limpar cache: {e}")
        
        return 0
    
    def health_check(self) -> str:
        """Verifica saúde do cache."""
        if not self.enabled:
            return "disabled"
        
        if not self._client:
            return "not_configured"
        
        try:
            self._client.ping()
            return "ok"
        except Exception:
            return "error"


def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator para cachear resultados de funções.
    
    Usage:
        @cached("operadoras_search", ttl=300)
        def search_operadoras(query: str):
            # expensive operation
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Tenta obter do cache
            cache_manager = kwargs.get('_cache_manager')
            if not cache_manager:
                return func(*args, **kwargs)
            
            cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            cached_value = cache_manager.get(cache_key)
            
            if cached_value is not None:
                print(f"✓ Cache hit: {prefix}")
                return cached_value
            
            # Executa função e cacheia resultado
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            print(f"✓ Cache miss: {prefix} (cached)")
            
            return result
        
        return wrapper
    return decorator
