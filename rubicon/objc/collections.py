from .types import NSNotFound, NSRange
from .runtime import (
    NSArray, NSDictionary, NSMutableArray, NSMutableDictionary, ObjCClass, ObjCInstance, for_objcclass, ns_from_py,
    send_message
)


@for_objcclass(NSArray)
class ObjCListInstance(ObjCInstance):
    def __getitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(len(self))
            if step == 1:
                return self.subarrayWithRange(NSRange(start, stop-start))
            else:
                return ns_from_py([self.objectAtIndex(x) for x in range(start, stop, step)])

        if item < 0:
            item = len(self) + item
        if item >= len(self):
            raise IndexError('list index out of range')

        return self.objectAtIndex(item)

    def __len__(self):
        return send_message(self.ptr, 'count').value or 0

    def __iter__(self):
        for i in range(len(self)):
            yield self.objectAtIndex(i)

    def __contains__(self, item):
        return self.containsObject_(item)

    def __eq__(self, other):
        for a, b in zip(self, other):
            if a != b:
                return False
        return True

    def index(self, value):
        idx = self.indexOfObject_(value)
        if idx == NSNotFound:
            raise ValueError('%r is not in list' % value)
        return idx

    def count(self, value):
        return len([x for x in self if x == value])

    def copy(self):
        return self.objc_class.arrayWithArray_(self)


@for_objcclass(NSMutableArray)
class ObjCMutableListInstance(ObjCListInstance):
    def __setitem__(self, item, value):
        if isinstance(item, slice):
            arr = ns_from_py(value)
            if not isinstance(arr, NSArray):
                raise TypeError(
                    '{cls.__module__}.{cls.__qualname__} is not convertible to NSArray'
                    .format(cls=type(value))
                )

            start, stop, step = item.indices(len(self))
            if step == 1:
                self.replaceObjectsInRange(NSRange(start, stop-start), withObjectsFromArray=arr)
            else:
                indices = range(start, stop, step)
                if len(arr) != len(indices):
                    raise ValueError(
                        'attempt to assign sequence of size {} to extended slice of size {}'
                        .format(len(value), len(indices))
                    )

                for idx, obj in zip(indices, arr):
                    self.replaceObjectAtIndex(idx, withObject=obj)

            return

        if item < 0:
            item = len(self) + item
        if item >= len(self):
            raise IndexError('list assignment index out of range')

        self.replaceObjectAtIndex_withObject_(item, value)

    def __delitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(len(self))
            if step == 1:
                self.removeObjectsInRange(NSRange(start, stop-start))
            else:
                for idx in sorted(range(start, stop, step), reverse=True):
                    self.removeObjectAtIndex(idx)
            return

        if item < 0:
            item = len(self) + item
        if item >= len(self):
            raise IndexError('list assignment index out of range')

        self.removeObjectAtIndex_(item)

    def append(self, value):
        self.addObject_(value)

    def extend(self, values):
        for value in values:
            self.addObject_(value)

    def clear(self):
        self.removeAllObjects()

    def pop(self, item=-1):
        value = self[item]
        del self[item]
        return value

    def remove(self, value):
        del self[self.index(value)]

    def reverse(self):
        self.removeAllObjects  # this is a test
        new_contents = self.reverseObjectEnumerator().allObjects()
        self.removeAllObjects()
        self.addObjectsFromArray_(new_contents)

    def insert(self, idx, value):
        self.insertObject_atIndex_(value, idx)


@for_objcclass(NSDictionary)
class ObjCDictInstance(ObjCInstance):
    def __getitem__(self, item):
        v = self.objectForKey_(item)
        if v is None:
            raise KeyError(item)
        return v

    def __len__(self):
        return self.count

    def __iter__(self):
        for key in self.allKeys():
            yield key

    def __contains__(self, item):
        return self.objectForKey_(item) is not None

    def __eq__(self, other):
        if set(self.keys()) != set(other.keys()):
            return False
        for item in self:
            if self[item] != other[item]:
                return False

        return True

    def get(self, item, default=None):
        v = self.objectForKey_(item)
        if v is None:
            return default
        return v

    def keys(self):
        return self.allKeys()

    def values(self):
        return self.allValues()

    def items(self):
        for key in self.allKeys():
            yield key, self.objectForKey_(key)

    def copy(self):
        return ObjCClass('NSMutableDictionary').dictionaryWithDictionary_(self)


@for_objcclass(NSMutableDictionary)
class ObjCMutableDictInstance(ObjCDictInstance):
    no_pop_default = object()

    def __setitem__(self, item, value):
        self.setObject_forKey_(value, item)

    def __delitem__(self, item):
        if item not in self:
            raise KeyError(item)

        self.removeObjectForKey_(item)

    def clear(self):
        self.removeAllObjects()

    def pop(self, item, default=no_pop_default):
        if item not in self:
            if default is not self.no_pop_default:
                return default
            else:
                raise KeyError(item)

        value = self.objectForKey_(item)
        self.removeObjectForKey_(item)
        return value

    def popitem(self):
        key = self.allKeys().firstObject()
        value = self.objectForKey_(key)
        self.removeObjectForKey_(key)
        return (key, value)

    def setdefault(self, key, default=None):
        value = self.objectForKey_(key)
        if value is None:
            value = default
        if value is not None:
            self.setObject_forKey_(default, key)
        return value

    def update(self, new=None, **kwargs):
        if new is None:
            new = kwargs
        else:
            new = dict(new)

        for k, v in new.items():
            self.setObject_forKey_(v, k)
