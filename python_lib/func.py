"""
Contains functional programming style methods
"""
from functools import partial
from itertools import chain


def take(c, *items):
    """
    Takes the specified items from collection c, creating a new collection
    :param c: The collection to take the items from
    :param items: The items to take
    :return: the new collection

    >>> take([1, 2, 3], 0, 2)
    [1, 3]
    >>> take((1, 2, 3), 1)
    (2,)
    >>> take({"a": 1, "b": 2, "c": 3}, "a", "c")
    {'a': 1, 'c': 3}
    """
    if isinstance(c, tuple):
        return tuple(c[i] for i in items)
    elif isinstance(c, list):
        return [c[i] for i in items]
    elif isinstance(c, dict):
        return {i: c[i] for i in items}


def is_list_type(o):
    """
    Returns true if this is a list type.
    :param o: item to check if is list
    :return: true if is list

    >>> is_list_type(frozenset())
    True
    >>> is_list_type(list())
    True
    >>> is_list_type(set())
    True
    >>> is_list_type(tupe())
    True
    >>> is_list_type("")
    False
    >>> is_list_type(None)
    False
    """
    return isinstance(o, (frozenset, list, set, tuple,))


def list_to_dict(key, *l):
    """
    Transforms a list to a dict using key to determine what key to use
    :param l: list to transform
    :param key: If callable, gets call with item and should return key
                If list, zip together in a dict
                Else, use index accessor with the value to get the key
    :return: dict created from list

    >>> list_to_dict(0, [['one', 'two', 'three'], ['four', 'five', 'six']])
    {'four': ['four', 'five', 'six'], 'one': ['one', 'two', 'three']}
    >>> list_to_dict('id', [{'id': 0, 'one': 1, 'two': 2, 'three': 3}, {'id': 10, 'four': 4, 'five': 5, 'six': 6}])
    {0: {'three': 3, 'id': 0, 'two': 2, 'one': 1}, 10: {'four': 4, 'six': 6, 'five': 5, 'id': 10}}
    """

    chained = chain(*l)
    if is_list_type(key):
        return dict(zip(key, chained))
    else:
        output = {}
        for item in chained:
            k = key(item) if callable(key) else item[key]
            output[k] = item
        return output


def dict_to_list(keys, *dicts):
    """
    Transforms a dict to a list using the given keys
    :param keys: If empty, uses the sorted keys from the dict, else
                If list, takes the values of the keys from the list
    :param dicts: dicts to transform
    :return: dict created from list

    >>> dict_to_list(None, {'a': 1, 'b': 2, 'c': 3}, {'d': 4, 'e': 5, 'f': 6})
    [[1, 2, 3], [4, 5, 6]]
    >>> dict_to_list(['a', 'd'], {'a': 1, 'b': 2, 'c': 3}, {'d': 4, 'e': 5, 'f': 6})
    [[1], [4]]
    """
    if not keys:
        keys = sorted(list(x for x in chain(*[d.keys() for d in dicts])))

    out = []
    for d in dicts:
        out.append([d[k] for k in keys if k in d])
    return out


def flatten_list(l):
    """
    Flattens the list recursively

    :param l: This list to flatten
    :return: flattened list

    >>> flatten_list([1, [2, [3, 4, [5, 6]], 7], 8, [9, 1], 2, 3])
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3]
    """
    output = []
    for item in l:
        if is_list_type(item):
            output.extend(flatten_list(item))
        else:
            output.append(item)
    return output


def flatten_dict(d, concat="_"):
    """
    Flatten the dictionary, concatenating the keys
    :param d: dictionary to flatten
    :param concat: If callable, takes key and new key and should return
                   a new unique hashable object
                   If else, concatenates using add operator
    :return: Flattened dict

    >>> flatten_dict(dict(a=1, b=dict(c=2, d=dict(e=3, f1=dict(f=4)), g=dict(h=5)), j=6, k=7))
    {'a': 1, 'j': 6, 'k': 7, 'b_c': 2, 'b_d_e': 3, 'b_d_f1_f': 4, 'b_g_h': 5}
    >>> flatten_dict(dict(a=1, b=dict(c=2, d=dict(e=3))), concat=lambda k, n: k + '$' + n)
    {'a': 1, 'b$d$e': 3, 'b$c': 2}
    """

    output = {}
    for k, v in d.iteritems():

        if not isinstance(v, dict):
            output[k] = v
        else:
            flat_child = flatten_dict(v, concat=concat)
            for child_k, child_v in flat_child.iteritems():
                if callable(concat):
                    new_k = concat(k, child_k)
                else:
                    new_k = k + concat + child_k

                output[new_k] = child_v

    return output


def filter_all(fn, *l):
    """
    Runs the filter function on all items in a list of lists
    :param fn: Filter function
    :param l: list of lists to filter
    :return: list of filtered lists

    >>> filter_all(lambda x: x != "", ['a'], ['b'], [""], ["d"])
    [['a'], ['b'], [], ['d']]
    """
    return [filter(fn, lst) for lst in chain(*l)]


def item_split(split_fn, *l):
    """
    Splits lists into multiple lists based on a function
    working against each item in the list.

    NOTE: The split_fn must return the same number of rows every time,
    or it'll only take the first n items, where n is the minimum number
    of rows returned by split_fn!

    :param split_fn: Function to run to split items. # of items returned
                     maps to each list. Returning 4 items makes 4 lists
    :param l: List to split
    :return: list of lists containing the split items

    >>> item_split(lambda x: x.split('_'), ['a_b'], ['c_d'])
    [('a', 'c'), ('b', 'd')]
    >>> item_split(lambda x: x.split('_'), ['a_b'], ['c_d'], ['e'])
    [('a', 'c', 'e')]
    """
    return zip(*map(split_fn, list(chain(*l))))


def transform_keys(transform, d):
    """
    Transforms the keys in a dict.

    :param transform: If method, calls with key and value, returns new key
                      If dict, maps keys to key values for new key
                      If list, only returns dict with specified keys
                      Else returns original dict
    :param d: dictionary on which we're transforming keys, or list of dicts

    :return: Dictionary with transformed keys

    >>> transform_keys(lambda k, v: k.replace('o', '0'), dict(one=1, two=2))
    {'tw0': 2, '0ne': 1}
    >>> transform_keys({'one': 1}, dict(one=1, two=2))
    {1: 1, 'two': 2}
    >>> transform_keys(['one'], dict(one=1, two=2))
    {'one': 1}
    >>> transform_keys(None, dict(one=1, two=2))
    {'two': 2, 'one': 1}
    """
    if isinstance(d, list):
        return [transform_keys(transform, i) for i in d]

    if callable(transform):
        return {transform(k, v): v for k, v in d.iteritems()}
    elif isinstance(transform, dict):
        return {transform.get(k, k): v for k, v in d.iteritems()}
    elif isinstance(transform, list):
        return {k: v for k, v in d.iteritems() if k in transform}
    else:
        return d
