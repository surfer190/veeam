'''
Errors for the Veeam Client

Having a root exception lets consumers of your API catch exceptions you raise on purpose. 
'''

class VeeamError(Exception):
    '''
    Base-class for all exceptions raised by veeam
    '''
    def __init__(self, message=None, errors=None):
        if errors:
            message = ', '.join(errors)

        self.errors = errors

        super().__init__(message)


class NoConfigError(VeeamError):
    '''
    Error for no Config Found
    '''
    pass


class LoginFailError(VeeamError):
    '''
    Login failed
    '''
    pass

class LoginFailSessionKeyError(VeeamError):
    '''
    Login faied the session key is not in the login response headers
    '''
    pass
