
class NoConfigError(ValueError):
    '''
    Error for no Config Found
    '''
    pass


class LoginFailError(ValueError):
    '''
    Login failed
    '''
    pass

class LoginFailSessionKeyError(ValueError):
    '''
    Login faied the session key is not in the login response headers
    '''
    pass
