"""
Contains python data structures
"""

import copy
import csv
import json
import subprocess
import tempfile

import func


class DynamicObject(object):
    """
    Object that does not throw exceptions when working with attributes that it does not
    currently contain.  Can specify a default for attributes that do not exist.
    """
    def __init__(self, default=None, **kwargs):
        self._default=default
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def __getattr__(self, item):
        return self._default

    def __delattr__(self, item):
        try:
            delattr(self, item)
        except AttributeError:
            pass


O = DynamicObject


class AttrDict(dict):
    """
    Dictionary class that allows for dot notation when accessing members.
    If dict contains sub-dicts, those dicts will be converted to AttrDict
    so that the sub members can be accessed using dot notation as well.
    Example: dict1.dict2.value
    """

    def __init__(self, initial=None, dict_default=None, **kwargs):
        super(AttrDict, self).__setattr__('_dict_default', dict_default)
        super(AttrDict, self).__init__(initial or {}, **kwargs)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            return self._dict_default if '_dict_default' in self.__dict__ else None

    def __setitem__(self, key, value):
        if type(value) == dict:
            # Make so sub-dicts can be accessed using dot notation
            value = AttrDict(value)
        super(AttrDict, self).__setitem__(key, value)

    def __setattr__(self, key, value):
        if key in dir(self):
            super(AttrDict, self).__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __delattr__(self, item):
        if item in dir(self):
            super(AttrDict, self).__delattr__(item)
        else:
            self.__delitem__(item)

    def add_member(self, name, value):
        """
        To get around default setattr behavior to add a member such as a method to this class,
        you can call this method.
        """
        super(AttrDict, self).__setattr__(name, value)


D = AttrDict


