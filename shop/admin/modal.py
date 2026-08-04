from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse


class RelatedObjectModalAdminMixin:
    modal_query_parameter = "_modal"
    modal_response_template = "admin/related_object_modal_response.html"

    def is_related_modal_request(self, request: HttpRequest) -> bool:
        return (
            request.GET.get(self.modal_query_parameter) == "1"
            or request.POST.get(self.modal_query_parameter) == "1"
        )

    def get_related_modal_payload(self, obj, *, action: str) -> dict:
        return {
            "type": "admin-related-object-saved",
            "action": action,
            "model": obj._meta.label_lower,
            "objectId": str(obj.pk),
            "objectLabel": str(obj),
            "message": f"{obj._meta.verbose_name.capitalize()} saved successfully.",
        }

    def get_related_modal_response(
        self,
        request: HttpRequest,
        obj,
        *,
        action: str,
    ) -> TemplateResponse:
        return TemplateResponse(
            request,
            self.modal_response_template,
            {
                "modal_payload": self.get_related_modal_payload(
                    obj,
                    action=action,
                ),
            },
        )

    def response_add(self, request, obj, post_url_continue=None):
        if self.is_related_modal_request(request):
            return self.get_related_modal_response(
                request,
                obj,
                action="add",
            )

        return super().response_add(
            request,
            obj,
            post_url_continue,
        )

    def response_change(self, request, obj):
        if self.is_related_modal_request(request):
            return self.get_related_modal_response(
                request,
                obj,
                action="change",
            )

        return super().response_change(request, obj)

    def add_view(
        self,
        request,
        form_url="",
        extra_context=None,
    ) -> HttpResponse:
        response = super().add_view(
            request,
            form_url=form_url,
            extra_context=extra_context,
        )
        return self._allow_same_origin_frame(request, response)

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ) -> HttpResponse:
        response = super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=extra_context,
        )
        return self._allow_same_origin_frame(request, response)

    def _allow_same_origin_frame(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:
        if self.is_related_modal_request(request):
            response.headers["X-Frame-Options"] = "SAMEORIGIN"

        return response
