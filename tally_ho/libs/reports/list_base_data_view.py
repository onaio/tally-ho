"""
This module is to a data view response of type list; what BaseDataView is to
a data view response of type queryset
"""

from django_datatables_view.base_datatable_view import BaseDatatableView


def sort_list_of_dicts(data, order):
    # TODO - support for sorting on multiple attributes.
    first_term = order[0]
    reverse = False  # sort in ascending by default
    key_name = first_term
    if first_term.startswith('-'):
        key_name = first_term[1:]
        reverse = True

    return sorted(data, key=lambda item: item[key_name], reverse=reverse)


class NoneQsDatatableMixin(BaseDatatableView):
    """Json data based of list for datatables"""

    def ordering(self, qs):
        # Number of columns that are used in sorting
        sorting_cols = 0
        if self.pre_camel_case_notation:
            try:
                sorting_cols = int(self._querydict.get("iSortingCols", 0))
            except ValueError:
                sorting_cols = 0
        else:
            sort_key = "order[{0}][column]".format(sorting_cols)
            while sort_key in self._querydict:
                sorting_cols += 1
                sort_key = "order[{0}][column]".format(sorting_cols)

        order = []
        order_columns = self.get_order_columns()
        for i in range(sorting_cols):
            # sorting column
            sort_dir = "asc"
            try:
                if self.pre_camel_case_notation:
                    sort_col = int(
                        self._querydict.get("iSortCol_{0}".format(i))
                        )
                    # sorting order
                    sort_dir = self._querydict.get("sSortDir_{0}".format(i))
                else:
                    sort_col = int(
                        self._querydict.get("order[{0}][column]".format(i))
                        )
                    # sorting order
                    sort_dir = self._querydict.get("order[{0}][dir]".format(i))
            except ValueError:
                sort_col = 0

            sdir = "-" if sort_dir == "desc" else ""
            sortcol = order_columns[sort_col]

            if isinstance(sortcol, list):
                for sc in sortcol:
                    order.append("{0}{1}".format(sdir, sc.replace(".", "__")))
            else:
                order.append("{0}{1}".format(sdir, sortcol.replace(".", "__")))
        if order:
            return sort_list_of_dicts(qs, order)
        return qs

    def get_initial_queryset(self):
        return []

    def filter_queryset(self, qs):
        return qs

    def count_records(self, qs):
        return len(qs)

    def get_aggregate(self, qs):
        return None

    def get_context_data(self, *args, **kwargs):
        try:
            self.initialize(*args, **kwargs)

            # prepare columns data (for DataTables 1.10+)
            self.columns_data = self.extract_datatables_column_data()
            self.is_data_list = True
            if self.columns_data:
                self.is_data_list = False
                try:
                    int(self.columns_data[0]["data"])
                    self.is_data_list = True
                except ValueError:
                    pass

            # prepare list of columns to be returned
            self._columns = self.get_columns()

            # prepare initial queryset
            qs = self.get_initial_queryset()

            # store the total number of records (before filtering)
            total_records = self.count_records(qs=qs)

            # apply filters
            qs = self.filter_queryset(qs)

            # number of records after filtering
            total_display_records = self.count_records(qs=qs)

            # apply ordering
            qs = self.ordering(qs)

            # get aggregate here
            aggregate = self.get_aggregate(qs)

            # apply pagintion
            qs = self.paging(qs)

            # prepare output data
            if self.pre_camel_case_notation:
                aa_data = self.prepare_results(qs)

                ret = {
                    "sEcho": int(self._querydict.get("sEcho", 0)),
                    "iTotalRecords": total_records,
                    "iTotalDisplayRecords": total_display_records,
                    "aaData": aa_data,
                    }

            else:
                data = self.prepare_results(qs)

                ret = {
                    "draw": int(self._querydict.get("draw", 0)),
                    "recordsTotal": total_records,
                    "recordsFiltered": total_display_records,
                    "data": data,
                    }

            if aggregate:
                ret["aggregate"] = aggregate

            return ret
        except Exception as e:
            return self.handle_exception(e)