class Table(object):
    """
    Table models a lean data table.  Supports filtering, mapping, and joins.
    """

    def __init__(self, data, columns=None):
        self.columns = columns
        self._raw_data = data
        if not func.is_list_type(data):
            data = [data]

        if not data:
            return

        if func.is_list_type(data[0]):
            if not columns:
                raise Exception("Headers must be specified if passing a list of data")

            self._data = func.list_to_dict(columns, data)
        elif isinstance(data[0], dict):
            if not columns:
                self.columns = list(data[0].keys())

            self._data = [self._initialize_row(row) for row in data]
        else:
            raise Exception("Data type %s not supported for a row", type(data[0]))

    @staticmethod
    def from_csv(f):
        is_path = False
        if isinstance(f, str):
            is_path = True
            f = open(f, mode='r')
        reader = csv.DictReader(f)
        table = Table([x for x in reader], reader.fieldnames)
        if is_path:
            f.close()
        return table

    @staticmethod
    def from_json(f):
        is_path = False
        if isinstance(f, str):
            is_path = True
            f = open(f, mode='r')
        data = json.load(f)
        if data:
            table = Table(data, list(data[0].keys()))
        else:
            table = Table()
        if is_path:
            f.close()
        return table

    @staticmethod
    def from_clipboard(self):
        data = subprocess.check_output('pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')
        with tempfile.NamedTemporaryFile() as t:
            t.write(data)

        try:
            return Table.from_json(t.name)
        except:
            return Table.from_csv(t.name)


    def to_dicts(self):
        return copy.copy(self._data)

    def to_lists(self):
        return func.dict_to_list(self.columns, self._data)

    def _initialize_row(self, row):
        return func.take(row, *self.columns)

    def filter(self, fn):
        return Table(filter(fn, self._data), columns=self.columns)

    def map(self, fn):
        return Table(map(fn, self._data), columns=self.columns)

    def group(self, *columns):
        return self._group(self._data, self.unique(*columns), *columns)

    def _group(self, data, unique_data, columns):
        if not columns:
            return copy.copy(data)

        output = {}
        for unique in unique_data[0]:
            output[unique] = self._group([d for d in data if d[columns[0]] == unique], unique_data[1:], columns[1:])

    def unique(self, *columns):
        return [list(set(self[col]) for col in columns)]

    def aggregate(self, *group, **agg):
        data = [self._data]
        if group:
            data = func.flatten_dict(self.group(*group))

        table_data = []
        for d in data:
            output = func.take(d[0], *group)
            for col, fn in agg.items():
                output[col] = fn(col, func.take(d, col).values())

            table_data += output

        return Table(table_data, self.columns)

    def sort(self, cmp=None, key=None, reverse=False):
        output = sorted(copy.copy(self._data), cmp=cmp, key=key, reverse=reverse)
        return Table(output, self.columns)

    def join(self, table, left_on, right_on, how='left', default=None):
        if not table or not left_on or not right_on:
            raise Exception("Missing arguments to join. Table, left_on, and right_on must have values.")
        if not len(left_on) == len(right_on):
            raise Exception("Left on and right on args to join must be same length.")
        if isinstance(left_on, str):
            left_on = [left_on]
        if isinstance(right_on, str):
            right_on = [right_on]
        if any(l not in self.columns for l in left_on):
            raise Exception("Left on join field not in columns: " + ", ".join(self.columns))
        if any(r not in table.columns for r in right_on):
            raise Exception("Right on join field not in columns: " + ", ".join(table.columns))

        data = []
        for left in self._data:
            for right in table._data:
                matches = all(left[left_on[i]] == right[right_on[i]] for i in range(len(left_on)))
                if how == 'inner':
                    if matches:
                        new = self._join_column(left, right)
                        data.append(new)
                elif how == 'left':
                    if matches:
                        new = self._join_column(left, right)
                    else:
                        new = self._join_empty_column(table.columns, default, left)
                    data.append(new)
                elif how == 'outer':
                    if matches:
                        new = self._join_column(left, right)
                        data.append(new)
                    else:
                        new = self._join_empty_column(table.columns, default, left)
                        data.append(new)
                        new = self._join_empty_column(self.columns, default, right, suffix='right')
                        data.append(new)

        new_cols = copy.copy(self.columns)
        for right_col in table.columns:
            if right_col in new_cols:
                right_col = "_right"
            new_cols.append(right_col)

        return Table(data, new_cols)

    def _join_empty_column(self, columns, default, row, suffix="left"):
        new = copy.copy(row)
        for column in columns:
            if column in new:
                column += "_" + suffix
            new[column] = default
        return new

    def _join_column(self, left, right):
        new = copy.copy(left)
        for k, v in right.items():
            if k in left:
                k += "_right"
            new[k] = v
        return new

    def __getitem__(self, item):
        if callable(item):
            return [copy.copy(item(d)) for d in self._data]
        elif isinstance(item, str):
            if item not in self.columns:
                raise Exception("Table does not have column: " + item)
            return [copy.copy(d[item]) for d in self._data]
        elif isinstance(item, int):
            return copy.copy(self._data[item])
        elif func.is_list_type(item):
            if not all(isinstance(i, (str, int)) for i in item):
                raise Exception("List of columns to get item must be all of either string or int, cannot mix them")

            if isinstance(item[0], int):
                return Table([self[i] for i in item], columns=self.columns)
            elif isinstance(item[0], str):
                return Table([func.take(d, *item) for d in self._data], columns=item)

    def __setitem__(self, key, value):
        if isinstance(key, str):
            for item in self._data:
                item[key] = value
            if not key in self.columns:
                self.columns.append(key)
        elif isinstance(key, int):
            self._data[key] = self._initialize_row(value)
        elif func.is_list_type(key):
            for k in key:
                self[k] = value

    def __delitem__(self, key):
        if isinstance(key, str):
            for item in self._data:
                del item[key]
            del self.columns[self.columns.index(key)]
        elif isinstance(key, int):
            del self._data[key]
        elif func.is_list_type(key):
            for k in key:
                del self[k]

    def __iter__(self):
        for d in self._data:
            yield copy.copy(d)

    def to_csv(self, f):
        is_path = False
        if isinstance(f, str):
            is_path = True
            f = open(f, mode='w')
        writer = csv.DictWriter(f, self.columns)
        writer.writerows(self._data)
        if is_path:
            f.close()

    def __repr__(self):
        return "Table [{headers}] (Rows: {num_rows})".format(headers=", ".join(self.columns), num_rows=len(self._data))

    def __str__(self):
        return json.dumps(self._data, indent=4, sort_keys=True)

