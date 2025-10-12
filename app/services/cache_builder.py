def user_aware_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
):
    """Build cache key that includes user ID."""
    from fastapi_cache.decorator import default_key_builder
    
    # Get the base key
    base_key = default_key_builder(func, namespace, request, response, *args, **kwargs)
    
    # Add user ID from kwargs (passed by Depends)
    user = kwargs.get("user")
    if user:
        return f"{base_key}:user:{user.id}"
    
    return base_key
