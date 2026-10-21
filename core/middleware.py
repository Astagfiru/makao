import secrets

from django.http import HttpRequest, HttpResponse

# Яндекс.Карта — единственное, что встраивается с чужого сайта (и только по клику посетителя).
CSP_TEMPLATE = (
    "default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; frame-src https://yandex.ru https://*.yandex.ru; "
    "form-action 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'"
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class SecurityHeadersMiddleware:
    """Content-Security-Policy с nonce для встроенного скрипта темы и Permissions-Policy.

    Админку не трогаем: у Django admin свои скрипты и стили.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        is_html = response.get("Content-Type", "").startswith("text/html")
        if is_html and not request.path.startswith("/admin/"):
            response.setdefault("Content-Security-Policy", CSP_TEMPLATE.format(nonce=request.csp_nonce))
        return response
