from django.db.models import QuerySet
from django.views.generic import ListView


class ListViewClass(ListView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        search_form = kwargs.get('search_form', None)

        filter_parameters = ''

        if search_form:
            context['search_form'] = search_form()
            search_form = search_form(self.request.GET)

            if search_form.is_valid():
                context['search_form'] = search_form
                data = search_form.cleaned_data
                filter_parameters = ''
                for key, value in data.items():
                    if value:
                        if isinstance(value, QuerySet):
                            for ele in value:
                                filter_parameters += '{}={}&'.format(key, ele.pk)
                        else:
                            filter_parameters += '{}={}&'.format(key, value)
                context['search_form'] = search_form

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (
                                                  order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['filter_parameters'] = filter_parameters
        context[
            'filter_parameters_with_order_by'] = filter_parameters_with_order_by

        context['expand_accordion'] = 'show'

        return context

    def get_order_by(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            elif direction == 'des':
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        return order_by
