from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from orders.services import import_products_from_yaml


class PartnerImportView(APIView):
    """
    View для импорта товаров из YAML файла.
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.type != 'shop':
            return Response(
                {'error': 'Только поставщик может импортировать товары'},
                status=status.HTTP_403_FORBIDDEN
            )

        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response({'error': 'Файл не предоставлен'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not uploaded_file.name.endswith(('.yaml', '.yml')):
            return Response({'error': 'Неверный формат файла. Ожидается .yaml или .yml'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            result = import_products_from_yaml(file_obj=uploaded_file, user=request.user)
        except ValueError as error:
            return Response(
                {'error': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'status': 'success',
                'message': 'Товары успешно импортированы',
                'shop': result['shop'],
                'imported_count': result['imported_count']
            },
            status=status.HTTP_201_CREATED
        )
