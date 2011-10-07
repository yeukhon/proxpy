def proxy_mangle_request(req):
    print req
    print '{POST}', req.getParams()
    print
    return req

def proxy_mangle_response(res):
    print res
    return res
