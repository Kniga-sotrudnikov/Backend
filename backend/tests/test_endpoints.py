from rest_framework.views import APIView, Response

from accounts.permissions import IsHR, IsOwnerOrHR


class Obj:
    def __init__(self, user_id):
        self.user_id = user_id


class IsHRView(APIView):
    permission_classes = [IsHR]

    def get(self, request):
        return Response()


class IsOwnerOrHRView(APIView):
    permission_classes = [IsOwnerOrHR]

    def get(self, request, user_id=None):
        self.check_object_permissions(request, Obj(user_id))
        return Response()

    def post(self, request, user_id=None):
        self.check_object_permissions(request, Obj(user_id))
        return Response()
