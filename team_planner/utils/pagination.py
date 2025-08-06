from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict
import math


class CustomPageNumberPagination(PageNumberPagination):
    """Custom pagination class that matches frontend expectations."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        """Return paginated response in the format expected by frontend."""
        total_pages = math.ceil(self.page.paginator.count / self.page_size) if self.page.paginator.count > 0 else 1
        
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', total_pages),
            ('current_page', self.page.number),
            ('has_next', self.page.has_next()),
            ('has_previous', self.page.has_previous()),
            ('results', data)
        ]))
