import json
import time
import logging
import traceback

from django.http.response import HttpResponseNotFound
api_log = logging.getLogger('api_log')
error_log = logging.getLogger('error_log')


def api_recorder(func):
    def inner(request, *args, **kwargs):
        if 'pk' in kwargs:
            try:
                pk = int(kwargs.get('pk'))
                if not (0 < pk <= (1 << 32)):
                    return HttpResponseNotFound(content="非法资源")
            except Exception as e:
                error_log.error(e)
                return HttpResponseNotFound(content="非法资源")

        value = {
            'path': request.get_full_path(),
        }
        try:
            value.update(post=request.POST.dict())
            value.update(get=request.GET.dict())
            if request.content_type == 'application/json':
                value.update(body=json.loads(request.body))
        except Exception as e:
            error_log.error(e)
        start = time.time()
        try:
            resp = func(request, *args, **kwargs)
            return resp
        except Exception:
            error_log.error(traceback.format_exc())
            raise
        finally:
            finish = time.time()
            value = json.dumps(value, ensure_ascii=False)
            api_log.info(','.join(('SEND', 'http', '[%s,%s,%s,%s,%s]' % (request.method, request.user,
                                                                         request.path, round(finish - start, 3),
                                                                         value))))
    return inner
