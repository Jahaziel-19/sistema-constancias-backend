from django.urls import path

from uh_documentos.public_views import DocumentoPublicoRetrieveView

urlpatterns = [
    path("documentos/<str:folio>/", DocumentoPublicoRetrieveView.as_view(), name="documento-publico"),
]