# class DataTable(object):
#
#     class DataColumn(AttrDict):
#
#         def __init__(self, table, dict_default='', data=None, **kwargs):
#             self.table = table
#
#             super(DataTable.DataColumn, self).__init__(
#                 initial=data, dict_default=dict_default, **kwargs
#             )
#
#         @property
#         def cells(self):
#             return [cell for _, cell in self]
#
#         def get_default_value(self, value):
#             if self.default_value:
#                 return self.default_value
#             elif self.table.meta.default_value:
#                 return self.table.default_value
#             elif self.type == "decimal":
#                 return Decimal()
#             elif self.type == "int" or self.type == "long":
#                 return 0
#             elif self.type == "bool" or self.type == "string":
#                 return ''
#             else:
#                 return value
#
#         def index(self):
#             return self.table.columns.indexOf(self)
#
#         def __iter__(self):
#             for row in self.table.rows:
#                 for cell in row.cells:
#                     if cell.column == self:
#                         yield row, cell
#
#     class DataRow(AttrDict):
#
#         def __init__(self, table, data_obj, cells=None, dict_default='', data=None, **kwargs):
#             self.table = table
#             self.data_obj = data_obj
#             self.cells = cells or ()
#
#             super(DataTable.DataRow, self).__init__(
#                 initial=data, dict_default=dict_default, **kwargs
#             )
#
#         def get_date_cell(self):
#             for cell in self.cells:
#                 if cell.type == "date" or cell.type == "datetime":
#                     return cell
#             return None
#
#         def index(self):
#             return self.table.all_rows.indexOf(self)
#
#         def __iter__(self):
#             return (cell for cell in self.cells)
#
#     class DataCell(AttrDict):
#
#         def __init__(self, table, row, column, dict_default='', data=None, **kwargs):
#             self.table = table
#             self.row = row
#             self.column = column
#
#             super(DataTable.DataCell, self).__init__(
#                 initial=data, dict_default=dict_default, **kwargs
#             )
#
#         @property
#         def prefix(self):
#             return self.column.prefix or ''
#
#         @property
#         def suffix(self):
#             return self.column.suffix or ''
#
#         @property
#         def precision(self):
#             return self.column.precision or 2
#
#         @property
#         def type(self):
#
#             if isinstance(self.value, datetime.datetime):
#                 return "datetime"
#             elif isinstance(self.value, datetime.date):
#                 return "date"
#             elif isinstance(self.value, Decimal):
#                 return "decimal"
#             elif isinstance(self.value, int):
#                 return "int"
#             elif isinstance(self.value, long):
#                 return "long"
#             elif isinstance(self.value, type(None)):
#                 return "null"
#             elif isinstance(self.value, basestring):
#                 return "string"
#             elif isinstance(self.value, bool):
#                 return "bool"
#             else:
#                 raise TypeError("Unknown type specified for DataCell")
#
#         def index(self):
#             return self.row.cells.indexOf(self)
#
#     def __init__(self, data_objects, columns, total_data_object=None,
#                  table_meta=None, row_meta=None, cell_meta=None):
#
#         self.data_objects = data_objects
#         self.total_data_object = total_data_object
#
#         self._table_meta = table_meta or {}
#         self._row_meta = row_meta or {}
#         self._cell_meta = cell_meta or {}
#         self.meta = AttrDict(self._table_meta)
#
#         self.columns = tuple([self._build_column(column) for column in columns])
#
#         self._build_table()
#
#     @property
#     def columns_by_name(self):
#         return {col.name: col for col in self.columns if col.name}
#
#     @property
#     def cells(self):
#         return [cell for _, _, cell in self]
#
#     def _build_table(self):
#
#         rows = []
#         if self.data_objects:
#             for data_obj in self.data_objects:
#                 row = self._build_row(data_obj)
#                 row.cells = tuple([self._build_cell(row, column, data_obj) for column in self.columns])
#                 rows.append(row)
#
#         self.rows = tuple(rows)
#
#         self._build_total()
#
#     def _build_total(self):
#         self.total_row = None
#         if self.total_data_object:
#             self.total_row = self._build_total_row(self.total_data_object)
#             cells = tuple([self._build_total_cell(self.total_row, column,
#                                                   self.total_data_object)
#                            for column in self.columns])
#             self.total_row.cells = cells
#
#             self.all_rows = tuple(self.rows + (self.total_row,))
#
#         else:
#             self.all_rows = tuple(self.rows)
#
#     def _build_column(self, column):
#         return self.DataColumn(self, data=column)
#
#     def _build_total_row(self, data_obj, cells=None):
#         return self._build_row(data_obj, cells=cells)
#
#     def _build_row(self, data_obj, cells=None):
#         return self.DataRow(self, data_obj, cells=cells, data=self._row_meta)
#
#     def _build_total_cell(self, row, column, data_obj):
#         return self._build_cell(row, column, data_obj, column.total_value)
#
#     def _build_cell(self, row, column, data_obj, value_getter=None):
#         return self.DataCell(
#             self,
#             row,
#             column,
#             data=self._cell_meta,
#             value=self._get_cell_value(data_obj, column, value_getter or column.value)
#         )
#
#     def _get_cell_value(self, obj, column, value_getter):
#
#         if callable(value_getter):
#             if column.value_args:
#                 value = value_getter(obj, **column.value_args) # Make callback if given
#             else:
#                 value = value_getter(obj)
#             return self._coerce_value(column, value)
#
#         if isinstance(value_getter, basestring): # Try dict or attr lookup if string first
#             try:
#                 value = self._get_cell_value_from_string(obj, value_getter)
#                 return self._coerce_value(column, value)
#             except:
#                 return value_getter
#
#         return value_getter # Assume value passed in is static value
#
#     def _get_cell_value_from_string(self, obj, value_getter):
#         val = obj
#         # Allow . access to other values
#         for attr in value_getter.split('.'):
#             # Check dict/list val first
#             try:
#                 val = val[attr]
#             except (KeyError, IndexError, TypeError):
#                 # Not dict/list val, use getattr
#                 val = getattr(val, attr)
#
#             # Allow traversing callables
#             if callable(val):
#                 val = val()
#
#         return val
#
#     def _coerce_value(self, column, value):
#         type = column.type
#         if not value:
#             # Use Default value if the value is None
#             return column.get_default_value(value)
#
#         if column.coerce_value:
#             # If column defines its own value coercion, use that
#             return column.coerce_value(value)
#
#         if type == "datetime":
#             if not column.output_format:
#                 column.output_format = "m/d/Y h:i A"
#             if isinstance(value, basestring):
#                 formatter = column.input_format or '%Y-%m-%d %H:%M:%S.%f'
#                 return datetime.datetime.strptime(value, formatter)
#             if isinstance(value, int) or isinstance(value, long) or isinstance(value, Decimal):
#                 return datetime.datetime.fromtimestamp(Decimal(str(value)))
#         elif type == "date":
#             if not column.output_format:
#                 column.output_format = "m/d/Y"
#
#             if isinstance(value, basestring):
#                 formatter = column.input_format or '%Y-%m-%d'
#                 return datetime.datetime.strptime(value, formatter)
#             if isinstance(value, int) or isinstance(value, long) or isinstance(value, Decimal):
#                 return datetime.datetime.fromtimestamp(Decimal(str(value)))
#         elif type == "int":
#             return int(value)
#         elif type == "long":
#             return long(value)
#         elif type == "decimal":
#             # Add the precision to round decimal to if not found
#             if not column.precision or not isinstance(column.precision, int):
#                 column.precision = 2
#             return Decimal(str(value))
#         elif type == "bool":
#             return bool(value)
#         elif type == "null":
#             return None
#         elif type == "string":
#             return unicode(value)
#
#         return value
#
#     def __len__(self):
#         return len(self.rows)
#
#     def __iter__(self):
#         for row in self.rows:
#             for column in self.columns:
#                 for cell in row.cells:
#                     yield row, column, cell

