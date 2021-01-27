import inspect
from enum import EnumMeta
from typing import Any, Type, TypeVar, _GenericAlias

import grpc

from protobuf_gen.const import ATOMS


class Service:
    stub_cls: Any = None

    def __init__(self, channel: grpc.Channel):
        self.channel = channel
        self.stub = self.stub_cls(self.channel)


T = TypeVar('T')
B = TypeVar('B')


class Message:
    pb_cls: Type[T] = None
    __slots__ = []

    def __eq__(self, other):
        if isinstance(other, Message):
            if self.__slots__ != other.__slots__:
                return False
            else:
                for n in self.__slots__:
                    if getattr(self, n) != getattr(other, n):
                        return False
                return True
        else:
            return False

    def to_pb(self, inst=None) -> T:
        if inst is None:
            inst = self.pb_cls()

        try:
            for n, t in zip(self.__slots__, self.get_slot_types()):
                val = getattr(self, n)

                if t in ATOMS:
                    setattr(inst, n, val)
                elif inspect.isclass(t) and issubclass(t, Message):
                    if val is not None:
                        val.to_pb(getattr(inst, n))
                elif (inspect.isclass(t) and issubclass(t, EnumMeta)) or issubclass(type(t), EnumMeta):
                    setattr(inst, n, val.value)
                elif isinstance(t, _GenericAlias) and t._name == 'List':
                    st = t.__args__[0]

                    val_inst = getattr(inst, n)
                    for i, x in enumerate(val):
                        if st in ATOMS:
                            val_inst.append(x)
                        elif inspect.isclass(st) and issubclass(st, Message):
                            added = val_inst.add()
                            x.to_pb(added)
                        elif (inspect.isclass(st) and issubclass(st, EnumMeta)) or issubclass(type(st), EnumMeta):
                            val_inst.append(x.value)
                        else:
                            assert False, (t, st, val)
                else:
                    assert False, (t, val)
        except:
            raise ValueError(f'While serializing {self}')

        return inst

    def __repr__(self):
        flds = [f'{x}={repr(getattr(self, x))}' for x in self.__slots__]

        flds = ', '.join(flds)

        return f'{self.__class__.__name__}({flds})'

    @classmethod
    def get_slot_types(cls):
        return []

    @classmethod
    def _from_pb_type(cls, t, val):
        if t in ATOMS:
            return val
        elif inspect.isclass(t) and issubclass(t, Message):
            return t.from_pb(val)
        elif (inspect.isclass(t) and issubclass(t, EnumMeta)) or issubclass(type(t), EnumMeta):
            return t(val)
        elif isinstance(t, _GenericAlias) and t._name == 'List':
            return [cls._from_pb_type(t.__args__[0], x) for x in val]
        else:
            assert False, (t, val)

    @classmethod
    def from_pb(cls, inst):
        kwargs = {}

        for n, t in zip(cls.__slots__, cls.get_slot_types()):
            kwargs[n] = cls._from_pb_type(t, getattr(inst, n))

        return cls(**kwargs)
