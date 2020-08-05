from django.utils.deprecation import MiddlewareMixin

from mes.conf import PROJECT_API_TREE
from production.utils import OpreationLogRecorder


class DisableCSRF(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        setattr(request, '_dont_enforce_csrf_checks', True)



class OperationLogRecordMiddleware(MiddlewareMixin):


    def process_view(self, request, view_func, view_args, view_kwargs):
        method = request.method
        try:
            if method.lower() in ["put", "post", "delete", "patch"]:
                module =  request.path.split("/")[3]
                api = request.path.split("/")[4]
                if module in PROJECT_API_TREE:
                    if api in PROJECT_API_TREE[module]:
                        body = request.POST.dict()
                        params = request.GET.dict()
                        content = {}
                        content.update(url=request.get_full_path(), method=method, body=body, params=params, user=request.user.username)
                        equip_no = body.get("equip_no")
                        OpreationLogRecorder(equip_no=equip_no, content=content).log_recoder()
        except Exception as e:
            pass